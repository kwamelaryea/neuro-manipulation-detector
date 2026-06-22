"""Tests for ROI vertex mapping and z-scored activation extraction.

With population z-scoring, roi_means returns z-scores (unbounded, signed)
rather than [0,1] values. Tests verify structure and z-behavior.
"""
import numpy as np

from roi import get_roi_vertex_indices, roi_means, EMOTIONAL_ROIS, CONTROL_ROIS, LIMBIC_ROIS, PFC_ROIS


def test_roi_index_map_covers_required_regions():
    idx = get_roi_vertex_indices()
    for roi in EMOTIONAL_ROIS + CONTROL_ROIS:
        assert roi in idx, f"missing ROI: {roi}"
        assert len(idx[roi]) > 0
        assert max(idx[roi]) < 20484


def test_roi_means_returns_all_rois():
    idx = get_roi_vertex_indices()
    acts = np.random.randn(5, 20484).astype(np.float32) * 0.2
    means = roi_means(acts, idx)
    for roi in EMOTIONAL_ROIS + CONTROL_ROIS:
        assert roi in means
        assert isinstance(means[roi], float)


def test_roi_means_z_scores_are_signed():
    """Z-scored values can be negative (below neutral baseline)."""
    idx = get_roi_vertex_indices()
    acts = np.random.randn(5, 20484).astype(np.float32) * 0.3 - 0.5
    means = roi_means(acts, idx)
    has_negative = any(v < 0 for v in means.values())
    assert has_negative, "z-scored means should include negative values for below-baseline input"


def test_roi_vertex_indices_within_bounds():
    idx = get_roi_vertex_indices()
    for roi, verts in idx.items():
        assert all(0 <= v < 20484 for v in verts), f"{roi} has out-of-bounds vertices"


def test_backward_compat_aliases():
    assert LIMBIC_ROIS == EMOTIONAL_ROIS
    assert PFC_ROIS == CONTROL_ROIS
