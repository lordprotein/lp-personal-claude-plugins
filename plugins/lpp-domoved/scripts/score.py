#!/usr/bin/env python3
"""Domoved total score.

Takes the analysis JSON (schemas/report.schema.json), a weight profile from
config/profiles.json and adds the "score" block. The calculation is deterministic,
so the same analysis always gives the same total.

Rules:
- a criterion without a score or with confidence "none" is left out of the average
  and goes to missing ("проверить лично", check in person);
- the criterion weight is multiplied by the confidence coefficient, so
  weakly supported scores affect the total less;
- each major flag subtracts 0.3 points (no more than 1.0 in total);
- any stop flag caps the total at 5.4.

Usage:
  score.py analysis.json [--profile balance] [--out scored.json | --in-place]
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROFILES_PATH = os.path.join(HERE, "..", "config", "profiles.json")

CONFIDENCE_ORDER = ["none", "low", "medium", "high"]


def load_config(path=PROFILES_PATH):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _num(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _auto_flags(analysis):
    """Flags that follow directly from the data and must not be lost."""
    flags = list(analysis.get("red_flags") or [])
    ids = {f.get("id") for f in flags}
    valuation = analysis.get("valuation") or {}
    if valuation.get("mortgage_eligible") is False and "not_mortgage_eligible" not in ids:
        flags.append({
            "id": "not_mortgage_eligible",
            "title": "Объект, скорее всего, не проходит по ипотеке",
            "severity": "major",
            "criterion": "value_liquidity",
            "detail": "Круг будущих покупателей сильно сужается, продать будет дольше и дешевле.",
            "auto": True,
        })
    return flags


def compute(analysis, profile_name=None, config=None):
    config = config or load_config()
    meta = analysis.get("meta") or {}
    profile_name = profile_name or meta.get("profile") or "balance"
    profiles = config["profiles"]
    if profile_name not in profiles:
        raise ValueError("Unknown profile: %s (available: %s)" % (profile_name, ", ".join(profiles)))
    profile = profiles[profile_name]
    weights = profile["weights"]
    rules = config["rules"]
    conf_factor = rules["confidence_factor"]
    titles = config["criteria"]
    obj_type = (analysis.get("object") or {}).get("type")

    criteria = analysis.get("criteria") or {}
    warnings = []
    for key in criteria:
        if key not in weights:
            warnings.append("Criterion '%s' is not in the profile and was ignored" % key)

    per = {}
    weighted_sum = 0.0
    eff_weight_sum = 0.0
    coverage = 0.0
    conf_weighted = 0.0
    missing = []

    for cid, weight in weights.items():
        meta_c = titles.get(cid, {})
        title = meta_c.get("title", cid)
        if obj_type == "private_house" and meta_c.get("title_private_house"):
            title = meta_c["title_private_house"]
        c = criteria.get(cid) or {}
        score = _num(c.get("score"))
        conf = c.get("confidence") or ("none" if score is None else "medium")
        if conf not in conf_factor:
            warnings.append("Unknown confidence '%s' for '%s', treating as medium" % (conf, cid))
            conf = "medium"
        if score is not None:
            if score < 0 or score > 10:
                warnings.append("Score '%s' outside 0..10 (%s), clipped" % (cid, score))
            score = max(0.0, min(10.0, score))
        factor = conf_factor[conf] if score is not None else 0.0
        eff = weight * factor
        entry = {
            "title": title,
            "icon": meta_c.get("icon", ""),
            "score": None if score is None else round(score, 1),
            "confidence": conf if score is not None else "none",
            "weight": weight,
            "effective_weight": round(eff, 4),
            "contribution": None,
        }
        if score is None or factor == 0:
            missing.append(cid)
        else:
            weighted_sum += score * eff
            eff_weight_sum += eff
            coverage += weight
            conf_weighted += weight * factor
            entry["_raw"] = score * eff
        per[cid] = entry

    raw_total = weighted_sum / eff_weight_sum if eff_weight_sum else 0.0
    for entry in per.values():
        raw = entry.pop("_raw", None)
        if raw is not None and eff_weight_sum:
            entry["contribution"] = round(raw / eff_weight_sum, 2)

    flags = _auto_flags(analysis)
    stop_flags = [f.get("title", f.get("id", "")) for f in flags if f.get("severity") == "stop"]
    major_flags = [f.get("title", f.get("id", "")) for f in flags if f.get("severity") == "major"]

    penalty = min(len(major_flags) * rules["major_flag_penalty"], rules["major_flag_penalty_max"])
    total = max(0.0, raw_total - penalty)
    capped = False
    cap_reason = []
    if stop_flags and total > rules["stop_flag_cap"]:
        total = rules["stop_flag_cap"]
        capped = True
        cap_reason = stop_flags

    avg_conf = conf_weighted / coverage if coverage else 0.0
    if coverage >= 0.85 and avg_conf >= 0.85:
        confidence = "high"
    elif coverage >= rules["min_coverage_for_verdict"] and avg_conf >= 0.6:
        confidence = "medium"
    else:
        confidence = "low"

    verdict = config["verdicts"][-1]
    for v in config["verdicts"]:
        if total >= v["min"]:
            verdict = v
            break
    verdict_title = verdict["title"]
    if coverage < rules["min_coverage_for_verdict"]:
        verdict_title += " (мало данных, вывод предварительный)"

    result = {
        "total": round(total, 1),
        "raw_total": round(raw_total, 2),
        "penalty": round(penalty, 2),
        "capped": capped,
        "cap_reason": cap_reason,
        "verdict_code": verdict["code"],
        "verdict_title": verdict_title,
        "verdict_color": verdict["color"],
        "profile": profile_name,
        "profile_title": profile["title"],
        "coverage": round(coverage, 2),
        "confidence": confidence,
        "missing": missing,
        "stop_flags": stop_flags,
        "major_flags": major_flags,
        "per_criterion": per,
    }
    if warnings:
        result["warnings"] = warnings
    return result, flags


def main(argv=None):
    parser = argparse.ArgumentParser(description="Domoved total score from the analysis JSON")
    parser.add_argument("analysis", help="path to the analysis JSON")
    parser.add_argument("--profile", help="balance | family | investment | quiet (default from meta.profile or balance)")
    out = parser.add_mutually_exclusive_group()
    out.add_argument("--out", help="where to write the JSON with the score block")
    out.add_argument("--in-place", action="store_true", help="add score to the source file")
    args = parser.parse_args(argv)

    try:
        with open(args.analysis, encoding="utf-8") as f:
            analysis = json.load(f)
        score, flags = compute(analysis, args.profile)
    except (OSError, ValueError, KeyError) as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 1

    analysis["score"] = score
    analysis["red_flags"] = flags
    analysis.setdefault("meta", {})["profile"] = score["profile"]
    target = args.analysis if args.in_place else args.out
    if target:
        with open(target, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
    print(json.dumps(score, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
