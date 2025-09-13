# Prompt template for simulating vendor responses
VENDOR_SIMULATION_PROMPT = """
You are simulating a realistic vendor response to a negotiation attempt.

<context>
  <vendor_message>{vendor_message}</vendor_message>
  <customer_proposal>{proposal}</customer_proposal>
  <original_price>${original_price}/month</original_price>
  <target_price>${target_price}/month</target_price>
  <service_type>{service_type}</service_type>
  <relationship_length>{relationship}</relationship_length>
</context>

<instructions>
  As a vendor, consider the following:
  - Your margins and flexibility.
  - The customer's value and the importance of retention.
  - Competitive pressure and market rates.
  - The length of the relationship and customer loyalty.
  - Business pressures (e.g., end of quarter).

  Your response must be a JSON object with the following structure:
  ```json
  {{
      "response": "The vendor's email reply",
      "accepted_price": 450,
      "reasoning": "Why the vendor made this decision",
      "success": true
  }}
  ```

  Be realistic. Vendors typically concede 15–35% on the first reply; avoid going below target on the first hop unless justified.
</instructions>

<example>
  <input>
    <vendor_message>Your renewal is coming up at $1000/month.</vendor_message>
    <customer_proposal>We're looking for a rate closer to $800/month.</customer_proposal>
  </input>
  <output>
  ```json
  {{
      "response": "Thanks for reaching out. We can offer a discounted rate of $900/month.",
      "accepted_price": 900,
      "reasoning": "Offered a 10% discount to retain a valued customer.",
      "success": true
  }}
  ```
  </output>
</example>
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
```json
{{
    "polite_argument": "Key points for collaborative approach",
    "firm_argument": "Key points for direct approach",
    "recommendation": "polite|firm|hybrid",
    "reasoning": "Why this approach is best for this situation"
}}
```
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

# Prompts for the negotiation agent
# Contains system prompts and strategy-specific templates

# Main system prompt for the negotiation agent
SYSTEM_PROMPT = """You are an expert negotiation consultant with 20+ years of experience in B2B vendor negotiations. 

Your expertise includes:
- SaaS and technology service negotiations
- Understanding vendor psychology and business pressures
- Crafting persuasive yet respectful communication
- Balancing relationship preservation with cost savings
- Recognizing negotiation leverage and timing

Always return ONLY valid JSON when requested. Do not include any prose outside JSON.
"""

# Prompt template for generating negotiation proposals
PROPOSAL_PROMPT = """
Analyze this negotiation scenario and generate a proposal following the specified strategy.

<context>
{context}
</context>

<strategy>
{strategy}
</strategy>

<instructions>
Your response must be a JSON object with the following structure:
```json
{{
    "proposal": "The full text of the negotiation proposal.",
    "reasoning": "The strategic reasoning behind this proposal.",
    "expected_outcome": "What outcome is expected from this approach."
}}
```
Return ONLY JSON with keys: proposal, reasoning, expected_outcome.
Keep proposal ≤ 140 words. No invented facts.

<example>
  <input>
    <context>Vendor is increasing the price from $500 to $600.</context>
    <strategy>polite</strategy>
  </input>
  <output>
  ```json
  {{
      "proposal": "We'd like to propose a renewal at $525/month.",
      "reasoning": "A polite opening with a modest counter-offer.",
      "expected_outcome": "The vendor is likely to accept or provide a further discount."
  }}
  ```
  </output>
</example>
"""
