"""
export_siglip_model.py
----------------------
One-time offline setup utility for SigLIP zero-shot category validation.
Runs on any development machine with internet access (not necessarily the POS machine).

Downloads a lightweight SigLIP model checkpoint (google/siglip-base-patch16-224),
exports the image and text encoder towers to ONNX, extracts the SentencePiece
tokenizer model file, and generates deployment metadata.

Usage:
    pip install transformers torch onnx sentencepiece
    python export_siglip_model.py

Outputs (in models/):
    1. models/siglip_image.onnx       - Vision encoder tower (224x224 input -> 768-dim L2 vector)
    2. models/siglip_text.onnx        - Text encoder tower (64-token input -> 768-dim L2 vector)
    3. models/siglip_tokenizer.model  - SentencePiece vocabulary/tokenizer model
    4. models/siglip_meta.json        - Config & preprocessing parameters
"""

import os
import sys

# Ensure stdout and stderr support emojis on Windows (avoids cp1252 charmap encode error on \u2705)
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import json
import shutil

MODEL_ID = "google/siglip-base-patch16-224"
IMAGE_SIZE = 224
MAX_TEXT_LENGTH = 64
OPSET_VERSION = 18


def check_prerequisites():
    missing = []
    for pkg in ("torch", "transformers", "onnx", "sentencepiece"):
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        print("=" * 72)
        print("ERROR: Missing required export dependencies:")
        print(f"  {', '.join(missing)}")
        print("\nPlease install them on this setup machine by running:")
        print(f"  pip install {' '.join(missing)}")
        print("=" * 72)
        sys.exit(1)


