"""
Simple example showing how to use the audit trail system.

This can be run standalone or integrated into your notebook.
"""

from src.tools.audit_trail import get_audit_trail, generate_session_id
from src.tools.audit_helper import log_agent_interaction
from src.tools.audit_viewer import view_recent_audit_logs, get_audit_summary, format_audit_entry


def example_basic_usage():
    """Example of basic audit trail usage."""
    
    # Initialize audit trail (creates audit_trail.db if it doesn't exist)
    audit = get_audit_trail()
    
    # Generate a session ID for a conversation
    session_id = generate_session_id()
    print(f"Session ID: {session_id}")
    
    # Log a user request
    audit_log_id = audit.log_request(
        session_id=session_id,
        agent_name="hr_manager",
        user_message="I want to apply for 7 days of annual leave",
        employee_id="mark_tan"
    )
    print(f"Logged request with ID: {audit_log_id}")
    
    # Log a tool call
    audit.log_tool_call(
        audit_log_id=audit_log_id,
        tool_name="draft_leave_request_tool",
        tool_params={
            "employee_id": "mark_tan",
            "leave_type": "annual",
            "start_date": "2025-12-05",
            "end_date": "2025-12-11"
        },
        tool_result='{"draft_id": "draft-12345", "status": "created", "days": 7}',
        execution_time_ms=125.5,
        success=True
    )
    
    # Log agent delegation
    audit.log_delegation(
        audit_log_id=audit_log_id,
        from_agent="hr_manager",
        to_agent="leave_specialist",
        delegation_reason="User requested leave application"
    )
    
    # Log the agent response
    audit.log_response(
        audit_log_id=audit_log_id,
        agent_response="I've created a draft leave request for 7 days of annual leave from 2025-12-05 to 2025-12-11. Your draft ID is draft-12345."
    )
    
    print("✓ Audit trail entry created")


def example_using_helper():
    """Example using the helper function for simpler logging."""
    
    session_id = generate_session_id()
    
    # Use the helper function to log everything at once
    log_agent_interaction(
        session_id=session_id,
        agent_name="hr_manager",
        user_message="Check my leave balance",
        agent_response="You have 15 days of annual leave remaining.",
        employee_id="mark_tan",
        tool_calls=[
            {
                'tool_name': 'get_leave_balance_tool',
                'params': {'employee_id': 'mark_tan', 'leave_type': 'annual'},
                'result': '{"balance": 15, "unit": "days"}',
                'execution_time_ms': 45.2,
                'success': True
            }
        ],
        delegations=[
            {
                'from_agent': 'hr_manager',
                'to_agent': 'leave_specialist',
                'reason': 'User requested leave balance check'
            }
        ]
    )
    
    print("✓ Audit trail entry created using helper")


def example_viewing_logs():
    """Example of viewing audit logs."""
    
    print("\n=== Recent Audit Logs ===")
    recent_logs = view_recent_audit_logs(limit=5)
    for log in recent_logs:
        print(log)
        print("-" * 80)
    
    print("\n=== Audit Summary ===")
    summary = get_audit_summary()
    import json
    print(json.dumps(summary, indent=2, default=str))


def example_session_history():
    """Example of retrieving session history."""
    
    audit = get_audit_trail()
    
    # Get all session IDs
    conn = audit._get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT session_id FROM audit_log LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        session_id = row[0]
        print(f"\n=== History for Session: {session_id} ===")
        history = audit.get_session_history(session_id)
        
        for entry in history:
            print(format_audit_entry(entry))
            print("-" * 80)


if __name__ == "__main__":
    print("Creating example audit trail entries...")
    example_basic_usage()
    example_using_helper()
    
    print("\n" + "=" * 80)
    example_viewing_logs()
    example_session_history()

