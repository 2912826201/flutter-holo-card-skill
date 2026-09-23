"""Validate human visual scorecards; never infer artistic quality from pixels."""
from __future__ import annotations

import math

PROFILES = {
    "foreground": (85, {"completeness": 40, "placement": 35, "edges": 25}),
    "background": (80, {"style": 30, "removal": 40, "continuity": 30}),
    "lineart": (75, {"structure": 35, "placement": 35, "cleanliness": 30}),
    "composite": (80, {"readability": 40, "layering": 35, "appearance": 25}),
}
REQUIRED = {
    "height": ("foreground", "background", "lineart", "composite"),
    "medium": ("lineart", "composite"),
    "low": ("composite",),
}


def assess(cards, required):
    if not isinstance(cards, dict) or set(cards) != set(required):
        raise ValueError("Quality review must contain exactly: " + ", ".join(required))
    results = {}
    for kind in required:
        card = cards[kind]
        threshold, weights = PROFILES[kind]
        scores = card.get("scores", {})
        if set(scores) != set(weights):
            raise ValueError(f"{kind}: incorrect quality dimensions")
        for value in scores.values():
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not math.isfinite(value) or not 0 <= value <= 100):
                raise ValueError("Quality scores must be finite numbers within 0–100")
        blockers = card.get("blockers")
        if not isinstance(blockers, list) or any(
            not isinstance(item, str) or not item.strip() for item in blockers
        ):
            raise ValueError("blockers must be a list of concrete defect descriptions")
        if not isinstance(card.get("notes"), str) or not card["notes"].strip():
            raise ValueError("Quality review needs actual visual observations")
        attempts = card.get("attempts")
        if type(attempts) is not int or attempts not in (1, 2):
            raise ValueError("Default budget is one initial request plus one edit")
        raw_score = sum(scores[key] * weight for key, weight in weights.items()) / 100
        accepted = raw_score >= threshold and not blockers
        results[kind] = {
            "score": round(raw_score, 2), "threshold": threshold,
            "accepted": accepted,
            "next_action": "reuse" if accepted else "edit_once" if attempts == 1 else "stop",
        }
    return {"accepted": all(r["accepted"] for r in results.values()), "assets": results}


def record(cards, required, decision):
    result = assess(cards, required)
    if decision == "pass" and not result["accepted"]:
        raise ValueError("Below-threshold or blocked assets cannot be marked pass")
    return {"cards": cards, "result": result}


def verify(quality, required):
    if not isinstance(quality, dict):
        raise ValueError("Missing asset-specific visual quality review")
    current = assess(quality.get("cards"), required)
    if current != quality.get("result") or not current["accepted"]:
        raise ValueError("Failed or modified visual quality review")
