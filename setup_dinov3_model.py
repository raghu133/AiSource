"""
setup_dinov3_model.py
---------------------
One-time setup utility for Meta DINOv3 (ViT-S/16) ONNX vision embeddings.
Runs on any machine with internet access (not necessarily the POS machine).

Downloads the pre-exported, freely-downloadable DINOv3 ViT-S/16 ONNX weights
from the onnx-community mirror on Hugging Face (requiring no gated access form,
and requiring only huggingface_hub -- no PyTorch or torchvision required).

Outputs in models/:
    1. models/dinov3_vits16.onnx      - ONNX computation graph (~138 KB)
    2. models/dinov3_vits16.onnx_data - Pretrained weight tensor sidecar (~86.3 MB)
    3. models/DINOV3_LICENSE.txt     - Official Meta DINOv3 license text
    4. models/dinov3_meta.json       - Input/output specifications & preprocessing parameters

ATTRIBUTION REQUIREMENT:
    DINOv3 is released under the Meta DINOv3 License.
    Any redistribution or deployment of an application utilizing these weights must
    prominently include the required attribution:
        "Built with DINOv3"
"""

import os
import sys
import json
import shutil

REPO_ID = "onnx-community/dinov3-vits16-pretrain-lvd1689m-ONNX"
MODEL_SUBPATH_ONNX = "onnx/model.onnx"
MODEL_SUBPATH_DATA = "onnx/model.onnx_data"
LICENSE_SUBPATH = "LICENSE.md"
CONFIG_SUBPATH = "config.json"
PREPROCESSOR_SUBPATH = "preprocessor_config.json"

TARGET_ONNX_NAME = "dinov3_vits16.onnx"
TARGET_DATA_NAME = "dinov3_vits16.onnx_data"
TARGET_LICENSE_NAME = "DINOV3_LICENSE.txt"
TARGET_META_NAME = "dinov3_meta.json"


def check_prerequisites():
    try:
        import huggingface_hub
    except ImportError:
        print("=" * 72)
        print("ERROR: Missing 'huggingface_hub' package.")
        print("Please install it by running:")
        print("    pip install huggingface_hub")
        print("=" * 72)
        sys.exit(1)


def setup_dinov3(target_dir: str):
    from huggingface_hub import hf_hub_download

    os.makedirs(target_dir, exist_ok=True)
    target_onnx = os.path.join(target_dir, TARGET_ONNX_NAME)
    target_data = os.path.join(target_dir, TARGET_DATA_NAME)
    target_license = os.path.join(target_dir, TARGET_LICENSE_NAME)
    target_meta = os.path.join(target_dir, TARGET_META_NAME)

    print("=" * 72)
    print(f"[*] Downloading pre-converted DINOv3 ViT-S/16 ONNX weights from:")
    print(f"    https://huggingface.co/{REPO_ID}")
    print("=" * 72)

    # 1. Download Model ONNX graph
    print("\n[1/4] Fetching ONNX computation graph...")
    onnx_src = hf_hub_download(repo_id=REPO_ID, filename=MODEL_SUBPATH_ONNX)
    shutil.copyfile(onnx_src, target_onnx)
    print(f"      [OK] Saved to: {target_onnx} ({os.path.getsize(target_onnx) / 1024:.1f} KB)")

    # 2. Download Model weights sidecar (.onnx_data)
    print("\n[2/4] Fetching ONNX weights sidecar data (~86 MB)...")
    data_src = hf_hub_download(repo_id=REPO_ID, filename=MODEL_SUBPATH_DATA)
    shutil.copyfile(data_src, target_data)
    target_internal_data = os.path.join(target_dir, "model.onnx_data")
    shutil.copyfile(data_src, target_internal_data)
    print(f"      [OK] Saved to: {target_data} and {target_internal_data} ({os.path.getsize(target_data) / (1024*1024):.1f} MB)")

    # 3. Download License
    print("\n[3/4] Fetching Meta DINOv3 License terms...")
    license_src = hf_hub_download(repo_id=REPO_ID, filename=LICENSE_SUBPATH)
    shutil.copyfile(license_src, target_license)
    print(f"      [OK] Saved to: {target_license}")

    # 4. Generate Metadata
    print("\n[4/4] Extracting configuration & preprocessing metadata...")
    cfg_src = hf_hub_download(repo_id=REPO_ID, filename=CONFIG_SUBPATH)
    prep_src = hf_hub_download(repo_id=REPO_ID, filename=PREPROCESSOR_SUBPATH)
    with open(cfg_src, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    with open(prep_src, "r", encoding="utf-8") as f:
        prep = json.load(f)

    meta = {
        "model_name": "Meta DINOv3 (ViT-S/16)",
        "source_repo": REPO_ID,
        "embedding_dim": int(cfg.get("hidden_size", 384)),
        "image_size": int(cfg.get("image_size", 224)),
        "patch_size": int(cfg.get("patch_size", 16)),
        "image_mean": prep.get("image_mean", [0.485, 0.456, 0.406]),
        "image_std": prep.get("image_std", [0.229, 0.224, 0.225]),
        "license": "Meta DINOv3 License",
        "attribution_notice": "Built with DINOv3",
    }
    with open(target_meta, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"      [OK] Saved to: {target_meta}")

    print("\n" + "=" * 72)
    print("[SUCCESS] DINOv3 ViT-S/16 ONNX Artifacts Successfully Set Up!")
    print("=" * 72)
    print("Installed files in 'models/':")
    print(f"  - {TARGET_ONNX_NAME}")
    print(f"  - {TARGET_DATA_NAME}")
    print(f"  - {TARGET_LICENSE_NAME}")
    print(f"  - {TARGET_META_NAME}")
    print("\nIMPORTANT LICENSING & ATTRIBUTION NOTICE:")
    print("  These weights are governed by the Meta DINOv3 License.")
    print("  When deploying or distributing this application, you must include:")
    print("  'Built with DINOv3'")
    print("  in the application UI and documentation.")
    print("\nDEPLOYMENT TO OFFLINE POS MACHINE:")
    print("  Copy the 'models/' folder containing these 4 files to your POS machine.")
    print("  Then run:")
    print("      python main2.py")
    print("=" * 72)


if __name__ == "__main__":
    check_prerequisites()
    app_root = os.path.dirname(os.path.abspath(__file__))
    models_dir = os.path.join(app_root, "models")
    setup_dinov3(models_dir)
