import json

# ── LOAD SEVERITY MAP DYNAMICALLY FROM POLICY JSON ────────────
# Maps policy callout_level values to our internal severity tiers.
# This is the key that links the PDF policy to this module.
CALLOUT_TO_SEVERITY = {
    "CRITICAL": "CRITICAL",
    "WARNING":  "HIGH",
    "LOW":      "LOW",
}

def load_rules(policy_path="outputs/policy_rules.json"):
    """
    Load the policy rules extracted by parse_policy.py.
    Returns the raw JSON dict, or None if file is missing.
    """
    try:
        with open(policy_path) as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"[severity.py] Warning: '{policy_path}' not found. Using fallback defaults.")
        return None
    except json.JSONDecodeError as e:
        print(f"[severity.py] Warning: Could not parse '{policy_path}': {e}. Using fallback defaults.")
        return None


def build_severity_map(rules):
    """
    Dynamically build the SEVERITY_MAP from policy_rules.json.
    
    Each class in the JSON has a 'callout_level' (e.g., WARNING, CRITICAL).
    We translate that directly into our severity tier using CALLOUT_TO_SEVERITY.
    
    Returns: dict mapping behavior name -> severity tier string
    Example: {"Safe Walkway Violation": "HIGH", "Unauthorized Intervention": "CRITICAL", ...}
    """
    if not rules:
        # Fallback hardcoded map if JSON is unavailable
        print("[severity.py] Using hardcoded fallback severity map.")
        return {
            "Safe Walkway Violation":        "CRITICAL",
            "Carrying Overload with Forklift": "CRITICAL",
            "Unauthorized Intervention":     "HIGH",
            "Opened Panel Cover":            "LOW",
        }

    severity_map = {}
    for cls in rules.get("classes", []):
        behavior_name = cls.get("unsafe_name")
        callout_level = cls.get("callout_level", "WARNING")
        if behavior_name:
            severity_map[behavior_name] = CALLOUT_TO_SEVERITY.get(callout_level, "MEDIUM")

    print(f"[severity.py] Loaded severity map for {len(severity_map)} behavior class(es) from policy.")
    return severity_map


# ── BUILD MAPS AT MODULE LOAD TIME ────────────────────────────
# These are computed once when the module is first imported,
# so all callers share the same loaded data.
_rules = load_rules()
SEVERITY_MAP = build_severity_map(_rules)

# Context-based escalation: if panel is open AND someone is nearby → escalate LOW to MEDIUM
CONTEXT_ESCALATION = {
    ("Opened Panel Cover", "person_nearby"): "MEDIUM",
}


# ── CORE FUNCTIONS ────────────────────────────────────────────
def assign_severity(behavior_class, context=None):
    """
    Assign severity tier to a detected violation.
    
    Args:
        behavior_class: Name of the detected unsafe behavior (str)
        context: Optional dict with keys like 'person_nearby' (bool)
    
    Returns: severity string (CRITICAL / HIGH / MEDIUM / LOW)
    """
    base_severity = SEVERITY_MAP.get(behavior_class, "MEDIUM")

    # Context-based escalation
    if context:
        key = (behavior_class, "person_nearby")
        if context.get("person_nearby") and key in CONTEXT_ESCALATION:
            return CONTEXT_ESCALATION[key]

    return base_severity


def get_escalation_action(severity):
    """Determine what action to take based on severity tier."""
    if severity in ["HIGH", "CRITICAL"]:
        return "Real-time alert triggered + DB log"
    else:
        return "Logged to DB"


def enrich_violation(violation, context=None):
    """
    Main function called by run.py and dashboard.py.
    Takes a raw violation dict and adds severity + escalation info.
    
    Input:  {"behavior_class": "...", "zone": "...", ...}
    Output: Same dict + {"severity": "...", "escalation_action": "...", "needs_alert": bool}
    """
    severity = assign_severity(violation["behavior_class"], context)
    action = get_escalation_action(severity)
    return {
        **violation,
        "severity": severity,
        "escalation_action": action,
        "needs_alert": severity in ["HIGH", "CRITICAL"]
    }


if __name__ == "__main__":
    print("\n-- Loaded Severity Map ----------------------------------")
    for behavior, tier in SEVERITY_MAP.items():
        print(f"  {behavior:<40} -> {tier}")
    print()

    # Test enrich_violation
    test = {
        "behavior_class": "Unauthorized Intervention",
        "zone": "Equipment Zone"
    }
    result = enrich_violation(test)
    print("-- Test Result ------------------------------------------")
    print(result)