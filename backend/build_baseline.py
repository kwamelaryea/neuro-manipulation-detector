"""Build the z-scoring baseline from a neutral reference corpus.

Runs each neutral text through TRIBE v2 on Modal, collects raw activations,
computes per-vertex mean and std, saves as .npy files.

Usage:
  python build_baseline.py                  # run all, save baseline
  python build_baseline.py --resume         # skip already-cached texts
  python build_baseline.py --dry-run        # print corpus, don't run

Output:
  calibration/baseline_mean.npy   (20484,)
  calibration/baseline_std.npy    (20484,)
  calibration/baseline_meta.json  corpus info, per-text stats
"""
import argparse
import json
import os
import tempfile
import time
from pathlib import Path

import numpy as np

NEUTRAL_CORPUS = [
    {
        "id": "academic-finance",
        "text": "The committee meets quarterly to review audited financial statements and compliance reports. Minutes from the previous session were approved unanimously. The treasurer presented the annual budget variance analysis, noting a 2.3% underspend in operational expenses. No corrective actions were deemed necessary.",
    },
    {
        "id": "academic-biology",
        "text": "Mitochondria are membrane-bound organelles found in the cytoplasm of eukaryotic cells. They generate most of the cell's supply of adenosine triphosphate, used as a source of chemical energy. The number of mitochondria in a cell varies widely by organism, tissue, and cell type.",
    },
    {
        "id": "academic-history",
        "text": "The Treaty of Westphalia, signed in 1648, ended the Thirty Years' War in the Holy Roman Empire and the Eighty Years' War between Spain and the Dutch Republic. It established the principle of state sovereignty and is considered a foundational event in the development of the modern international system.",
    },
    {
        "id": "academic-chemistry",
        "text": "The periodic table organizes chemical elements by their atomic number, electron configuration, and recurring chemical properties. Elements in the same column share similar valence electron configurations and tend to exhibit comparable chemical behavior. The table was first proposed by Dmitri Mendeleev in 1869.",
    },
    {
        "id": "academic-law",
        "text": "Contract law governs agreements between parties that create mutual obligations enforceable by law. The basic elements required for a valid contract include offer, acceptance, consideration, and mutual assent. Contracts may be written or oral, though certain types must be in writing under the statute of frauds.",
    },
    {
        "id": "wiki-geography",
        "text": "Portugal is a country located on the Iberian Peninsula in southwestern Europe. It is bordered by Spain to the north and east and the Atlantic Ocean to the west and south. The country has a population of approximately 10.3 million and its capital and largest city is Lisbon.",
    },
    {
        "id": "wiki-technology",
        "text": "The Internet is a global system of interconnected computer networks that uses the Internet protocol suite to communicate between networks and devices. It carries a vast range of information resources and services, including the interlinked hypertext documents and applications of the World Wide Web.",
    },
    {
        "id": "wiki-sports",
        "text": "The 2026 FIFA World Cup is the 23rd edition of the FIFA World Cup, the quadrennial international men's football championship. The tournament is jointly hosted by Canada, Mexico, and the United States across 16 venues. 48 teams compete in the expanded format, up from 32 in previous editions.",
    },
    {
        "id": "wiki-music",
        "text": "Jazz is a music genre that originated in the African-American communities of New Orleans, Louisiana, in the late 19th and early 20th centuries. It developed from roots in blues and ragtime and incorporates elements from European and African musical traditions. Jazz is characterized by swing and blue notes, complex chords, and improvisation.",
    },
    {
        "id": "wiki-architecture",
        "text": "Gothic architecture is a style that flourished in Europe during the High and Late Middle Ages. It evolved from Romanesque architecture and was succeeded by Renaissance architecture. Characteristic features include pointed arches, ribbed vaults, flying buttresses, and large stained glass windows.",
    },
    {
        "id": "wire-politics",
        "text": "The European Council concluded its two-day summit in Brussels on Thursday, reaching agreement on the next seven-year budget framework. The compromise allocates additional funding to defense and migration management while maintaining existing commitments to agricultural subsidies. The agreement must still be ratified by the European Parliament.",
    },
    {
        "id": "wire-economics",
        "text": "The central bank held interest rates steady at its June meeting, as expected by most economists. The accompanying statement noted that inflation has moderated but remains above the 2% target. Policymakers signaled that the pace of future rate adjustments will depend on incoming economic data.",
    },
    {
        "id": "wire-science",
        "text": "Researchers at the University of Cambridge published findings in Nature describing a new method for sequencing ancient DNA from soil samples. The technique allows reconstruction of ecosystems from up to 400,000 years ago without requiring preserved bone fragments. The team analyzed sediment from caves in southern France.",
    },
    {
        "id": "wire-business",
        "text": "The semiconductor manufacturer reported quarterly revenue of $14.2 billion, exceeding analyst estimates of $13.8 billion. The company attributed the growth to continued demand for chips used in data centers and artificial intelligence applications. Shares rose 3.2% in after-hours trading.",
    },
    {
        "id": "wire-diplomacy",
        "text": "Representatives from 12 Pacific Island nations met in Suva, Fiji, to discuss a regional framework for climate adaptation funding. The proposed mechanism would pool contributions from international donors and distribute grants based on vulnerability assessments. A final agreement is expected at next month's follow-up session.",
    },
    {
        "id": "technical-api",
        "text": "The REST API accepts JSON payloads via HTTP POST to the /analyze endpoint. Authentication is handled via Bearer tokens in the Authorization header. Rate limiting is set to 100 requests per minute per API key. Responses include a status code, timestamp, and the analysis result object.",
    },
    {
        "id": "technical-database",
        "text": "PostgreSQL is an open-source relational database management system emphasizing extensibility and SQL compliance. It supports both SQL querying for relational data and JSON querying for non-relational data. The system uses multiversion concurrency control to handle simultaneous transactions.",
    },
    {
        "id": "technical-math",
        "text": "The Pythagorean theorem states that in a right triangle, the square of the length of the hypotenuse equals the sum of the squares of the other two sides. This can be written as a squared plus b squared equals c squared, where c represents the hypotenuse and a and b represent the other two sides.",
    },
    {
        "id": "instructions-recipe",
        "text": "Preheat the oven to 180 degrees Celsius. Combine flour, sugar, and salt in a large bowl. In a separate bowl, whisk together eggs, milk, and melted butter. Add the wet ingredients to the dry ingredients and stir until just combined. Pour the batter into a greased baking pan and bake for 25 minutes.",
    },
    {
        "id": "instructions-assembly",
        "text": "Remove all parts from the packaging and verify against the included parts list. Attach the side panels to the base using the provided hex bolts and Allen key. Ensure all bolts are finger-tight before final tightening. Slide the shelf brackets into the pre-drilled slots and secure with locking clips.",
    },
    {
        "id": "encyclopedia-animal",
        "text": "The African elephant is the largest living terrestrial animal. Adult males can reach a height of 3.3 meters at the shoulder and weigh up to 6,000 kilograms. They are herbivores and consume grasses, roots, bark, and fruit. African elephants live in matriarchal family groups led by the oldest female.",
    },
    {
        "id": "encyclopedia-astronomy",
        "text": "The Sun is a G-type main-sequence star that comprises approximately 99.86% of the total mass of the Solar System. Its diameter is about 1.39 million kilometers, roughly 109 times that of Earth. Nuclear fusion reactions in the Sun's core convert hydrogen into helium, releasing energy in the process.",
    },
    {
        "id": "legal-terms",
        "text": "This agreement shall be governed by and construed in accordance with the laws of the State of Delaware. Any dispute arising under this agreement shall be resolved through binding arbitration administered by the American Arbitration Association. The prevailing party shall be entitled to recover reasonable attorneys' fees.",
    },
    {
        "id": "weather-report",
        "text": "Partly cloudy skies are expected through midweek with temperatures reaching 24 degrees Celsius on Tuesday and 26 degrees on Wednesday. A cold front approaching from the northwest may bring scattered showers by Thursday afternoon. Weekend conditions are forecast to be dry with light winds from the southwest.",
    },
    {
        "id": "sports-recap",
        "text": "The match ended in a 1-1 draw after 90 minutes. The home side took the lead in the 34th minute through a header from a corner kick. The visitors equalized early in the second half with a low strike from the edge of the area. Both teams had chances to win in the closing stages but neither could find the breakthrough.",
    },
    {
        "id": "travel-guide",
        "text": "The historic district is best explored on foot. Walking tours depart from the main square at 10am and 2pm daily. Key landmarks include the 14th-century cathedral, the former royal palace, and the covered market, which has operated continuously since 1882. Comfortable shoes are recommended as the streets are paved with cobblestones.",
    },
    {
        "id": "medical-reference",
        "text": "Hypertension is defined as a sustained systolic blood pressure above 140 mmHg or diastolic pressure above 90 mmHg. Risk factors include age, family history, obesity, high sodium intake, and physical inactivity. First-line treatment typically involves lifestyle modifications followed by pharmacological intervention if targets are not met.",
    },
    {
        "id": "financial-report",
        "text": "Operating expenses for the quarter totaled $42.3 million, a 6% increase from the prior year period. The increase was primarily attributable to higher personnel costs associated with the expansion of the engineering team. Adjusted EBITDA margin improved to 18.4% from 16.9% in the year-ago quarter.",
    },
    {
        "id": "research-abstract",
        "text": "This study examined the relationship between sleep duration and cognitive performance in a cohort of 2,400 adults aged 45 to 65. Participants who reported sleeping fewer than six hours per night scored significantly lower on tests of executive function and working memory compared to those sleeping seven to eight hours.",
    },
    {
        "id": "census-data",
        "text": "According to the most recent census, the metropolitan area has a population of 2.8 million residents. The median household income is $58,400 per year. Approximately 34% of residents hold a bachelor's degree or higher. The largest employment sectors are healthcare, education, and professional services.",
    },
]


