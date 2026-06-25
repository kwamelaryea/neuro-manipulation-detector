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


def test_long_text_dilution_regression():
    """Manipulative peaks in mostly-neutral long text must not be diluted.

    Simulates a long article (100 time steps) where 10% of steps have
    elevated emotional activation. The old grand-mean aggregation would
    wash these peaks out; the 90th-percentile fix must preserve them.
    """
    idx = get_roi_vertex_indices()
    baseline_mean, baseline_std = np.zeros(20484), np.ones(20484)

    rng = np.random.default_rng(42)
    acts = rng.normal(loc=0, scale=1, size=(100, 20484)).astype(np.float64)
    acts *= baseline_std
    acts += baseline_mean

    peak_rows = range(90, 100)
    for roi in EMOTIONAL_ROIS:
        for v in idx[roi]:
            for t in peak_rows:
                acts[t, v] += 3.0 * baseline_std[v]

    means = roi_means(acts, idx)
    for roi in EMOTIONAL_ROIS:
        assert means[roi] > 1.5, (
            f"{roi} z-score {means[roi]:.2f} too low — "
            f"peaks diluted by neutral body text"
        )

    grand_mean_would_be = {roi: float(acts[:, list(idx[roi])].mean()) for roi in EMOTIONAL_ROIS}
    for roi in EMOTIONAL_ROIS:
        assert means[roi] > grand_mean_would_be[roi], (
            f"{roi}: percentile ({means[roi]:.2f}) should exceed "
            f"grand mean ({grand_mean_would_be[roi]:.2f})"
        )


def test_neutral_long_text_stays_low():
    """Purely neutral long text should not score high with percentile aggregation."""
    idx = get_roi_vertex_indices()
    rng = np.random.default_rng(99)
    acts = rng.normal(loc=0, scale=0.5, size=(100, 20484)).astype(np.float64)
    means = roi_means(acts, idx)
    for roi in EMOTIONAL_ROIS + CONTROL_ROIS:
        assert means[roi] < 2.0, (
            f"{roi} z-score {means[roi]:.2f} unexpectedly high for neutral text"
        )
