import json


feature_db = [
    {
        "id": 1,
        "feature": "Leaves Agent",
        "description": "This agent helps you to apply for leaves"
    },
    {
        "id": 2,
        "feature": "Devices Agent",
        "description": "This agent helps you to apply for devices"
    }
]

def get_available_agents():
    return json.dumps(feature_db)

common_tools = [
    {
        "type": "function",
        "function": {
            "name": "get_available_agents",
            "description": "Return a list of all available agents that can assist with user requests & workflows",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
        },
    },
]