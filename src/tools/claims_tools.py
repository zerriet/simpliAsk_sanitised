import json
import random
import sqlite3
from contextlib import contextmanager
from datetime import datetime

# --- Database Setup (Persistence) ---
DB_NAME = "claims_poc.db"

@contextmanager
def _get_db():
    """Context manager for database connections to ensure proper cleanup."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Access columns by name
    try:
        yield conn
    finally:
        conn.close()

def _init_db():
    """Initialize the SQLite database with the necessary table."""
    with _get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS claims (
                claim_id TEXT PRIMARY KEY,
                employee_id TEXT NOT NULL,
                status TEXT NOT NULL, -- 'draft' or 'submitted'
                created_at TEXT,
                data JSON -- Stores provider, amount, etc.
            )
        """)
        conn.commit()

# Initialize DB on module import
_init_db()

# --- Helper Functions ---

def _generate_claim_id() -> str:
    """Generate a unique claim ID, checking for collisions."""
    max_attempts = 10
    for _ in range(max_attempts):
        claim_id = f"claim-{random.randint(10000, 99999)}"
        with _get_db() as conn:
            cursor = conn.execute("SELECT 1 FROM claims WHERE claim_id = ?", (claim_id,))
            if cursor.fetchone() is None:
                return claim_id
    raise RuntimeError("Failed to generate unique claim ID after multiple attempts")

def _validate_date(date_str: str) -> bool:
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

# --- Tool Functions ---

def list_claims(employee_id: str) -> str:
    with _get_db() as conn:
        cursor = conn.execute(
            "SELECT claim_id, status, data FROM claims WHERE employee_id = ?", 
            (employee_id,)
        )
        rows = cursor.fetchall()

    results = []
    for row in rows:
        try:
            claim_data = json.loads(row["data"])
        except (json.JSONDecodeError, TypeError) as e:
            # Skip corrupted data entries
            continue
        # Merge DB columns with the JSON data blob for a complete view
        full_record = {
            "claim_id": row["claim_id"],
            "status": row["status"],
            **claim_data
        }
        results.append(full_record)

    return json.dumps({"employee_id": employee_id, "claims": results}, indent=2)


def draft_medical_claim(
    employee_id: str,
    medical_provider: str,
    receipt_no: str,
    receipt_date: str,
    receipt_amount: float,
    diagnosis: str,
    gst_inclusive: bool
) -> str:
    if not _validate_date(receipt_date):
        return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})

    claim_id = _generate_claim_id()
    
    # We store the variable fields in a JSON blob for flexibility
    claim_details = {
        "medical_provider": medical_provider,
        "receipt_no": receipt_no,
        "receipt_date": receipt_date,
        "receipt_amount": float(receipt_amount),
        "diagnosis": diagnosis,
        "gst_inclusive": bool(gst_inclusive)
    }

    try:
        with _get_db() as conn:
            conn.execute(
                "INSERT INTO claims (claim_id, employee_id, status, created_at, data) VALUES (?, ?, ?, ?, ?)",
                (claim_id, employee_id, "draft", datetime.now().isoformat(), json.dumps(claim_details))
            )
            conn.commit()
    except sqlite3.IntegrityError as e:
        return json.dumps({"error": f"Database error: Claim ID collision or constraint violation. {str(e)}"})
    except Exception as e:
        return json.dumps({"error": f"Database error: {str(e)}"})

    return json.dumps({
        "status": "draft",
        "message": "Draft created successfully.",
        "claim_id": claim_id,
        "details": claim_details
    })


def update_medical_claim(
    employee_id: str,
    claim_id: str,
    field: str,
    value: str
) -> str:
    """
    Updates a specific field in a draft claim.
    Valid fields: medical_provider, receipt_no, receipt_date, receipt_amount, diagnosis, gst_inclusive
    """
    # Validate field name
    valid_fields = {"medical_provider", "receipt_no", "receipt_date", "receipt_amount", "diagnosis", "gst_inclusive"}
    if field not in valid_fields:
        return json.dumps({"error": f"Invalid field '{field}'. Valid fields: {', '.join(sorted(valid_fields))}"})

    with _get_db() as conn:
        cursor = conn.execute(
            "SELECT status, data FROM claims WHERE claim_id = ? AND employee_id = ?", 
            (claim_id, employee_id)
        )
        row = cursor.fetchone()

        if not row:
            return json.dumps({"error": "Claim not found."})

        if row["status"] != "draft":
            return json.dumps({"error": f"Cannot update claim. Current status is {row['status']}."})

        try:
            data = json.loads(row["data"])
        except (json.JSONDecodeError, TypeError) as e:
            return json.dumps({"error": f"Corrupted claim data: {str(e)}"})

        # Basic type safety for the update
        if field == "receipt_amount":
            try:
                data[field] = float(value)
            except ValueError:
                return json.dumps({"error": "receipt_amount must be a number."})
        elif field == "receipt_date":
            # Validate date format when updating
            if not _validate_date(value):
                return json.dumps({"error": "Invalid date format. Use YYYY-MM-DD."})
            data[field] = value
        elif field == "gst_inclusive":
            data[field] = str(value).lower() in ("true", "1", "yes")
        else:
            # Default to string update
            data[field] = value

        conn.execute(
            "UPDATE claims SET data = ? WHERE claim_id = ?",
            (json.dumps(data), claim_id)
        )
        conn.commit()

    return json.dumps({
        "status": "updated",
        "message": f"Updated {field} to {value} for claim {claim_id}.",
        "current_data": data
    })


def submit_medical_claim(employee_id: str, claim_id: str) -> str:
    with _get_db() as conn:
        # Use a single transaction to check and update atomically (prevents race conditions)
        cursor = conn.execute(
            "SELECT status FROM claims WHERE claim_id = ? AND employee_id = ?", 
            (claim_id, employee_id)
        )
        row = cursor.fetchone()

        if not row:
            return json.dumps({"error": "Claim not found."})

        if row["status"] != "draft":
            return json.dumps({"error": f"Claim is already {row['status']}."})

        # Update in the same transaction
        cursor = conn.execute(
            "UPDATE claims SET status = 'submitted' WHERE claim_id = ? AND status = 'draft'",
            (claim_id,)
        )
        
        if cursor.rowcount == 0:
            # Status changed between SELECT and UPDATE (race condition detected)
            return json.dumps({"error": "Claim status changed. Please refresh and try again."})
        
        conn.commit()

    print(f"--- SYSTEM: Claim {claim_id} formally submitted to backend ---")
    
    return json.dumps({
        "status": "submitted",
        "message": f"Claim {claim_id} has been submitted for processing.",
        "employee_id": employee_id
    })


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
      "name": "update_medical_claim",
      "description": (
        "Update a specific field in an existing draft claim. "
        "Use this when the user wants to correct a mistake in a draft (e.g., wrong amount or date)."
      ),
      "parameters": {
        "type": "object",
        "properties": {
          "employee_id": {"type": "string"},
          "claim_id": {"type": "string"},
          "field": {
            "type": "string",
            "description": "The field to update (e.g., 'receipt_amount', 'receipt_date', 'diagnosis')"
          },
          "value": {
            "type": "string",
            "description": "The new value for the field. For amounts, provide the number as a string."
          }
        },
        "required": ["employee_id", "claim_id", "field", "value"]
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
