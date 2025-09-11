import json
import random
from typing import Dict, Any

from llm import LLMWrapper
from prompts import SYSTEM_PROMPT, PROPOSAL_PROMPT, VENDOR_SIMULATION_PROMPT

class NegotiationAgent:
    """
    Core negotiation agent that generates proposals and simulates vendor responses
    """
    
    def __init__(self):
        self.llm = LLMWrapper()
    
    def generate_proposals(self, context: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
        """
        Generate three different negotiation proposals: polite, firm, and term_swap
        
        Args:
            context: Dictionary containing vendor_message, past_price, target_price, etc.
            
        Returns:
            Dictionary with three proposal types, each containing content and reasoning
        """
        
        # Prepare context for the LLM
        context_str = self._format_context(context)
        
        proposals = {}
        strategies = ["polite", "firm", "term_swap"]
        
        for strategy in strategies:
            try:
                # Generate proposal for this strategy
                prompt = PROPOSAL_PROMPT.format(
                    context=context_str,
                    strategy=strategy,
                    past_price=context["past_price"],
                    target_price=context["target_price"]
                )
                
                response = self.llm.generate(
                    system_prompt=SYSTEM_PROMPT,
                    user_prompt=prompt
                )
                
                # Parse the response (expecting JSON format)
                try:
                    parsed_response = json.loads(response)
                    proposals[strategy] = {
                        "content": parsed_response.get("proposal", ""),
                        "reasoning": parsed_response.get("reasoning", ""),
                        "expected_outcome": parsed_response.get("expected_outcome", "")
                    }
                except json.JSONDecodeError:
                    # Fallback if JSON parsing fails
                    proposals[strategy] = {
                        "content": response,
                        "reasoning": f"Generated {strategy} negotiation approach",
                        "expected_outcome": "Moderate success expected"
                    }
                    
            except Exception as e:
                # Fallback proposal in case of error
                proposals[strategy] = self._get_fallback_proposal(strategy, context)
        
        return proposals
    
    def simulate_vendor_response(self, context: Dict[str, Any], selected_proposal: Dict[str, str]) -> Dict[str, Any]:
        """
        Simulate how a vendor might respond to the selected proposal
        
        Args:
            context: Original negotiation context
            selected_proposal: The proposal that was selected
            
        Returns:
            Dictionary containing vendor response and accepted price
        """
        
        try:
            # Format the simulation prompt
            prompt = VENDOR_SIMULATION_PROMPT.format(
                vendor_message=context["vendor_message"],
                proposal=selected_proposal["content"],
                original_price=context["past_price"],
                target_price=context["target_price"],
                service_type=context["service_type"],
                relationship=context["relationship"]
            )
            
            response = self.llm.generate(
                system_prompt="You are simulating a vendor's response to a negotiation. Be realistic and consider business factors.",
                user_prompt=prompt
            )
            
            # Try to parse JSON response
            try:
                parsed_response = json.loads(response)
                return {
                    "content": parsed_response.get("response", ""),
                    "accepted_price": parsed_response.get("accepted_price"),
                    "reasoning": parsed_response.get("reasoning", ""),
                    "success": parsed_response.get("success", False)
                }
            except json.JSONDecodeError:
                # Fallback simulation
                return self._get_fallback_vendor_response(context)
                
        except Exception as e:
            # Fallback in case of error
            return self._get_fallback_vendor_response(context)
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for the LLM"""
        return f"""
        Vendor Message: {context['vendor_message']}
        Current/Past Price: ${context['past_price']}/month
        Target Price: ${context['target_price']}/month
        Service Type: {context['service_type']}
        Relationship Length: {context['relationship']}
        """
    
    def _get_fallback_proposal(self, strategy: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate fallback proposals when LLM fails"""
        
        fallback_proposals = {
            "polite": {
                "content": f"Hi there,\n\nThank you for the renewal notice. We've really valued our partnership over the years. Given our current budget constraints and the competitive landscape, I was wondering if there might be some flexibility in the pricing? We're hoping to find a solution that works for both of us - perhaps around ${context['target_price']}/month?\n\nI'd love to discuss this further. When would be a good time to chat?\n\nBest regards",
                "reasoning": "Uses collaborative language and emphasizes the relationship while introducing budget constraints as a reason for the request.",
                "expected_outcome": "Moderate success expected due to polite approach"
            },
            "firm": {
                "content": f"Hello,\n\nI've received your renewal quote of ${context['past_price']}/month. Based on our research of current market rates and competitive offerings, this pricing is above what we can justify. We have budget approval for ${context['target_price']}/month for this service.\n\nCan you match this rate? If not, we'll need to evaluate other options.\n\nPlease let me know your thoughts by end of week.\n\nThanks",
                "reasoning": "Direct approach that establishes a clear position with a deadline and consequence.",
                "expected_outcome": "Higher success rate but may strain relationship"
            },
            "term_swap": {
                "content": f"Hi,\n\nThanks for the renewal info. Instead of the current terms, would you consider ${context['target_price']}/month if we commit to a longer contract term? We could also discuss other value-adds like case studies, testimonials, or referrals that might justify a better rate.\n\nWhat creative options might work for both of us?\n\nLooking forward to your thoughts.",
                "reasoning": "Offers alternative value propositions and longer commitment in exchange for better pricing.",
                "expected_outcome": "Good success rate by providing vendor with added value"
            }
        }
        
        return fallback_proposals.get(strategy, fallback_proposals["polite"])
    
    def _get_fallback_vendor_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate fallback vendor response when simulation fails"""
        
        original_price = context["past_price"]
        target_price = context["target_price"]
        
        # Simulate realistic vendor behavior - usually meet somewhere in the middle
        discount_percent = random.uniform(0.15, 0.35)  # 15-35% discount
        accepted_price = int(original_price * (1 - discount_percent))
        
        # Don't go below target price too easily
        if accepted_price < target_price:
            accepted_price = int((target_price + original_price) / 2)
        
        responses = [
            f"Thank you for reaching out. We value our partnership and understand your budget concerns. We can offer ${accepted_price}/month for this renewal. Would this work for you?",
            f"I appreciate your business and loyalty. After reviewing your account, I can approve ${accepted_price}/month. This is our best offer given the value we provide.",
            f"Let me see what I can do... I've spoken with my manager and we can accommodate ${accepted_price}/month for a valued client like you."
        ]
        
        return {
            "content": random.choice(responses),
            "accepted_price": accepted_price,
            "reasoning": "Simulated response offering partial discount",
            "success": accepted_price < original_price
        }
    
    def get_engine_info(self) -> Dict[str, str]:
        """Get information about the current LLM engine"""
        return self.llm.get_engine_info()

# Multi-agent debate functionality (stretch goal)
class DebateOrchestrator:
    """
    Orchestrates debates between different negotiation strategies to pick the best approach
    """
    
    def __init__(self):
        self.llm = LLMWrapper()
    
    def conduct_debate(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Have polite and firm agents debate, then pick the best strategy
        
        Args:
            context: Negotiation context
            
        Returns:
            Best strategy recommendation with reasoning
        """
        
        debate_prompt = f"""
        Context: {context}
        
        You are orchestrating a debate between two negotiation experts:
        
        POLITE AGENT: Believes in relationship-building, collaborative language, win-win solutions
        FIRM AGENT: Believes in direct communication, clear boundaries, leveraging competitive alternatives
        
        Have them debate the best approach for this situation, then recommend the optimal strategy.
        
        Format your response as JSON:
        {{
            "polite_argument": "...",
            "firm_argument": "...", 
            "recommendation": "polite|firm|hybrid",
            "reasoning": "..."
        }}
        """
        
        try:
            response = self.llm.generate(
                system_prompt="You are a negotiation strategy orchestrator conducting an expert debate.",
                user_prompt=debate_prompt
            )
            
            return json.loads(response)
            
        except Exception as e:
            # Fallback recommendation
            return {
                "polite_argument": "Building relationships leads to long-term success",
                "firm_argument": "Clear boundaries establish respect and better outcomes",
                "recommendation": "polite",
                "reasoning": "Default to collaborative approach for relationship preservation"
            }