def get_raw_activations(scorer, text: str) -> np.ndarray:
    """Run TRIBE v2 and return the raw (T, 20484) activation matrix."""
    import tempfile, os
    result = scorer.probe.remote(text)
    # probe() returns stats, but we need the actual array.
    # We'll use score_raw() instead — need to add it.
    # For now, we'll collect stats and build baseline from multiple probes.
    return result


def run(args):
    import modal

    out_dir = Path("calibration")
    out_dir.mkdir(exist_ok=True)

    cache_dir = out_dir / "raw_activations"
    cache_dir.mkdir(exist_ok=True)

    TribeScorer = modal.Cls.from_name("nmd-tribe-scorer", "TribeScorer")
    scorer = TribeScorer()

    # We need the actual activation arrays, not just stats.
    # Add a method that returns the raw array serialized.
    # For now, use score_raw which we'll add.
    print(f"Building baseline from {len(NEUTRAL_CORPUS)} neutral texts...")
    print(f"Each takes ~30-35s on Modal A10G\n")

    if args.dry_run:
        for i, entry in enumerate(NEUTRAL_CORPUS):
            print(f"  [{i+1}] {entry['id']}: {entry['text'][:60]}...")
        print(f"\n{len(NEUTRAL_CORPUS)} texts, estimated time: {len(NEUTRAL_CORPUS) * 35 // 60} min")
        return

    all_acts = []
    meta = []

    for i, entry in enumerate(NEUTRAL_CORPUS):
        cache_file = cache_dir / f"{entry['id']}.npy"

        if args.resume and cache_file.exists():
            print(f"[{i+1}/{len(NEUTRAL_CORPUS)}] {entry['id']} (cached)")
            acts = np.load(cache_file)
        else:
            print(f"[{i+1}/{len(NEUTRAL_CORPUS)}] {entry['id']}...", end=" ", flush=True)
            t0 = time.time()
            # Get raw activations via score_raw method
            raw = scorer.score_raw.remote(entry["text"])
            acts = np.array(raw["activations"], dtype=np.float32)
            elapsed = time.time() - t0
            np.save(cache_file, acts)
            print(f"shape={acts.shape} min={acts.min():.3f} max={acts.max():.3f} ({elapsed:.1f}s)")

        all_acts.append(acts)
        meta.append({
            "id": entry["id"],
            "shape": list(acts.shape),
            "min": float(acts.min()),
            "max": float(acts.max()),
            "mean": float(acts.mean()),
            "std": float(acts.std()),
        })

    # Compute per-vertex statistics across ALL neutral texts
    # Stack: each text has (T_i, 20484), concatenate along time axis
    stacked = np.concatenate(all_acts, axis=0)  # (sum(T_i), 20484)
    print(f"\nStacked activations: {stacked.shape}")

    vertex_mean = stacked.mean(axis=0)  # (20484,)
    vertex_std = stacked.std(axis=0)    # (20484,)
    vertex_std = np.maximum(vertex_std, 1e-6)  # prevent div-by-zero

    np.save(out_dir / "baseline_mean.npy", vertex_mean)
    np.save(out_dir / "baseline_std.npy", vertex_std)

    baseline_meta = {
        "n_texts": len(NEUTRAL_CORPUS),
        "total_timepoints": int(stacked.shape[0]),
        "vertex_mean_range": [float(vertex_mean.min()), float(vertex_mean.max())],
        "vertex_std_range": [float(vertex_std.min()), float(vertex_std.max())],
        "per_text": meta,
    }
    with open(out_dir / "baseline_meta.json", "w") as f:
        json.dump(baseline_meta, f, indent=2)

    print(f"\nBaseline saved:")
    print(f"  calibration/baseline_mean.npy  {vertex_mean.shape}")
    print(f"  calibration/baseline_std.npy   {vertex_std.shape}")
    print(f"  calibration/baseline_meta.json")
    print(f"\nVertex mean range: [{vertex_mean.min():.4f}, {vertex_mean.max():.4f}]")
    print(f"Vertex std range:  [{vertex_std.min():.4f}, {vertex_std.max():.4f}]")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="Build z-scoring baseline from neutral corpus")
    p.add_argument("--resume", action="store_true", help="Skip already-cached texts")
    p.add_argument("--dry-run", action="store_true", help="Print corpus without running")
    run(p.parse_args())
