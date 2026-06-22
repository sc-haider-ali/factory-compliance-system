import google.generativeai as genai
import fitz  # PyMuPDF
import json
import os

from dotenv import load_dotenv

# Load key from .env file
load_dotenv()
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_KEY)

def extract_policy_rules(pdf_path="compliance_policy.pdf"):
    # Step 1: Read full PDF text
    doc = fitz.open(pdf_path)
    full_text = "\n".join([page.get_text() for page in doc])

    # Step 2: Ask Gemini to extract rules as JSON
    model = genai.GenerativeModel("gemini-2.5-flash")

    prompt = f"""
    You are parsing a factory safety policy document.
    Extract exactly 4 behavior classes and return ONLY valid JSON, nothing else.
    No markdown, no explanation, just the JSON object.

    Return this exact structure:
    {{
      "classes": [
        {{
          "id": 0,
          "unsafe_name": "Safe Walkway Violation",
          "safe_name": "Safe Walkway",
          "observable_indicator": "Person outside green floor markings",
          "policy_section": "Section 3.3.2",
          "callout_level": "WARNING",
          "domain": "Pedestrian Movement"
        }}
      ]
    }}

    Policy document text:
    {full_text}
    """

    response = model.generate_content(prompt)
    text = response.text.strip()

    # Clean up markdown
    text = text.replace("```json", "").replace("```", "").strip()
    rules = json.loads(text)

    # Step 3: Save for other modules
    if not os.path.exists("outputs"):
        os.makedirs("outputs")
        
    with open("outputs/policy_rules.json", "w") as f:
        json.dump(rules, f, indent=2)

    # SAFETY PRINT: Verify what the system parsed immediately
    print("\n--- POLICY PARSING SUCCESSFUL ---")
    for cls in rules["classes"]:
        print(f"ID {cls['id']}: {cls['unsafe_name']} (Severity: {cls['callout_level']})")
    print("---------------------------------\n")

    return rules

if __name__ == "__main__":
    extract_policy_rules()