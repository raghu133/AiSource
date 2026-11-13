"""
siglip_zero_shot.py
-------------------
Runtime module for offline SigLIP zero-shot produce category validation.

Provides an independent zero-shot sanity check: "does this live image
broadly look like [item_name] at all?", using an ONNX-exported SigLIP
model (image + text encoder) and a SentencePiece tokenizer.

Graceful degradation:
  If the model files (in models/) or runtime libraries (sentencepiece,
  cv2.dnn/onnxruntime) are missing, every function returns None/0.0
  and the application runs normally without any crash or forced dependency.

Performance:
  Text embeddings are cached in signatures/siglip_text_cache.json so the text
  encoder runs at most once per unique item name (effectively free at runtime).
"""

import os
import json
import threading
from typing import Optional, Dict, List

import cv2
import numpy as np

# Try importing sentencepiece
try:
    import sentencepiece as spm
    _SENTENCEPIECE_AVAILABLE = True
except ImportError:
    spm = None
    _SENTENCEPIECE_AVAILABLE = False

# Try importing onnxruntime as a robust fallback if cv2.dnn encounters unsupported ONNX ops
try:
    import onnxruntime as ort
    _ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ort = None
    _ONNXRUNTIME_AVAILABLE = False

# Import cropping helper from dino_vision if available
try:
    from dino_vision import crop_object_for_embedding, crop_polygon_for_embedding
    _VISION_HELPERS_AVAILABLE = True
except ImportError:
    crop_object_for_embedding = None
    crop_polygon_for_embedding = None
    _VISION_HELPERS_AVAILABLE = False


def _app_root_dir() -> str:
    return os.path.dirname(os.path.abspath(__file__))


