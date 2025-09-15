import json
import random
from typing import Dict, Any
from pydantic import ValidationError

from llm import LLMWrapper
from prompts import SYSTEM_PROMPT, PROPOSAL_PROMPT, VENDOR_SIMULATION_PROMPT, FALLBACK_TEMPLATES
from schemas import NegotiationProposal, VendorResponse  # Removed Debate

class NegotiationAgent:
    """
    Core negotiation agent that generates proposals and simulates vendor responses
    """
    
    def __init__(self):
        self.llm = LLMWrapper()
    
    def _parse_with_model(self, text: str, model_cls):
        data = json.loads(text)
        obj = model_cls(**data)   # raises ValidationError on mismatch
        return obj
    
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
            for attempt in range(2):  # Retry up to 1 additional time
                try:
                    # Generate proposal for this strategy
                    prompt = PROPOSAL_PROMPT.format(
                        context=context_str,
                        strategy=strategy,
                        past_price=context["past_price"],
                        target_price=context["target_price"]
                    )
                    
                    raw = self.llm.generate(
                        system_prompt=SYSTEM_PROMPT,
                        user_prompt=prompt,
                        temperature=0.65
                    )
                    
                    obj = self._parse_with_model(raw, NegotiationProposal)
                    proposals[strategy] = {
                        "content": obj.proposal,
                        "reasoning": obj.reasoning,
                        "expected_outcome": obj.expected_outcome
                    }
                    break  # Exit retry loop on success

                except (json.JSONDecodeError, ValidationError):
                    if attempt == 1:  # Last attempt
                        raw = self.llm.generate(
                            system_prompt=SYSTEM_PROMPT,
                            user_prompt=prompt + "\n\nReturn ONLY valid JSON with keys: proposal, reasoning, expected_outcome.",
                            temperature=0.6
                        )
                        obj = self._parse_with_model(raw, NegotiationProposal)
                        proposals[strategy] = {
                            "content": obj.proposal,
                            "reasoning": obj.reasoning,
                            "expected_outcome": obj.expected_outcome
                        }
                    else:
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
        
        for attempt in range(2):  # Retry up to 1 additional time
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
                
                raw = self.llm.generate(
                    system_prompt="You are simulating a vendor's response to a negotiation. Be realistic and consider business factors.",
                    user_prompt=prompt,
                    temperature=0.5
                )
                
                obj = self._parse_with_model(raw, VendorResponse)
                return {
                    "content": obj.response,
                    "accepted_price": obj.accepted_price,
                    "reasoning": obj.reasoning,
                    "success": obj.success
                }
            except (json.JSONDecodeError, ValidationError):
                if attempt == 1:  # Last attempt
                    raw = self.llm.generate(
                        system_prompt="You are simulating a vendor's response to a negotiation. Be realistic and consider business factors.",
                        user_prompt=prompt + "\n\nReturn ONLY valid JSON with keys: response, accepted_price, reasoning, success.",
                        temperature=0.45
                    )
                    obj = self._parse_with_model(raw, VendorResponse)
                    return {
                        "content": obj.response,
                        "accepted_price": obj.accepted_price,
                        "reasoning": obj.reasoning,
                        "success": obj.success
                    }
        
        return self._get_fallback_vendor_response(context)
    
    def _format_context(self, context: Dict[str, Any]) -> str:
        """Format context information for the LLM"""
        return f"""
<vendor_message>{context['vendor_message']}</vendor_message>
<current_price>${context['past_price']}/month</current_price>
<target_price>${context['target_price']}/month</target_price>
<service_type>{context['service_type']}</service_type>
<relationship_length>{context['relationship']}</relationship_length>
"""
    
    def _get_fallback_proposal(self, strategy: str, context: Dict[str, Any]) -> Dict[str, str]:
        """Generate dynamic fallback proposals when LLM fails"""
        
        target_price = context.get('target_price', 'a more competitive rate')
        
        proposals = FALLBACK_TEMPLATES.get(strategy, FALLBACK_TEMPLATES['polite'])
        
        return {
            "content": f"{proposals['opening']} {proposals['transition']} {proposals['ask']} around ${target_price}/month.",
            "reasoning": proposals['closing'],
            "expected_outcome": "Vendor is likely to be receptive to a discussion."
        }
    
    def _get_fallback_vendor_response(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a dynamic fallback vendor response when simulation fails"""
        
        original_price = context.get("past_price", 1000)
        target_price = context.get("target_price", 800)
        
        # Simulate a realistic concession
        concession = (original_price - target_price) * random.uniform(0.25, 0.75)
        accepted_price = round(original_price - concession, 2)
        
        response_text = f"Thank you for your proposal. We can offer a revised rate of ${accepted_price}/month."
        
        return {
            "content": response_text,
            "accepted_price": accepted_price,
            "reasoning": "Fallback simulation with a partial concession.",
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
            
            return Debate.model_validate_json(response).model_dump()
            
        except (json.JSONDecodeError, ValidationError):
            # Fallback recommendation
            return {
                "polite_argument": "Building relationships leads to long-term success",
                "firm_argument": "Clear boundaries establish respect and better outcomes",
                "recommendation": "polite",
                "reasoning": "Default to collaborative approach for relationship preservation"
            }
