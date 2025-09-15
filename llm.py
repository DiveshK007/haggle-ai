import os
import time
import requests
import json
from typing import Dict, Any, Optional
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential
from pydantic import ValidationError
from schemas import VendorResponse

# Load environment variables
load_dotenv()

def _with_retry(fn):
    def wrapper(*args, **kwargs):
        delays = [0.5, 1.0, 2.0]
        last_err = None
        for i in range(len(delays) + 1):
            try:
                return fn(*args, **kwargs)
            except Exception as e:
                last_err = e
                if i < len(delays):
                    print(f"[LLM RETRY] attempt {i + 1} failed: {e}. sleeping {delays[i]}s")
                    time.sleep(delays[i])
        raise last_err
    return wrapper

class LLMWrapper:
    """
    Wrapper class to handle both Ollama and OpenAI API calls
    Engine selection controlled by .env file
    """

    def __init__(self):
        self.engine = os.getenv("ENGINE", "ollama").lower()
        
        if self.engine == "openai":
            try:
                import openai
                self.openai_client = openai.OpenAI(
                    api_key=os.getenv("OPENAI_API_KEY")
                )
                self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
            except ImportError:
                raise Exception("OpenAI library not installed. Run: pip install openai")
                
        elif self.engine == "ollama":
            self.ollama_url = os.getenv("OLLAMA_URL", "http://localhost:11434")
            self.model = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
            
            # Test Ollama connection
            self._test_ollama_connection()
        else:
            raise ValueError(f"Unsupported engine: {self.engine}. Use 'openai' or 'ollama'")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    @_with_retry
    def generate(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """
        Generate text using the configured LLM engine with retry logic.
        
        Args:
            system_prompt: System/role prompt
            user_prompt: User's actual prompt
            temperature: Sampling temperature (0.0 to 1.0)
            
        Returns:
            Generated text response
        """
        
        if self.engine == "openai":
            response = self._generate_openai(system_prompt, user_prompt, temperature)
        elif self.engine == "ollama":
            response = self._generate_ollama(system_prompt, user_prompt, temperature)
        else:
            raise ValueError(f"Unknown engine: {self.engine}")

        # Validate response against VendorResponse schema
        try:
            if isinstance(response, str):
                return response  # Return the string response directly
            else:
                parsed_response = VendorResponse.model_validate_json(response)
            return parsed_response.response  # Return the validated response
        except (json.JSONDecodeError, ValidationError):
            raise Exception("Invalid JSON response from LLM.")
    
    @_with_retry
    def _generate_openai(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """Generate using OpenAI API"""
        
        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=temperature,
                max_tokens=2000
            )
            raw_response = response.choices[0].message.content.strip()
            print(f"[LLM RESPONSE] Raw response: {raw_response}")  # Log the raw response
            return raw_response
            
        except Exception as e:
            raise Exception(f"OpenAI API error: {str(e)}")
    
    @_with_retry
    def _generate_ollama(self, system_prompt: str, user_prompt: str, temperature: float) -> str:
        """Generate using local Ollama"""
        
        try:
            # Combine system and user prompts for Ollama
            combined_prompt = f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"
            
            payload = {
                "model": self.model,
                "prompt": combined_prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": 2000
                }
            }
            
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                raw_response = result["response"].strip()
                print(f"[LLM RESPONSE] Raw response: {raw_response}")  # Log the raw response
                return raw_response
            else:
                raise Exception(f"Ollama API returned status {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Ollama connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Ollama generation error: {str(e)}")
    
    def _test_ollama_connection(self):
        """Test if Ollama is running and has the required model"""
        
        try:
            # Check if Ollama is running
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            
            if response.status_code != 200:
                raise Exception(f"Ollama server not responding (status {response.status_code})")
            
            # Check if the required model exists
            models = response.json()
            model_names = [model["name"] for model in models.get("models", [])]
            
            if self.model not in model_names:
                raise Exception(
                    f"Model '{self.model}' not found in Ollama. "
                    f"Available models: {', '.join(model_names) if model_names else 'None'}. "
                    f"Run: ollama pull {self.model}"
                )
                
        except requests.exceptions.RequestException:
            raise Exception(
                f"Cannot connect to Ollama at {self.ollama_url}. "
                "Make sure Ollama is running with: ollama serve"
            )
    
    def get_engine_info(self) -> Dict[str, str]:
        """Get information about the current engine configuration"""
        
        info = {
            "engine": self.engine,
            "model": self.model
        }
        
        if self.engine == "ollama":
            info["url"] = self.ollama_url
        
        return info
    
    def list_available_models(self) -> list:
        """List available models for the current engine"""
        
        if self.engine == "ollama":
            try:
                response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
                if response.status_code == 200:
                    models = response.json()
                    return [model["name"] for model in models.get("models", [])]
            except:
                pass
            return []
            
        elif self.engine == "openai":
            # Common OpenAI models - could be extended to fetch from API
            return ["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"]
        
        return []

# Utility functions for quick testing
def test_connection():
    """Test the LLM connection with a simple prompt"""
    
    try:
        llm = LLMWrapper()
        response = llm.generate(
            system_prompt="You are a helpful assistant.",
            user_prompt="Say hello and confirm you're working."
        )
        
        print(f"✅ {llm.engine.upper()} connection successful!")
        print(f"Model: {llm.model}")
        print(f"Response: {response}")
        
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Test the connection when run directly
    test_connection()
