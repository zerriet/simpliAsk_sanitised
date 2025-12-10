# Audit Log Viewer GUI

A simple web-based GUI for viewing SimpliAsk audit logs.

## Setup

1. Install dependencies:
```bash
pip install -r audit_gui/requirements.txt
```

2. Run the Flask app:
```bash
python audit_gui/app.py
```

3. Open your browser to:
```
http://localhost:5000
```

## Features

- **Recent Logs View**: View the most recent audit log entries
- **Session View**: View all entries for a specific session
- **Employee View**: View all audit logs for a specific employee
- **Filtering**: Filter by agent name
- **Statistics**: View summary statistics (total requests, sessions, employees, agents)
- **Tool Call Details**: See detailed information about tool executions
- **Delegation Tracking**: View agent delegations (manager → specialist)
- **Auto-refresh**: Automatically refreshes every 30 seconds

## API Endpoints

- `GET /api/audit/recent` - Get recent audit logs
- `GET /api/audit/session/<session_id>` - Get session history
- `GET /api/audit/employee/<employee_id>` - Get employee logs
- `GET /api/audit/sessions` - Get list of all sessions
- `GET /api/audit/summary` - Get summary statistics
- `GET /api/audit/agents` - Get list of all agents
- `GET /api/audit/employees` - Get list of all employees

## Usage

1. Select a view type (Recent Logs, By Session, or By Employee)
2. Apply filters (agent name, limit)
3. Click "Refresh" or wait for auto-refresh
4. View detailed information including tool calls and delegations

