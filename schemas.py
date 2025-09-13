from pydantic import BaseModel, Field
from typing import Optional, Literal, List

class NegotiationProposal(BaseModel):
    strategy: Literal["polite", "firm", "term_swap"]
    proposal: str = Field(..., min_length=10, max_length=1200)
    reasoning: str = Field(..., min_length=5, max_length=600)
    expected_outcome: str = Field(..., min_length=3, max_length=300)

class VendorResponse(BaseModel):
    response: str = Field(..., min_length=5, max_length=1200)
    accepted_price: Optional[float]  # allow null when no number given
    reasoning: str = Field(..., min_length=5, max_length=600)
    success: bool

# Optional for stretch
class DebateResult(BaseModel):
    polite_argument: str
    firm_argument: str
    recommendation: Literal["polite", "firm", "hybrid"]
    reasoning: str