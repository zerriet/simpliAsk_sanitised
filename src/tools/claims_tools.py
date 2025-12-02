import json
import random
from datetime import datetime

claims_db = {
  "mark_tan": [
    # {
    #   "claim_id": "claim-10001",
    #   "medical_provider": "ABC Clinic",
    #   "receipt_no": "R-12345",
    #   "receipt_date": "2025-01-01",
    #   "receipt_amount": 85.50,
    #   "diagnosis": "Common cold",
    #   "gst_inclusive": True,
    #   "status": "approved"
    # }
  ],
  "jane_doe": []
}


def _generate_claim_id():
  return f"claim-{random.randint(10000, 99999)}"


def list_claims(employee_id: str) -> str:
  claims = claims_db.get(employee_id, [])
  return json.dumps({"employee_id": employee_id, "claims": claims})


def draft_medical_claim(
  employee_id: str,
  medical_provider: str,
  receipt_no: str,
  receipt_date: str,
  receipt_amount: float,
  diagnosis: str,
  gst_inclusive: bool
) -> str:
  try:
    datetime.strptime(receipt_date, "%Y-%m-%d")
  except ValueError:
    return json.dumps({"error": "Invalid receipt_date format. Use YYYY-MM-DD."})

  claim_id = _generate_claim_id()

  claim = {
    "claim_id": claim_id,
    "medical_provider": medical_provider,
    "receipt_no": receipt_no,
    "receipt_date": receipt_date,
    "receipt_amount": float(receipt_amount),
    "diagnosis": diagnosis,
    "gst_inclusive": bool(gst_inclusive),
    "status": "draft"
  }

  if employee_id not in claims_db:
    claims_db[employee_id] = []
  claims_db[employee_id].append(claim)

  print(f"--- SYSTEM: Draft medical claim {claim_id} created for {employee_id} ---")

  return json.dumps({
    "status": "draft",
    "message": "Draft medical claim created.",
    "employee_id": employee_id,
    "claim": claim
  })


def submit_medical_claim(employee_id: str, claim_id: str) -> str:
  """Submit a previously drafted medical claim."""
  user_claims = claims_db.get(employee_id)
  if not user_claims:
    return json.dumps({"error": "No claims found for this employee."})

  for claim in user_claims:
    if claim["claim_id"] == claim_id:
      if claim["status"] != "draft":
        return json.dumps({
          "error": f"Claim {claim_id} is not in draft status (current: {claim['status']})."
        })
      claim["status"] = "submitted"
      print(f"--- SYSTEM: Claim {claim_id} submitted for {employee_id} ---")
      return json.dumps({
        "status": "submitted",
        "message": f"Claim {claim_id} submitted for processing.",
        "employee_id": employee_id,
        "claim": claim
      })

  return json.dumps({"error": f"Claim {claim_id} not found for employee {employee_id}."})


claims_tools = [
  {
    "type": "function",
    "function": {
      "name": "list_claims",
      "description": "List all past medical claims for a given employee.",
      "parameters": {
        "type": "object",
        "properties": {
          "employee_id": {"type": "string"},
        },
        "required": ["employee_id"]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "draft_medical_claim",
      "description": (
        "Create a draft medical claim using extracted information from the user's receipt. "
        "ONLY use this after you have confirmed the extracted values with the user."
      ),
      "parameters": {
        "type": "object",
        "properties": {
          "employee_id": {"type": "string"},
          "medical_provider": {"type": "string"},
          "receipt_no": {"type": "string"},
          "receipt_date": {
            "type": "string",
            "description": "Receipt date in YYYY-MM-DD format"
          },
          "receipt_amount": {"type": "number"},
          "diagnosis": {"type": "string"},
          "gst_inclusive": {
            "type": "boolean",
            "description": "True if GST is included in the receipt amount"
          }
        },
        "required": [
          "employee_id",
          "medical_provider",
          "receipt_no",
          "receipt_date",
          "receipt_amount",
          "diagnosis",
          "gst_inclusive"
        ]
      }
    }
  },
  {
    "type": "function",
    "function": {
      "name": "submit_medical_claim",
      "description": (
        "Submit a previously drafted medical claim for processing. "
        "Use this ONLY AFTER the user has explicitly approved the draft."
      ),
      "parameters": {
        "type": "object",
        "properties": {
          "employee_id": {"type": "string"},
          "claim_id": {"type": "string"}
        },
        "required": ["employee_id", "claim_id"]
      }
    }
  }
]
