# 🏭 Factory Compliance & Alert Escalation System

Interface.png

## 🔄 Module Sequential Pipeline

```
┌─────────────────────┐
│  compliance_policy  │──┐
│       .pdf          │  │
└─────────────────────┘  │
                         ▼
                ┌─────────────────┐     ┌──────────────────────┐
                │  parse_policy   │────▶│ outputs/             │
                │  (Gemini LLM)   │     │  policy_rules.json   │
                └─────────────────┘     └──────────┬───────────┘
                                                   │
          ┌────────────────────────────────────────┼─────────┐
          │                                        │         │
          ▼                                        ▼         │
┌─────────────────┐   ┌──────────────┐   ┌────────────────┐  │
│  data_run/      │──▶│  Module 1    │──▶│  Module 2      │  │
│  (video clips)  │   │  Detection   │   │  Severity      │  │
│                 │   │  Engine      │   │  Matrix        │  │
└─────────────────┘   │ (ResNet-50)  │   │                │  │
                      └──────────────┘   └───────┬────────┘  │
                                                 │           │
                                    ┌────────────┼───────┐   │
                                    ▼            ▼       │   │
                             ┌────────────┐ ┌─────────┐  │   │
                             │  Module 3  │ │Module 4  │  │   │
                             │ Escalation │ │ Reports  │  │   │
                             │  Pipeline  │ │ (SQLite) │  │   │
                             └──────┬─────┘ └────┬────┘  │   │
                                    │            │       │   │
                                    ▼            ▼       │   │
                             ┌──────────────────────────┐│   │
                             │      Module 5            ││   │
                             │  Operations Dashboard    │◀───┘
                             │     (Streamlit)          │
                             └──────────────────────────┘
```

## 🧠 Model
We use a **Fine-Tuned ResNet-50 Model** combined with **Google Gemini**.
- **Gemini 2.5 Flash** parses the unstructured `compliance_policy.pdf` document and extracts specific safety rules dynamically.
- **ResNet-50** performs Computer Vision inference on factory video clips to detect safety violations, using majority-vote logic across video frames for robust accuracy.

## 🛠️ Setup & Running

**1. Setup Environment**
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

**2. Configure API Key**
Create a `.env` file in the root directory and add your key:
```env
GEMINI_API_KEY="your-api-key-here"
```

**3. Running the System (`run.py`)**
The `run.py` script is the central entry point for the system. 

To launch the interactive **Web Dashboard** (where you can upload videos and policies):
```bash
python run.py --dashboard
```

To run the **Batch Processing Pipeline** in the background (analyzes all videos in the `data_run/` folder automatically):
```bash
python run.py --policy compliance_policy.pdf --data data_run/
```

## 📂 File Directory

- `run.py`: The main entry point for running batch compliance processing or launching the dashboard.
- `src/parse_policy.py`: Uses Gemini API to extract structured safety rules from the PDF policy document.
- `src/detection.py`: Loads the ResNet-50 model and processes video frames to detect unsafe behaviors.
- `src/severity.py`: Maps detected unsafe behaviors to severity tiers (CRITICAL, HIGH, etc.) based on policy rules.
- `src/escalation.py`: Triggers simulated SMS/Email notifications for High/Critical violations.
- `src/reports.py`: Handles SQLite database operations (saving/fetching violations) and CSV exporting.
- `src/dashboard.py`: The Streamlit web interface for monitoring live feeds, alert timelines, and historical logs.
