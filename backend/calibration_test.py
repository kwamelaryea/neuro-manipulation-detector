"""Calibration test harness — runs known texts through both scorers and compares.

Usage:
  python calibration_test.py              # fast (LLM) only, ~10s
  python calibration_test.py --deep       # TRIBE v2 via Modal, ~4 min per text
  python calibration_test.py --both       # side-by-side comparison

Requires: server running at localhost:8000 (or pass --url)
"""
import argparse
import json
import sys
import time

import requests

CORPUS = [
    {
        "id": "neutral-academic",
        "label": "Academic (neutral)",
        "expected": (0, 3),
        "text": (
            "The committee meets quarterly to review audited financial statements "
            "and compliance reports. Minutes from the previous session were approved "
            "unanimously. The treasurer presented the annual budget variance analysis, "
            "noting a 2.3% underspend in operational expenses. No corrective actions "
            "were deemed necessary. The next meeting is scheduled for September 15."
        ),
    },
    {
        "id": "neutral-wikipedia",
        "label": "Wikipedia (neutral)",
        "expected": (0, 3),
        "text": (
            "The 2026 FIFA World Cup is scheduled to be the 23rd edition of the "
            "FIFA World Cup, the quadrennial international men's football championship "
            "contested by the national teams of the member associations of FIFA. "
            "The tournament is jointly hosted by Canada, Mexico, and the United States "
            "across 16 venues in 16 host cities. 48 teams compete in the expanded format, "
            "up from 32 in previous editions. The opening match will be held at "
            "Estadio Azteca in Mexico City."
        ),
    },
    {
        "id": "editorial-reuters",
        "label": "Reuters (editorial)",
        "expected": (0, 4),
        "text": (
            "British Prime Minister announced his resignation on Sunday after months "
            "of pressure from within his own party. Speaking outside Downing Street, "
            "he said there would be an orderly process to choose his replacement and "
            "that a successor would be in place before the Commons summer recess. "
            "He paid tribute to his family, saying he would now focus on being the "
            "best husband and father. Markets are expected to react when trading "
            "opens on Monday morning."
        ),
    },
    {
        "id": "editorial-ap",
        "label": "AP News (editorial)",
        "expected": (0, 4),
        "text": (
            "European Union leaders agreed Thursday to begin formal negotiations "
            "with Ukraine on its membership bid, a historic step that comes nearly "
            "two years after Russia's full-scale invasion. The decision was reached "
            "at a summit in Brussels after Hungary lifted its veto following hours "
            "of diplomatic pressure. Ukrainian President Zelenskyy called it a "
            "victory but cautioned that the accession process could take years."
        ),
    },
    {
        "id": "tabloid-fear",
        "label": "Tabloid fear article",
        "expected": (5, 10),
        "text": (
            "EXCLUSIVE: Britain faces hottest day EVER as Met Office issues rare red "
            "'extreme heat' warning — temperatures could now climb to 40C this week "
            "with MAJOR disruption to roads, railways and airports. Experts warn "
            "thousands could DIE as hospitals prepare for surge in heat-related "
            "emergencies. Schools ordered to CLOSE early. Are YOU prepared? "
            "Here's what you MUST do to survive the killer heatwave."
        ),
    },
    {
        "id": "tabloid-urgency",
        "label": "Tabloid urgency/FOMO",
        "expected": (5, 10),
        "text": (
            "BREAKING: Your savings account is quietly LOSING money every single day. "
            "Banks are pocketing billions while your hard-earned cash shrinks. "
            "Only 2 days left to switch before the deadline EXPIRES. Thousands have "
            "already moved — don't be the last one holding the bag. Act NOW or watch "
            "your retirement vanish. This is NOT a drill."
        ),
    },
    {
        "id": "marketing-subtle",
        "label": "Marketing (subtle)",
        "expected": (2, 6),
        "text": (
            "There is a difference between using a tool and owning one. Every major "
            "AI platform is built on the former. Your conversations train the next model. "
            "What you ask reveals who you are, and that data is never truly yours. "
            "Cloud storage is access you rent, not a home you own. We built something "
            "different: an AI that runs inside a Trusted Execution Environment where "
            "even the operator cannot read your prompts. Proof is on-chain. Not promised."
        ),
    },
    {
        "id": "marketing-aggressive",
        "label": "Marketing (aggressive)",
        "expected": (6, 10),
        "text": (
            "WARNING: Every AI company is reading your private conversations RIGHT NOW. "
            "Your medical questions. Your financial plans. Your deepest secrets. All "
            "harvested, sold, and fed back into models that profit from YOUR data. "
            "Don't be a victim. Switch to ZDrive before it's too late — the only AI "
            "that CANNOT spy on you. Limited free tier closing soon. Protect yourself NOW."
        ),
    },
]


