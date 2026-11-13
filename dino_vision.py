"""
dino_vision.py
--------------
Segmentation + crop pipeline for the DINOv2 feature extractor.

Segmentation stays classical CV (background subtraction + LAB shadow/glare
suppression). Everything downstream -- what the object *is* -- runs through
the DINOv2 embedding (see dino_embedding.py).

Pipeline:
  1. Segmentation: background subtraction against a captured empty-platform
     frame, with LAB-based shadow/glare suppression.
  2. Crop: padded bounding box, background pixels replaced with neutral gray.
  3. Illumination normalization: gray-world white balance on the crop.

Adapted from dino_ai/vision.py for integration into the main AiSourceCode
project.  All config constants are passed as arguments or defined locally.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

import cv2
import numpy as np

from dino_embedding import EmbeddingExtractor


# ---------------------------------------------------------------------------
# Default constants (from dino_ai/config.py)
# ---------------------------------------------------------------------------
BG_DIFF_THRESHOLD = 25
MORPH_KERNEL_SIZE = 5
MIN_OBJECT_AREA = 50
MIN_STABLE_MASK_PIXELS = 80
# Soft warning threshold: objects below this trigger advisory notice
SMALL_OBJECT_WARNING_AREA = 400

# Shadow suppression (LAB-based)
LAB_SHADOW_L_RATIO_MIN = 0.35
LAB_SHADOW_L_RATIO_MAX = 0.95
LAB_SHADOW_AB_TOLERANCE = 12

# Glare suppression (LAB-based)
LAB_GLARE_L_MIN = 225
LAB_GLARE_AB_NEUTRAL_TOLERANCE = 15

# Crop settings
CROP_PADDING_RATIO = 0.12
CROP_BACKGROUND_FILL = (128, 128, 128)


# Pre-allocated morphology kernel
_MORPH_KERNEL = cv2.getStructuringElement(
    cv2.MORPH_ELLIPSE, (MORPH_KERNEL_SIZE, MORPH_KERNEL_SIZE)
)

_BG_CACHE = {
    "bg_ref": None,
    "bg_gray": None,
    "bg_lab": None,
    "l_bg": None,
}


def _get_bg_representations(background_bgr: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return cached (bg_gray, bg_lab, l_bg) to avoid repeating cvtColor on the static background."""
    global _BG_CACHE
    if _BG_CACHE["bg_ref"] is background_bgr and _BG_CACHE["bg_gray"] is not None:
        return _BG_CACHE["bg_gray"], _BG_CACHE["bg_lab"], _BG_CACHE["l_bg"]

    bg_gray = cv2.cvtColor(background_bgr, cv2.COLOR_BGR2GRAY)
    bg_lab = cv2.cvtColor(background_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    l_bg = bg_lab[:, :, 0] + 1e-6

    _BG_CACHE["bg_ref"] = background_bgr
    _BG_CACHE["bg_gray"] = bg_gray
    _BG_CACHE["bg_lab"] = bg_lab
    _BG_CACHE["l_bg"] = l_bg
    return bg_gray, bg_lab, l_bg


def _lab_shadow_and_glare_mask(frame_bgr: np.ndarray, background_bgr: np.ndarray,
                                raw_fg_mask: np.ndarray,
                                bg_lab: Optional[np.ndarray] = None,
                                l_bg: Optional[np.ndarray] = None) -> np.ndarray:
    """LAB-based shadow/glare suppression: L (lightness) is cleanly
    separated from A/B (true color), so a shadow or a specular
    reflection on the scale surface doesn't get pulled into the object
    mask."""
    frame_lab = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    if bg_lab is None or l_bg is None:
        _, bg_lab, l_bg = _get_bg_representations(background_bgr)

    l_ratio = frame_lab[:, :, 0] / l_bg

    ab_drift = (
        np.abs(frame_lab[:, :, 1] - bg_lab[:, :, 1])
        + np.abs(frame_lab[:, :, 2] - bg_lab[:, :, 2])
    )

    is_shadow = (
        (l_ratio >= LAB_SHADOW_L_RATIO_MIN)
        & (l_ratio <= LAB_SHADOW_L_RATIO_MAX)
        & (ab_drift <= LAB_SHADOW_AB_TOLERANCE)
    )

    ab_neutral_distance = np.sqrt(
        (frame_lab[:, :, 1] - 128.0) ** 2 + (frame_lab[:, :, 2] - 128.0) ** 2
    )
    is_glare = (
        (frame_lab[:, :, 0] >= LAB_GLARE_L_MIN)
        & (ab_neutral_distance <= LAB_GLARE_AB_NEUTRAL_TOLERANCE)
        & (np.abs(frame_lab[:, :, 0] - l_bg) <= 45.0)
    )

    cleaned = raw_fg_mask.copy()
    cleaned[is_shadow] = 0
    cleaned[is_glare] = 0
    return cleaned


def segment_object(frame_bgr: np.ndarray, background_bgr: np.ndarray
                    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """Segment the foreground object out of `frame_bgr` given a
    previously captured empty-platform `background_bgr`. Returns
    (mask, largest_contour) or (None, None) if nothing big/stable
    enough was found."""
    if background_bgr is None:
        return None, None

    bg_gray, bg_lab, l_bg = _get_bg_representations(background_bgr)

    frame_gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    diff = cv2.absdiff(frame_gray, bg_gray)
    _, raw_mask = cv2.threshold(diff, BG_DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)

    mask = _lab_shadow_and_glare_mask(frame_bgr, background_bgr, raw_mask, bg_lab=bg_lab, l_bg=l_bg)

    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, _MORPH_KERNEL)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, _MORPH_KERNEL)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None, None

    largest = max(contours, key=cv2.contourArea)
    if cv2.contourArea(largest) < MIN_OBJECT_AREA:
        return None, None

    object_mask = np.zeros_like(mask)
    cv2.drawContours(object_mask, [largest], -1, 255, thickness=cv2.FILLED)

    mask_pixels = int(np.count_nonzero(object_mask))
    if mask_pixels < MIN_STABLE_MASK_PIXELS:
        return None, None

    return object_mask, largest


