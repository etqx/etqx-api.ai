# app.py
import os, json, math
import numpy as np
import httpx
from enum import Enum
from typing import Dict
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL = "gpt-4o-mini"

# ---------------------------
# EWL core
# ---------------------------
def U(theta, phi):
    c, s = np.cos(theta/2), np.sin(theta/2)
    eip, eim = np.exp(1j*phi), np.exp(-1j*phi)
    return np.array([[eip*c, s], [-s, eim*c]], dtype=complex)

def D():
    return np.array([[0, 1], [-1, 0]], dtype=complex)

def J(gamma):
    # Closed form since (D⊗D)^2 = I: J = cos(g/2)·I4 - i·sin(g/2)·(D⊗D)
    I4 = np.eye(4, dtype=complex)
    Dk = np.kron(D(), D())
    cg, sg = np.cos(gamma/2), np.sin(gamma/2)
    return cg * I4 - 1j * sg * Dk

def probabilities(thetaA, phiA, thetaB, phiB, gamma):
    UA, UB = U(thetaA, phiA), U(thetaB, phiB)
    UAB = np.kron(UA, UB)
    Jg = J(gamma)
    Jdg = Jg.conj().T
    psi0 = np.array([1, 0, 0, 0], dtype=complex)  # |CC>
    psi_f = Jdg @ (UAB @ (Jg @ psi0))
    probs = np.abs(psi_f) ** 2
    probs = probs / np.sum(probs)
    PCC, PCD, PDC, PDD = [float(x) for x in probs]
    return {"CC": PCC, "CD": PCD, "DC": PDC, "DD": PDD}

def expected(payoff: Dict[str, float], P: Dict[str, float]):
    r, p, t, s = payoff["r"], payoff["p"], payoff["t"], payoff["s"]
    you   = r*P["CC"] + p*P["DD"] + t*P["DC"] + s*P["CD"]
    other = r*P["CC"] + p*P["DD"] + t*P["CD"] + s*P["DC"]
    return {"you": float(you), "other": float(other)}

# ---------------------------
# LLM extractor
# ---------------------------
SYSTEM = "You extract strategy features. Return ONLY valid JSON matching the schema. No prose."
SCHEMA = {
  "actors":{"you":"string","other":"string|optional","powerAsymmetry":"you|other|balanced"},
  "objectives":{"you":["string"],"other":["string|optional"]},
  "trust":"low|medium|high",
  "riskTolerance":"low|medium|high",
  "timeHorizon":"short|medium|long",
  "constraints":["string"],
  "commitmentSignals":["string"],
  "uncertainty":"low|medium|high",
  "domain":"string",
  "notes":["string"],
  "confidence":0.0
}

async def extract_features(strategy: str, use_case: str, context: str) -> dict:
    if not OPENAI_API_KEY:
        raise HTTPException(500, "OPENAI_API_KEY missing")
    prompt = f"Schema:\n{json.dumps(SCHEMA)}\n\nStrategy:{strategy}\nUseCase:{use_case}\nContext:\n\"\"\"{context}\"\"\"\nReturn JSON now."
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": MODEL,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": prompt},
                ],
            },
        )
    data = r.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    try:
        return json.loads(content)
    except Exception:
        raise HTTPException(502, "Extractor returned invalid JSON")

# ---------------------------
# feature → params/payoff mapping
# ---------------------------
def to01(x: str) -> float:
    return {"low": 0.0, "medium": 0.5, "high": 1.0}.get(x, 0.5)

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def base_map(f: dict):
    trust = to01(f.get("trust", "medium"))
    risk = to01(f.get("riskTolerance", "medium"))
    horizon = {"short": 0, "medium": 0.5, "long": 1}.get(f.get("timeHorizon", "medium"), 0.5)
    commit = min(1.0, 0.3 * len(f.get("commitmentSignals", [])))
    uncert = to01(f.get("uncertainty", "medium"))
    asym = (f.get("actors") or {}).get("powerAsymmetry", "balanced")

    gamma  = (0.2 + 0.5*trust + 0.3*commit + 0.2*(1 - horizon)) * (math.pi/2)
    thetaA = (0.2 + 0.7*risk - 0.2*uncert) * math.pi
    thetaB = (0.5 + 0.3*trust - 0.2*risk) * math.pi
    phiA   = (0.3 + 0.5*trust) * (math.pi/2)
    phiB   = (0.3 + 0.5*trust) * (math.pi/2)

    if asym == "other":
        thetaB += 0.15 * math.pi
    if asym == "you":
        thetaA += 0.15 * math.pi

    params = {
        "thetaA": clamp(thetaA, 0, math.pi),
        "phiA":   clamp(phiA,   0, math.pi/2),
        "thetaB": clamp(thetaB, 0, math.pi),
        "phiB":   clamp(phiB,   0, math.pi/2),
        "gamma":  clamp(gamma,  0, math.pi/2),
    }
    rationale = [f"γ from trust/commitments/horizon; θ/φ from risk & uncertainty; asym={asym}."]
    return {**params, "rationale": rationale}

