"""
Flask web application for viewing audit logs.
Run with: python audit_gui/app.py
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from src.tools.audit_trail import get_audit_trail
from src.tools.audit_viewer import format_audit_entry
import json
from datetime import datetime

app = Flask(__name__)
CORS(app)  # Enable CORS for API endpoints


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/audit/recent')
def get_recent_logs():
    """Get recent audit log entries."""
    limit = request.args.get('limit', 20, type=int)
    agent_name = request.args.get('agent_name', None)
    employee_id = request.args.get('employee_id', None)
    
    audit = get_audit_trail()
    conn = audit._get_connection()
    cursor = conn.cursor()
    
    # Build query to get session IDs with filters
    # If filtering by agent_name, include entries where:
    # 1. The agent_name matches directly, OR
    # 2. The agent was delegated to (via agent_delegations table)
    if agent_name:
        query = """
            SELECT DISTINCT al.session_id
            FROM audit_log al
            WHERE 1=1
        """
        params = []
        
        # Check if agent_name matches directly or was delegated to
        query += """
            AND (
                al.agent_name = ?
                OR EXISTS (
                    SELECT 1 FROM agent_delegations ad
                    WHERE ad.audit_log_id = al.id
                    AND ad.to_agent = ?
                )
            )
        """
        params.extend([agent_name, agent_name])
        
        if employee_id:
            query += " AND al.employee_id = ?"
            params.append(employee_id)
        
        query += " ORDER BY (SELECT MAX(timestamp) FROM audit_log WHERE session_id = al.session_id) DESC LIMIT ?"
        params.append(limit)
    else:
        query = "SELECT DISTINCT session_id FROM audit_log WHERE 1=1"
        params = []
        
        if employee_id:
            query += " AND employee_id = ?"
            params.append(employee_id)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
    
    cursor.execute(query, params)
    session_ids = [row[0] for row in cursor.fetchall()]
    
    results = []
    for session_id in session_ids:
        history = audit.get_session_history(session_id, limit=1)
        if history:
            entry = history[0]
            # Convert to dict and parse JSON fields
            entry_dict = dict(entry)
            if entry_dict.get('metadata'):
                try:
                    entry_dict['metadata'] = json.loads(entry_dict['metadata']) if isinstance(entry_dict['metadata'], str) else entry_dict['metadata']
                except:
                    entry_dict['metadata'] = {}
            
            # Parse tool call params
            for tc in entry_dict.get('tool_calls', []):
                if tc.get('tool_params') and isinstance(tc['tool_params'], str):
                    try:
                        tc['tool_params'] = json.loads(tc['tool_params'])
                    except:
                        pass
            
            # If filtering by agent_name, only include if it matches or was delegated to
            if agent_name:
                matches_directly = entry_dict.get('agent_name') == agent_name
                matches_delegation = any(
                    d.get('to_agent') == agent_name 
                    for d in entry_dict.get('delegations', [])
                )
                if matches_directly or matches_delegation:
                    results.append(entry_dict)
            else:
                results.append(entry_dict)
    
    return jsonify(results)


@app.route('/api/audit/session/<session_id>')
def get_session_history(session_id):
    """Get full history for a specific session."""
    agent_name = request.args.get('agent_name', None)
    audit = get_audit_trail()
    history = audit.get_session_history(session_id)
    
    # Parse JSON fields
    filtered_history = []
    for entry in history:
        # If filtering by agent_name, check if it matches
        if agent_name:
            matches_directly = entry.get('agent_name') == agent_name
            matches_delegation = any(
                d.get('to_agent') == agent_name 
                for d in entry.get('delegations', [])
            )
            if not (matches_directly or matches_delegation):
                continue  # Skip this entry
        
        if entry.get('metadata') and isinstance(entry['metadata'], str):
            try:
                entry['metadata'] = json.loads(entry['metadata'])
            except:
                entry['metadata'] = {}
        
        for tc in entry.get('tool_calls', []):
            if tc.get('tool_params') and isinstance(tc['tool_params'], str):
                try:
                    tc['tool_params'] = json.loads(tc['tool_params'])
                except:
                    pass
        
        filtered_history.append(entry)
    
    return jsonify(filtered_history)


@app.route('/api/audit/employee/<employee_id>')
def get_employee_logs(employee_id):
    """Get audit logs for a specific employee."""
    limit = request.args.get('limit', 50, type=int)
    agent_name = request.args.get('agent_name', None)
    audit = get_audit_trail()
    logs = audit.get_employee_audit_trail(employee_id, limit=limit)
    
    # Parse JSON fields and filter by agent if needed
    filtered_logs = []
    for log in logs:
        # If filtering by agent_name, check if it matches
        if agent_name:
            matches_directly = log.get('agent_name') == agent_name
            # For employee logs, we need to check delegations via audit_log_id
            matches_delegation = False
            if log.get('id'):
                conn = audit._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT COUNT(*) FROM agent_delegations
                    WHERE audit_log_id = ? AND to_agent = ?
                """, (log['id'], agent_name))
                matches_delegation = cursor.fetchone()[0] > 0
            
            if not (matches_directly or matches_delegation):
                continue  # Skip this entry
        
        if log.get('metadata') and isinstance(log['metadata'], str):
            try:
                log['metadata'] = json.loads(log['metadata'])
            except:
                log['metadata'] = {}
        
        filtered_logs.append(log)
    
    return jsonify(filtered_logs)


