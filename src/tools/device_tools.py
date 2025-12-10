import json
import random
from typing import Dict, Any, Optional


# In-memory store for device requests (prototype only)
device_requests_db: Dict[str, Dict[str, Any]] = {}
# In-memory store for device drafts
device_drafts_db: Dict[str, Dict[str, Any]] = {}


device_db = [
    {"id": 1, "name": "2M HDMI Cable", "cost": 6.50},
    {"id": 2, "name": "Wireless Mouse", "cost": 15.00},
    {"id": 3, "name": "Mechanical Keyboard", "cost": 45.00},
    {"id": 4, "name": "27-inch Monitor", "cost": 230.00},
    {"id": 5, "name": "USB-C Hub", "cost": 25.50},
    {"id": 6, "name": "External Hard Drive 1TB", "cost": 65.00},
    {"id": 7, "name": "Laptop Stand", "cost": 30.00},
    {"id": 8, "name": "Webcam 1080p", "cost": 40.00}
]


# --- Helper Functions ---

def _get_device_by_id(device_id: int) -> Optional[Dict[str, Any]]:
    """Get device information by ID."""
    for device in device_db:
        if device["id"] == device_id:
            return device
    return None


def _generate_request_id() -> str:
    """Generate a unique request ID, checking for collisions."""
    max_attempts = 10
    for _ in range(max_attempts):
        case_number = random.randint(10000, 99999)
        request_id = f"MW{case_number}"
        if request_id not in device_requests_db:
            return request_id
    raise RuntimeError("Failed to generate unique request ID after multiple attempts")


# --- Tool Functions ---

def get_available_devices() -> str:
    """Return a list of all available devices that employees can request."""
    return json.dumps(device_db, indent=2)


def submit_device_request(employee_id: str, device_id: int, device_name: str) -> str:
    """Submit a device request for an employee."""
    # Validate inputs
    if not employee_id or not employee_id.strip():
        return json.dumps({"error": "Employee ID cannot be empty"})
    
    if device_id <= 0:
        return json.dumps({"error": "Device ID must be a positive integer"})
    
    if not device_name or not device_name.strip():
        return json.dumps({"error": "Device name cannot be empty"})
    
    # Validate device exists
    device = _get_device_by_id(device_id)
    if not device:
        return json.dumps({"error": f"Device with ID {device_id} not found"})
    
    # Validate device name matches
    if device["name"] != device_name:
        return json.dumps({
            "error": f"Device name mismatch. Expected '{device['name']}', got '{device_name}'"
        })
    
    # Generate unique request ID
    try:
        request_id = _generate_request_id()
    except RuntimeError as e:
        return json.dumps({"error": str(e)})
    
    # Store request
    device_requests_db[request_id] = {
        "employee_id": employee_id,
        "device_id": device_id,
        "device_name": device_name,
        "device_cost": device["cost"],
        "status": "pending",
    }
    
    print(
        f"--- SYSTEM: Submitting request for {device_id}: {device_name} "
        f"(${device['cost']:.2f}) for {employee_id} with request ID {request_id} ---"
    )
    
    return json.dumps({
        "status": "success",
        "request_id": request_id,
        "message": f"Request ID #{request_id} submitted pending manager review."
    })


def draft_device_request(employee_id: str, device_id: int, device_name: str) -> str:
    """Create a draft device request for an employee before final submission."""
    # Validate inputs
    if not employee_id or not employee_id.strip():
        return json.dumps({"error": "Employee ID cannot be empty"})
    
    if device_id <= 0:
        return json.dumps({"error": "Device ID must be a positive integer"})
    
    if not device_name or not device_name.strip():
        return json.dumps({"error": "Device name cannot be empty"})
    
    # Validate device exists
    device = _get_device_by_id(device_id)
    if not device:
        return json.dumps({"error": f"Device with ID {device_id} not found"})
    
    # Validate device name matches
    if device["name"] != device_name:
        return json.dumps({
            "error": f"Device name mismatch. Expected '{device['name']}', got '{device_name}'"
        })
    
    # Generate draft ID
    draft_id = f"draft-{random.randint(10000, 99999)}"
    while draft_id in device_drafts_db:
        draft_id = f"draft-{random.randint(10000, 99999)}"
    
    draft = {
        "draft_id": draft_id,
        "employee_id": employee_id,
        "device_id": device_id,
        "device_name": device_name,
        "device_cost": device["cost"],
        "status": "draft",
    }
    
    # Store draft
    device_drafts_db[draft_id] = draft
    
    print(
        f"--- SYSTEM: Draft created for {employee_id} (device request) "
        f"for {device_name} (${device['cost']:.2f}) ---"
    )
    
    return json.dumps({
        "status": "draft",
        "message": "Draft device request created.",
        "draft_id": draft_id,
        "draft": draft
    })


def check_device_request_status(request_id: str) -> str:
    """Check the current status of a previously submitted device request."""
    request = device_requests_db.get(request_id)
    
    if not request:
        return json.dumps({
            "error": "Request not found",
            "request_id": request_id
        })
    
    return json.dumps({
        "request_id": request_id,
        "status": request["status"],
        "employee_id": request["employee_id"],
        "device_id": request["device_id"],
        "device_name": request["device_name"],
        "device_cost": request.get("device_cost"),
    })


def list_device_drafts(employee_id: str) -> str:
    """List all draft device requests for an employee."""
    drafts = [
        draft for draft in device_drafts_db.values() 
        if draft["employee_id"] == employee_id
    ]
    return json.dumps({"employee_id": employee_id, "drafts": drafts})


def submit_draft_device_request(employee_id: str, draft_id: str) -> str:
    """Submit a previously drafted device request for processing."""
    draft = device_drafts_db.get(draft_id)
    
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
    device_requests_db[request_id] = {
        "employee_id": draft["employee_id"],
        "device_id": draft["device_id"],
        "device_name": draft["device_name"],
        "device_cost": draft.get("device_cost"),
        "status": status,
    }
    
    # Mark draft as submitted
    draft["status"] = "submitted"
    
    print(
        f"--- SYSTEM: Submitting draft {draft_id} as {request_id} - "
        f"{draft['device_name']} (${draft.get('device_cost', 0):.2f}) for {employee_id} (status: {status}) ---"
    )
    
    return json.dumps({
        "status": "success",
        "request_id": request_id,
        "message": f"Request ID #{request_id} submitted pending manager review."
    })


device_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_available_devices",
            "description": "Return a list of all available devices that employees can request.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "submit_device_request",
            "description": "Submit a device request for an employee.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "device_id": {"type": "integer"},
                    "device_name": {"type": "string"},
                },
                "required": ["employee_id", "device_id", "device_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_device_request",
            "description": "Create a draft device request for an employee before final submission.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "device_id": {"type": "integer"},
                    "device_name": {"type": "string"},
                },
                "required": ["employee_id", "device_id", "device_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_device_request_status",
            "description": "Check the approval status of a device request using its request ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "request_id": {
                        "type": "string",
                        "description": "The device request ID, e.g. 'MW83052'."
                    }
                },
                "required": ["request_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_device_drafts",
            "description": "List all draft device requests for an employee.",
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"}
                },
                "required": ["employee_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "submit_draft_device_request",
            "description": (
                "Submit a previously drafted device request for processing. "
                "Use this ONLY AFTER the user has explicitly approved the draft."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "employee_id": {"type": "string"},
                    "draft_id": {"type": "string"}
                },
                "required": ["employee_id", "draft_id"]
            }
        }
    }
]