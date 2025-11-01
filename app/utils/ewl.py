import numpy as np
from typing import Dict, Tuple, Optional
from ..models.ewl import Payoff


def _U(theta: float, phi: float) -> np.ndarray:
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    eip, eim = np.exp(1j * phi), np.exp(-1j * phi)
    return np.array([[eip * c, s], [-s, eim * c]], dtype=complex)


def _D() -> np.ndarray:
    return np.array([[0, 1], [-1, 0]], dtype=complex)


def _J(gamma: float) -> np.ndarray:
    I4 = np.eye(4, dtype=complex)
    Dk = np.kron(_D(), _D())
    cg, sg = np.cos(gamma / 2), np.sin(gamma / 2)
    return cg * I4 - 1j * sg * Dk


def ewl_probabilities(thetaA: float, phiA: float, thetaB: float, phiB: float, gamma: float) -> Dict[str, float]:
    UA, UB = _U(thetaA, phiA), _U(thetaB, phiB)
    UAB = np.kron(UA, UB)
    Jg = _J(gamma)
    psi0 = np.array([1, 0, 0, 0], dtype=complex)  # |CC>
    psi_f = Jg.conj().T @ (UAB @ (Jg @ psi0))
    probs = np.abs(psi_f) ** 2
    probs = probs / np.sum(probs)
    PCC, PCD, PDC, PDD = [float(x) for x in probs]
    return {"CC": PCC, "CD": PCD, "DC": PDC, "DD": PDD}


def tidy_probs(P: Dict[str, float], eps: float = 1e-12) -> Dict[str, float]:
    Q = {k: (0.0 if v < eps else v) for k, v in P.items()}
    s = sum(Q.values())
    if s:
        Q = {k: v / s for k, v in Q.items()}
    return Q


def expected_payoff(payoff: Payoff, P: Dict[str, float]) -> Tuple[float, float]:
    r, p, t, s = payoff.r, payoff.p, payoff.t, payoff.s
    you = r * P["CC"] + p * P["DD"] + t * P["DC"] + s * P["CD"]
    other = r * P["CC"] + p * P["DD"] + t * P["CD"] + s * P["DC"]
    return float(you), float(other)


def derive_metrics(P: Dict[str, float], payoff: Optional[Payoff] = None) -> Dict[str, float]:
    miscoord = P["CD"] + P["DC"]
    coop = P["CC"]
    stalemate = P["DD"]
    tilt = P["CD"] - P["DC"]
    fairness = 0.0
    lift = None  # baseline lift not computed in minimal API
    if payoff:
        you, other = expected_payoff(payoff, P)
        fairness = abs(you - other)
    return {
        "cooperation": coop,
        "miscoordination": miscoord,
        "stalemate": stalemate,
        "fairness": fairness,
        "tilt": tilt,
        "lift": lift,
    }


def tidy_metrics(m: Dict[str, float], eps: float = 1e-12) -> Dict[str, float]:
    return {k: (0.0 if isinstance(v, float) and abs(v) < eps else v) for k, v in m.items()}


def new_run_id() -> str:
    import uuid

    return uuid.uuid4().hex[:12]
