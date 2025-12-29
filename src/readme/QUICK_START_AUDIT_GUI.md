# Quick Start: Audit Log Viewer GUI

## Installation

1. Install Flask and Flask-CORS:
```bash
pip install flask flask-cors
```

Or if you're using a virtual environment:
```bash
# Activate your virtual environment first
pip install -r audit_gui/requirements.txt
```

## Running the GUI

### Option 1: Use the startup script (easiest)
```bash
python scripts/run_audit_gui.py
```

### Option 2: Run Flask directly
```bash
python audit_gui/app.py
```

### Option 3: Use Flask command
```bash
cd audit_gui
flask run
```

## Access the GUI

Once running, open your browser to:
```
http://localhost:5000
```

## Features

✅ **Recent Logs** - View the most recent audit entries
✅ **Session View** - View all entries for a specific conversation session
✅ **Employee View** - View all logs for a specific employee
✅ **Filtering** - Filter by agent name
✅ **Statistics Dashboard** - See summary stats at a glance
✅ **Tool Call Details** - View detailed tool execution information
✅ **Delegation Tracking** - See manager → specialist routing
✅ **Auto-refresh** - Updates every 30 seconds automatically

## Troubleshooting

**Port already in use?**
- Change the port in `audit_gui/app.py` (line with `port=5000`)
- Or kill the process using port 5000

**Module not found errors?**
- Make sure you're in the project root directory
- Activate your virtual environment if you're using one
- Install dependencies: `pip install flask flask-cors`

**No data showing?**
- Make sure you have audit logs in `data/audit_trail.db`
- Check that your agents are logging to the audit trail
- Try refreshing the page

