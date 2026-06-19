import numpy as np

from roi import get_roi_vertex_indices, roi_means, LIMBIC_ROIS, PFC_ROIS


def test_roi_index_map_covers_required_regions():
    idx = get_roi_vertex_indices()
    for roi in LIMBIC_ROIS + PFC_ROIS:
        assert roi in idx, f"missing ROI: {roi}"
        assert len(idx[roi]) > 0
        assert max(idx[roi]) < 20484


def test_roi_means_shapes():
    idx = get_roi_vertex_indices()
    acts = np.random.rand(5, 20484)
    means = roi_means(acts, idx)
    for roi in LIMBIC_ROIS + PFC_ROIS:
        assert roi in means
        assert isinstance(means[roi], float)
        assert 0.0 <= means[roi] <= 1.0


def test_roi_means_uniform_matrix_returns_half():
    idx = get_roi_vertex_indices()
    # Uniform matrix normalizes to all-0 (lo==hi branch), result = 0.0
    acts = np.ones((3, 20484))
    means = roi_means(acts, idx)
    for roi in LIMBIC_ROIS + PFC_ROIS:
        assert means[roi] == 0.0


def test_roi_vertex_indices_within_bounds():
    idx = get_roi_vertex_indices()
    for roi, verts in idx.items():
        assert all(0 <= v < 20484 for v in verts), f"{roi} has out-of-bounds vertices"
