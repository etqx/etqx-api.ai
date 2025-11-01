from fastapi import APIRouter
from ..models.ewl import ComputeReq, ComputeRes, MetricsOut, Payoff
from ..utils.ewl import ewl_probabilities, derive_metrics, new_run_id
from ..config import settings

router = APIRouter(prefix="/api/ewl", tags=["ewl"])


@router.post("/compute", response_model=ComputeRes)
def compute(req: ComputeReq):
    payoff = req.payoff or Payoff(
        r=settings.payoff_r,
        p=settings.payoff_p,
        t=settings.payoff_t,
        s=settings.payoff_s,
    )
    p = req.params
    probs = ewl_probabilities(p.thetaA, p.phiA, p.thetaB, p.phiB, p.gamma)
    metrics = derive_metrics(probs, payoff)

    run_id = new_run_id()
    results_url = f"{settings.public_base.rstrip('/')}/run/{run_id}"

    inputs_out = {
        "params": p.model_dump(),
        "probs": probs,
    }
    if req.rationale:
        inputs_out["rationale"] = req.rationale

    return ComputeRes(
        run_id=run_id,
        results_url=results_url,
        frame=req.frame,
        inputs=inputs_out,
        metrics=MetricsOut(**metrics),
        source=req.source or "server",
    )

