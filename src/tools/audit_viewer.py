"""
Simple viewer/query interface for the audit trail database.
Useful for viewing audit logs in a backoffice GUI or for debugging.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Dict, Any
from src.tools.audit_trail import get_audit_trail
import json


def format_audit_entry(entry: Dict[str, Any], include_tool_calls: bool = True) -> str:
    """
    Format an audit log entry as a readable string.
    
    Args:
        entry: Audit log entry dictionary
        include_tool_calls: Whether to include tool call details
        
    Returns:
        Formatted string representation
    """
    lines = []
    lines.append(f"[{entry['timestamp']}] {entry['agent_name']} - {entry['event_type']}")
    lines.append(f"  Session: {entry['session_id']}")
    
    if entry['employee_id']:
        lines.append(f"  Employee: {entry['employee_id']}")
    
    if entry['user_message']:
        lines.append(f"  User: {entry['user_message'][:100]}...")
    
    if entry['agent_response']:
        response_preview = entry['agent_response'][:200]
        lines.append(f"  Response: {response_preview}...")
    
    if include_tool_calls and 'tool_calls' in entry:
        tool_calls = entry['tool_calls']
        if tool_calls:
            lines.append(f"  Tool Calls ({len(tool_calls)}):")
            for tc in tool_calls:
                status = "✓" if tc['success'] else "✗"
                lines.append(f"    {status} {tc['tool_name']}")
                if tc['tool_params']:
                    params = json.loads(tc['tool_params']) if isinstance(tc['tool_params'], str) else tc['tool_params']
                    lines.append(f"      Params: {json.dumps(params, indent=6)[:100]}")
                if tc['execution_time_ms']:
                    lines.append(f"      Time: {tc['execution_time_ms']:.2f}ms")
                if not tc['success'] and tc['error_message']:
                    lines.append(f"      Error: {tc['error_message']}")
    
    if 'delegations' in entry and entry['delegations']:
        delegations = entry['delegations']
        lines.append(f"  Delegations ({len(delegations)}):")
        for d in delegations:
            lines.append(f"    {d['from_agent']} → {d['to_agent']}")
            if d['delegation_reason']:
                lines.append(f"      Reason: {d['delegation_reason']}")
    
    return "\n".join(lines)


def view_recent_audit_logs(
    limit: int = 20,
    agent_name: Optional[str] = None,
    employee_id: Optional[str] = None
) -> List[str]:
    """
    View recent audit log entries.
    
    Args:
        limit: Maximum number of entries to return
        agent_name: Filter by agent name
        employee_id: Filter by employee ID
        
    Returns:
        List of formatted audit log strings
    """
    audit = get_audit_trail()
    conn = audit._get_connection()
    cursor = conn.cursor()
    
    query = "SELECT DISTINCT session_id FROM audit_log"
    conditions = []
    params = []
    
    if agent_name:
        conditions.append("agent_name = ?")
        params.append(agent_name)
    
    if employee_id:
        conditions.append("employee_id = ?")
        params.append(employee_id)
    
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    
    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    session_ids = [row[0] for row in cursor.fetchall()]
    
    results = []
    for session_id in session_ids:
        history = audit.get_session_history(session_id, limit=1)
        if history:
            results.append(format_audit_entry(history[0]))
    
    return results


def get_audit_summary(
    session_id: Optional[str] = None,
    employee_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get summary statistics from audit trail.
    
    Args:
        session_id: Filter by session ID
        employee_id: Filter by employee ID
        start_date: Start date filter (ISO format)
        end_date: End date filter (ISO format)
        
    Returns:
        Dictionary with summary statistics
    """
    audit = get_audit_trail()
    conn = audit._get_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT 
            COUNT(*) as total_requests,
            COUNT(DISTINCT session_id) as total_sessions,
            COUNT(DISTINCT employee_id) as total_employees,
            COUNT(DISTINCT agent_name) as total_agents
        FROM audit_log
        WHERE 1=1
    """
    params = []
    
    if session_id:
        query += " AND session_id = ?"
        params.append(session_id)
    
    if employee_id:
        query += " AND employee_id = ?"
        params.append(employee_id)
    
    if start_date:
        query += " AND timestamp >= ?"
        params.append(start_date)
    
    if end_date:
        query += " AND timestamp <= ?"
        params.append(end_date)
    
    cursor.execute(query, params)
    row = cursor.fetchone()
    
    # Get tool call statistics
    tool_query = """
        SELECT 
            tool_name,
            COUNT(*) as call_count,
            AVG(execution_time_ms) as avg_time_ms,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
        FROM tool_calls
        GROUP BY tool_name
        ORDER BY call_count DESC
    """
    cursor.execute(tool_query)
    tool_stats = [dict(row) for row in cursor.fetchall()]
    
    # Get agent delegation statistics
    delegation_query = """
        SELECT 
            from_agent,
            to_agent,
            COUNT(*) as delegation_count
        FROM agent_delegations
        GROUP BY from_agent, to_agent
        ORDER BY delegation_count DESC
    """
    cursor.execute(delegation_query)
    delegation_stats = [dict(row) for row in cursor.fetchall()]
    
    return {
        'summary': dict(row),
        'tool_statistics': tool_stats,
        'delegation_statistics': delegation_stats
    }


def export_audit_trail_to_json(
    output_file: str,
    session_id: Optional[str] = None,
    employee_id: Optional[str] = None
):
    """
    Export audit trail to JSON file.
    
    Args:
        output_file: Path to output JSON file
        session_id: Filter by session ID
        employee_id: Filter by employee ID
    """
    audit = get_audit_trail()
    
    if session_id:
        entries = audit.get_session_history(session_id)
    elif employee_id:
        entries = audit.get_employee_audit_trail(employee_id)
    else:
        # Get all entries
        conn = audit._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT session_id FROM audit_log")
        session_ids = [row[0] for row in cursor.fetchall()]
        entries = []
        for sid in session_ids:
            entries.extend(audit.get_session_history(sid))
    
    with open(output_file, 'w') as f:
        json.dump(entries, f, indent=2, default=str)
    
    print(f"Exported {len(entries)} audit log entries to {output_file}")


if __name__ == "__main__":
    # Example usage
    print("=== Recent Audit Logs ===")
    recent = view_recent_audit_logs(limit=5)
    for entry in recent:
        print(entry)
        print("-" * 80)
    
    print("\n=== Audit Summary ===")
    summary = get_audit_summary()
    print(json.dumps(summary, indent=2, default=str))