class SiglipZeroShotMatcher:
    """
    Singleton manager for offline SigLIP zero-shot category matching.
    Manages ONNX vision and text models, SentencePiece tokenizer, and
    the persistent text embedding cache.
    """

    _instance: Optional["SiglipZeroShotMatcher"] = None
    _instance_lock = threading.Lock()

    def __init__(self, app_dir: Optional[str] = None):
        self.app_dir = app_dir or _app_root_dir()
        self.models_dir = os.path.join(self.app_dir, "models")
        self.signatures_dir = os.path.join(self.app_dir, "signatures")

        self.image_model_path = os.path.join(self.models_dir, "siglip_image.onnx")
        self.text_model_path = os.path.join(self.models_dir, "siglip_text.onnx")
        self.tokenizer_path = os.path.join(self.models_dir, "siglip_tokenizer.model")
        self.meta_path = os.path.join(self.models_dir, "siglip_meta.json")
        self.cache_path = os.path.join(self.signatures_dir, "siglip_text_cache.json")

        self._lock = threading.Lock()
        self._image_engine = None  # ("cv2", net) or ("ort", session)
        self._text_engine = None   # ("cv2", net) or ("ort", session)
        self._tokenizer = None
        self._meta: Dict = {}
        self._text_cache: Dict[str, List[float]] = {}
        self._initialized = False
        self._unavailable_reason: Optional[str] = None

        self._load_cache()
        self._init_models()

    @classmethod
    def instance(cls, app_dir: Optional[str] = None) -> "SiglipZeroShotMatcher":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls(app_dir)
            return cls._instance

    def is_available(self) -> bool:
        return (
            self._initialized
            and self._image_engine is not None
            and self._text_engine is not None
            and self._tokenizer is not None
        )

    def unavailable_reason(self) -> Optional[str]:
        return self._unavailable_reason

    def _load_cache(self) -> None:
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    self._text_cache = data
            except Exception as e:
                print(f"[SigLIP] Notice: Could not read text cache ({e}), initializing empty cache.")
                self._text_cache = {}

    def _save_cache(self) -> None:
        try:
            os.makedirs(self.signatures_dir, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._text_cache, f, indent=2)
        except Exception as e:
            print(f"[SigLIP] Warning: Could not save text cache ({e}).")

    def _init_models(self) -> None:
        # Check files
        if not os.path.exists(self.image_model_path):
            self._unavailable_reason = f"Image model missing: {self.image_model_path}"
            return
        if not os.path.exists(self.text_model_path):
            self._unavailable_reason = f"Text model missing: {self.text_model_path}"
            return
        if not os.path.exists(self.tokenizer_path):
            self._unavailable_reason = f"Tokenizer missing: {self.tokenizer_path}"
            return
        if not _SENTENCEPIECE_AVAILABLE:
            self._unavailable_reason = "sentencepiece package not installed (run 'pip install sentencepiece')"
            return

        # Load metadata if present
        if os.path.exists(self.meta_path):
            try:
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    self._meta = json.load(f)
            except Exception:
                self._meta = {}

        # 1. Load Tokenizer
        try:
            self._tokenizer = spm.SentencePieceProcessor(model_file=self.tokenizer_path)
        except Exception as e:
            self._unavailable_reason = f"Failed to load sentencepiece tokenizer: {e}"
            return

        # 2. Load Vision Engine (Try cv2.dnn first, fall back to onnxruntime)
        self._image_engine = self._load_onnx_engine(self.image_model_path, "vision")
        if self._image_engine is None:
            self._unavailable_reason = "Could not initialize image ONNX engine (neither cv2.dnn nor onnxruntime succeeded)"
            return

        # 3. Load Text Engine (Try cv2.dnn first, fall back to onnxruntime)
        self._text_engine = self._load_onnx_engine(self.text_model_path, "text")
        if self._text_engine is None:
            self._unavailable_reason = "Could not initialize text ONNX engine (neither cv2.dnn nor onnxruntime succeeded)"
            return

        self._initialized = True
        self._unavailable_reason = None
        print(f"[SigLIP] Initialized successfully. Image Engine: {self._image_engine[0].upper()}, "
              f"Text Engine: {self._text_engine[0].upper()}, Cached items: {len(self._text_cache)}")

    def _load_onnx_engine(self, onnx_path: str, model_type: str):
        """
        Attempts to load model using onnxruntime first (optimal for transformers).
        Falls back to cv2.dnn if onnxruntime is not available.
        """
        if _ONNXRUNTIME_AVAILABLE:
            try:
                opts = ort.SessionOptions()
                opts.intra_op_num_threads = 2
                opts.inter_op_num_threads = 1
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                session = ort.InferenceSession(onnx_path, sess_options=opts, providers=["CPUExecutionProvider"])
                # Test run with dummy input to verify graph execution
                if model_type == "vision":
                    dummy = np.zeros((1, 3, 224, 224), dtype=np.float32)
                    res = session.run(None, {"pixel_values": dummy})[0]
                else:
                    dummy = np.zeros((1, 64), dtype=np.int64)
                    res = session.run(None, {"input_ids": dummy})[0]
                if not np.isnan(res).any():
                    return ("ort", session)
            except Exception as ort_err:
                print(f"[SigLIP] onnxruntime failed for {model_type}: {ort_err}")

        # Fallback to cv2.dnn
        try:
            net = cv2.dnn.readNetFromONNX(onnx_path)
            if model_type == "vision":
                dummy = np.zeros((1, 3, 224, 224), dtype=np.float32)
                net.setInput(dummy)
                res = net.forward()
            else:
                dummy = np.zeros((1, 64), dtype=np.int64)
                net.setInput(dummy)
                res = net.forward()
            if not np.isnan(res).any():
                return ("cv2", net)
            else:
                print(f"[SigLIP] cv2.dnn produced NaN outputs for {model_type}.")
                return None
        except Exception as cv_err:
            print(f"[SigLIP] cv2.dnn incompatible for {model_type}: {cv_err}")
            return None

    def compute_image_embedding(
        self,
        frame_bgr: np.ndarray,
        mask: Optional[np.ndarray] = None,
        contour: Optional[np.ndarray] = None,
        polygon: Optional[list] = None,
    ) -> Optional[np.ndarray]:
        """
        Produce an L2-normalized 768-dim SigLIP visual embedding from a camera frame.
        Reuses tight-crop with neutral-gray background fill and foreground-masked
        white balance from dino_vision.
        """
        if not self.is_available() or frame_bgr is None or getattr(frame_bgr, "size", 0) == 0:
            return None

        # 1. Produce crop
        crop = None
        if mask is not None and contour is not None and _VISION_HELPERS_AVAILABLE:
            try:
                crop = crop_object_for_embedding(frame_bgr, mask, contour)
            except Exception:
                crop = None

        if crop is None and polygon is not None and _VISION_HELPERS_AVAILABLE:
            try:
                crop = crop_polygon_for_embedding(frame_bgr, polygon)
            except Exception:
                crop = None

        if crop is None:
            # Degenerate fallback: central crop of frame
            h, w = frame_bgr.shape[:2]
            side = min(h, w)
            y0 = (h - side) // 2
            x0 = (w - side) // 2
            crop = frame_bgr[y0:y0+side, x0:x0+side].copy()

        if crop is None or getattr(crop, "size", 0) == 0:
            return None

        # 2. Preprocess for SigLIP (224x224, RGB, normalized with mean 0.5, std 0.5)
        try:
            resized = cv2.resize(crop, (224, 224), interpolation=cv2.INTER_CUBIC)
            rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            mean = np.array(self._meta.get("image_mean", [0.5, 0.5, 0.5]), dtype=np.float32)
            std = np.array(self._meta.get("image_std", [0.5, 0.5, 0.5]), dtype=np.float32)
            norm_img = (rgb - mean) / std
            blob = np.transpose(norm_img, (2, 0, 1))[None, ...].astype(np.float32)
        except Exception as e:
            print(f"[SigLIP] Preprocessing error: {e}")
            return None

        # 3. Forward pass through vision engine
        with self._lock:
            try:
                engine_type, engine = self._image_engine
                if engine_type == "cv2":
                    engine.setInput(blob)
                    out = engine.forward()
                else:
                    input_name = engine.get_inputs()[0].name
                    out = engine.run(None, {input_name: blob})[0]
            except Exception as e:
                print(f"[SigLIP] Vision forward pass error: {e}")
                return None

        # 4. L2-normalize
        emb = np.squeeze(out).astype(np.float32)
        norm = np.linalg.norm(emb)
        if norm > 1e-8:
            emb = emb / norm
        return emb

    def get_text_embedding_for_item(self, item_name: str) -> Optional[np.ndarray]:
        """
        Return the L2-normalized 768-dim SigLIP text embedding for an inventory item name.
        Uses persistent cache in signatures/siglip_text_cache.json:
        - Cache hit: O(1) instantaneous return.
        - Cache miss: runs SentencePiece tokenizer and text ONNX tower once, caches result.
        """
        if not item_name or not str(item_name).strip():
            return None

        clean_name = str(item_name).strip().upper()
        with self._lock:
            if clean_name in self._text_cache:
                cached_vec = self._text_cache[clean_name]
                arr = np.array(cached_vec, dtype=np.float32)
                norm = np.linalg.norm(arr)
                return (arr / norm) if norm > 1e-8 else arr

        if not self.is_available():
            return None

        # Tokenize using SentencePiece
        prompt_tmpl = self._meta.get("prompt_template", "a photo of a {item_name}")
        prompt = prompt_tmpl.format(item_name=clean_name.lower())
        max_len = int(self._meta.get("max_length", 64))
        pad_id = int(self._meta.get("pad_token_id", 1))
        eos_id = int(self._meta.get("eos_token_id", 2))

        try:
            tokens = self._tokenizer.encode_as_ids(prompt)
            # Truncate and append EOS
            tokens = tokens[: max_len - 1] + [eos_id]
            # Pad to max_len
            padded = tokens + [pad_id] * (max_len - len(tokens))
            input_ids = np.array([padded], dtype=np.int64)
        except Exception as e:
            print(f"[SigLIP] Tokenization error for '{prompt}': {e}")
            return None

        # Forward pass through text engine
        with self._lock:
            try:
                engine_type, engine = self._text_engine
                if engine_type == "cv2":
                    engine.setInput(input_ids)
                    out = engine.forward()
                else:
                    input_name = engine.get_inputs()[0].name
                    out = engine.run(None, {input_name: input_ids})[0]
            except Exception as e:
                print(f"[SigLIP] Text forward pass error: {e}")
                return None

        # L2-normalize
        emb = np.squeeze(out).astype(np.float32)
        norm = np.linalg.norm(emb)
        if norm > 1e-8:
            emb = emb / norm

        # Save in persistent cache
        with self._lock:
            self._text_cache[clean_name] = emb.tolist()
            self._save_cache()

        return emb


