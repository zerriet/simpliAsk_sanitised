from smolagents import ToolCallingAgent, tool
from src.agents.smol_base import get_smol_model
from src.tools import leave_tools as lt


@tool
def get_leave_balance_tool(employee_id: str, leave_type: str) -> str:
    """
    Get the remaining leave days for an employee.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".
        leave_type (str): Type of leave to check the balance for, such as "annual", "medical", or "family".

    Returns:
        str: A JSON string containing the remaining balance and unit (in days), or an error message.
    """
    return lt.get_leave_balance(employee_id, leave_type)


@tool
def draft_leave_request_tool(
    employee_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
) -> str:
    """
    Create a draft leave request before submitting.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".
        leave_type (str): Type of leave being applied for, such as "annual", "medical", or "family".
        start_date (str): Start date of the leave in YYYY-MM-DD format.
        end_date (str): End date of the leave in YYYY-MM-DD format.

    Returns:
        str: A JSON string containing the draft leave request details and status.
    """
    return lt.draft_leave_request(employee_id, leave_type, start_date, end_date)


@tool
def submit_leave_request_tool(
    employee_id: str,
    leave_type: str,
    days: int,
) -> str:
    """
    Submit a leave request after the user has approved the draft.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".
        leave_type (str): Type of leave being applied for, such as "annual", "medical", or "family".
        days (int): Number of leave days requested.

    Returns:
        str: A JSON string containing the submission status, generated request_id, and message.
    """
    return lt.submit_leave_request(employee_id, leave_type, days)


@tool
def check_leave_status_tool(request_id: str) -> str:
    """
    Check the status of a previously submitted leave request by its request ID.

    Args:
        request_id (str): The leave request identifier, for example "MW83052".

    Returns:
        str: A JSON string containing the current status and request details, or an error if not found.
    """
    return lt.check_leave_status(request_id)


LEAVE_INSTRUCTIONS = """
You are a helpful HR assistant for bank staff. You are tasked with helping staff with applying for leave.

GENERAL RULES:
- You MUST NOT make up or assume dates for a leave request.
- If the user mentions a number of days (e.g. "7 days of annual leave") but does NOT provide start and end dates, you MUST explicitly ask for the start date (and, if needed, confirm the end date) before calling any draft or submit tools.
- Only call `draft_leave_request_tool` AFTER the user has clearly provided (or confirmed) both start_date and end_date.
- If there is any ambiguity (e.g. the dates imply 8 days but the user said 7), ask the user to confirm which they prefer: the exact dates or the exact number of days.

TOOL USAGE:
- First, gather all necessary information: leave type, start_date, end_date, and approximate number of days.
- Use `draft_leave_request_tool` to create a draft once dates are clear and confirmed.
- Present the draft back to the user and ALWAYS ask for confirmation before calling `submit_leave_request_tool`.
- After the user confirms, call `submit_leave_request_tool` to submit the request.

CHECKING STATUS:
- You can also check the status of previously submitted leave requests using the `check_leave_status_tool` when the user asks whether a leave request is approved, rejected, or still pending.
- If the user refers to "my leave" or says things like "is it done?" or "is it approved?", look at the conversation to infer the relevant request ID (for example, from the response of the submit tool). If you cannot infer the request ID, politely ask the user to provide the request ID.

OUTPUT STYLE:
- Include the request ID in your response when appropriate.
- Whenever you call a tool, always include the tool output (summarised in natural language) in the response.

Current Employee ID: mark_tan.

EXAMPLES:

User: I would like to apply for 7 days of annual leave.
Assistant: Sure. Please provide the start date for your 7 days of annual leave (in YYYY-MM-DD format).

User: 2025-12-04
Assistant: You would like 7 days of annual leave starting on 2025-12-04. That would typically run from 2025-12-04 to 2025-12-10 (7 days). Please confirm if these dates are correct, or provide a different end date.
"""

leave_smol_agent = ToolCallingAgent(
    tools=[
        get_leave_balance_tool,
        draft_leave_request_tool,
        submit_leave_request_tool,
        check_leave_status_tool,
    ],
    model=get_smol_model(),
    instructions=LEAVE_INSTRUCTIONS,
    name="leave_specialist",
    description="Useful for questions about leave balances, drafting leave requests, and submitting leave applications. Handles annual, medical, and family leave."
)