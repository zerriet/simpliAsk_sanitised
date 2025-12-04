from smolagents import ToolCallingAgent, tool
from src.agents.smol_base import get_smol_model
from src.tools import claims_tools as ct


@tool
def list_claims_tool(employee_id: str) -> str:
    """
    List all past medical claims for a given employee.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".

    Returns:
        str: A JSON string containing the employee_id and a list of claims.
    """
    return ct.list_claims(employee_id)


@tool
def draft_medical_claim_tool(
    employee_id: str,
    medical_provider: str,
    receipt_no: str,
    receipt_date: str,
    receipt_amount: float,
    diagnosis: str,
    gst_inclusive: bool,
) -> str:
    """
    Create a draft medical claim using extracted information from the user's receipt.

    ONLY use this after you have confirmed the extracted values with the user.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".
        medical_provider (str): Name of the clinic or hospital shown on the receipt.
        receipt_no (str): Receipt or invoice number.
        receipt_date (str): Date on the receipt in YYYY-MM-DD format.
        receipt_amount (float): Total amount shown on the receipt.
        diagnosis (str): Diagnosis or reason for visit, derived from the receipt text.
        gst_inclusive (bool): True if GST is already included in the receipt amount.

    Returns:
        str: A JSON string containing the draft claim details, status, and generated claim_id.
    """
    return ct.draft_medical_claim(
        employee_id=employee_id,
        medical_provider=medical_provider,
        receipt_no=receipt_no,
        receipt_date=receipt_date,
        receipt_amount=receipt_amount,
        diagnosis=diagnosis,
        gst_inclusive=gst_inclusive,
    )


@tool
def submit_medical_claim_tool(
    employee_id: str,
    claim_id: str,
) -> str:
    """
    Submit a previously drafted medical claim for processing.

    Use this ONLY AFTER the user has explicitly approved the draft.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".
        claim_id (str): Identifier of the claim to submit, such as "claim-12345".

    Returns:
        str: A JSON string containing the submission status, employee_id, and claim details,
             or an error message if the claim cannot be submitted.
    """
    return ct.submit_medical_claim(employee_id, claim_id)


CLAIMS_INSTRUCTIONS = """
You are a helpful assistant that helps staff submit medical reimbursement claims
based on uploaded PDF receipts.

IMPORTANT BEHAVIOUR:
- First, carefully read the extracted text from the uploaded PDF and infer:
  medical provider, receipt number, receipt date, receipt amount,
  diagnosis/visit reason, and whether GST is inclusive.
- Then, PRESENT a clear summary of these inferred fields back to the user
  in a neat table.

- You MUST ALWAYS ask the user to confirm or correct these fields BEFORE
  calling the `draft_medical_claim_tool` tool.

- After calling `draft_medical_claim_tool`, show the draft details and the claim_id
  clearly to the user.

- You MUST NOT call `submit_medical_claim_tool` until the user explicitly and
  clearly approves, e.g. they say something like "Yes, please submit this claim."
  Never assume consent.

- When appropriate, you may also use `list_claims_tool` to show past claims to the user.

Current Employee ID: mark_tan.

Whenever you call a tool, always include the tool output in your natural language response.
"""

claims_smol_agent = ToolCallingAgent(
    tools=[
        list_claims_tool,
        draft_medical_claim_tool,
        submit_medical_claim_tool,
    ],
    model=get_smol_model(),
    instructions=CLAIMS_INSTRUCTIONS,
)
