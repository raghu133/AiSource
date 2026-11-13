# AiSource - AI Trainer & Vision Inspection System

An intelligent computer vision and hardware-integrated inspection application powered by PySide6, Deep Learning vision embeddings (DINOv3, SigLIP), and real-time serial scale measurements.

---

## 🌟 Key Features

- **Advanced Vision Inspection**:
  - **Meta DINOv3 Vision Embeddings**: High-precision visual representation for sample matching and similarity comparisons.
  - **Google SigLIP Zero-Shot Classification**: Semantic visual verification using multimodal embeddings.
  - **Color Matching & Analysis**: Multi-space color classification (HSV / Lab) with configurable thresholds.
- **Hardware Integration**:
  - Real-time digital weighing scale integration via RS-232 / COM serial communication.
  - Camera stream processing with custom ROI (Region of Interest) polygon boundary detection and background baseline subtraction.
- **Database & Inventory Sync**:
  - Connects to Microsoft SQL Server for real-time inventory management, item lookup, and pricing data.
- **Hardware-Locked Licensing**:
  - Machine-ID-bound cryptography and license manager using Fernet symmetric encryption and SQLite.
- **Desktop GUI**:
  - Modern, responsive Qt-based interface built with PySide6 (`dashboard.ui`).

---

## 📁 Repository Structure

```text
AiSource/
├── app_config.py                         # Application configuration & paths
├── color_matcher.py                      # HSV/Lab color analysis logic
├── dashboard.ui                          # PySide6 UI layout
├── deep_features.py                      # Vision feature extraction
├── dino_embedding.py / dino_vision.py    # DINO foundation model integration
├── dinov3_vision.py                      # DINOv3 ONNX vision pipeline
├── export_siglip_model.py                # SigLIP model export utilities
├── licence_generator.py                  # License generator tool
├── licence_manager.py                    # Client-side license verification
├── machine_id.py                         # Hardware fingerprinting
├── main2.py / main3.py                   # Primary application entry points
├── qr_utils.py                           # QR and barcode processing helpers
├── readweight.py                         # Weighing scale serial communication
├── requirements.txt                      # Python dependencies
├── settings.py / settings_store.py       # Configuration management
├── setup_dinov3_model.py                 # Setup script for DINOv3 weights
├── siglip_zero_shot.py                   # Zero-shot classification pipeline
├── icons/                                # UI SVG icons and assets
├── models/                               # Metadata and licenses for vision models
└── License Package/                      # Dedicated licensing tools and specs
```

---

## 🚀 Getting Started

### 1. Prerequisites

- Python 3.10+ (64-bit recommended)
- Git
- Microsoft Visual C++ Redistributable (for ONNX Runtime / PySide6 on Windows)

### 2. Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/raghu133/AiSource.git
   cd AiSource
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Windows CMD:
   .\.venv\Scripts\activate.bat
   ```

3. **Install dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**:
   Copy `.env.example` to `.env` and configure your encryption key:
   ```bash
   copy .env.example .env
   ```

5. **Download / Setup Model Weights**:
   Run the model preparation scripts to set up the vision model weights:
   ```bash
   python setup_dinov3_model.py
   ```

### 3. Running the Application

Launch the main trainer GUI:
```bash
python main2.py
# or
python main3.py
```

---

## 🛠️ Building Standalone Executable

The project includes PyInstaller specifications for building a standalone Windows executable:

```powershell
pyinstaller --noconfirm --clean main2.spec
```

The compiled application will be generated in `dist/AI_Trainer/`.

---

## 📄 License

Proprietary / Private - All rights reserved by [raghu133](https://github.com/raghu133).
