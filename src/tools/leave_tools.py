import json
import random

db = {
    "mark_tan": {"annual": 14, "medical": 14, "family": 3},
    "jane_doe": {"annual": 2, "medical": 10, "family": 0}
}

# In-memory store for leave requests (prototype only)
leave_requests_db = {}


def get_leave_balance(employee_id, leave_type):
    user_data = db.get(employee_id)
    if not user_data:
        return json.dumps({"error": "Employee not found"})
    
    balance = user_data.get(leave_type.lower())
    if balance is None:
        return json.dumps({"error": f"Invalid leave type: {leave_type}"})
        
    return json.dumps({"balance": balance, "unit": "days"})


def submit_leave_request(employee_id, leave_type, days):
    case_number = random.randint(10000, 99999)
    request_id = f"MW{case_number}"
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


def check_leave_status(request_id):
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


def draft_leave_request(employee_id, leave_type, start_date, end_date):
    draft = {
        "employee_id": employee_id,
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date,
        "status": "Draft",
    }

    print(
        f"--- SYSTEM: Draft created for {employee_id} ({leave_type} leave) "
        f"from {start_date} to {end_date} ---"
    )
    return json.dumps({
        "status": "draft",
        "message": "Draft leave request created.",
        "draft": draft
    })


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
                    "leave_type": {"type": "string"},
                    "days": {"type": "integer"},
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
                    "leave_type": {"type": "string"},
                    "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                    "end_date": {"type": "string", "description": "YYYY-MM-DD"}
                },
                "required": ["employee_id", "leave_type", "start_date", "end_date"]
            }
        }
    }
]
