"""Deep (CNN) appearance embeddings for product matching.

Uses a pretrained MobileNetV2 (ImageNet) in ONNX format, executed with
OpenCV's DNN module - no extra Python dependencies. The pooled CNN feature
captures texture + shape + color together, which stays far more stable than
hand-made color statistics when an item is viewed through a translucent,
folded plastic cover.

The model file is looked up at <app_dir>/models/mobilenetv2-7.onnx and is
downloaded automatically (in the background) on first run if missing.
"""

import os
import threading
import urllib.request
from typing import Optional

import cv2
import numpy as np

MODEL_FILE = "mobilenetv2-7.onnx"
MODEL_URLS = [
    "https://github.com/onnx/models/raw/main/validated/vision/classification/mobilenet/model/mobilenetv2-7.onnx",
    "https://github.com/onnx/models/raw/main/vision/classification/mobilenet/model/mobilenetv2-7.onnx",
]

_IMAGENET_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
_IMAGENET_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def simulate_cover(crop_bgr: np.ndarray, alpha: float, blur_ks: int = 9) -> np.ndarray:
    """Approximate how a crop looks under translucent plastic: milky white
    haze plus light scattering (blur) and washed-out contrast. Training with
    these variants lets a single bare capture also match later when the item
    sits inside a folded/shrunken cover."""
    white = np.full_like(crop_bgr, 235)
    hazed = cv2.addWeighted(crop_bgr, 1.0 - float(alpha), white, float(alpha), 0.0)
    k = max(3, int(blur_ks) | 1)
    return cv2.GaussianBlur(hazed, (k, k), 0)


class DeepEmbedder:
    def __init__(self, app_dir: str):
        self._model_path = os.path.join(app_dir, "models", MODEL_FILE)
        self._net = None
        self._out_name = None
        self._lock = threading.Lock()
        self._failed = False
        if os.path.exists(self._model_path):
            self._load()
        else:
            threading.Thread(target=self._download_and_load, daemon=True).start()

    def available(self) -> bool:
        return self._net is not None

    def _download_and_load(self) -> None:
        try:
            os.makedirs(os.path.dirname(self._model_path), exist_ok=True)
            tmp = self._model_path + ".part"
            for url in MODEL_URLS:
                try:
                    urllib.request.urlretrieve(url, tmp)
                    os.replace(tmp, self._model_path)
                    break
                except Exception:
                    continue
            if os.path.exists(self._model_path):
                self._load()
            else:
                self._failed = True
        except Exception:
            self._failed = True

    def _load(self) -> None:
        try:
            net = cv2.dnn.readNetFromONNX(self._model_path)
            out_name = None
            try:
                for name in net.getLayerNames():
                    low = str(name).lower()
                    if "pool" in low:
                        out_name = name  # keep the LAST pooling layer (global average pool)
            except Exception:
                out_name = None
            with self._lock:
                self._net = net
                self._out_name = out_name
        except Exception:
            self._failed = True

    def embed(self, crop_bgr: Optional[np.ndarray]) -> Optional[np.ndarray]:
        """L2-normalized deep feature for a BGR crop, or None if the model
        is not ready / the crop is unusable."""
        if crop_bgr is None or getattr(crop_bgr, "size", 0) == 0:
            return None
        with self._lock:
            net = self._net
            out_name = self._out_name
        if net is None:
            return None
        try:
            h, w = crop_bgr.shape[:2]
            side = max(h, w)
            pad = np.zeros((side, side, 3), dtype=np.uint8)
            y0 = (side - h) // 2
            x0 = (side - w) // 2
            pad[y0 : y0 + h, x0 : x0 + w] = crop_bgr
            img = cv2.resize(pad, (224, 224), interpolation=cv2.INTER_AREA)
            rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
            rgb = (rgb - _IMAGENET_MEAN) / _IMAGENET_STD
            blob = rgb.transpose(2, 0, 1)[None].astype(np.float32)
            with self._lock:
                net.setInput(blob)
                out = net.forward(out_name) if out_name else net.forward()
            vec = np.asarray(out, dtype=np.float32).flatten()
            norm = float(np.linalg.norm(vec) + 1e-9)
            return (vec / norm).astype(np.float32)
        except Exception:
            return None
