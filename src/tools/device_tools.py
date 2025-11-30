import json
import random


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

def get_available_devices():
    return json.dumps(device_db)


def submit_device_request(employee_id, device_id, device_name):
    case_number = random.randint(10000,99999)

    print(f"--- SYSTEM: Submitting request for {device_id}: {device_name} for {employee_id} ---")
    return json.dumps({"status": "success", "message": f"Request ID #MW{case_number} submitted pending manager review."})

def draft_device_request(employee_id, device_id, device_name):
    draft = {
        "employee_id": employee_id,
        "device_id": device_id,
        "device_name": device_name,
        "status": "Draft",
    }

    print(f"--- SYSTEM: Draft created for {employee_id} (device request) for {device_name} ---")
    return json.dumps({
        "status": "draft",
        "message": "Draft device request created.",
        "draft": draft
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
    }
]