def apply_strategy(strategy: str, f: dict):
    base = base_map(f)
    payoff = {"r": 3.0, "p": 1.0, "t": 5.0, "s": 0.0}
    rat = base["rationale"]

    if strategy == "cooperative_alignment":
        trust = to01(f.get("trust", "medium"))
        uncert = to01(f.get("uncertainty", "medium"))

        # Payoff tuned for alignment domain (PD shape, softened at low trust)
        payoff = {
            "r": 3.0 + 0.4*trust,     # cooperation more rewarding with trust
            "p": 1.0 + 0.2*uncert,    # DD cost rises with uncertainty
            "t": 5.0 - 0.3*trust,     # temptation shrinks as trust rises
            "s": 0.0 + 0.2*(1 - trust)# small cushion for the "sucker" at low trust
        }

        if trust >= 0.5:
            # High trust → symmetric Q & strong entanglement
            base["thetaA"] = base["thetaB"] = 0.0
            base["phiA"]   = base["phiB"]   = math.pi/2
            base["gamma"]  = 0.9 * (math.pi/2)
            rat += ["Symmetric Q strategy under strong entanglement for cooperative alignment."]
        else:
            # Low trust → symmetric exploration, light coupling, modest phase
            base["thetaA"] = base["thetaB"] = math.pi/2
            base["phiA"]   = base["phiB"]   = 0.3 * (math.pi/2)
            base["gamma"]  = 0.45 * (math.pi/2)
            rat += ["Low-trust preset: symmetric exploration with light coupling and modest phase."]

    elif strategy == "adversarial_contest":
        base["thetaA"] = clamp(base["thetaA"] + 0.2*math.pi, 0, math.pi)
        base["thetaB"] = clamp(base["thetaB"] + 0.1*math.pi, 0, math.pi)
        payoff = {"r": 2.0, "p": 1.2, "t": 5.2, "s": 0.3}
        rat += ["Adversarial stance: θ boost; zero-sum skew."]

    elif strategy == "asymmetric_capability":
        base["phiA"] = clamp(base["phiA"] + 0.2 * (math.pi/2), 0, math.pi/2)
        base["phiB"] = 0.0
        rat += ["Asymmetry: φ_A↑ (quantum leverage), φ_B→0 (classical)."]

    elif strategy == "self_alignment":
        commit = min(1.0, 0.3*len(f.get("commitmentSignals", [])))
        payoff = {
            "r": 3.5 + 0.5*commit,
            "p": 1.8 + 0.4*(1 - to01(f.get("trust", "medium"))),
            "t": 0.8 - 0.4*commit,
            "s": 0.8 - 0.2*to01(f.get("trust", "medium")),
        }
        rat += ["Self-alignment: reward coherence (r↑), penalize drift (p↑), suppress temptations (t/s↓)."]

    params = {k: base[k] for k in ["thetaA", "phiA", "thetaB", "phiB", "gamma"]}
    return {"params": params, "payoff": payoff, "rationale": rat}

# ---------------------------
# Classical baseline & Metrics
# ---------------------------
def snap_theta_to_classical(theta: float) -> float:
    # Simple snap: < π/2 => Cooperate (0), else Defect (π)
    return 0.0 if theta < (math.pi / 2) else math.pi

def classical_baseline(params: dict, payoff: dict):
    thetaA = snap_theta_to_classical(params["thetaA"])
    thetaB = snap_theta_to_classical(params["thetaB"])
    P0 = probabilities(thetaA, 0.0, thetaB, 0.0, 0.0)  # φ=0, γ=0
    return expected(payoff, P0)

def derive_metrics(P: dict, quantum: dict, classical: dict):
    miscoord = P["CD"] + P["DC"]
    coop = P["CC"]
    stalemate = P["DD"]
    fairness = abs(quantum["you"] - quantum["other"])
    lift_you = quantum["you"] - classical["you"]
    lift_other = quantum["other"] - classical["other"]
    tilt = P["CD"] - P["DC"]  # +: other exploits you; -: you exploit other
    return {
        "cooperation": coop,
        "miscoordination": miscoord,
        "stalemate": stalemate,
        "fairness": fairness,
        "lift": {"you": lift_you, "other": lift_other},
        "tilt": tilt,
    }

# ---------------------------
# LLM Coach (JSON)
# ---------------------------
COACH_SYSTEM = (
    "You are a strategy coach. Return ONLY valid JSON with short, actionable tips. "
    "No prose, no markdown."
)
COACH_SCHEMA = {
  "tips": ["string"],
  "actions": ["string"],
  "tuning": ["string"],
  "warnings": ["string"]
}

