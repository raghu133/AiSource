"""
Color Consistency Engine for POS Produce & Grocery Recognition.
Provides robust color descriptor extraction (HSV + Lab), background/specular suppression,
multi-color family profiling, and color compatibility gating to prevent cross-color
misclassifications (e.g., Green Tomato vs Red/Orange Tomato).
"""

from typing import Dict, List, Optional, Sequence, Set, Tuple
import cv2
import numpy as np

# 5 Broad Produce Color Families
COLOR_FAMILIES: List[str] = [
    "RED",          # Red, Crimson, Magenta, Scarlet
    "GREEN",        # Green, Lime, Olive, Cyan/Teal
    "YELLOW",       # Yellow, Orange, Gold, Amber
    "PURPLE/DARK",  # Purple, Blue, Violet, Black, Dark Navy
    "WHITE/BROWN",  # White, Cream, Gray, Brown, Earthy, Neutral
]

CHROMATIC_FAMILIES: Set[str] = {
    "RED",
    "GREEN",
    "YELLOW",
    "PURPLE/DARK",
}

# Perceptually adjacent / compatible color families (accounting for botanical layers, lighting shift and ripeness)
NEIGHBOR_FAMILIES: Dict[str, Set[str]] = {
    "RED": {"RED", "YELLOW", "PURPLE/DARK"},
    "YELLOW": {"YELLOW", "RED", "GREEN", "WHITE/BROWN"},
    "GREEN": {"GREEN", "YELLOW", "WHITE/BROWN"},
    "PURPLE/DARK": {"PURPLE/DARK", "RED", "WHITE/BROWN"},
    "WHITE/BROWN": {"WHITE/BROWN", "YELLOW", "PURPLE/DARK", "RED", "GREEN"},
}


def normalize_family(fam: Optional[str]) -> str:
    """
    Normalize any color family name (including legacy 12-family names)
    to the canonical 5 produce color families.
    """
    if not fam:
        return "WHITE/BROWN"
    u = str(fam).upper().strip()
    if u in ("RED", "PINK", "PINK/MAGENTA", "MAGENTA", "CORAL", "CRIMSON", "ORANGE", "DARK ORANGE"):
        return "RED"
    elif u in ("YELLOW", "GOLD", "AMBER", "LIGHT ORANGE"):
        return "YELLOW"
    elif u in ("PURPLE", "BLUE", "BLACK", "DARK", "VIOLET", "INDIGO", "PURPLE/DARK"):
        return "PURPLE/DARK"
    elif u in ("WHITE", "GRAY", "BROWN", "EARTHY", "NEUTRAL", "WHITE/BROWN"):
        return "WHITE/BROWN"
    return u


def classify_dominant_family(h: float, s: float, v: float) -> str:
    """Classify a single average HSV reading into one of the 5 families."""
    if s <= 38 and v >= 60:
        return "WHITE/BROWN"
    if v <= 40:
        return "PURPLE/DARK"
    if s <= 45:
        return "WHITE/BROWN"
    if (h <= 25 or h >= 165) and s <= 175 and v <= 145:
        return "WHITE/BROWN"
    if h <= 20 or h >= 150:
        return "RED"
    if 21 <= h <= 37:
        return "YELLOW"
    if 38 <= h <= 95:
        return "GREEN"
    if 96 <= h <= 149:
        return "PURPLE/DARK"
    return "WHITE/BROWN"


def isolate_object_mask_from_image(img_bgr: np.ndarray) -> np.ndarray:
    """
    Isolate the foreground object from studio/catalog backgrounds (pure white,
    dark borders, scale rim) using border statistics in Lab space.
    """
    h, w = img_bgr.shape[:2]
    bx = max(3, int(w * 0.05))
    by = max(3, int(h * 0.05))
    border_mask = np.ones((h, w), dtype=bool)
    border_mask[by : h - by, bx : w - bx] = False

    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    border_lab = lab[border_mask]
    b_mean = np.mean(border_lab, axis=0)
    b_std = np.std(border_lab, axis=0)

    dist = np.sqrt(np.sum(((lab - b_mean) / np.maximum(b_std, 12.0)) ** 2, axis=2))
    obj_mask = (dist > 1.85).astype(np.uint8) * 255

    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    obj_mask = cv2.morphologyEx(obj_mask, cv2.MORPH_OPEN, k)
    obj_mask = cv2.morphologyEx(obj_mask, cv2.MORPH_CLOSE, k)

    if cv2.countNonZero(obj_mask) < int(h * w * 0.05):
        return np.ones((h, w), dtype=np.uint8) * 255
    return obj_mask