# ---------------------------------------------------------------------------
# Illumination normalization + object crop
# ---------------------------------------------------------------------------

def _gray_world_white_balance(bgr: np.ndarray, fg_mask: Optional[np.ndarray] = None) -> np.ndarray:
    """Classic gray-world assumption: scales each channel so the mean
    of R, G, B match. Cheap and effective at pulling a warm/cool
    lighting cast back toward neutral before the crop goes into the
    network.

    IMPORTANT: if fg_mask is provided, the per-channel means are computed
    ONLY over foreground (object) pixels -- not the synthetic neutral-gray
    background fill. Including the gray fill in the mean dilutes/weakens
    the correction in proportion to how much of the crop is background,
    which disproportionately under-corrects small/irregularly-shaped
    objects (garlic, chilli) that don't tightly fill their padded bbox.
    """
    img = bgr.astype(np.float32)

    if fg_mask is not None and cv2.countNonZero(fg_mask) > 0:
        fg = fg_mask > 0
        b_mean = img[:, :, 0][fg].mean()
        g_mean = img[:, :, 1][fg].mean()
        r_mean = img[:, :, 2][fg].mean()
    else:
        b_mean, g_mean, r_mean = img[:, :, 0].mean(), img[:, :, 1].mean(), img[:, :, 2].mean()

    gray_mean = (b_mean + g_mean + r_mean) / 3.0
    eps = 1e-6

    # Clamp the correction gain so a large, single-dominant-color object
    # (tomato, capsicum) can't get aggressively desaturated toward gray --
    # gray-world's own known failure mode on saturated, uniformly-colored
    # subjects, independent of the masking issue above.
    MAX_GAIN = 1.5
    MIN_GAIN = 1.0 / MAX_GAIN
    gain_b = np.clip(gray_mean / (b_mean + eps), MIN_GAIN, MAX_GAIN)
    gain_g = np.clip(gray_mean / (g_mean + eps), MIN_GAIN, MAX_GAIN)
    gain_r = np.clip(gray_mean / (r_mean + eps), MIN_GAIN, MAX_GAIN)

    img[:, :, 0] *= gain_b
    img[:, :, 1] *= gain_g
    img[:, :, 2] *= gain_r
    return np.clip(img, 0, 255).astype(np.uint8)


def get_object_crop_bbox(
    frame_bgr: np.ndarray,
    mask: np.ndarray,
    contour: np.ndarray,
) -> Tuple[int, int, int, int]:
    """Compute padded bounding box (x0, y0, x1, y1) around contour for object crop."""
    x, y, w, h = cv2.boundingRect(contour)
    pad_x = max(14, int(w * max(0.18, CROP_PADDING_RATIO)))
    pad_y = max(14, int(h * max(0.18, CROP_PADDING_RATIO)))
    x0 = max(0, x - pad_x)
    y0 = max(0, y - pad_y)
    x1 = min(frame_bgr.shape[1], x + w + pad_x)
    y1 = min(frame_bgr.shape[0], y + h + pad_y)
    return x0, y0, x1, y1


