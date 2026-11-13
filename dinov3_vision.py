"""
dinov3_vision.py
----------------
Runtime engine for Meta DINOv3 (ViT-S/16) vision embeddings.
Runs offline on the POS machine alongside DINOv2.

Features:
- Graceful degradation: If models/dinov3_vits16.onnx or runtime dependencies
  are missing, is_available() returns False and all functions safely return
  None/0.0 with zero exceptions or impact on the DINOv2 pipeline.
- Engine loading: Tries cv2.dnn first, then falls back to onnxruntime.
  NOTE ON cv2.dnn: As of OpenCV 4.x/5.x, cv2.dnn cannot load this specific
  DINOv3 ONNX graph because of unsupported 'SplitToSequence' operations
  and dynamic shape assertion errors (!isDynamicShape in parseShape).
  Therefore, onnxruntime is utilized as the primary, high-performance ViT engine.
- Reuses the validated tight-crop and foreground-masked Gray-World white balance
  pipeline directly from dino_vision.py.
- Produces L2-normalized 384-dimensional feature embeddings for cosine similarity.

ATTRIBUTION NOTICE:
    Built with DINOv3 (Meta DINOv3 License).
"""

import os
import sys
import threading
from typing import Optional, Tuple, Dict, Any, Sequence, List, Union

import cv2
import numpy as np

# Try importing onnxruntime
try:
    import onnxruntime as ort
    _ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ort = None
    _ONNXRUNTIME_AVAILABLE = False

# Import preprocessing & cropping helpers from dino_vision
try:
    from dino_vision import crop_object_for_embedding, crop_polygon_for_embedding
    _VISION_HELPERS_AVAILABLE = True
except ImportError:
    crop_object_for_embedding = None
    crop_polygon_for_embedding = None
    _VISION_HELPERS_AVAILABLE = False


def _app_root_dir() -> str:
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            meipass_models = os.path.join(sys._MEIPASS, "models")
            if os.path.exists(meipass_models):
                return sys._MEIPASS
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


