# Audit Trail System

A SQLite-based audit trail system for logging agent workflows, simulating Apache Kafka-style audit logging for your SimpliAsk HR agents.

## Overview

This system provides comprehensive logging of:
- User requests and agent responses
- Tool calls (with parameters and results)
- Agent delegations (manager → specialist routing)
- Execution timing and success/failure status
- Employee ID tracking
- Session management

## Quick Start

### Basic Usage

```python
from src.tools.audit_trail import get_audit_trail, generate_session_id
from src.tools.audit_helper import log_agent_interaction

# Generate a session ID for a conversation
session_id = generate_session_id()

# Log a complete interaction
log_agent_interaction(
    session_id=session_id,
    agent_name="hr_manager",
    user_message="I want to apply for 7 days of annual leave",
    agent_response="I've created a draft leave request...",
    employee_id="mark_tan",
    tool_calls=[
        {
            'tool_name': 'draft_leave_request_tool',
            'params': {'employee_id': 'mark_tan', 'leave_type': 'annual', ...},
            'result': '{"draft_id": "draft-12345", ...}',
            'execution_time_ms': 125.5,
            'success': True
        }
    ],
    delegations=[
        {
            'from_agent': 'hr_manager',
            'to_agent': 'leave_specialist',
            'reason': 'User requested leave application'
        }
    ]
)
```

### Integration with Your Notebook

To integrate into `dual_agent_smol.ipynb`, modify your `unified_chat` function:

```python
from src.tools.audit_helper import get_or_create_session, log_agent_interaction
from src.tools.audit_trail import generate_session_id

# At the top of your notebook, initialize session tracking
_current_session = None

def get_or_create_session():
    global _current_session
    if _current_session is None:
        _current_session = generate_session_id()
    return _current_session

def unified_chat(message, history):
    """Unified chat function with audit logging."""
    from src.agents.manager_agent import manager_agent
    
    session_id = get_or_create_session()
    task = build_context(message, history)
    
    # Run agent
    response = manager_agent.run(task)
    cleaned_response = clean_response(response)
    
    # Log the interaction
    log_agent_interaction(
        session_id=session_id,
        agent_name="hr_manager",
        user_message=message,
        agent_response=cleaned_response,
        employee_id="mark_tan",  # or extract from message
        tool_calls=[],  # Populate from actual tool execution if available
        delegations=[]  # Populate from actual delegations if available
    )
    
    return cleaned_response
```

## Database Schema

The system creates three main tables:

### `audit_log`
Main table storing all agent interactions:
- `id`: Primary key
- `session_id`: Conversation/session identifier
- `timestamp`: ISO format timestamp
- `agent_name`: Name of the agent handling the request
- `event_type`: Type of event (e.g., "request", "response")
- `user_message`: User's input message
- `agent_response`: Agent's response
- `employee_id`: Employee identifier
- `metadata`: JSON metadata
- `created_at`: Database timestamp

### `tool_calls`
Detailed tool execution tracking:
- `id`: Primary key
- `audit_log_id`: Foreign key to `audit_log`
- `tool_name`: Name of the tool
- `tool_params`: JSON parameters
- `tool_result`: Tool result/output
- `execution_time_ms`: Execution time in milliseconds
- `success`: Boolean success flag
- `error_message`: Error message if failed

### `agent_delegations`
Tracks manager → specialist routing:
- `id`: Primary key
- `audit_log_id`: Foreign key to `audit_log`
- `from_agent`: Agent doing the delegation
- `to_agent`: Agent being delegated to
- `delegation_reason`: Optional reason for delegation

## Viewing Audit Logs

### Using the Viewer Module

```python
from src.tools.audit_viewer import (
    view_recent_audit_logs,
    get_audit_summary,
    export_audit_trail_to_json
)

# View recent logs
recent = view_recent_audit_logs(limit=20, agent_name="hr_manager")

# Get summary statistics
summary = get_audit_summary(employee_id="mark_tan")

# Export to JSON
export_audit_trail_to_json("audit_export.json", employee_id="mark_tan")
```

### Direct Database Queries

```python
from src.tools.audit_trail import get_audit_trail

audit = get_audit_trail()

# Get session history
history = audit.get_session_history("session_abc123")

# Get employee audit trail
employee_logs = audit.get_employee_audit_trail("mark_tan", limit=50)
```

## Advanced Usage

### Wrapping Tool Functions

To automatically log tool calls, wrap your tool functions:

```python
from src.tools.audit_integration_example import create_audited_tool
from src.tools import leave_tools as lt

# Create audited version
audited_draft = create_audited_tool(
    lt.draft_leave_request,
    "draft_leave_request"
)

# Use it normally - it will automatically log
result = audited_draft("mark_tan", "annual", "2025-12-05", "2025-12-11")
```

### Custom Metadata

Add custom metadata to audit entries:

```python
log_agent_interaction(
    session_id=session_id,
    agent_name="hr_manager",
    user_message=message,
    agent_response=response,
    employee_id="mark_tan",
    metadata={
        'ip_address': '192.168.1.1',
        'user_agent': 'Gradio/5.0',
        'custom_field': 'custom_value'
    }
)
```

## Database Location

By default, the audit trail database is created as `data/audit_trail.db`. You can specify a custom path:

```python
from src.tools.audit_trail import AuditTrail

audit = AuditTrail(db_path="data/audit_trail.db")  # Default
# Or use a custom path:
audit = AuditTrail(db_path="custom/path/audit_trail.db")
```

## Thread Safety

The audit trail system is thread-safe and uses thread-local database connections, making it suitable for use in multi-threaded environments like Gradio.

## Example Queries

### Find all leave requests for an employee

```sql
SELECT al.*, tc.tool_name, tc.tool_params
FROM audit_log al
JOIN tool_calls tc ON al.id = tc.audit_log_id
WHERE al.employee_id = 'mark_tan'
  AND tc.tool_name LIKE '%leave%'
ORDER BY al.timestamp DESC;
```

### Get delegation statistics

```sql
SELECT from_agent, to_agent, COUNT(*) as count
FROM agent_delegations
GROUP BY from_agent, to_agent
ORDER BY count DESC;
```

### Find failed tool calls

```sql
SELECT al.timestamp, al.agent_name, tc.tool_name, tc.error_message
FROM audit_log al
JOIN tool_calls tc ON al.id = tc.audit_log_id
WHERE tc.success = 0
ORDER BY al.timestamp DESC;
```

## Integration with Backoffice GUI

The audit trail database can be easily queried by a backoffice GUI application. Example Flask endpoint:

```python
from flask import Flask, jsonify
from src.tools.audit_trail import get_audit_trail

app = Flask(__name__)

@app.route('/api/audit/<employee_id>')
def get_employee_audit(employee_id):
    audit = get_audit_trail()
    logs = audit.get_employee_audit_trail(employee_id, limit=100)
    return jsonify(logs)
```

## Files

- `audit_trail.py`: Core audit trail system with database operations
- `audit_helper.py`: Helper functions for easier integration
- `audit_viewer.py`: Viewing and querying audit logs
- `audit_integration_example.py`: Example integration code
- `scripts/audit_trail_usage_example.py`: Standalone usage examples

