import json
import random
from datetime import datetime
from typing import Dict, Any

db = {
    "mark_tan": {"annual": 14, "medical": 14, "family": 3},
    "jane_doe": {"annual": 2, "medical": 10, "family": 0}
}

# In-memory store for leave requests (prototype only)
leave_requests_db: Dict[str, Dict[str, Any]] = {}
# In-memory store for leave drafts
leave_drafts_db: Dict[str, Dict[str, Any]] = {}


# --- Helper Functions ---

def _validate_date(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _calculate_days(start_date: str, end_date: str) -> int:
    """Calculate number of days between start and end date (inclusive)."""
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        return (end - start).days + 1  # Inclusive of both dates
    except ValueError:
        return -1


def _generate_request_id() -> str:
    """Generate a unique request ID, checking for collisions."""
    max_attempts = 10
    for _ in range(max_attempts):
        case_number = random.randint(10000, 99999)
        request_id = f"MW{case_number}"
        if request_id not in leave_requests_db:
            return request_id
    raise RuntimeError("Failed to generate unique request ID after multiple attempts")


def _validate_leave_type(leave_type: str) -> bool:
    """Validate that leave_type is one of the allowed values."""
    return leave_type.lower() in ["annual", "medical", "family"]


# --- Tool Functions ---

def get_leave_balance(employee_id: str, leave_type: str) -> str:
    """Get the remaining leave days for an employee."""
    if not _validate_leave_type(leave_type):
        return json.dumps({"error": f"Invalid leave type: {leave_type}. Must be one of: annual, medical, family"})
    
    user_data = db.get(employee_id)
    if not user_data:
        return json.dumps({"error": "Employee not found"})
    
    balance = user_data.get(leave_type.lower())
    if balance is None:
        return json.dumps({"error": f"Invalid leave type: {leave_type}"})
        
    return json.dumps({"balance": balance, "unit": "days"})


def submit_leave_request(employee_id: str, leave_type: str, days: int) -> str:
    """Submit a leave application after user has reviewed draft."""
    # Validate inputs
    if not _validate_leave_type(leave_type):
        return json.dumps({"error": f"Invalid leave type: {leave_type}. Must be one of: annual, medical, family"})
    
    if days <= 0:
        return json.dumps({"error": "Days must be a positive integer"})
    
    # Check employee exists
    user_data = db.get(employee_id)
    if not user_data:
        return json.dumps({"error": "Employee not found"})
    
    # Check leave balance
    balance = user_data.get(leave_type.lower())
    if balance is None:
        return json.dumps({"error": f"Invalid leave type: {leave_type}"})
    
    if days > balance:
        return json.dumps({
            "error": f"Insufficient leave balance. Requested: {days} days, Available: {balance} days"
        })
    
    # Generate unique request ID
    try:
        request_id = _generate_request_id()
    except RuntimeError as e:
        return json.dumps({"error": str(e)})
    
    status = "pending"

    # Store in toy DB
    leave_requests_db[request_id] = {
        "employee_id": employee_id,
        "leave_type": leave_type,
        "days": days,
        "status": status,
    }

    print(
        f"--- SYSTEM: Submitting {days} days of {leave_type} leave for "
        f"{employee_id} with request ID {request_id} (status: {status}) ---"
    )

    return json.dumps({
        "status": "success",
        "request_id": request_id,
        "leave_status": status,
        "message": f"Request ID #{request_id} submitted and pending manager review."
    })


def check_leave_status(request_id: str) -> str:
    """Check the current status of a previously submitted leave request."""
    request = leave_requests_db.get(request_id)

    if not request:
        return json.dumps({
            "error": "Request not found",
            "request_id": request_id
        })

    return json.dumps({
        "request_id": request_id,
        "status": request["status"],
        "employee_id": request["employee_id"],
        "leave_type": request["leave_type"],
        "days": request["days"],
    })


def draft_leave_request(employee_id: str, leave_type: str, start_date: str, end_date: str) -> str:
    """Create a draft leave request before submitting."""
    # Validate inputs
    if not _validate_leave_type(leave_type):
        return json.dumps({"error": f"Invalid leave type: {leave_type}. Must be one of: annual, medical, family"})
    
    if not _validate_date(start_date):
        return json.dumps({"error": "Invalid start_date format. Use YYYY-MM-DD."})
    
    if not _validate_date(end_date):
        return json.dumps({"error": "Invalid end_date format. Use YYYY-MM-DD."})
    
    # Validate date logic (end_date must be after or equal to start_date)
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        if end < start:
            return json.dumps({"error": "End date must be after or equal to start date."})
    except ValueError:
        return json.dumps({"error": "Invalid date format. Please check date formats."})
    
    # Calculate days
    days = _calculate_days(start_date, end_date)
    if days < 0:
        return json.dumps({"error": "Invalid date calculation. Please check date formats."})
    
    # Check employee exists
    user_data = db.get(employee_id)
    if not user_data:
        return json.dumps({"error": "Employee not found"})
    
    # Check leave balance
    balance = user_data.get(leave_type.lower())
    if balance is None:
        return json.dumps({"error": f"Invalid leave type: {leave_type}"})
    
    if days > balance:
        return json.dumps({
            "error": f"Insufficient leave balance. Requested: {days} days, Available: {balance} days"
        })
    
    # Generate draft ID
    draft_id = f"draft-{random.randint(10000, 99999)}"
    while draft_id in leave_drafts_db:
        draft_id = f"draft-{random.randint(10000, 99999)}"
    
    draft = {
        "draft_id": draft_id,
        "employee_id": employee_id,
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "days": days,
        "status": "draft",
    }
    
    # Store draft
    leave_drafts_db[draft_id] = draft

    print(
        f"--- SYSTEM: Draft created for {employee_id} ({leave_type} leave) "
        f"from {start_date} to {end_date} ({days} days) ---"
    )
    return json.dumps({
        "status": "draft",
        "message": "Draft leave request created.",
        "draft_id": draft_id,
        "draft": draft
    })


def submit_draft_leave_request(employee_id: str, draft_id: str) -> str:
    """Submit a previously drafted leave request for processing."""
    draft = leave_drafts_db.get(draft_id)
    
    if not draft:
        return json.dumps({"error": "Draft not found"})
    
    if draft["employee_id"] != employee_id:
        return json.dumps({"error": "Draft does not belong to this employee"})
    
    if draft["status"] != "draft":
        return json.dumps({"error": f"Draft is already {draft['status']}"})
    
    # Generate unique request ID
    try:
        request_id = _generate_request_id()
    except RuntimeError as e:
        return json.dumps({"error": str(e)})
    
    status = "pending"
    
    # Store in requests DB
    leave_requests_db[request_id] = {
        "employee_id": draft["employee_id"],
        "leave_type": draft["leave_type"],
        "days": draft["days"],
        "start_date": draft["start_date"],
        "end_date": draft["end_date"],
        "status": status,
    }
    
    # Mark draft as submitted
    draft["status"] = "submitted"
    
    print(
        f"--- SYSTEM: Submitting draft {draft_id} as {request_id} - "
        f"{draft['days']} days of {draft['leave_type']} leave for {employee_id} (status: {status}) ---"
    )
    
    return json.dumps({
        "status": "success",
        "request_id": request_id,
        "leave_status": status,
        "message": f"Request ID #{request_id} submitted and pending manager review."
    })


def list_leave_drafts(employee_id: str) -> str:
    """List all draft leave requests for an employee."""
    drafts = [draft for draft in leave_drafts_db.values() if draft["employee_id"] == employee_id]
    return json.dumps({"employee_id": employee_id, "drafts": drafts})


leave_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_leave_balance",
            "description": "Get the remaining leave days for an employee.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "leave_type": {
                        "type": "string",
                        "enum": ["annual", "medical", "family"]
                    },
                },
                "required": ["employee_id", "leave_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_leave_request",
            "description": "Submit a leave application after user has reviewed draft",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "leave_type": {
                        "type": "string",
                        "enum": ["annual", "medical", "family"]
                    },
                    "days": {"type": "integer", "minimum": 1},
                },
                "required": ["employee_id", "leave_type", "days"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_leave_status",
            "description": "Check the approval status of a leave request using its request ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "The leave request ID, e.g. 'MW83052'."
                    }
                },
                "required": ["request_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "draft_leave_request",
            "description": "Create a draft leave request before submitting.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "leave_type": {
                        "type": "string",
                        "enum": ["annual", "medical", "family"]
                    },
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["employee_id", "leave_type", "start_date", "end_date"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_draft_leave_request",
            "description": "Submit a previously drafted leave request for processing. Use this ONLY AFTER the user has explicitly approved the draft.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "draft_id": {"type": "string"}
                },
                "required": ["employee_id", "draft_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_leave_drafts",
            "description": "List all draft leave requests for an employee.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"}
                },
                "required": ["employee_id"]
            }
        }
    }
]
