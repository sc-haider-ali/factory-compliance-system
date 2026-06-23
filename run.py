"""
Factory Compliance & Alert Escalation System — Main Pipeline
=============================================================
Runs the full end-to-end compliance pipeline:
  1. Parse the compliance policy PDF → extract rules (Module 1 prerequisite)
  2. Initialise the violations database          (Module 4)
  3. Detect violations in video clips            (Module 1)
  4. Assign severity + save + escalate           (Modules 2, 3, 4)

Usage:
  python run.py                                           # defaults
  python run.py --policy compliance_policy.pdf            # explicit policy
  python run.py --data data_run/                          # explicit data folder
  python run.py --skip-policy                             # reuse existing rules
  python run.py --policy compliance_policy.pdf --data data_run/
"""

import os
import sys
import argparse
import subprocess

sys.path.append(os.path.dirname(__file__))

from src.parse_policy import extract_policy_rules
from src.detection import process_all_videos
from src.severity import enrich_violation
from src.reports import init_database, save_violation
from src.escalation import trigger_escalation


def parse_args():
    parser = argparse.ArgumentParser(
        description="Factory Compliance & Alert Escalation System — "
                    "End-to-end pipeline for detecting safety violations in factory video."
    )
    parser.add_argument(
        "--policy",
        type=str,
        default="compliance_policy.pdf",
        help="Path to the facility's EHS compliance policy PDF (default: compliance_policy.pdf)"
    )
    parser.add_argument(
        "--data",
        type=str,
        default="data_run/",
        help="Path to the folder containing video clips to analyze (default: data_run/)"
    )
    parser.add_argument(
        "--skip-policy",
        action="store_true",
        help="Skip policy parsing and reuse existing outputs/policy_rules.json"
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Launch the Streamlit web dashboard"
    )
    return parser.parse_args()


def print_summary(violations):
    """Print a structured summary table of violations by severity."""
    counts = {}
    for v in violations:
        sev = v.get("severity", "UNKNOWN")
        counts[sev] = counts.get(sev, 0) + 1

    tier_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    print("\n" + "=" * 50)
    print("COMPLIANCE SUMMARY REPORT")
    print("=" * 50)
    print(f"  {'Severity':<12} {'Count':>6}")
    print(f"  {'-'*12} {'-'*6}")
    for tier in tier_order:
        count = counts.get(tier, 0)
        if count > 0:
            print(f"  {tier:<12} {count:>6}")
    print(f"  {'-'*12} {'-'*6}")
    print(f"  {'TOTAL':<12} {len(violations):>6}")
    print("=" * 50)


def main():
    args = parse_args()

    if args.dashboard:
        print("🚀 Launching Dashboard...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "src/dashboard.py"])
        return

    print("=" * 50)
    print("FACTORY COMPLIANCE & ALERT ESCALATION SYSTEM")
    print("=" * 50)

    # ── Step 1: Parse compliance policy document ─────────────
    if args.skip_policy:
        print("\n[1/4] Skipping policy parsing (--skip-policy flag set)")
        print("       Using existing outputs/policy_rules.json")
        if not os.path.exists("outputs/policy_rules.json"):
            print("  ❌ ERROR: outputs/policy_rules.json not found!")
            print("     Run without --skip-policy first.")
            sys.exit(1)
    else:
        print(f"\n[1/4] Parsing compliance policy document...")
        print(f"       Input: {args.policy}")
        if not os.path.exists(args.policy):
            print(f"  ❌ ERROR: Policy document not found: {args.policy}")
            sys.exit(1)
        rules = extract_policy_rules(args.policy)
        print(f"  ✅ Extracted {len(rules['classes'])} behavior classes from policy")

    # ── Step 2: Initialise violations database ───────────────
    print("\n[2/4] Setting up violations database...")
    init_database()

    # ── Step 3: Detect violations in video clips ─────────────
    print(f"\n[3/4] Running detection on video clips...")
    print(f"       Input folder: {args.data}")
    if not os.path.exists(args.data):
        print(f"  ❌ ERROR: Data folder not found: {args.data}")
        sys.exit(1)

    # Count videos before processing
    video_extensions = ('.mp4', '.avi', '.mov', '.MP4', '.AVI')
    video_count = sum(
        1 for root, dirs, files in os.walk(args.data)
        for f in files if f.endswith(video_extensions)
    )
    print(f"       Found {video_count} video clip(s) to process")

    raw_violations = process_all_videos(args.data)

    # ── Step 4: Enrich with severity, save, and escalate ─────
    print(f"\n[4/4] Assigning severity and saving reports...")
    enriched_violations = []
    for v in raw_violations:
        enriched = enrich_violation(v)
        event_id = save_violation(enriched)

        # Module 3 — Escalation Pipeline
        trigger_escalation(enriched)

        action = enriched["escalation_action"]
        print(f"  [{enriched['severity']}] {v['behavior_class']} — {action} (ID: {event_id[:8]}...)")
        enriched_violations.append(enriched)

    # ── Summary ──────────────────────────────────────────────
    print_summary(enriched_violations)
    print(f"\n✅ Done! {len(enriched_violations)} violation(s) processed and logged.")
    print(f"   Policy:    {args.policy}")
    print(f"   Data:      {args.data}")
    print(f"   Database:  outputs/violations.db")
    print(f"\n💡 Launch the dashboard with:")
    print(f"   streamlit run src/dashboard.py")


if __name__ == "__main__":
    main()