class DinoV3VisionMatcher:
    """
    Singleton manager for DINOv3 ViT-S/16 ONNX model inference.
    Loads models/dinov3_vits16.onnx and provides fast, offline embedding extraction.
    """

    _instance: Optional["DinoV3VisionMatcher"] = None
    _instance_lock = threading.Lock()

    def __init__(self, app_dir: Optional[str] = None):
        self.app_dir = app_dir or _app_root_dir()
        
        # Search candidate locations for models directory
        candidates = [os.path.join(self.app_dir, "models")]
        if getattr(sys, "frozen", False):
            if hasattr(sys, "_MEIPASS"):
                candidates.insert(0, os.path.join(sys._MEIPASS, "models"))
                candidates.append(os.path.join(sys._MEIPASS, "Imgs", "models"))
            candidates.append(os.path.join(os.path.dirname(sys.executable), "models"))

        self.models_dir = candidates[0]
        for c in candidates:
            if os.path.exists(os.path.join(c, "dinov3_vits16.onnx")):
                self.models_dir = c
                break

        self.onnx_path = os.path.join(self.models_dir, "dinov3_vits16.onnx")
        self.data_path = os.path.join(self.models_dir, "dinov3_vits16.onnx_data")
        self.meta_path = os.path.join(self.models_dir, "dinov3_meta.json")

        self._lock = threading.Lock()
        self._engine_type: Optional[str] = None  # "ort" or "cv2"
        self._session: Any = None
        self._input_name: str = "pixel_values"
        self._output_name: str = "pooler_output"
        self._image_size: int = 224
        self._embedding_dim: int = 384
        self._mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self._std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

        self._initialized = False
        self._unavailable_reason: Optional[str] = None

        self._init_model()

    @classmethod
    def instance(cls, app_dir: Optional[str] = None) -> "DinoV3VisionMatcher":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(app_dir)
            return cls._instance

    def is_available(self) -> bool:
        return self._initialized and self._session is not None

    def unavailable_reason(self) -> Optional[str]:
        return self._unavailable_reason

    def _init_model(self) -> None:
        if not os.path.exists(self.onnx_path):
            self._unavailable_reason = f"DINOv3 ONNX model missing: {self.onnx_path}"
            return

        # Check sidecar data if external data is used
        alt_data = os.path.join(self.models_dir, "model.onnx_data")
        if not os.path.exists(alt_data) and os.path.exists(self.data_path):
            try:
                import shutil
                shutil.copyfile(self.data_path, alt_data)
            except Exception:
                pass
        elif not os.path.exists(self.data_path) and os.path.exists(alt_data):
            self.data_path = alt_data

        if not os.path.exists(self.data_path) and not os.path.exists(alt_data):
            # If the onnx file is tiny (< 1MB) but .onnx_data is missing, it cannot run
            if os.path.getsize(self.onnx_path) < 1024 * 1024:
                self._unavailable_reason = f"DINOv3 weights sidecar missing: {self.data_path}"
                return

        # 1. Prefer ONNX Runtime for Vision Transformers (ViT)
        # (OpenCV's cv2.dnn parser does not support SplitToSequence or dynamic ViT shapes)
        if _ONNXRUNTIME_AVAILABLE:
            try:
                opts = ort.SessionOptions()
                # Balance parallel tensor math while reserving CPU headroom for Qt GUI & Windows message loop
                available_cores = os.cpu_count() or 4
                opts.intra_op_num_threads = max(1, min(3, (available_cores - 1) if available_cores > 2 else 1))
                opts.inter_op_num_threads = 1
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                opts.enable_cpu_mem_arena = True
                opts.enable_mem_pattern = True
                opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
                try:
                    opts.add_session_config_entry("session.intra_op.allow_spinning", "0")
                except Exception:
                    pass
                session = ort.InferenceSession(self.onnx_path, sess_options=opts, providers=["CPUExecutionProvider"])

                # Read dynamic input and output names
                inputs = session.get_inputs()
                if inputs:
                    self._input_name = inputs[0].name

                outputs = session.get_outputs()
                found_output = None
                for out in outputs:
                    if "pooler" in out.name.lower():
                        found_output = out.name
                        break
                if not found_output and outputs:
                    found_output = outputs[-1].name
                self._output_name = found_output or "pooler_output"

                # Verify execution with dummy input
                dummy = np.zeros((1, 3, self._image_size, self._image_size), dtype=np.float32)
                res = session.run([self._output_name], {self._input_name: dummy})[0]
                if res is not None and not np.isnan(res).any():
                    self._engine_type = "ort"
                    self._session = session
                    self._embedding_dim = int(res.shape[-1])
                    self._initialized = True
                    self._unavailable_reason = None
                    print(f"[DINOv3] Initialized successfully using ONNX Runtime (dim={self._embedding_dim}).")
                    return
                else:
                    self._unavailable_reason = "ONNX Runtime produced NaN output on test inference."
                    return
            except Exception as ort_err:
                self._unavailable_reason = f"ONNX Runtime failed to initialize DINOv3 model: {ort_err}"

        # 2. Fallback to cv2.dnn if onnxruntime is absent
        try:
            cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
            net = cv2.dnn.readNetFromONNX(self.onnx_path)
            dummy = np.zeros((1, 3, self._image_size, self._image_size), dtype=np.float32)
            net.setInput(dummy)
            res = net.forward()
            if res is not None and not np.isnan(res).any():
                self._engine_type = "cv2"
                self._session = net
                self._initialized = True
                self._unavailable_reason = None
                print("[DINOv3] Initialized successfully using cv2.dnn engine.")
                return
        except Exception:
            pass

        if not self._initialized:
            self._unavailable_reason = "Neither onnxruntime nor cv2.dnn could load the DINOv3 model."

    def extract_crop(
        self,
        frame_bgr: np.ndarray,
        mask: Optional[np.ndarray] = None,
        contour: Optional[np.ndarray] = None,
        polygon: Optional[list] = None,
    ) -> Optional[np.ndarray]:
        if frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
            return None

        # Clean unzoomed ROI: crop directly to polygon boundary without auto-zooming onto sub-contours
        if polygon is not None and len(polygon) >= 3 and _VISION_HELPERS_AVAILABLE:
            try:
                crop = crop_polygon_for_embedding(frame_bgr, polygon)
                if crop is not None and crop.size > 0:
                    return crop
            except Exception:
                pass

        # Fallback to square center crop
        h, w = frame_bgr.shape[:2]
        side = min(h, w)
        y0 = (h - side) // 2
        x0 = (w - side) // 2
        return frame_bgr[y0 : y0 + side, x0 : x0 + side].copy()

    def preprocess_crop(self, crop: np.ndarray) -> Optional[np.ndarray]:
        if crop is None or getattr(crop, "size", 0) == 0:
            return None
        try:
            resized = cv2.resize(crop, (self._image_size, self._image_size), interpolation=cv2.INTER_LINEAR)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            norm_img = (rgb - self._mean) / self._std
            blob = np.transpose(norm_img, (2, 0, 1)).astype(np.float32)
            return blob
        except Exception as e:
            print(f"[DINOv3] Preprocessing error: {e}")
            return None

    def _forward_blob(self, blob: np.ndarray) -> List[np.ndarray]:
        with self._lock:
            try:
                if self._engine_type == "cv2":
                    self._session.setInput(blob)
                    out = self._session.forward()
                else:
                    out = self._session.run([self._output_name], {self._input_name: blob})[0]
            except Exception as e:
                print(f"[DINOv3] Forward pass error: {e}")
                return []
        embs = np.asarray(out, dtype=np.float32)
        if embs.ndim == 1:
            embs = embs.reshape(1, -1)
        norms = np.linalg.norm(embs, axis=1, keepdims=True)
        norms = np.where(norms > 1e-8, norms, 1.0)
        embs_norm = embs / norms
        return [embs_norm[i] for i in range(len(embs_norm))]

    def embed_crop(self, crop: np.ndarray) -> Optional[np.ndarray]:
        blob = self.preprocess_crop(crop)
        if blob is None:
            return None
        res = self._forward_blob(blob[None, ...])
        return res[0] if res else None

    def embed_batch(self, crops: Sequence[np.ndarray]) -> List[np.ndarray]:
        if not self.is_available() or not crops:
            return []
        blobs = []
        for c in crops:
            b = self.preprocess_crop(c)
            if b is not None:
                blobs.append(b)
        if not blobs:
            return []
        stacked = np.stack(blobs, axis=0)
        return self._forward_blob(stacked)

    DEFAULT_ROTATION_ANGLES: Tuple[float, ...] = (
        45.0, 90.0, 135.0, 180.0, 225.0, 270.0, 315.0
    )

    def embed_pose_variants(
        self,
        bgr_crop: np.ndarray,
        angles: Optional[Sequence[float]] = None,
        include_flip: bool = True,
        add_photometric: bool = True,
        include_zoom: bool = False,
    ) -> List[np.ndarray]:
        if bgr_crop is None or getattr(bgr_crop, "size", 0) == 0:
            return []
        if angles is None:
            angles = self.DEFAULT_ROTATION_ANGLES

        # Pre-scale high-resolution crop once to 256x256 to speed up rotations by ~7x
        h, w = bgr_crop.shape[:2]
        if max(h, w) > 256:
            base_crop = cv2.resize(bgr_crop, (256, 256), interpolation=cv2.INTER_AREA)
        else:
            base_crop = bgr_crop

        crops = [base_crop]
        rng = np.random.default_rng()

        # 1. Rotations (Bare)
        rotated_crops = []
        for ang in angles:
            rot = _rotate_image(base_crop, float(ang))
            crops.append(rot)
            rotated_crops.append(rot)

        # 2. Flips (Bare)
        flipped_crops = []
        if include_flip:
            flp = cv2.flip(base_crop, 1)
            crops.append(flp)
            flipped_crops.append(flp)
            # Also include 90-degree flip for asymmetric items
            rot90_flp = cv2.flip(_rotate_image(base_crop, 90.0), 1)
            crops.append(rot90_flp)
            flipped_crops.append(rot90_flp)

        if include_zoom:
            crops.append(_zoom_image(base_crop, 1.20))
            crops.append(_zoom_image(base_crop, 0.85))
        if add_photometric:
            crops.append(_random_photometric_jitter(base_crop, rng))

        # 3. Multi-Angle Translucent Cover Simulation (Cover Invariance)
        # Transparent bag light haze (0°)
        white_light = np.full_like(base_crop, 240)
        crops.append(cv2.addWeighted(base_crop, 0.78, white_light, 0.22, 0))

        # Milky HDPE translucent cover variants on base crop (0°)
        crops.append(_simulate_translucent_cover(base_crop, veil_alpha=0.38, blur_k=9))
        crops.append(_simulate_translucent_cover(base_crop, veil_alpha=0.52, blur_k=11))

        # Translucent cover simulation across rotated angles (45°, 90°, 135°, 180°, 225°, 270°, 315°)
        for rot in rotated_crops:
            crops.append(_simulate_translucent_cover(rot, veil_alpha=0.42, blur_k=9))

        # Translucent cover simulation across flipped orientations
        for flp in flipped_crops:
            crops.append(_simulate_translucent_cover(flp, veil_alpha=0.42, blur_k=9))

        # 4. Excess Plastic Bag Dominance (Cover >> Product, 10-25% product ratio)
        crops.append(_simulate_excess_plastic_cover(base_crop, shrink_ratio=0.35))
        crops.append(_simulate_excess_plastic_cover(base_crop, shrink_ratio=0.22))

        # 5. De-Hazed Reference Vector (Direct gallery pairing for live de-hazed camera streams)
        dehazed_ref = dehaze_crop(base_crop)
        if dehazed_ref is not None and getattr(dehazed_ref, "size", 0) > 0:
            crops.append(dehazed_ref)

        return self.embed_batch(crops)

    def compute_embedding(
        self,
        frame_bgr: np.ndarray,
        mask: Optional[np.ndarray] = None,
        contour: Optional[np.ndarray] = None,
        polygon: Optional[list] = None,
    ) -> Optional[np.ndarray]:
        """
        Extract L2-normalized 384-dimensional DINOv3 embedding from a frame.
        """
        crop = self.extract_crop(frame_bgr, mask=mask, contour=contour, polygon=polygon)
        if crop is None:
            return None
        return self.embed_crop(crop)

    def compute_multi_view_embeddings(
        self,
        frame_bgr: np.ndarray,
        mask: Optional[np.ndarray] = None,
        contour: Optional[np.ndarray] = None,
        polygon: Optional[list] = None,
    ) -> List[np.ndarray]:
        """
        Multi-View Live Embedding (Full Product Preserved):
        Always captures 100% of the full product (no auto-zoom clipping):
        1. Raw full crop (100% full product as placed on scale)
        2. De-hazed full crop (100% full product with translucent bag veil stripped)
        Both embedded in ONE single batched forward pass.
        Returns List of valid L2-normalized 384-dim embeddings.
        """
        crop = self.extract_crop(frame_bgr, mask=mask, contour=contour, polygon=polygon)
        if crop is None or getattr(crop, "size", 0) == 0:
            return []

        crops_to_embed = [crop]
        # De-hazed full view - preserves the entire product while stripping translucent cover veil
        dehazed = dehaze_crop(crop)
        if dehazed is not None and getattr(dehazed, "size", 0) > 0:
            crops_to_embed.append(dehazed)

        return self.embed_batch(crops_to_embed)

    def compute_dual_embeddings(
        self,
        frame_bgr: np.ndarray,
        mask: Optional[np.ndarray] = None,
        contour: Optional[np.ndarray] = None,
        polygon: Optional[list] = None,
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Live De-Hazing Dual Stream (backwards-compatible):
        Extracts both raw crop embedding AND de-hazed (translucent bag stripped) embedding.
        Returns: (raw_embedding, dehazed_embedding)
        """
        embs = self.compute_multi_view_embeddings(frame_bgr, mask=mask, contour=contour, polygon=polygon)
        if len(embs) >= 2:
            return embs[0], embs[1]
        elif len(embs) == 1:
            return embs[0], embs[0]
        return None, None


def _simulate_excess_plastic_cover(bgr: np.ndarray, shrink_ratio: float = 0.35) -> np.ndarray:
    """
    Simulates produce occupying only 10-25% of the camera view inside a large,
    spread-out milky HDPE grocery cover with 75-90% empty white plastic folds.
    """
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return bgr
    try:
        h, w = bgr.shape[:2]
        canvas_side = max(h, w, 224)
        # Create a large milky plastic background canvas with crinkles and creases
        canvas = np.full((canvas_side, canvas_side, 3), 235, dtype=np.uint8)

        # Add crinkle texture to the plastic background
        for _ in range(3):
            pt1 = (int(np.random.uniform(0, canvas_side)), int(np.random.uniform(0, canvas_side)))
            pt2 = (int(np.random.uniform(0, canvas_side)), int(np.random.uniform(0, canvas_side)))
            cv2.line(canvas, pt1, pt2, (215, 215, 215), thickness=max(2, canvas_side // 40))
        canvas = cv2.GaussianBlur(canvas, (9, 9), 0)

        # Scale down the produce to simulate it being a small part of the bag
        target_w = max(20, int(w * shrink_ratio))
        target_h = max(20, int(h * shrink_ratio))
        shrunk = cv2.resize(bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)
        # Diffuse the produce slightly
        shrunk_covered = _simulate_translucent_cover(shrunk, veil_alpha=0.45, blur_k=7)

        # Place the produce inside the plastic canvas (slightly off-center as in real bag)
        ox = max(0, min(canvas_side - target_w, (canvas_side - target_w) // 2 + int(np.random.uniform(-15, 15))))
        oy = max(0, min(canvas_side - target_h, (canvas_side - target_h) // 2 + int(np.random.uniform(-15, 15))))

        canvas[oy : oy + target_h, ox : ox + target_w] = shrunk_covered
        return cv2.resize(canvas, (w, h), interpolation=cv2.INTER_AREA)
    except Exception:
        return bgr


def _simulate_translucent_cover(bgr: np.ndarray, veil_alpha: float = 0.40, blur_k: int = 9) -> np.ndarray:
    """
    Simulates optical effects of milky/translucent plastic grocery covers (HDPE bags):
    - Light diffusion blur through milky plastic membrane
    - White veil / contrast reduction from plastic scattering
    - Bag crease/crinkle specular sheen
    """
    if bgr is None or getattr(bgr, "size", 0) == 0:
        return bgr
    try:
        # 1. Diffusion blur through translucent bag
        k = max(3, blur_k | 1)
        diffused = cv2.GaussianBlur(bgr, (k, k), 0)

        # 2. White/milky scattering veil
        veil = np.full_like(diffused, 235)
        blended = cv2.addWeighted(diffused, float(1.0 - veil_alpha), veil, float(veil_alpha), 0)

        # 3. Subtle crinkle/wrinkle specular streak across bag
        h, w = bgr.shape[:2]
        if h > 10 and w > 10:
            crinkle = np.zeros((h, w), dtype=np.uint8)
            pt1 = (int(w * 0.15), int(h * 0.2))
            pt2 = (int(w * 0.85), int(h * 0.8))
            cv2.line(crinkle, pt1, pt2, 40, thickness=max(2, min(h, w) // 25))
            crinkle = cv2.GaussianBlur(crinkle, (15, 15), 0)
            blended = cv2.add(blended, cv2.merge([crinkle, crinkle, crinkle]))

        return blended
    except Exception:
        return bgr


def _rotate_image(bgr: np.ndarray, angle_deg: float, border_value=(128, 128, 128)) -> np.ndarray:
    h, w = bgr.shape[:2]
    # Pad to square diagonal canvas to preserve 100% of the object without cropping corners
    diag = int(np.ceil(np.sqrt(h * h + w * w)))
    pad_top = (diag - h) // 2
    pad_bottom = diag - h - pad_top
    pad_left = (diag - w) // 2
    pad_right = diag - w - pad_left
    canvas = cv2.copyMakeBorder(
        bgr,
        pad_top,
        pad_bottom,
        pad_left,
        pad_right,
        cv2.BORDER_CONSTANT,
        value=border_value,
    )
    center = (diag / 2.0, diag / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    return cv2.warpAffine(canvas, matrix, (diag, diag), borderMode=cv2.BORDER_CONSTANT, borderValue=border_value)


def _zoom_image(bgr: np.ndarray, zoom_factor: float, border_value=(128, 128, 128)) -> np.ndarray:
    h, w = bgr.shape[:2]
    if h <= 0 or w <= 0:
        return bgr
    if abs(zoom_factor - 1.0) < 0.01:
        return bgr
    if zoom_factor > 1.0:
        crop_h = max(1, int(h / zoom_factor))
        crop_w = max(1, int(w / zoom_factor))
        y0 = max(0, (h - crop_h) // 2)
        x0 = max(0, (w - crop_w) // 2)
        cropped = bgr[y0 : y0 + crop_h, x0 : x0 + crop_w]
        return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_CUBIC)
    else:
        target_w = max(1, int(w * zoom_factor))
        target_h = max(1, int(h * zoom_factor))
        shrunk = cv2.resize(bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)
        pad_top = (h - target_h) // 2
        pad_bottom = h - target_h - pad_top
        pad_left = (w - target_w) // 2
        pad_right = w - target_w - pad_left
        return cv2.copyMakeBorder(shrunk, pad_top, pad_bottom, pad_left, pad_right, cv2.BORDER_CONSTANT, value=border_value)


def _random_photometric_jitter(bgr: np.ndarray, rng: Optional[np.random.Generator] = None) -> np.ndarray:
    if rng is None:
        rng = np.random.default_rng()
    alpha = float(rng.uniform(0.90, 1.10))
    beta = float(rng.uniform(-10.0, 10.0))
    b_scale = float(rng.uniform(0.95, 1.05))
    g_scale = float(rng.uniform(0.95, 1.05))
    r_scale = float(rng.uniform(0.95, 1.05))
    out = bgr.astype(np.float32)
    out = out * alpha + beta
    out[:, :, 0] *= b_scale
    out[:, :, 1] *= g_scale
    out[:, :, 2] *= r_scale
    return np.clip(out, 0, 255).astype(np.uint8)


# Module-level convenience functions
def is_available() -> bool:
    return DinoV3VisionMatcher.instance().is_available()


def unavailable_reason() -> Optional[str]:
    return DinoV3VisionMatcher.instance().unavailable_reason()


def compute_embedding(
    frame_bgr: np.ndarray,
    mask: Optional[np.ndarray] = None,
    contour: Optional[np.ndarray] = None,
    polygon: Optional[list] = None,
) -> Optional[np.ndarray]:
    return DinoV3VisionMatcher.instance().compute_embedding(
        frame_bgr, mask=mask, contour=contour, polygon=polygon
    )


def compute_multi_view_embeddings(
    frame_bgr: np.ndarray,
    mask: Optional[np.ndarray] = None,
    contour: Optional[np.ndarray] = None,
    polygon: Optional[list] = None,
) -> List[np.ndarray]:
    """
    Live Multi-View Feature Extraction (Full Product Preserved):
    Extracts raw crop and de-hazed crop in parallel without auto-zoom.
    Returns: List of L2-normalized 384-dim embeddings.
    """
    return DinoV3VisionMatcher.instance().compute_multi_view_embeddings(
        frame_bgr, mask=mask, contour=contour, polygon=polygon
    )


def compute_dual_embeddings(
    frame_bgr: np.ndarray,
    mask: Optional[np.ndarray] = None,
    contour: Optional[np.ndarray] = None,
    polygon: Optional[list] = None,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Live De-Hazing Dual Stream:
    Extracts both raw crop embedding AND de-hazed (translucent bag stripped) embedding.
    Returns: (raw_embedding, dehazed_embedding)
    """
    return DinoV3VisionMatcher.instance().compute_dual_embeddings(
        frame_bgr, mask=mask, contour=contour, polygon=polygon
    )


def extract_dinov3_pose_variants(
    frame_bgr: np.ndarray,
    polygon: Optional[list] = None,
    mask: Optional[np.ndarray] = None,
) -> List[np.ndarray]:
    matcher = DinoV3VisionMatcher.instance()
    if not matcher.is_available():
        return []
    crop = matcher.extract_crop(frame_bgr, mask=mask, polygon=polygon)
    if crop is None:
        return []
    return matcher.embed_pose_variants(crop)


def compare_embeddings(vec_a: Optional[np.ndarray], vec_b: Optional[np.ndarray]) -> float:
    """
    Compute cosine similarity between two normalized DINOv3 embeddings.
    Returns float in range [0.0, 1.0].
    """
    if vec_a is None or vec_b is None:
        return 0.0
    try:
        dot = float(np.dot(vec_a, vec_b))
        return float(max(0.0, min(1.0, dot)))
    except Exception:
        return 0.0


def compare_gallery(live_emb: Optional[np.ndarray], samples: Optional[Sequence[Any]]) -> float:
    """
    Compute best-of-gallery cosine similarity between a live embedding and a list of sample vectors.
    Returns maximum similarity in range [0.0, 1.0].
    """
    if live_emb is None or not samples:
        return 0.0
    try:
        arr = np.asarray(samples, dtype=np.float32)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        dots = np.dot(arr, live_emb)
        best = float(np.max(dots))
        return float(max(0.0, min(1.0, best)))
    except Exception:
        return 0.0


def dehaze_crop(crop_bgr: np.ndarray) -> np.ndarray:
    """
    Fast Guided Retinex / De-Hazing contrast restoration for crops under translucent milky bags.
    Recovers true saturation, deepens washed-out contrast, and removes white veil in ~10ms.
    """
    if crop_bgr is None or getattr(crop_bgr, "size", 0) == 0:
        return crop_bgr
    try:
        h_orig, w_orig = crop_bgr.shape[:2]
        needs_resize = (max(h_orig, w_orig) > 180)
        if needs_resize:
            scale = 180.0 / max(h_orig, w_orig)
            small = cv2.resize(crop_bgr, (int(w_orig * scale), int(h_orig * scale)), interpolation=cv2.INTER_AREA)
        else:
            small = crop_bgr

        img = small.astype(np.float32)
        dark = np.min(img, axis=2)
        dark_min = cv2.erode(dark, np.ones((3, 3), np.uint8))
        A = float(np.percentile(dark_min.ravel()[::4], 98.0))
        A = max(175.0, min(A, 245.0))
        t = 1.0 - 0.72 * (dark_min / A)
        t = np.clip(t, 0.28, 1.0)
        t = cv2.blur(t, (5, 5))
        t = np.expand_dims(t, axis=2)
        J = (img - A) / t + A
        res = np.clip(J, 0, 255).astype(np.uint8)
        lab = cv2.cvtColor(res, cv2.COLOR_BGR2LAB)
        clahe = cv2.createCLAHE(clipLimit=2.2, tileGridSize=(6, 6))
        lab[:, :, 0] = clahe.apply(lab[:, :, 0])
        hsv = cv2.cvtColor(cv2.cvtColor(lab, cv2.COLOR_LAB2BGR), cv2.COLOR_BGR2HSV)
        hsv[:, :, 1] = cv2.multiply(hsv[:, :, 1], 1.35)
        out_small = cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR)
        if needs_resize:
            return cv2.resize(out_small, (w_orig, h_orig), interpolation=cv2.INTER_LINEAR)
        return out_small
    except Exception:
        return crop_bgr