async def coach_tips_llm(
    strategy: str,
    use_case: str,
    features: dict,
    params: dict,
    payoff: dict,
    probs: dict,
    quantum: dict,
    classical: dict,
    metrics: dict
) -> dict:
    if not OPENAI_API_KEY:
        raise HTTPException(500, "OPENAI_API_KEY missing")
    # Keep payload compact but informative
    brief = {
        "strategy": strategy,
        "useCase": use_case,
        "features": {
            "trust": features.get("trust"),
            "uncertainty": features.get("uncertainty"),
            "commitmentSignals": features.get("commitmentSignals", []),
            "powerAsymmetry": (features.get("actors") or {}).get("powerAsymmetry", "balanced"),
            "constraints": features.get("constraints", []),
            "domain": features.get("domain")
        },
        "params": {k: round(float(v), 4) for k,v in params.items()},
        "payoff": payoff,
        "probs": {k: round(float(v), 4) for k,v in probs.items()},
        "quantum": {"you": round(quantum["you"], 4), "other": round(quantum["other"], 4)},
        "classical": {"you": round(classical["you"], 4), "other": round(classical["other"], 4)},
        "metrics": {k: (v if not isinstance(v, dict) else {ik: round(iv,4) for ik,iv in v.items()})
                    for k,v in metrics.items()}
    }

    user_prompt = (
        "Schema:\n"
        + json.dumps(COACH_SCHEMA)
        + "\n\nGiven this simulation result, produce concise, actionable coaching.\n"
        "Prefer 3–6 items per section. Keep each item <120 chars. "
        "If a section has nothing useful, return an empty array for it.\n\n"
        "Input:\n"
        + json.dumps(brief)
        + "\n\nReturn JSON now."
    )

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
            json={
                "model": MODEL,
                "temperature": 0,
                "messages": [
                    {"role": "system", "content": COACH_SYSTEM},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
    data = r.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "{}")
    obj = json.loads(content)  # let it raise; caller handles
    # ensure keys exist
    for k in ["tips","actions","tuning","warnings"]:
        obj.setdefault(k, [])
    return obj

# ---------------------------
# Rule-based fallback coach (used only if LLM fails)
# ---------------------------
def coaching(strategy: str, trust: str, metrics: dict):
    hints = []
    actions = []
    tuning = []
    warnings = []
    if strategy == "cooperative_alignment":
        if metrics["miscoordination"] > 0.6:
            actions.append("Add pilot + weekly check-ins to raise γ.")
        if metrics["cooperation"] < 0.3:
            actions.append("Write shared one-pager to align φ.")
        if metrics["tilt"] > 0.1:
            warnings.append("Counterparty exploiting; add guardrails / reduce scope.")
            tuning.append("Lower θ to reduce optionality.")
        if metrics["tilt"] < -0.1:
            warnings.append("You are exploiting; align incentives if goal is partnership.")
            tuning.append("Lower temptation or narrow options (θ).")
        if trust == "low" and metrics["stalemate"] > 0.15:
            actions.append("Clarify budget/timeline to reduce DD risk.")
        hints.extend(["Focus on transparent goals.", "Start with a small reversible step."])
    return {"tips": hints, "actions": actions, "tuning": tuning, "warnings": warnings}

# ---------------------------
# API
# ---------------------------
class Strategy(str, Enum):
    cooperative_alignment   = "cooperative_alignment"
    adversarial_contest     = "adversarial_contest"
    asymmetric_capability   = "asymmetric_capability"
    self_alignment          = "self_alignment"
    # (Add more as you implement)

class RunReq(BaseModel):
    strategy: Strategy
    useCase: str
    context: str

app = FastAPI()
# CORS (relax in dev; restrict in prod)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/strategy/run")
async def run(req: RunReq):
    feats = await extract_features(req.strategy.value, req.useCase, req.context)
    mapped = apply_strategy(req.strategy.value, feats)
    P = probabilities(**mapped["params"])
    pay = expected(mapped["payoff"], P)

    base = classical_baseline(mapped["params"], mapped["payoff"])
    metrics = derive_metrics(P, pay, base)

    # Try LLM coach first; fall back to rules if anything goes wrong
    coach_source = "llm"
    try:
        tips = await coach_tips_llm(
            req.strategy.value, req.useCase, feats,
            mapped["params"], mapped["payoff"], P, pay, base, metrics
        )
    except Exception:
        tips = coaching(req.strategy.value, feats.get("trust","medium"), metrics)
        coach_source = "rule"

    return {
        "features": feats,
        "paramsResolved": mapped["params"],
        "payoff": mapped["payoff"],
        "quantum": {"you": pay["you"], "other": pay["other"], "probs": P},
        "classical": base,
        "metrics": metrics,
        "coach": tips,
        "coach_source": coach_source,
        "explain": {"rationale": mapped["rationale"]},
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    # Enable `python app.py` for local runs
    import uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