def _fill_mask_holes(mask: np.ndarray) -> np.ndarray:
    """Fills internal holes in a binary mask while preserving external boundaries."""
    if mask is None or cv2.countNonZero(mask) == 0:
        return mask
    h, w = mask.shape[:2]
    padded = np.zeros((h + 2, w + 2), dtype=np.uint8)
    padded[1 : h + 1, 1 : w + 1] = mask.astype(np.uint8)
    inv = cv2.bitwise_not(padded)
    cv2.floodFill(inv, None, (0, 0), 0)
    internal_holes = inv[1 : h + 1, 1 : w + 1]
    return cv2.bitwise_or(mask.astype(np.uint8), internal_holes)


def crop_object_for_embedding(frame_bgr: np.ndarray, mask: np.ndarray,
                               contour: np.ndarray,
                               bbox: Optional[Tuple[int, int, int, int]] = None) -> np.ndarray:
    """
    Produce the exact crop that gets fed to the CNN:
      1. Padded bounding box around the object contour.
      2. Background pixels replaced with neutral gray.
      3. Gray-world white balance to reduce lighting drift.
    """
    if bbox is not None:
        x0, y0, x1, y1 = bbox
    else:
        x0, y0, x1, y1 = get_object_crop_bbox(frame_bgr, mask, contour)

    crop = frame_bgr[y0:y1, x0:x1].copy()
    raw_crop_mask = mask[y0:y1, x0:x1]
    # Fill internal holes inside the crop mask so glare/plastic highlights don't punch gray holes!
    crop_mask = _fill_mask_holes(raw_crop_mask)

    background_fill = np.full_like(crop, CROP_BACKGROUND_FILL)
    object_only = np.where(crop_mask[:, :, None] > 0, crop, background_fill)

    return _gray_world_white_balance(object_only, fg_mask=crop_mask)


# ---------------------------------------------------------------------------
# High-level helpers for the main app
# ---------------------------------------------------------------------------

def detect_object_box(
    frame_bgr: np.ndarray,
    background_bgr: np.ndarray,
    polygon: Optional[list] = None,
) -> Tuple[Optional[Tuple[int, int, int, int]], bool, float]:
    """
    Lightweight helper to segment the foreground object and return its
    padded bounding box, small object warning flag, and area without
    running DINOv2 neural inference.

    Returns:
        (bbox, is_small_warning, area) or (None, False, 0.0)
    """
    mask, contour = segment_object(frame_bgr, background_bgr)
    if mask is None or contour is None:
        return None, False, 0.0

    if polygon is not None and len(polygon) >= 3:
        roi_mask = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
        cv2.fillPoly(roi_mask, [np.array(polygon, dtype=np.int32)], 255)
        mask = cv2.bitwise_and(mask, roi_mask)
        if cv2.countNonZero(mask) < MIN_OBJECT_AREA:
            return None, False, 0.0
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None, False, 0.0
        contour = max(contours, key=cv2.contourArea)

    bbox = get_object_crop_bbox(frame_bgr, mask, contour)
    area = float(cv2.countNonZero(mask))
    is_small = bool(area < SMALL_OBJECT_WARNING_AREA)
    return bbox, is_small, area


def crop_polygon_for_embedding(frame_bgr: np.ndarray, polygon: list) -> Optional[np.ndarray]:
    """
    Produce a crop of the polygon ROI when no individual foreground object
    contour can be isolated by background subtraction (e.g. low contrast, lighting drift).
    Applies gray-world white balance and returns the BGR crop.
    """
    if not polygon or len(polygon) < 3:
        return None
    pts = np.array(polygon, dtype=np.int32)
    x, y, w, h = cv2.boundingRect(pts)
    if w <= 0 or h <= 0:
        return None
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(frame_bgr.shape[1], x + w)
    y1 = min(frame_bgr.shape[0], y + h)
    crop = frame_bgr[y0:y1, x0:x1].copy()
    return _gray_world_white_balance(crop)


