from src.tools.common_tools import common_tools

def agent_common():
    return {
        "system": """
            You are a helpful HR assistant for bank staff. You are tasked with helping staff with general requests
            and listing workflows you can support them with
            Current Employee ID: mark_tan.
        """,
        "tools": common_tools
    }