def trigger_escalation(violation):
    """
    Module 3: Escalation Pipeline
    Routes LOW/MED to DB log; routes HIGH/CRIT to real-time alert + DB log.
    (DB logging is handled by reports.py, this handles the active alerts)
    """
    severity = violation.get("severity", "LOW")
    behavior = violation.get("behavior_class", "Unknown")
    zone = violation.get("zone", "Unknown Zone")

    if severity in ["HIGH", "CRITICAL"]:
        # Simulate sending a real-time alert (e.g., SMS, Email, Slack)
        print(f"\n[🚨 REAL-TIME ALERT TRIGGERED] {severity} Safety Violation!")
        print(f"   -> Behavior: {behavior}")
        print(f"   -> Location: {zone}")
        print(f"   -> Action: Dispatching automated SMS to Safety Manager and Shift Supervisor...\n")
        return True
    
    # LOW / MEDIUM do not trigger active alerts
    return False