def scan(url: str, text: str, mode: str) -> dict:
    r = requests.post(
        f"{url}/analyze",
        json={"text": text, "mode": mode},
        timeout=360,
    )
    r.raise_for_status()
    return r.json()


def run(args):
    url = args.url.rstrip("/")
    modes = []
    if args.both:
        modes = ["fast", "deep"]
    elif args.deep:
        modes = ["deep"]
    else:
        modes = ["fast"]

    results = []
    total = len(CORPUS) * len(modes)
    done = 0

    for entry in CORPUS:
        row = {"id": entry["id"], "label": entry["label"], "expected": entry["expected"]}
        for mode in modes:
            done += 1
            tag = "LLM" if mode == "fast" else "TRIBE"
            print(f"[{done}/{total}] {tag}: {entry['label']}...", end=" ", flush=True)
            t0 = time.time()
            try:
                data = scan(url, entry["text"], mode)
                elapsed = time.time() - t0
                row[f"{mode}_mi"] = data["manipulation_index"]
                row[f"{mode}_technique"] = data["dominant_technique"]
                row[f"{mode}_scorer"] = data.get("scorer", mode)
                row[f"{mode}_time"] = round(elapsed, 1)
                print(f"MI={data['manipulation_index']:.1f} ({elapsed:.1f}s)")
            except Exception as e:
                print(f"FAILED: {e}")
                row[f"{mode}_mi"] = None
                row[f"{mode}_technique"] = "error"
                row[f"{mode}_time"] = None
        results.append(row)

    print("\n" + "=" * 90)
    print("CALIBRATION RESULTS")
    print("=" * 90)

    if len(modes) == 1:
        mode = modes[0]
        tag = "LLM" if mode == "fast" else "TRIBE"
        print(f"\n{'Text':<30s} {'Expected':>10s} {tag+' MI':>8s} {'Technique':<20s} {'Pass':>5s}")
        print("-" * 80)
        passed = 0
        for r in results:
            mi = r.get(f"{mode}_mi")
            lo, hi = r["expected"]
            ok = mi is not None and lo <= mi <= hi
            passed += ok
            mi_str = f"{mi:.1f}" if mi is not None else "ERR"
            tech = r.get(f"{mode}_technique", "?")
            mark = "OK" if ok else "FAIL"
            print(f"{r['label']:<30s} {lo}-{hi} {mi_str:>8s} {tech:<20s} {mark:>5s}")
        print(f"\n{passed}/{len(results)} passed")
    else:
        print(f"\n{'Text':<28s} {'Expected':>8s} {'LLM MI':>7s} {'TRIBE MI':>9s} {'Delta':>6s} {'LLM Tech':<15s} {'TRIBE Tech':<15s} {'Pass':>5s}")
        print("-" * 100)
        passed = 0
        for r in results:
            fast_mi = r.get("fast_mi")
            deep_mi = r.get("deep_mi")
            lo, hi = r["expected"]
            fast_ok = fast_mi is not None and lo <= fast_mi <= hi
            deep_ok = deep_mi is not None and lo <= deep_mi <= hi
            ok = fast_ok and deep_ok
            passed += ok
            fast_str = f"{fast_mi:.1f}" if fast_mi is not None else "ERR"
            deep_str = f"{deep_mi:.1f}" if deep_mi is not None else "ERR"
            delta = f"{abs(fast_mi - deep_mi):.1f}" if fast_mi and deep_mi else "?"
            fast_tech = r.get("fast_technique", "?")
            deep_tech = r.get("deep_technique", "?")
            mark = "OK" if ok else "FAIL"
            print(f"{r['label']:<28s} {lo}-{hi} {fast_str:>7s} {deep_str:>9s} {delta:>6s} {fast_tech:<15s} {deep_tech:<15s} {mark:>5s}")
        print(f"\n{passed}/{len(results)} passed (both scorers in expected range)")

    if args.json:
        with open(args.json, "w") as f:
            json.dump(results, f, indent=2)
        print(f"\nResults saved to {args.json}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Calibration test harness")
    p.add_argument("--deep", action="store_true", help="Run TRIBE v2 deep scans")
    p.add_argument("--both", action="store_true", help="Run both LLM and TRIBE v2, compare")
    p.add_argument("--url", default="http://localhost:8000", help="Backend URL")
    p.add_argument("--json", default=None, help="Save results to JSON file")
    run(p.parse_args())
