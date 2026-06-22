import json

# Load policy rules (extracted by Module 1)
def load_rules():
    try:
        with open("outputs/policy_rules.json") as f:
            return json.load(f)
    except:
        return None

# Severity mapping — derived from policy callout levels
# "CRITICAL SAFETY NOTICE" in policy → CRITICAL here
# "WARNING" in policy → HIGH here
# State-based (no person needed) → LOW
SEVERITY_MAP = {
    "Safe Walkway Violation":        "CRITICAL",  # Policy: highest-frequency, WARNING callout
    "Carrying Overload with Forklift": "CRITICAL", # Policy: CRITICAL SAFETY NOTICE
    "Unauthorized Intervention":     "HIGH",       # Policy: WARNING callout
    "Opened Panel Cover":            "LOW",        # Policy: state-based, no person required
}

# If panel is open AND person is nearby → escalate to MEDIUM
CONTEXT_ESCALATION = {
    ("Opened Panel Cover", "person_nearby"): "MEDIUM",
}

def assign_severity(behavior_class, context=None):
    """
    Assign severity tier to a violation.
    context: dict with optional keys like 'person_nearby' (bool)
    """
    base_severity = SEVERITY_MAP.get(behavior_class, "MEDIUM")

    # Context-based escalation
    if context:
        key = (behavior_class, "person_nearby")
        if context.get("person_nearby") and key in CONTEXT_ESCALATION:
            return CONTEXT_ESCALATION[key]

    return base_severity

def get_escalation_action(severity):
    """Determine what action to take based on severity."""
    if severity in ["HIGH", "CRITICAL"]:
        return "Real-time alert triggered + DB log"
    else:
        return "Logged to DB"

def enrich_violation(violation, context=None):
    """Add severity and escalation action to a violation record."""
    severity = assign_severity(violation["behavior_class"], context)
    action = get_escalation_action(severity)
    return {
        **violation,
        "severity": severity,
        "escalation_action": action,
        "needs_alert": severity in ["HIGH", "CRITICAL"]
    }

if __name__ == "__main__":
    # Test
    test = {
        "behavior_class": "Safe Walkway Violation",
        "zone": "Walkway Zone"
    }
    result = enrich_violation(test)
    print(result)