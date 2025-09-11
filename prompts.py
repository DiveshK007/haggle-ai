# Prompt template for simulating vendor responses
VENDOR_SIMULATION_PROMPT = """
You are simulating a realistic vendor response to a negotiation attempt.

ORIGINAL VENDOR MESSAGE: {vendor_message}
CUSTOMER'S NEGOTIATION PROPOSAL: {proposal}

CONTEXT:
- Original price: ${original_price}/month
- Customer's target: ${target_price}/month  
- Service type: {service_type}
- Relationship length: {relationship}

As a vendor, consider:
- Your margins and flexibility
- Customer's value and retention importance
- Competitive pressure and market rates
- Relationship length and loyalty
- Business pressures (end of quarter, etc.)

Respond in this JSON format:
{{
    "response": "The vendor's email reply",
    "accepted_price": 450,
    "reasoning": "Why the vendor made this decision", 
    "success": true
}}

Be realistic - vendors rarely accept first offers but often provide partial discounts for good customers.
"""

# Prompt for multi-agent debate (stretch goal)
DEBATE_PROMPT = """
Conduct a debate between negotiation experts to determine the best strategy.

POLITE AGENT PERSPECTIVE:
- Relationship preservation is key for long-term success
- Collaborative language builds trust and goodwill
- Win-win solutions create lasting partnerships
- Aggressive tactics can backfire and damage relationships

FIRM AGENT PERSPECTIVE:  
- Clear boundaries establish respect and credibility
- Market leverage should be used when available
- Direct communication saves time and shows confidence
- Vendors respect customers who know their value

CONTEXT: {context}

Have each agent make their case, then recommend the optimal approach for this specific situation.

Respond in JSON format:
{{
    "polite_argument": "Key points for collaborative approach",
    "firm_argument": "Key points for direct approach", 
    "recommendation": "polite|firm|hybrid",
    "reasoning": "Why this approach is best for this situation",
    "hybrid_approach": "If hybrid, explain the combination strategy"
}}
"""

# Prompt for market benchmark analysis (stretch goal)
BENCHMARK_PROMPT = """
Analyze this pricing against market benchmarks and provide negotiation leverage.

SERVICE: {service_type}
CURRENT PRICE: ${current_price}
PROPOSED PRICE: ${proposed_price}

Research typical market rates for {service_type} and provide:
1. Market range analysis
2. Negotiation leverage points
3. Supporting arguments for price reduction
4. Risk factors to consider

Focus on factual, business-case arguments that justify the target price.
"""

# Quick templates for fallback scenarios
FALLBACK_TEMPLATES = {
    "polite": {
        "opening": "Thank you for the renewal information. We've really valued our partnership",
        "transition": "Given our current budget planning and the competitive landscape", 
        "ask": "I was wondering if there might be some flexibility in the pricing",
        "closing": "I'd love to discuss options that work for both of us"
    },
    "firm": {
        "opening": "I've received your renewal quote", 
        "transition": "Based on our research of current market rates and competitive offerings",
        "ask": "We have budget approval for [target_price] for this service",
        "closing": "Please let me know if you can match this rate by [deadline]"
    },
    "term_swap": {
        "opening": "Thanks for the renewal information",
        "transition": "Instead of the standard terms, would you consider",
        "ask": "We could discuss longer commitment, case studies, or other value-adds",
        "closing": "What creative options might work for both of us?"
    }
}

# Email signature template
EMAIL_SIGNATURE = """
Best regards,
[Your Name]
[Company]
[Contact Info]
"""

def format_email_template(template_type: str, context: dict) -> str:
    """
    Helper function to format email templates with context
    
    Args:
        template_type: 'polite', 'firm', or 'term_swap'
        context: Dictionary with negotiation context
        
    Returns:
        Formatted email template
    """
    
    template = FALLBACK_TEMPLATES.get(template_type, FALLBACK_TEMPLATES['polite'])
    
    email = f"""Hi there,

{template['opening']}. {template['transition']}, {template['ask']} around ${context.get('target_price', 'XXX')}/month.

{template['closing']}.

{EMAIL_SIGNATURE}
"""
    
    return email
Prompts for the negotiation agent
Contains system prompts and strategy-specific templates
"""

# Main system prompt for the negotiation agent
SYSTEM_PROMPT = """You are an expert negotiation consultant with 20+ years of experience in B2B vendor negotiations. 

Your expertise includes:
- SaaS and technology service negotiations
- Understanding vendor psychology and business pressures
- Crafting persuasive yet respectful communication
- Balancing relationship preservation with cost savings
- Recognizing negotiation leverage and timing

You always respond in valid JSON format when requested. Be professional, strategic, and realistic in your advice."""

# Prompt template for generating negotiation proposals
PROPOSAL_PROMPT = """
Analyze this negotiation scenario
