import json
from schemas import NegotiationProposal, VendorResponse
from agent import NegotiationAgent

def validate_proposals(agent, context):
    proposals = agent.generate_proposals(context)
    for strategy, proposal in proposals.items():
        try:
            # Validate each proposal against the schema
            obj = NegotiationProposal(**proposal)
            print(f"{strategy.capitalize()} proposal: PASS")
        except Exception as e:
            print(f"{strategy.capitalize()} proposal: FAIL - {str(e)}")

def validate_vendor_response(agent, context, selected_proposal):
    try:
        response = agent.simulate_vendor_response(context, selected_proposal)
        obj = VendorResponse(**response)
        print("Vendor response: PASS")
    except Exception as e:
        print(f"Vendor response: FAIL - {str(e)}")

if __name__ == "__main__":
    agent = NegotiationAgent()
    
    # Fixed context for testing
    context = {
        "vendor_message": "Your renewal is coming up at $1000/month.",
        "past_price": 500,
        "target_price": 400,
        "service_type": "SaaS Subscription",
        "relationship": "1-3 Years"
    }
    
    # Validate proposals
    validate_proposals(agent, context)
    
    # Validate vendor response using the first proposal
    if 'polite' in agent.generate_proposals(context):
        selected_proposal = agent.generate_proposals(context)['polite']
        validate_vendor_response(agent, context, selected_proposal)