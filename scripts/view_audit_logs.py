"""
Simple script to view audit logs.
Run this in your notebook or as a standalone script.
"""

from src.tools.audit_viewer import (
    view_recent_audit_logs,
    get_audit_summary,
    format_audit_entry,
    export_audit_trail_to_json
)
from src.tools.audit_trail import get_audit_trail
import json


def view_all_recent_logs(limit=10):
    """View the most recent audit log entries."""
    print("=" * 80)
    print(f"RECENT AUDIT LOGS (Last {limit} entries)")
    print("=" * 80)
    
    recent = view_recent_audit_logs(limit=limit)
    
    if not recent:
        print("No audit logs found.")
        return
    
    for i, log in enumerate(recent, 1):
        print(f"\n--- Entry {i} ---")
        print(log)
        print("-" * 80)


def view_summary():
    """View audit trail summary statistics."""
    print("=" * 80)
    print("AUDIT TRAIL SUMMARY")
    print("=" * 80)
    
    summary = get_audit_summary()
    
    print("\nOverall Statistics:")
    print(json.dumps(summary['summary'], indent=2, default=str))
    
    if summary['tool_statistics']:
        print("\nTool Call Statistics:")
        for tool_stat in summary['tool_statistics']:
            print(f"  {tool_stat['tool_name']}:")
            print(f"    - Total calls: {tool_stat['call_count']}")
            print(f"    - Success rate: {tool_stat['success_count']}/{tool_stat['call_count']}")
            print(f"    - Avg time: {tool_stat['avg_time_ms']:.2f}ms")
    
    if summary['delegation_statistics']:
        print("\nAgent Delegation Statistics:")
        for del_stat in summary['delegation_statistics']:
            print(f"  {del_stat['from_agent']} → {del_stat['to_agent']}: {del_stat['delegation_count']} times")


def view_session_history(session_id=None):
    """View history for a specific session or all sessions."""
    audit = get_audit_trail()
    
    if session_id:
        print(f"=" * 80)
        print(f"SESSION HISTORY: {session_id}")
        print("=" * 80)
        history = audit.get_session_history(session_id)
    else:
        # Get all session IDs
        conn = audit._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT session_id FROM audit_log ORDER BY timestamp DESC LIMIT 5")
        session_ids = [row[0] for row in cursor.fetchall()]
        
        if not session_ids:
            print("No sessions found.")
            return
        
        print("=" * 80)
        print(f"RECENT SESSIONS (showing first 5)")
        print("=" * 80)
        
        for sid in session_ids:
            history = audit.get_session_history(sid, limit=10)
            print(f"\n--- Session: {sid} ({len(history)} entries) ---")
            for entry in history:
                print(format_audit_entry(entry))
                print("-" * 80)
        return
    
    if not history:
        print("No history found for this session.")
        return
    
    for entry in history:
        print(format_audit_entry(entry))
        print("-" * 80)


def view_employee_logs(employee_id="mark_tan", limit=20):
    """View audit logs for a specific employee."""
    audit = get_audit_trail()
    
    print("=" * 80)
    print(f"AUDIT LOGS FOR EMPLOYEE: {employee_id}")
    print("=" * 80)
    
    logs = audit.get_employee_audit_trail(employee_id, limit=limit)
    
    if not logs:
        print(f"No logs found for employee {employee_id}.")
        return
    
    for i, log in enumerate(logs, 1):
        print(f"\n--- Entry {i} ---")
        print(f"Timestamp: {log['timestamp']}")
        print(f"Agent: {log['agent_name']}")
        print(f"Session: {log['session_id']}")
        if log['user_message']:
            print(f"User: {log['user_message'][:100]}...")
        if log['agent_response']:
            print(f"Response: {log['agent_response'][:200]}...")
        print("-" * 80)


if __name__ == "__main__":
    # Example usage - uncomment what you want to see
    
    # View recent logs
    view_all_recent_logs(limit=10)
    
    # View summary statistics
    print("\n\n")
    view_summary()
    
    # View session history
    print("\n\n")
    view_session_history()
    
    # View employee logs
    print("\n\n")
    view_employee_logs("mark_tan", limit=10)

