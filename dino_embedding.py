"""
dino_embedding.py
-----------------
Local, 100%-offline-at-runtime AI feature extractor using DINOv2 ViT-S/14.

Produces a 384-dim L2-normalized embedding vector for any BGR crop.
Two photos of the *same* produce type yield cosine similarity near 1.0,
even under different lighting, angle, or natural specimen variation.

Adapted from dino_ai/embedding.py for integration into the main
AiSourceCode project.  All config constants are defined locally
(no external config module dependency).

Offline behaviour:
  1. ONE-TIME, NEEDS INTERNET: DINOv2 ViT-S/14 weights (~86 MB) are
     downloaded once via torch.hub and cached locally.
  2. FOREVER AFTER: loads cached weights from disk, CPU-only inference.
"""

import os
import threading
from typing import Optional, List, Tuple

import cv2
import numpy as np


# ---------------------------------------------------------------------------
# Constants (previously in dino_ai/config.py)
# ---------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = "dinov2_vits14"
EMBEDDING_INPUT_SIZE = 224
TRAIN_AUGMENT_SHOTS = 4


class ModelNotAvailableError(RuntimeError):
    """Raised when the local model weights aren't cached and can't be
    fetched (no internet). Tells the operator exactly what to do."""


class EmbeddingExtractor:
    """
    Thin singleton wrapper around a frozen, pretrained DINOv2 ViT-S/14
    used purely as a feature extractor. Loaded once per process; every
    call after that is pure local CPU inference.
    """

    _instance: Optional["EmbeddingExtractor"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._model = None
        self._torch = None
        self._preprocess_mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        self._preprocess_std = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    @classmethod
    def instance(cls) -> "EmbeddingExtractor":
        with cls._lock:
            if cls._instance is None:
                cls._instance = EmbeddingExtractor()
            return cls._instance

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------
    def is_loaded(self) -> bool:
        return self._model is not None

    def available(self) -> bool:
        """Return True if the model is loaded and ready for inference."""
        return self._model is not None

    def load(self) -> None:
        """
        Load DINOv2 ViT-S/14 as a frozen feature extractor, CPU only.
        Safe to call repeatedly (no-op if already loaded). Raises
        ModelNotAvailableError with an actionable message if the weights
        are neither cached locally nor downloadable right now.
        """
        if self._model is not None:
            return

        try:
            import torch
        except ImportError as exc:
            raise ModelNotAvailableError(
                "PyTorch isn't installed. Run:\n"
                "    pip install torch --index-url https://download.pytorch.org/whl/cpu\n"
                "This needs internet once, same as any pip package."
            ) from exc

        self._torch = torch
        torch.set_num_threads(max(1, os.cpu_count() or 1))

        try:
            model = torch.hub.load(
                'facebookresearch/dinov2', EMBEDDING_MODEL_NAME,
                pretrained=True,
            )
        except Exception as exc:
            raise ModelNotAvailableError(
                "Local AI model weights aren't downloaded yet, and no "
                "internet connection is available to fetch them.\n\n"
                "This is a ONE-TIME step (~86 MB): connect this machine "
                "to the internet once and run:\n"
                "    python dino_ai/download_model.py\n\n"
                "After that one-time download, the app runs fully "
                "offline forever -- no internet needed again."
            ) from exc

        model.eval()
        self._model = model

    def _inference_ctx(self):
        """Use torch.inference_mode if available, else torch.no_grad."""
        if hasattr(self._torch, "inference_mode"):
            return self._torch.inference_mode()
        return self._torch.no_grad()

    # ------------------------------------------------------------------
    # Preprocessing
    # ------------------------------------------------------------------
    def _preprocess(self, bgr_crop: np.ndarray) -> "object":
        """BGR uint8 crop -> normalized CHW float tensor, batch size 1."""
        rgb = cv2.cvtColor(bgr_crop, cv2.COLOR_BGR2RGB)
        rgb = cv2.resize(
            rgb, (EMBEDDING_INPUT_SIZE, EMBEDDING_INPUT_SIZE),
            interpolation=cv2.INTER_AREA,
        )
        arr = rgb.astype(np.float32) * (1.0 / 255.0)
        arr -= self._preprocess_mean
        arr /= self._preprocess_std
        arr = np.ascontiguousarray(np.transpose(arr, (2, 0, 1)))  # HWC -> CHW
        tensor = self._torch.from_numpy(arr).unsqueeze(0)
        return tensor

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------
    def embed(self, bgr_crop: np.ndarray) -> np.ndarray:
        """
        Run one crop through the network. Returns an L2-normalized
        384-dim embedding (so plain dot product == cosine similarity).
        """
        self.load()
        tensor = self._preprocess(bgr_crop)
        with self._inference_ctx():
            features = self._model(tensor)
        vec = features.squeeze(0).numpy().astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 1e-8:
            vec = vec / norm
        return vec

    def embed_with_augmentation(self, bgr_crop: np.ndarray,
                                 n_augments: int = None) -> np.ndarray:
        """
        Used ONLY at training time (once per item). Runs the crop
        through the network several times under small random
        brightness/contrast/white-balance jitter and averages the
        resulting embeddings before re-normalizing.

        This bakes lighting- and reflection-invariance into the
        stored fingerprint itself.
        """
        n = n_augments if n_augments is not None else TRAIN_AUGMENT_SHOTS
        vectors = [self.embed(bgr_crop)]
        rng = np.random.default_rng()
        for _ in range(max(0, n - 1)):
            jittered = _random_photometric_jitter(bgr_crop, rng)
            vectors.append(self.embed(jittered))
        mean_vec = np.mean(vectors, axis=0)
        norm = np.linalg.norm(mean_vec)
        if norm > 1e-8:
            mean_vec = mean_vec / norm
        return mean_vec

    def embed_batch(self, bgr_crops: List[np.ndarray]) -> List[np.ndarray]:
        """
        Run a batch of crops through the network in a single forward pass.
        Returns a list of L2-normalized 384-dim embedding vectors.
        """
        if not bgr_crops:
            return []
        self.load()
        try:
            tensors = [self._preprocess(c) for c in bgr_crops]
            batch_tensor = self._torch.cat(tensors, dim=0)
            with self._inference_ctx():
                features = self._model(batch_tensor)
            vecs = features.numpy().astype(np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.where(norms > 1e-8, norms, 1.0)
            vecs = vecs / norms
            return [vecs[i] for i in range(len(bgr_crops))]
        except Exception:
            # Fallback: sequential embed
            return [self.embed(c) for c in bgr_crops]

    def embed_pose_variants(
        self,
        bgr_crop: np.ndarray,
        angles: Tuple[float, ...] = (-30.0, -15.0, 15.0, 30.0),
        include_flip: bool = True,
        add_photometric: bool = True,
    ) -> List[np.ndarray]:
        """
        Generate geometric and photometric variants of a captured crop to multiply
        pose diversity in the gallery.

        NOTE: This synthetic augmentation only helps with in-plane rotation and mirroring;
        it CANNOT simulate a genuinely different resting face or 3D aspect of an object
        (e.g., garlic root-side-down vs. root-side-up) -- that still requires an actual
        different real capture from guided multi-pose training.
        """
        self.load()
        crops = [bgr_crop]
        rng = np.random.default_rng()

        # In-plane rotations
        for ang in angles:
            rot = _rotate_image(bgr_crop, float(ang))
            crops.append(rot)

        # Horizontal flip (mirroring)
        if include_flip:
            flip = cv2.flip(bgr_crop, 1)
            crops.append(flip)

        # Photometric jitter on original for extra lighting robustness
        if add_photometric:
            jittered = _random_photometric_jitter(bgr_crop, rng)
            crops.append(jittered)

        return self.embed_batch(crops)


def _rotate_image(bgr: np.ndarray, angle_deg: float, border_value=(128, 128, 128)) -> np.ndarray:
    """Rotate an image in-plane around its center by angle_deg degrees.
    Fills empty boundary pixels with neutral gray matching CROP_BACKGROUND_FILL."""
    h, w = bgr.shape[:2]
    center = (w / 2.0, h / 2.0)
    matrix = cv2.getRotationMatrix2D(center, angle_deg, 1.0)
    return cv2.warpAffine(bgr, matrix, (w, h), borderMode=cv2.BORDER_CONSTANT, borderValue=border_value)


def _random_photometric_jitter(bgr: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """Small random brightness/contrast/white-balance shift -- simulates
    the kind of lighting/reflection variation the same item will be seen
    under at different times of day, WITHOUT changing its shape/texture."""
    img = bgr.astype(np.float32)

    # Brightness
    brightness = rng.uniform(-25, 25)
    img = img + brightness

    # Contrast
    contrast = rng.uniform(0.85, 1.15)
    img = (img - 128.0) * contrast + 128.0

    # Mild per-channel white-balance shift
    for c in range(3):
        img[:, :, c] *= rng.uniform(0.92, 1.08)

    return np.clip(img, 0, 255).astype(np.uint8)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Both vectors are expected to already be L2-normalized (embed()
    guarantees this), so this is just a dot product."""
    return float(np.dot(a, b))