def export_models(output_dir: str):
    import torch
    import torch.nn as nn
    from transformers import AutoModel, AutoTokenizer
    from huggingface_hub import hf_hub_download

    os.makedirs(output_dir, exist_ok=True)
    image_onnx_path = os.path.join(output_dir, "siglip_image.onnx")
    text_onnx_path = os.path.join(output_dir, "siglip_text.onnx")
    tokenizer_model_path = os.path.join(output_dir, "siglip_tokenizer.model")
    meta_json_path = os.path.join(output_dir, "siglip_meta.json")

    print(f"[*] Downloading / loading '{MODEL_ID}' from Hugging Face...")
    model = AutoModel.from_pretrained(MODEL_ID)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    model.eval()

    # ---------------------------------------------------------
    # 1. Export Image Encoder Tower
    # ---------------------------------------------------------
    print("\n[*] Exporting Image Encoder tower to ONNX...")
    class SiglipVisionWrapper(nn.Module):
        def __init__(self, vision_model):
            super().__init__()
            self.vision_model = vision_model

        def forward(self, pixel_values: torch.Tensor) -> torch.Tensor:
            outputs = self.vision_model(pixel_values=pixel_values)
            # pooler_output shape: (B, hidden_size)
            embeds = outputs.pooler_output
            embeds = embeds / embeds.norm(dim=-1, keepdim=True)
            return embeds

    vision_wrapper = SiglipVisionWrapper(model.vision_model).eval()
    dummy_image = torch.randn(1, 3, IMAGE_SIZE, IMAGE_SIZE, dtype=torch.float32)

    torch.onnx.export(
        vision_wrapper,
        dummy_image,
        image_onnx_path,
        export_params=True,
        opset_version=OPSET_VERSION,
        do_constant_folding=True,
        input_names=["pixel_values"],
        output_names=["image_embedding"],
        dynamic_axes={"pixel_values": {0: "batch_size"}, "image_embedding": {0: "batch_size"}},
    )
    print(f"[+] Image encoder saved: {image_onnx_path} ({os.path.getsize(image_onnx_path) / (1024*1024):.1f} MB)")

    # ---------------------------------------------------------
    # 2. Export Text Encoder Tower
    # ---------------------------------------------------------
    print("\n[*] Exporting Text Encoder tower to ONNX...")
    class SiglipTextWrapper(nn.Module):
        def __init__(self, text_model):
            super().__init__()
            self.text_model = text_model

        def forward(self, input_ids: torch.Tensor) -> torch.Tensor:
            outputs = self.text_model(input_ids=input_ids)
            # pooler_output shape: (B, hidden_size)
            embeds = outputs.pooler_output
            embeds = embeds / embeds.norm(dim=-1, keepdim=True)
            return embeds

    text_wrapper = SiglipTextWrapper(model.text_model).eval()
    dummy_text = torch.zeros((1, MAX_TEXT_LENGTH), dtype=torch.int64)

    torch.onnx.export(
        text_wrapper,
        dummy_text,
        text_onnx_path,
        export_params=True,
        opset_version=OPSET_VERSION,
        do_constant_folding=True,
        input_names=["input_ids"],
        output_names=["text_embedding"],
        dynamic_axes={"input_ids": {0: "batch_size"}, "text_embedding": {0: "batch_size"}},
    )
    print(f"[+] Text encoder saved: {text_onnx_path} ({os.path.getsize(text_onnx_path) / (1024*1024):.1f} MB)")

    # ---------------------------------------------------------
    # 3. Export SentencePiece Tokenizer Model
    # ---------------------------------------------------------
    print("\n[*] Extracting SentencePiece tokenizer model...")
    sp_downloaded = None
    try:
        sp_downloaded = hf_hub_download(repo_id=MODEL_ID, filename="spiece.model")
    except Exception as e:
        print(f"[-] Could not download spiece.model directly: {e}")

    if not sp_downloaded or not os.path.exists(sp_downloaded):
        # Fallback: check vocab_file attribute
        vocab_file = getattr(tokenizer, "vocab_file", None)
        if vocab_file and os.path.exists(vocab_file):
            sp_downloaded = vocab_file

    if sp_downloaded and os.path.exists(sp_downloaded):
        shutil.copyfile(sp_downloaded, tokenizer_model_path)
        print(f"[+] Tokenizer model saved: {tokenizer_model_path} ({os.path.getsize(tokenizer_model_path) / 1024:.1f} KB)")
    else:
        print("[-] Warning: spiece.model could not be copied automatically.")

    # ---------------------------------------------------------
    # 4. Save Metadata & Config JSON
    # ---------------------------------------------------------
    pad_id = int(getattr(tokenizer, "pad_token_id", 1) if getattr(tokenizer, "pad_token_id", None) is not None else 1)
    eos_id = int(getattr(tokenizer, "eos_token_id", 2) if getattr(tokenizer, "eos_token_id", None) is not None else 2)

    meta = {
        "model_id": MODEL_ID,
        "embedding_dim": 768,
        "image_size": IMAGE_SIZE,
        "max_length": MAX_TEXT_LENGTH,
        "pad_token_id": pad_id,
        "eos_token_id": eos_id,
        "image_mean": [0.5, 0.5, 0.5],
        "image_std": [0.5, 0.5, 0.5],
        "prompt_template": "a photo of a {item_name}",
    }
    with open(meta_json_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)
    print(f"[+] Metadata saved: {meta_json_path}")

    # ---------------------------------------------------------
    # 5. Output Instructions
    # ---------------------------------------------------------
    print("\n" + "=" * 72)
    print("[SUCCESS] SigLIP Zero-Shot Model Artifacts Exported Successfully!")
    print("=" * 72)
    print(f"Exported files located in '{output_dir}':")
    print(f"  1. {os.path.basename(image_onnx_path)}")
    print(f"  2. {os.path.basename(text_onnx_path)}")
    print(f"  3. {os.path.basename(tokenizer_model_path)}")
    print(f"  4. {os.path.basename(meta_json_path)}")
    print("\nDEPLOYMENT TO POS MACHINE (100% OFFLINE RUNTIME):")
    print("  1. Copy the 'models/' folder containing these 4 files into your")
    print("     POS application directory.")
    print("  2. On the POS machine, install the lightweight tokenizer package:")
    print("     pip install sentencepiece")
    print("  3. Run the new entry point:")
    print("     python main2.py")
    print("=" * 72)


if __name__ == "__main__":
    check_prerequisites()
    app_root = os.path.dirname(os.path.abspath(__file__))
    models_target_dir = os.path.join(app_root, "models")
    export_models(models_target_dir)
