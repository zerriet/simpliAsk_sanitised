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
    Submit a device request directly without creating a draft first.

    NOTE: This is an alternative method for direct submission. The preferred workflow is to:
    1. Create a draft using `draft_device_request_tool`
    2. Submit the draft using `submit_draft_device_request_tool`
    
    Only use this tool if the user explicitly wants to skip the draft step and submit directly.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".
        device_id (int): Identifier of the selected device from the device catalog.
        device_name (str): Name of the selected device, used for display and confirmation.

    Returns:
        str: A JSON string containing the submission status and generated request ID.
    """
    return dt.submit_device_request(employee_id, device_id, device_name)


@tool
def check_device_request_status_tool(request_id: str) -> str:
    """
    Check the status of a previously submitted device request by its request ID.

    Args:
        request_id (str): The device request identifier, for example "MW83052".

    Returns:
        str: A JSON string containing the current status and request details, or an error if not found.
    """
    return dt.check_device_request_status(request_id)


@tool
def submit_draft_device_request_tool(employee_id: str, draft_id: str) -> str:
    """
    Submit a previously drafted device request for processing.

    Use this ONLY AFTER the user has explicitly approved the draft.
    This is the preferred method for submitting device requests that were created as drafts.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".
        draft_id (str): Identifier of the draft to submit, such as "draft-12345".

    Returns:
        str: A JSON string containing the submission status, generated request_id, and message.
    """
    return dt.submit_draft_device_request(employee_id, draft_id)


@tool
def list_device_drafts_tool(employee_id: str) -> str:
    """
    List all draft device requests for an employee.

    Use this when the user wants to see their saved drafts or review previous draft requests.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".

    Returns:
        str: A JSON string containing the employee_id and a list of all draft device requests.
    """
    return dt.list_device_drafts(employee_id)


DEVICE_INSTRUCTIONS = """
You are a helpful HR assistant for bank staff. You are tasked with helping staff with requesting for new devices.

GENERAL RULES:
- You MUST NOT make up or assume device information. Always use `get_available_devices_tool` to show available devices.
- If the user mentions a device but you're unsure of the exact device_id or device_name, use `get_available_devices_tool` first to confirm.
- Only call `draft_device_request_tool` AFTER the user has clearly selected a device (by ID or name).

WORKFLOW:
1. DEVICE SELECTION:
   - Use `get_available_devices_tool` to show available devices when the user wants to see options or is unsure.
   - Present the device list clearly with id, name, and cost.

2. DRAFT CREATION:
   - First, gather all necessary information: employee_id, device_id, and device_name.
   - Ensure device_id and device_name match (the tool will validate this).
   - Use `draft_device_request_tool` to create a draft once device selection is clear.
   - Present the draft details (including draft_id and device cost) back to the user clearly.

3. SUBMISSION:
   - PREFERRED METHOD: After the user confirms the draft, use `submit_draft_device_request_tool` with the draft_id.
     This is the recommended workflow as it preserves all draft information.
   - ALTERNATIVE METHOD: If the user wants to submit directly without a draft, use `submit_device_request_tool` 
     with employee_id, device_id, and device_name. Only use this if the user explicitly wants to skip the draft step.
   - You MUST NOT call any submit tool until the user explicitly and clearly approves.

4. DRAFT MANAGEMENT:
   - Use `list_device_drafts_tool` when the user wants to see their saved drafts or review previous draft requests.
   - If the user wants to modify a draft, they will need to create a new draft with corrected information.

CHECKING STATUS:
- Use `check_device_request_status_tool` when the user asks whether a device request is approved, rejected, or still pending.
- If the user refers to "my device request" or says things like "is it done?" or "is it approved?", look at the conversation to infer the relevant request ID (for example, from the response of the submit tool). If you cannot infer the request ID, politely ask the user to provide the request ID.

OUTPUT STYLE:
- Include the request ID or draft ID in your response when appropriate.
- Whenever you call a tool, always include the tool output (summarised in natural language) in the response.
- When presenting a draft, clearly show the draft_id and device cost so the user can reference it later.
- When showing device lists, format them clearly with device name, ID, and cost.

Current Employee ID: mark_tan.
"""

device_smol_agent = ToolCallingAgent(
    tools=[
        get_available_devices_tool,
        draft_device_request_tool,
        submit_draft_device_request_tool,
        submit_device_request_tool,
        list_device_drafts_tool,
        check_device_request_status_tool,
    ],
    model=get_smol_model(),
    instructions=DEVICE_INSTRUCTIONS,
    name="device_specialist",
    description="Useful for requesting new IT peripherals and devices (cables, mice, keyboards, etc.). Handles device catalog browsing, drafting device requests, listing drafts, and submitting device applications."
)