def compute_color_profile(
    img_bgr: np.ndarray,
    mask: Optional[np.ndarray] = None,
    polygon: Optional[Sequence[Sequence[int]]] = None,
) -> dict:
    """
    Extract a compact, robust color profile classified into the 5 broad families.
    Filters out specular glare, background, and shadows, and generates:
    - Dominant and secondary family
    - 5-family distribution
    - 16-bin circular hue histogram
    - Saturation & Lightness statistics
    """
    if img_bgr is None or getattr(img_bgr, "size", 0) == 0:
        return {}

    h, w = img_bgr.shape[:2]
    combined_mask = None

    if polygon is not None and len(polygon) >= 3:
        combined_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(combined_mask, [np.array(polygon, dtype=np.int32)], 255)

    if mask is not None and mask.shape[:2] == (h, w) and cv2.countNonZero(mask) >= 30:
        if combined_mask is not None:
            combined_mask = cv2.bitwise_and(combined_mask, mask.astype(np.uint8))
        else:
            combined_mask = mask.astype(np.uint8)

    if combined_mask is None or cv2.countNonZero(combined_mask) < 30:
        combined_mask = isolate_object_mask_from_image(img_bgr)

    # Performance optimization: Crop img_bgr and combined_mask to the bounding box
    # of the target object/polygon. This restricts HSV/LAB conversions and Chroma math
    # to ~150,000 pixels instead of the full 2,000,000 frame (10x faster).
    bx, by, bw, bh = cv2.boundingRect(combined_mask)
    if bw < 5 or bh < 5:
        return {}
    img_crop = img_bgr[by : by + bh, bx : bx + bw]
    mask_crop = combined_mask[by : by + bh, bx : bx + bw]

    hsv = cv2.cvtColor(img_crop, cv2.COLOR_BGR2HSV)
    lab = cv2.cvtColor(img_crop, cv2.COLOR_BGR2LAB)

    H = hsv[:, :, 0]
    S = hsv[:, :, 1]
    V = hsv[:, :, 2]

    valid = (mask_crop > 0)
    glare = (S < 22) & (V > 248)
    shadow = (V < 20)
    valid_obj = valid & (~glare) & (~shadow)
    total_valid = int(np.count_nonzero(valid_obj))

    if total_valid < 30:
        valid_obj = valid
        total_valid = int(np.count_nonzero(valid_obj))
        if total_valid == 0:
            return {}

    # Extract 1D vectors for valid object pixels only:
    h_vals = H[valid_obj]
    s_vals = S[valid_obj]
    v_vals = V[valid_obj]
    l_vals = lab[:, :, 0][valid_obj]

    # Compute chroma directly on valid 1D pixels (skips math on background/irrelevant pixels)
    a_vals = lab[:, :, 1][valid_obj].astype(np.float32) - 128.0
    b_vals = lab[:, :, 2][valid_obj].astype(np.float32) - 128.0
    c_vals = np.sqrt(a_vals * a_vals + b_vals * b_vals)

    # Fast integer family codes:
    # 0: RED, 1: YELLOW, 2: GREEN, 3: PURPLE/DARK, 4: WHITE/BROWN
    fam_ids = np.empty(total_valid, dtype=np.uint8)

    # 1. White / Gray / Brown (WHITE/BROWN = 4)
    # When produce is veiled by translucent milky HDPE bags, saturation drops by 50-70% (down to 22-45),
    # but hue is strictly preserved. Protect genuine chromatic produce hues (Green, Red, Yellow, Purple)
    # so they are not falsely absorbed into neutral white/gray.
    is_chromatic_hue = (
        ((h_vals >= 38) & (h_vals <= 95)) |       # Green (capsicum, cucumber, beans, herbs)
        ((h_vals >= 21) & (h_vals <= 37)) |       # Yellow / Orange (banana, lemon, carrot)
        ((h_vals <= 20) | (h_vals >= 150)) |      # Red (apple, tomato, red onion)
        ((h_vals >= 96) & (h_vals <= 149))        # Purple / Violet (brinjal, beetroot)
    )
    is_faded_chromatic = is_chromatic_hue & (s_vals >= 22) & (c_vals >= 12.0)

    # Truly neutral pixels (milky HDPE film, stainless steel scale tray, pale glare):
    is_white_gray = (s_vals <= 48) & (v_vals > 38) & (c_vals <= 28) & (~is_faded_chromatic)
    is_brown_hue = ((h_vals <= 25) | (h_vals >= 165))
    is_brown = (
        (~is_white_gray)
        & is_brown_hue
        & (s_vals >= 35)
        & (s_vals <= 175)
        & (v_vals >= 38)
        & (v_vals <= 145)
    )
    is_white_brown = is_white_gray | is_brown

    # 2. Deep dark / Black (achromatic part of PURPLE/DARK = 3)
    is_deep_dark = (v_vals <= 38)

    # 3. Vivid / Chromatic produce
    is_achromatic = is_white_gray | is_deep_dark
    is_chromatic = ~is_achromatic

    fam_ids[is_white_brown] = 4
    fam_ids[is_deep_dark] = 3

    # For chromatic pixels (not brown, not white/gray, not deep dark):
    m_chroma_pure = is_chromatic & (~is_brown)
    c_h = h_vals[m_chroma_pure]
    if len(c_h) > 0:
        c_fam_ids = np.full(len(c_h), 3, dtype=np.uint8)  # default PURPLE/DARK
        m_red = (c_h <= 20) | (c_h >= 150)
        m_yellow = (c_h >= 21) & (c_h <= 37)
        m_green = (c_h >= 38) & (c_h <= 95)

        c_fam_ids[m_red] = 0     # RED
        c_fam_ids[m_yellow] = 1  # YELLOW
        c_fam_ids[m_green] = 2   # GREEN
        fam_ids[m_chroma_pure] = c_fam_ids
    else:
        c_fam_ids = np.empty(0, dtype=np.uint8)

    # Ultra-fast bincount in C:
    counts = np.bincount(fam_ids, minlength=5)
    fam_names = ("RED", "YELLOW", "GREEN", "PURPLE/DARK", "WHITE/BROWN")
    fam_weights: Dict[str, float] = {}
    for idx, fam in enumerate(fam_names):
        w_fam = float(counts[idx]) / float(total_valid)
        if w_fam >= 0.04:
            fam_weights[fam] = round(float(w_fam), 3)

    sum_w = sum(fam_weights.values()) or 1.0
    fam_weights = {k: round(float(v / sum_w), 3) for k, v in fam_weights.items()}

    sorted_fams = sorted(fam_weights.items(), key=lambda x: x[1], reverse=True)
    top_fam, top_w = sorted_fams[0] if sorted_fams else ("WHITE/BROWN", 1.0)

    # Count genuine vivid chromatic pixels (RED=0, YELLOW=1, GREEN=2)
    vivid_fams: Dict[str, float] = {}
    if len(c_fam_ids) > 0:
        c_counts = np.bincount(c_fam_ids, minlength=4)
        for idx, fam in enumerate(("RED", "YELLOW", "GREEN")):
            w_vivid = float(c_counts[idx]) / float(total_valid)
            if w_vivid >= 0.05:
                vivid_fams[fam] = round(float(w_vivid), 3)

    sorted_vivid = sorted(vivid_fams.items(), key=lambda x: x[1], reverse=True)
    dominant_chromatic = sorted_vivid[0][0] if sorted_vivid else None

    chroma_ratio = float(np.count_nonzero(m_chroma_pure)) / float(total_valid)

    # 1. White/Brown produce rule:
    # If the product is predominantly white/brown (e.g. Cauliflower, Garlic, White Radish, Peeled Potato, Onion >= 40%
    # with WHITE/BROWN being the top family), it is genuinely a WHITE/BROWN produce item!
    # Dark shadows or minor tint should NEVER override its true white identity.
    if top_fam == "WHITE/BROWN" and top_w >= 0.40:
        if dominant_chromatic and fam_weights.get(dominant_chromatic, 0.0) >= 0.38 and dominant_chromatic in ("RED", "YELLOW", "GREEN"):
            dominant_family = dominant_chromatic
            secondary_family = "WHITE/BROWN"
        else:
            dominant_family = "WHITE/BROWN"
            secondary_family = sorted_fams[1][0] if len(sorted_fams) > 1 else None
    # 2. Chromatic produce on neutral tray/desk rule:
    # When a colorful item (Carrot, Tomato, Green Bean) sits on a gray/white table,
    # prioritize its vivid chromatic color as dominant.
    elif dominant_chromatic and fam_weights.get(dominant_chromatic, 0.0) >= 0.06 and chroma_ratio >= 0.06:
        dominant_family = dominant_chromatic
        secondary_family = sorted_fams[0][0] if sorted_fams[0][0] != dominant_family else (sorted_fams[1][0] if len(sorted_fams) > 1 else None)
    else:
        dominant_family = top_fam
        secondary_family = sorted_fams[1][0] if len(sorted_fams) > 1 else None

    mean_v = float(np.mean(v_vals))
    std_v = float(np.std(v_vals))
    mean_s = float(np.mean(s_vals))
    std_s = float(np.std(s_vals))
    mean_l = float(np.mean(l_vals))
    std_l = float(np.std(l_vals))

    has_genuine_chroma = bool(dominant_chromatic and fam_weights.get(dominant_chromatic, 0.0) >= 0.08)
    is_neutral = bool(
        (chroma_ratio < 0.22 and not has_genuine_chroma)
        or (dominant_family == "WHITE/BROWN" and not has_genuine_chroma)
        or (dominant_family == "PURPLE/DARK" and mean_v <= 50 and mean_s <= 55)
    )
    neutral_type = "WHITE/BROWN" if dominant_family == "WHITE/BROWN" else ("DARK" if is_neutral else None)

    # 16-bin circular smoothed hue histogram
    n_bins = 16
    hue_hist = [0.0] * n_bins
    if len(c_h) > 0:
        bin_idx = np.clip((c_h.astype(np.float32) / 180.0 * n_bins).astype(int), 0, n_bins - 1)
        b_counts = np.bincount(bin_idx, minlength=n_bins)
        norm_b = b_counts.astype(np.float32) / float(len(c_h))
        smoothed = np.zeros(n_bins, dtype=np.float32)
        for i in range(n_bins):
            im1 = (i - 1) % n_bins
            ip1 = (i + 1) % n_bins
            smoothed[i] = 0.25 * norm_b[im1] + 0.50 * norm_b[i] + 0.25 * norm_b[ip1]
        sum_s = float(np.sum(smoothed)) or 1.0
        hue_hist = [round(float(x / sum_s), 4) for x in smoothed]

    return {
        "dominant_family": dominant_family,
        "secondary_family": secondary_family,
        "dominant_chromatic": dominant_chromatic,
        "families": fam_weights,
        "chroma_ratio": round(chroma_ratio, 3),
        "is_neutral": is_neutral,
        "neutral_type": neutral_type,
        "mean_v": round(mean_v, 1),
        "std_v": round(std_v, 1),
        "mean_s": round(mean_s, 1),
        "std_s": round(std_s, 1),
        "mean_l": round(mean_l, 1),
        "std_l": round(std_l, 1),
        "hue_hist": hue_hist,
    }


