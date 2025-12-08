from smolagents import ToolCallingAgent, tool
from src.agents.smol_base import get_smol_model
from src.tools import device_tools as dt


@tool
def get_available_devices_tool() -> str:
    """
    Return a list of all available devices that employees can request.

    Args:
        None

    Returns:
        str: A JSON string containing a list of devices with id, name, and cost.
    """
    return dt.get_available_devices()


@tool
def draft_device_request_tool(
    employee_id: str,
    device_id: int,
    device_name: str,
) -> str:
    """
    Create a draft device request for an employee before final submission.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".
        device_id (int): Identifier of the selected device from the device catalog.
        device_name (str): Name of the selected device, used for display and confirmation.

    Returns:
        str: A JSON string containing the draft device request details and status.
    """
    return dt.draft_device_request(employee_id, device_id, device_name)


@tool
def submit_device_request_tool(
    employee_id: str,
    device_id: int,
    device_name: str,
) -> str:
    """
    Submit a device request for an employee after the draft is confirmed.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".
        device_id (int): Identifier of the selected device from the device catalog.
        device_name (str): Name of the selected device, used for display and confirmation.

    Returns:
        str: A JSON string containing the submission status and generated request ID.
    """
    return dt.submit_device_request(employee_id, device_id, device_name)


DEVICE_INSTRUCTIONS = """
You are a helpful HR assistant for bank staff. You are tasked with helping staff with requesting for new devices.
Before submitting a request always make sure you have drafted the request. After draft is approved by user, always use submit tool.
Include request ID in response when appropriate.
Whenever you call a tool, always include the tool output in the response.
Current Employee ID: mark_tan.
"""

device_smol_agent = ToolCallingAgent(
    tools=[
        get_available_devices_tool,
        draft_device_request_tool,
        submit_device_request_tool,
    ],
    model=get_smol_model(),
    instructions=DEVICE_INSTRUCTIONS,
    name="device_specialist",
    description="Useful for requesting new IT peripherals and devices (cables, mice, keyboards, etc.)."
)