def is_available() -> bool:
    return SiglipZeroShotMatcher.instance().is_available()


def unavailable_reason() -> Optional[str]:
    return SiglipZeroShotMatcher.instance().unavailable_reason()


def compute_image_embedding(
    frame_bgr: np.ndarray,
    mask: Optional[np.ndarray] = None,
    contour: Optional[np.ndarray] = None,
    polygon: Optional[list] = None,
) -> Optional[np.ndarray]:
    return SiglipZeroShotMatcher.instance().compute_image_embedding(
        frame_bgr, mask=mask, contour=contour, polygon=polygon
    )


def get_text_embedding_for_item(item_name: str) -> Optional[np.ndarray]:
    return SiglipZeroShotMatcher.instance().get_text_embedding_for_item(item_name)


def calibrate_siglip_score(raw_cosine: float) -> float:
    """
    Calibrate raw SigLIP cosine similarity using SigLIP's learned temperature and bias:
        logit = raw_cosine * exp(logit_scale) + logit_bias
              = raw_cosine * 117.33076 - 12.93244
        probability = 1 / (1 + exp(-logit))
    Maps raw cross-modal cosine similarity into an intuitive confidence probability in [0.0, 1.0].
    """
    import math
    if raw_cosine is None:
        return 0.0
    try:
        logit = float(raw_cosine) * 117.33076 - 12.93244
        logit = max(-30.0, min(30.0, logit))
        return float(1.0 / (1.0 + math.exp(-logit)))
    except Exception:
        return 0.0


def compare_zero_shot(
    image_embedding: Optional[np.ndarray],
    text_embedding: Optional[np.ndarray],
    calibrated: bool = True,
) -> float:
    """
    Compute similarity between normalized SigLIP image and text embeddings.
    If calibrated=True (default), maps raw cosine similarity via SigLIP's
    sigmoid calibration into an intuitive [0.0, 1.0] probability.
    If calibrated=False, returns raw cosine similarity in [0.0, 1.0].
    """
    if image_embedding is None or text_embedding is None:
        return 0.0
    try:
        score = float(np.dot(image_embedding, text_embedding))
        raw = float(max(0.0, min(1.0, score)))
        if calibrated:
            return calibrate_siglip_score(raw)
        return raw
    except Exception:
        return 0.0
