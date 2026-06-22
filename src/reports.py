import sqlite3
import uuid
import json
import csv
import os
from datetime import datetime

DB_PATH = "outputs/violations.db"

def init_database():
    """Create the database table if it doesn't exist."""
    os.makedirs("outputs", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS violations (
            event_id        TEXT PRIMARY KEY,
            timestamp       TEXT NOT NULL,
            clip_id         TEXT NOT NULL,
            zone            TEXT NOT NULL,
            behavior_class  TEXT NOT NULL,
            policy_rule_ref TEXT NOT NULL,
            event_description TEXT NOT NULL,
            severity        TEXT NOT NULL,
            escalation_action TEXT NOT NULL,
            frame_number    INTEGER,
            created_at      TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("Database initialized at:", DB_PATH)

def save_violation(violation):
    """Save one violation to the database and return its event_id."""
    event_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO violations
        (event_id, timestamp, clip_id, zone, behavior_class,
         policy_rule_ref, event_description, severity, escalation_action, frame_number)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        event_id,
        timestamp,
        violation.get("clip_id", "unknown"),
        violation.get("zone", "Zone-1"),
        violation.get("behavior_class", "Unknown"),
        violation.get("policy_section", "Unknown"),
        violation.get("description", "Violation detected"),
        violation.get("severity", "MEDIUM"),
        violation.get("escalation_action", "Logged to DB"),
        violation.get("frame", 0)
    ))
    conn.commit()
    conn.close()
    return event_id

def get_all_violations(severity_filter=None, behavior_filter=None):
    """Fetch violations from DB with optional filters."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM violations WHERE 1=1"
    params = []

    if severity_filter and severity_filter != "All":
        query += " AND severity = ?"
        params.append(severity_filter)

    if behavior_filter and behavior_filter != "All":
        query += " AND behavior_class = ?"
        params.append(behavior_filter)

    query += " ORDER BY timestamp DESC"

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def export_to_csv(filepath="outputs/violations_export.csv"):
    """Export all violations to CSV."""
    violations = get_all_violations()
    if not violations:
        return None
    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=violations[0].keys())
        writer.writeheader()
        writer.writerows(violations)
    return filepath

def get_summary_stats():
    """Get counts by severity for dashboard stats."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("""
        SELECT severity, COUNT(*) as count
        FROM violations
        GROUP BY severity
    """).fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}

if __name__ == "__main__":
    init_database()
    print("DB ready.")