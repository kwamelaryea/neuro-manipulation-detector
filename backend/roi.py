"""Map TRIBE v2 (T, 20484) fsaverage5 vertex activations to ROI z-scores
using the Destrieux surface atlas via nilearn.

Phase 2 calibration (2026-06-22): replaced per-sample min-max normalization
with population z-scoring against a neutral reference baseline (30 texts).
Revised ROIs based on TRIBE v2 paper empirical findings (Figures 5-6):
  - Emotional-salience axis: insula, TPJ, MTG (+ parahippocampal retained)
  - Linguistic-control axis: Broca45, STS, dlPFC, ACC

Destrieux label IDs (bilateral, same for both hemispheres):
  insula               → 17, 18, 48, 49, 50
  tpj                  → 25 G_pariet_inf-Angular, 36 G_temp_sup-Plan_tempo
  mtg                  → 38 G_temporal_middle
  parahippocampal      → 23 G_oc-temp_med-Parahip
  broca45              → 14 G_front_inf-Triangul, 12 G_front_inf-Opercular
  sts                  → 73 S_temporal_sup
  dlpfc                → 15 G_front_middle, 54 S_front_middle
  acc                  → 6 G_and_S_cingul-Ant, 7 G_and_S_cingul-Mid-Ant
"""
from functools import lru_cache
from pathlib import Path

import numpy as np
from nilearn import datasets

EMOTIONAL_ROIS = ("insula", "tpj", "mtg", "parahippocampal")
CONTROL_ROIS = ("broca45", "sts", "dlpfc", "acc")

# Keep old names as aliases for backward compat in AnalyzeResponse
LIMBIC_ROIS = EMOTIONAL_ROIS
PFC_ROIS = CONTROL_ROIS

VERTICES_PER_HEMI = 10242  # fsaverage5

_DESTRIEUX_IDS: dict[str, list[int]] = {
    "insula":           [17, 18, 48, 49, 50],
    "tpj":              [25, 36],
    "mtg":              [38],
    "parahippocampal":  [23],
    "broca45":          [12, 14],
    "sts":              [73],
    "dlpfc":            [15, 54],
    "acc":              [6, 7],
}

_BASELINE_DIR = Path(__file__).parent / "calibration"
if not _BASELINE_DIR.exists():
    _BASELINE_DIR = Path("/root/calibration")


@lru_cache(maxsize=1)
def _load_baseline() -> tuple[np.ndarray, np.ndarray]:
    """Load per-vertex mean and std from the neutral reference corpus."""
    mean_path = _BASELINE_DIR / "baseline_mean.npy"
    std_path = _BASELINE_DIR / "baseline_std.npy"
    if not mean_path.exists() or not std_path.exists():
        return None, None
    return np.load(mean_path), np.load(std_path)


@lru_cache(maxsize=1)
def get_roi_vertex_indices() -> dict[str, tuple[int, ...]]:
    atlas = datasets.fetch_atlas_surf_destrieux()
    map_lh = atlas["map_left"]
    map_rh = atlas["map_right"]

    all_rois = EMOTIONAL_ROIS + CONTROL_ROIS
    index_map: dict[str, list[int]] = {roi: [] for roi in all_rois}

    for roi in index_map:
        label_ids = _DESTRIEUX_IDS.get(roi, [])
        for lid in label_ids:
            lh_verts = np.where(map_lh == lid)[0]
            index_map[roi].extend(int(v) for v in lh_verts)
            rh_verts = np.where(map_rh == lid)[0]
            index_map[roi].extend(int(v) + VERTICES_PER_HEMI for v in rh_verts)

    return {roi: tuple(v) for roi, v in index_map.items()}


def roi_means(activations: np.ndarray, index_map: dict[str, tuple[int, ...]]) -> dict[str, float]:
    """Per-ROI z-scored activation means, relative to neutral baseline.

    If baseline files exist: z-score each vertex against population stats,
    then average z-scores over time and ROI vertices. Positive z = this text
    activates this region more than neutral text does.

    If no baseline: fall back to per-sample min-max (legacy behavior).
    """
    a = activations.astype(np.float64)

    baseline_mean, baseline_std = _load_baseline()
    if baseline_mean is not None:
        a = (a - baseline_mean) / (baseline_std + 1e-6)
    else:
        lo, hi = a.min(), a.max()
        if hi > lo:
            a = (a - lo) / (hi - lo)
        else:
            a = np.zeros_like(a)

    means: dict[str, float] = {}
    for roi, idx in index_map.items():
        if not idx:
            means[roi] = 0.0
            continue
        roi_acts = a[:, list(idx)]
        means[roi] = float(roi_acts.mean())
    return means