def extract_dino_embedding(frame_bgr: np.ndarray, background_bgr: np.ndarray,
                            polygon: Optional[list] = None,
                            for_training: bool = False,
                            extractor: Optional[EmbeddingExtractor] = None,
                            return_details: bool = False,
                            ):
    """
    All-in-one helper: segment the object, crop it, and run through DINOv2.

    Args:
        frame_bgr: Live camera frame.
        background_bgr: Empty-tray reference frame.
        polygon: Camera ROI polygon (used to restrict segmentation area).
        for_training: If True, uses augmented embedding for robustness.
        extractor: Optional EmbeddingExtractor instance (uses singleton if None).
        return_details: If True, returns (embedding, bbox, is_small_warning, details).
                        If False (default), returns embedding or None.

    Returns:
        L2-normalized 384-dim embedding vector (if return_details is False),
        or Tuple[Optional[np.ndarray], Optional[Tuple[int, int, int, int]], bool, dict].
    """
    crop = None
    bbox = None
    obj_area = 0.0
    is_small_warning = False

    mask, contour = segment_object(frame_bgr, background_bgr)
    if mask is not None:
        if polygon is not None and len(polygon) >= 3:
            roi_mask = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
            cv2.fillPoly(roi_mask, [np.array(polygon, dtype=np.int32)], 255)
            mask = cv2.bitwise_and(mask, roi_mask)
            if cv2.countNonZero(mask) >= MIN_OBJECT_AREA:
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    contour = max(contours, key=cv2.contourArea)
                    bbox = get_object_crop_bbox(frame_bgr, mask, contour)
                    obj_area = float(cv2.countNonZero(mask))
                    is_small_warning = bool(obj_area < SMALL_OBJECT_WARNING_AREA)
                    crop = crop_object_for_embedding(frame_bgr, mask, contour, bbox=bbox)
        else:
            bbox = get_object_crop_bbox(frame_bgr, mask, contour)
            obj_area = float(cv2.countNonZero(mask))
            is_small_warning = bool(obj_area < SMALL_OBJECT_WARNING_AREA)
            crop = crop_object_for_embedding(frame_bgr, mask, contour, bbox=bbox)

    # Fallback to polygon ROI crop if background subtraction did not isolate a contour
    if crop is None and polygon is not None and len(polygon) >= 3:
        crop = crop_polygon_for_embedding(frame_bgr, polygon)

    if crop is None:
        if return_details:
            return None, None, False, {"reason": "no_crop_possible"}
        return None

    ext = extractor or EmbeddingExtractor.instance()

    if for_training:
        emb = ext.embed_with_augmentation(crop)
    else:
        emb = ext.embed(crop)

    if return_details:
        details = {
            "bbox": bbox,
            "area": obj_area,
            "is_small_warning": is_small_warning,
            "reason": "tight_crop" if bbox is not None else "polygon_roi_crop",
        }
        return emb, bbox, is_small_warning, details

    return emb


def extract_dino_pose_variants(
    frame_bgr: np.ndarray,
    background_bgr: np.ndarray,
    polygon: Optional[list] = None,
    extractor: Optional[EmbeddingExtractor] = None,
) -> List[np.ndarray]:
    """
    Extract multiple synthetic pose variant embeddings for training from a single frame.
    Segments the object, crops it, and runs it through embed_pose_variants().

    Returns:
        List of L2-normalized 384-dim embedding vectors, or empty list if no crop possible.
    """
    crop = None
    mask, contour = segment_object(frame_bgr, background_bgr)
    if mask is not None:
        if polygon is not None and len(polygon) >= 3:
            roi_mask = np.zeros(frame_bgr.shape[:2], dtype=np.uint8)
            cv2.fillPoly(roi_mask, [np.array(polygon, dtype=np.int32)], 255)
            mask = cv2.bitwise_and(mask, roi_mask)
            if cv2.countNonZero(mask) >= MIN_OBJECT_AREA:
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    contour = max(contours, key=cv2.contourArea)
                    crop = crop_object_for_embedding(frame_bgr, mask, contour)
        else:
            crop = crop_object_for_embedding(frame_bgr, mask, contour)

    # Fallback to polygon ROI crop if background subtraction did not isolate a contour
    if crop is None and polygon is not None and len(polygon) >= 3:
        crop = crop_polygon_for_embedding(frame_bgr, polygon)

    if crop is None:
        return []

    ext = extractor or EmbeddingExtractor.instance()
    return ext.embed_pose_variants(crop)
