import os
import sys
sys.path.append(os.path.dirname(__file__))

from src.parse_policy import extract_policy_rules
from src.detection import process_all_videos
from src.severity import enrich_violation
from src.reports import init_database, save_violation
from src.escalation import trigger_escalation

def main():
    print("=" * 50)
    print("FACTORY COMPLIANCE SYSTEM")
    print("=" * 50)

    # Step 1: Parse policy
    print("\n[1/4] Parsing compliance policy...")
    rules = extract_policy_rules("compliance_policy.pdf")
    print(f"  Extracted {len(rules['classes'])} behavior classes")

    # Step 2: Initialize database
    print("\n[2/4] Setting up database...")
    init_database()

    # Step 3: Process all videos
    print("\n[3/4] Running detection on all videos...")
    raw_violations = process_all_videos("data/")

    # Step 4: Enrich and save
    print("\n[4/4] Assigning severity and saving reports...")
    for v in raw_violations:
        enriched = enrich_violation(v)
        event_id = save_violation(enriched)
        
        # Call Escalation Pipeline (Module 3)
        trigger_escalation(enriched)
        
        action = enriched["escalation_action"]
        print(f"  [{enriched['severity']}] {v['behavior_class']} — {action} (ID: {event_id[:8]}...)")

    print(f"\n✅ Done! {len(raw_violations)} violations processed.")
    print("Run dashboard with: streamlit run src/dashboard.py")

if __name__ == "__main__":
    main()
