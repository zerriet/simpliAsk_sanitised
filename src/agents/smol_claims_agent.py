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
def update_medical_claim_tool(
    employee_id: str,
    claim_id: str,
    field: str,
    value: str,
) -> str:
    """
    Update a specific field in an existing draft claim.

    Use this when the user wants to correct a mistake in a draft claim
    (e.g., wrong amount, date, or diagnosis) without creating a new claim.

    Args:
        employee_id (str): Unique identifier of the employee, for example "mark_tan".
        claim_id (str): Identifier of the claim to update, such as "claim-12345".
        field (str): The field to update. Valid fields are:
            - "medical_provider": Name of the clinic or hospital
            - "receipt_no": Receipt or invoice number
            - "receipt_date": Date in YYYY-MM-DD format
            - "receipt_amount": Total amount (provide as string, e.g., "85.50")
            - "diagnosis": Diagnosis or reason for visit
            - "gst_inclusive": Whether GST is included (provide "true" or "false" as string)
        value (str): The new value for the field. For amounts, provide the number as a string.

    Returns:
        str: A JSON string containing the update status, message, and current claim data,
             or an error message if the update cannot be performed.
    """
    return ct.update_medical_claim(employee_id, claim_id, field, value)


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

WORKFLOW:
1. EXTRACTION & CONFIRMATION:
   - Carefully read the extracted text from the uploaded PDF and infer:
     medical provider, receipt number, receipt date, receipt amount,
     diagnosis/visit reason, and whether GST is inclusive.
   - Present a clear summary of these inferred fields back to the user in a neat table.
   - You MUST ALWAYS ask the user to confirm or correct these fields BEFORE
     calling the `draft_medical_claim_tool` tool.

2. DRAFT CREATION:
   - After calling `draft_medical_claim_tool`, show the draft details and the claim_id
     clearly to the user.
   - If the user notices any errors in the draft, use `update_medical_claim_tool` to
     correct specific fields (e.g., wrong amount, date, or diagnosis).

3. SUBMISSION:
   - You MUST NOT call `submit_medical_claim_tool` until the user explicitly and
     clearly approves, e.g. they say something like "Yes, please submit this claim."
   - Never assume consent - wait for explicit confirmation.

4. ADDITIONAL TOOLS:
   - Use `list_claims_tool` when the user wants to see their past claims.
   - Use `update_medical_claim_tool` when the user wants to correct a mistake in a draft.

IMPORTANT RULES:
- Current Employee ID: mark_tan
- Always include tool output in your natural language response.
- Only draft claims can be updated - submitted claims cannot be modified.
- Always validate that dates are in YYYY-MM-DD format before using them.
"""

claims_smol_agent = ToolCallingAgent(
    tools=[
        list_claims_tool,
        draft_medical_claim_tool,
        update_medical_claim_tool,
        submit_medical_claim_tool,
    ],
    model=get_smol_model(),
    instructions=CLAIMS_INSTRUCTIONS,
    name="claims_specialist",
    description="Useful for handling medical reimbursement claims. Can draft claims from receipt details, update draft claims, and submit them."
)