@app.route('/api/audit/sessions')
def get_sessions():
    """Get list of all session IDs."""
    limit = request.args.get('limit', None)
    audit = get_audit_trail()
    conn = audit._get_connection()
    cursor = conn.cursor()
    
    # If limit is provided and is a valid integer, use it; otherwise get all sessions
    if limit is not None:
        try:
            limit = int(limit)
            if limit > 0:
                query = """
                    SELECT DISTINCT session_id, MAX(timestamp) as last_activity
                    FROM audit_log
                    GROUP BY session_id
                    ORDER BY last_activity DESC
                    LIMIT ?
                """
                cursor.execute(query, (limit,))
            else:
                # Invalid limit, get all
                query = """
                    SELECT DISTINCT session_id, MAX(timestamp) as last_activity
                    FROM audit_log
                    GROUP BY session_id
                    ORDER BY last_activity DESC
                """
                cursor.execute(query)
        except (ValueError, TypeError):
            # Invalid limit parameter, get all sessions
            query = """
                SELECT DISTINCT session_id, MAX(timestamp) as last_activity
                FROM audit_log
                GROUP BY session_id
                ORDER BY last_activity DESC
            """
            cursor.execute(query)
    else:
        # No limit specified, get all sessions
        query = """
            SELECT DISTINCT session_id, MAX(timestamp) as last_activity
            FROM audit_log
            GROUP BY session_id
            ORDER BY last_activity DESC
        """
        cursor.execute(query)
    
    sessions = [{'session_id': row[0], 'last_activity': row[1]} for row in cursor.fetchall()]
    
    # Also get total count for reference
    cursor.execute("SELECT COUNT(DISTINCT session_id) FROM audit_log")
    total_count = cursor.fetchone()[0]
    
    return jsonify({
        'sessions': sessions,
        'total': total_count,
        'returned': len(sessions)
    })


@app.route('/api/audit/summary')
def get_summary():
    """Get audit trail summary statistics."""
    from src.tools.audit_viewer import get_audit_summary
    
    summary = get_audit_summary()
    return jsonify(summary)


@app.route('/api/audit/agents')
def get_agents():
    """Get list of all agent names (from audit_log and delegations)."""
    audit = get_audit_trail()
    conn = audit._get_connection()
    cursor = conn.cursor()
    
    # Get agents from audit_log
    cursor.execute("SELECT DISTINCT agent_name FROM audit_log WHERE agent_name IS NOT NULL")
    agents_from_logs = {row[0] for row in cursor.fetchall()}
    
    # Get agents from delegations (both from_agent and to_agent)
    cursor.execute("""
        SELECT DISTINCT from_agent FROM agent_delegations WHERE from_agent IS NOT NULL
        UNION
        SELECT DISTINCT to_agent FROM agent_delegations WHERE to_agent IS NOT NULL
    """)
    agents_from_delegations = {row[0] for row in cursor.fetchall()}
    
    # Combine all unique agent names
    all_agents = sorted(agents_from_logs.union(agents_from_delegations))
    
    return jsonify(all_agents)


@app.route('/api/audit/employees')
def get_employees():
    """Get list of all employee IDs."""
    audit = get_audit_trail()
    conn = audit._get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT employee_id FROM audit_log WHERE employee_id IS NOT NULL ORDER BY employee_id")
    employees = [row[0] for row in cursor.fetchall()]
    return jsonify(employees)


if __name__ == '__main__':
    print("Starting Audit Log Viewer...")
    print("Open http://localhost:5000 in your browser")
    app.run(debug=True, host='0.0.0.0', port=5000)

