from typing import Literal, Optional, Dict
from pydantic import BaseModel, Field

Frame = Literal["cooperative", "adversarial_contest", "asymmetric_capability", "self_alignment"]


class Payoff(BaseModel):
    r: float = 3.0
    p: float = 1.0
    t: float = 5.0
    s: float = 0.0


class Params(BaseModel):
    # A = you, B = other. Radians.
    thetaA: float = Field(ge=0.0, le=3.141592653589793)
    phiA: float = Field(ge=0.0, le=1.5707963267948966)
    thetaB: float = Field(ge=0.0, le=3.141592653589793)
    phiB: float = Field(ge=0.0, le=1.5707963267948966)
    gamma: float = Field(ge=0.0, le=1.5707963267948966)


class ComputeReq(BaseModel):
    frame: Frame
    params: Params
    payoff: Optional[Payoff] = None
    source: Optional[str] = "server"  # e.g., "gpt","user","server"
    rationale: Optional[str] = None  # optional free text from GPT


class MetricsOut(BaseModel):
    cooperation: float
    miscoordination: float
    stalemate: float
    fairness: float
    tilt: float
    lift: Optional[float] = None  # left null in this minimal API


class ComputeRes(BaseModel):
    run_id: str
    results_url: str
    frame: Frame
    inputs: Dict[str, object]  # echoes params + computed probs
    metrics: MetricsOut
    source: str = "server"

