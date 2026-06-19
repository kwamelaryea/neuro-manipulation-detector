"""Map TRIBE v2 (T, 20484) fsaverage5 vertex activations to ROI means
using the Destrieux surface atlas via nilearn (fetch_atlas_surf_destrieux).

nilearn 0.11+ dropped 'annot_left/right' from fetch_surf_fsaverage; the
Destrieux atlas is the correct replacement that ships via fetch_atlas_surf_destrieux.

Desikan-style name → Destrieux label IDs (bilateral):
  insula           → 17 G_Ins_lg_and_S_cent_ins, 18 G_insular_short,
                     48 S_circular_insula_ant, 49 S_circular_insula_inf, 50 S_circular_insula_sup
  entorhinal       → 44 Pole_temporal (nearest surface proxy)
  parahippocampal  → 23 G_oc-temp_med-Parahip
  rostralmiddlefrontal → 15 G_front_middle, 54 S_front_middle
  caudalanteriorcingulate  → 7  G_and_S_cingul-Mid-Ant
  rostralanteriorcingulate → 6  G_and_S_cingul-Ant
"""
from functools import lru_cache

import numpy as np
from nilearn import datasets

LIMBIC_ROIS = ("insula", "entorhinal", "parahippocampal")
PFC_ROIS = ("rostralmiddlefrontal", "caudalanteriorcingulate", "rostralanteriorcingulate")

VERTICES_PER_HEMI = 10242  # fsaverage5

# Destrieux label indices for each logical ROI (same for both hemispheres).
_DESTRIEUX_IDS: dict[str, list[int]] = {
    "insula":                  [17, 18, 48, 49, 50],
    "entorhinal":              [44],
    "parahippocampal":         [23],
    "rostralmiddlefrontal":    [15, 54],
    "caudalanteriorcingulate":  [7],
    "rostralanteriorcingulate": [6],
}


@lru_cache(maxsize=1)
def get_roi_vertex_indices() -> dict[str, tuple[int, ...]]:
    """Return {roi_name: (vertex indices into the 0..20483 concatenated array)}.

    Concatenation: left hemisphere [0..10241], right [10242..20483].
    """
    atlas = datasets.fetch_atlas_surf_destrieux()
    map_lh = atlas["map_left"]   # shape (10242,) — per-vertex Destrieux label id
    map_rh = atlas["map_right"]  # shape (10242,)

    index_map: dict[str, list[int]] = {roi: [] for roi in LIMBIC_ROIS + PFC_ROIS}

    for roi in index_map:
        label_ids = _DESTRIEUX_IDS.get(roi, [])
        for lid in label_ids:
            lh_verts = np.where(map_lh == lid)[0]
            index_map[roi].extend(int(v) for v in lh_verts)
            rh_verts = np.where(map_rh == lid)[0]
            index_map[roi].extend(int(v) + VERTICES_PER_HEMI for v in rh_verts)

    return {roi: tuple(v) for roi, v in index_map.items()}


def roi_means(activations: np.ndarray, index_map: dict[str, tuple[int, ...]]) -> dict[str, float]:
    """Mean activation per ROI, averaged over time and vertices, normalized to 0–1.

    activations: (T, 20484)
    """
    a = activations.astype(np.float64)
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