# Backwards-compatible alias for compute_color_profile
extract_color_profile = compute_color_profile


def compare_color(p1: dict, p2: dict) -> Tuple[bool, float, str]:
    """
    Compare live color profile p1 with stored candidate profile p2 using the 5 families.
    Returns: (is_incompatible: bool, color_score: float, reason: str)

    If is_incompatible is True, the candidate MUST BE REJECTED regardless of DINOv3 score.
    """
    if not p1 or not p2:
        return False, 0.50, "missing_profile"

    fams1_raw = p1.get("families", {})
    if isinstance(fams1_raw, (list, tuple, set)):
        fams1_raw = {str(f): 1.0 / max(1, len(fams1_raw)) for f in fams1_raw}
    elif not isinstance(fams1_raw, dict):
        fams1_raw = {}

    fams2_raw = p2.get("families", {})
    if isinstance(fams2_raw, (list, tuple, set)):
        fams2_raw = {str(f): 1.0 / max(1, len(fams2_raw)) for f in fams2_raw}
    elif not isinstance(fams2_raw, dict):
        fams2_raw = {}

    if not fams1_raw or not fams2_raw:
        return False, 0.50, "empty_families"

    # Normalize families to 5 canonical families and aggregate weights
    fams1: Dict[str, float] = {}
    for f, w in fams1_raw.items():
        norm_f = normalize_family(f)
        fams1[norm_f] = fams1.get(norm_f, 0.0) + float(w)

    fams2: Dict[str, float] = {}
    for f, w in fams2_raw.items():
        norm_f = normalize_family(f)
        fams2[norm_f] = fams2.get(norm_f, 0.0) + float(w)

    dom1 = normalize_family(p1.get("dominant_family", "WHITE/BROWN"))
    dom2 = normalize_family(p2.get("dominant_family", "WHITE/BROWN"))
    c1 = float(p1.get("chroma_ratio", 0.5))
    c2 = float(p2.get("chroma_ratio", 0.5))
    chr1 = normalize_family(p1.get("dominant_chromatic")) if p1.get("dominant_chromatic") else None
    chr2 = normalize_family(p2.get("dominant_chromatic")) if p2.get("dominant_chromatic") else None

    s1 = float(p1.get("mean_s", 128.0))
    s2 = float(p2.get("mean_s", 128.0))
    v1 = float(p1.get("mean_v", 128.0))
    v2 = float(p2.get("mean_v", 128.0))

    LOW_SAT_THRESHOLD = 32.0  # (25-35 on a 0-255 scale)
    is_low_sat1 = (s1 <= LOW_SAT_THRESHOLD) or bool(p1.get("is_neutral", False))
    is_low_sat2 = (s2 <= LOW_SAT_THRESHOLD) or bool(p2.get("is_neutral", False))

    # CRITICAL EDGE CASE: neutral / low-saturation objects
    # If either the live object's or stored product's saturation mean is below low-saturation threshold,
    # do NOT perform hue-family rejection.
    # Compare using value/lightness and saturation similarity only, with a wider tolerance.
    if is_low_sat1 or is_low_sat2:
        # Both neutral / low-saturation
        if is_low_sat1 and is_low_sat2:
            v_diff = abs(v1 - v2)
            # White vs Black is clearly incompatible (extreme lightness mismatch)
            is_dom1_dark = (dom1 == "PURPLE/DARK" and v1 <= 55) or (v1 <= 45)
            is_dom2_dark = (dom2 == "PURPLE/DARK" and v2 <= 55) or (v2 <= 45)
            is_dom1_white = (dom1 == "WHITE/BROWN" and v1 >= 170) or (v1 >= 195)
            is_dom2_white = (dom2 == "WHITE/BROWN" and v2 >= 170) or (v2 >= 195)
            if (is_dom1_white and is_dom2_dark) or (is_dom1_dark and is_dom2_white):
                return True, 0.10, "neutral_white_vs_black"
            if v_diff > 140.0:  # Very wide tolerance
                return True, 0.20, f"neutral_lightness_mismatch(v_diff={v_diff:.1f})"
            score = max(0.40, 1.0 - (v_diff / 255.0))
            return False, score, "neutral_compatible"

        # One is neutral/low-saturation and the other is strongly chromatic (high saturation)
        # E.g. White Garlic vs Vivid Red Tomato or Vivid Green Capsicum
        # CRITICAL TRANSLUCENT COVER COMPATIBILITY:
        # If the live object's dominant chromatic hue aligns with the stored product's chromatic family
        # (e.g., both are GREEN, or both are RED, or both are YELLOW, or neighbors),
        # this is produce desaturated by a translucent bag/cover, NOT an incompatible color!
        if chr1 and chr2 and (chr1 == chr2 or chr2 in NEIGHBOR_FAMILIES.get(chr1, set())):
            return False, 0.70, f"chromatic_aligned_under_cover({chr1})"

        sat_diff = abs(s1 - s2)
        if sat_diff > 70.0 and (c1 > 0.50 or c2 > 0.50):
            # Check if chromatic item contains significant neutral component (e.g. multi-color Red+White)
            neutral_in_chromatic = fams2.get("WHITE/BROWN", 0.0) if is_low_sat1 else fams1.get("WHITE/BROWN", 0.0)
            if neutral_in_chromatic < 0.20:
                # Multi-layer produce rule (e.g. Red Onion with papery White/Brown skin, Purple Plum with pale bloom):
                # If the chromatic item has shared neighbor families (PURPLE, RED, WHITE/BROWN >= 15%), it is compatible!
                chromatic_fams = fams2 if is_low_sat1 else fams1
                shared_multi = chromatic_fams.get("PURPLE/DARK", 0.0) + chromatic_fams.get("RED", 0.0) + chromatic_fams.get("WHITE/BROWN", 0.0)
                if shared_multi < 0.15:
                    return True, 0.15, f"low_sat_vs_vivid_chromatic(s_diff={sat_diff:.1f})"

        return False, 0.60, "low_saturation_compatible"

    # Both objects have adequate saturation (hue is reliable):
    # Direct family overlap (e.g. multi-color Red+White vs Red+White)
    all_fams = set(fams1.keys()) | set(fams2.keys())
    direct_overlap = sum(min(fams1.get(f, 0.0), fams2.get(f, 0.0)) for f in all_fams)

    # Soft neighbor overlap
    soft_overlap = 0.0
    for f1, w1 in fams1.items():
        for f2, w2 in fams2.items():
            if f1 == f2:
                soft_overlap += min(w1, w2) * 1.0
            elif f2 in NEIGHBOR_FAMILIES.get(f1, set()):
                soft_overlap += min(w1, w2) * 0.65

    # Multi-color hue histogram intersection
    hist1 = p1.get("hue_hist", [])
    hist2 = p2.get("hue_hist", [])
    hist_sim = 0.0
    if len(hist1) == 16 and len(hist2) == 16:
        hist_sim = sum(min(hist1[i], hist2[i]) for i in range(16))

    color_score = max(direct_overlap, soft_overlap * 0.85, hist_sim)

    # Chromatic incompatibility gate
    if chr1 and chr2:
        if chr2 not in NEIGHBOR_FAMILIES.get(chr1, set()):
            # Opposing color families (e.g. GREEN vs RED, GREEN vs PURPLE/DARK, RED vs PURPLE/DARK)
            w_candidate_in_live = fams1.get(chr2, 0.0)
            w_live_in_candidate = fams2.get(chr1, 0.0)
            if w_candidate_in_live < 0.20 and w_live_in_candidate < 0.20:
                return True, color_score, f"opposing_chromatic({chr1}_vs_{chr2})"
        elif (chr1 == "GREEN" and chr2 == "YELLOW") or (chr1 == "YELLOW" and chr2 == "GREEN"):
            # Check if the yellow item is in the orange sub-band (Hue <= 22 or legacy ORANGE)
            # Orange vs Green is strictly opposing (e.g. Orange Carrot / Orange Tomato vs Green Cucumber / Green Tomato)
            y_prof = p2 if chr2 == "YELLOW" else p1
            raw_dom = str(y_prof.get("dominant_family", "")).upper()
            raw_chr = str(y_prof.get("dominant_chromatic", "")).upper()
            y_hist = y_prof.get("hue_hist", [])
            orange_ratio = (y_hist[0] + y_hist[1]) if len(y_hist) >= 2 else 0.0
            if "ORANGE" in raw_dom or "ORANGE" in raw_chr or orange_ratio > 0.40:
                return True, color_score, "opposing_chromatic(GREEN_vs_ORANGE)"

    # Low overall overlap gate
    if soft_overlap < 0.18 and hist_sim < 0.18 and direct_overlap < 0.15:
        return True, color_score, f"low_color_overlap({soft_overlap:.2f})"

    return False, color_score, "compatible"


def is_color_compatible(live_profile: dict, stored_profile: dict) -> bool:
    """
    Hard boolean gate: returns True if live_profile is color-compatible with stored_profile,
    or False if there is a definite color mismatch.
    """
    is_incomp, _, _ = compare_color(live_profile, stored_profile)
    return not is_incomp
