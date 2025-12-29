# Claims Agent System Documentation

## Overview

The Claims Agent System is a medical reimbursement claims management solution built using `smolagents`. It enables employees to submit medical claims through natural language interactions, with the agent handling receipt extraction, draft creation, updates, and submission workflows.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interaction                          │
│              (Natural Language Queries)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              smol_claims_agent.py                           │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ToolCallingAgent (claims_specialist)                │  │
│  │  - Model: gpt-4.1-mini (via smol_base)               │  │
│  │  - Instructions: CLAIMS_INSTRUCTIONS                  │  │
│  │  - Tools: 4 tool functions                            │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              claims_tools.py                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tool Functions (4):                                  │  │
│  │  - list_claims()                                      │  │
│  │  - draft_medical_claim()                              │  │
│  │  - update_medical_claim()                             │  │
│  │  - submit_medical_claim()                             │  │
│  └──────────────────────────────────────────────────────┘  │
│                       │                                      │
│                       ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  SQLite Database (data/claims_poc.db)                 │  │
│  │  - Table: claims                                      │  │
│  │  - Schema: claim_id, employee_id, status,            │  │
│  │            created_at, data (JSON)                    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. smol_claims_agent.py

### Purpose
The agent layer that provides natural language interface for medical claims management. It wraps the underlying tool functions and provides intelligent routing and workflow management.

### Key Components

#### Agent Configuration
- **Name**: `claims_specialist`
- **Model**: `gpt-4.1-mini` (via `get_smol_model()` from `smol_base.py`)
- **Framework**: `smolagents.ToolCallingAgent`
- **Tools**: 4 tool functions (see below)

#### Tool Functions

1. **`list_claims_tool(employee_id: str)`**
   - Lists all medical claims for an employee
   - Returns JSON string with employee_id and claims array

2. **`draft_medical_claim_tool(...)`**
   - Creates a draft medical claim from receipt information
   - Parameters: employee_id, medical_provider, receipt_no, receipt_date, receipt_amount, diagnosis, gst_inclusive
   - **Important**: Agent must confirm with user before calling this tool

3. **`update_medical_claim_tool(employee_id, claim_id, field, value)`**
   - Updates a specific field in a draft claim
   - Valid fields: medical_provider, receipt_no, receipt_date, receipt_amount, diagnosis, gst_inclusive
   - Only works on draft claims (not submitted)

4. **`submit_medical_claim_tool(employee_id, claim_id)`**
   - Submits a draft claim for processing
   - **Important**: Agent must wait for explicit user approval before calling

#### Agent Instructions (`CLAIMS_INSTRUCTIONS`)

The agent follows a structured 4-step workflow:

1. **EXTRACTION & CONFIRMATION**
   - Extract fields from PDF receipt text
   - Present summary in table format
   - **MUST** ask user to confirm before drafting

2. **DRAFT CREATION**
   - Show draft details and claim_id after creation
   - Use update tool if user finds errors

3. **SUBMISSION**
   - **MUST NOT** submit without explicit user approval
   - Wait for phrases like "Yes, please submit this claim"

4. **ADDITIONAL TOOLS**
   - Use list_claims_tool for viewing past claims
   - Use update_medical_claim_tool for corrections

#### Important Rules
- Current Employee ID: `mark_tan` (hardcoded in instructions)
- Always include tool output in natural language response
- Only draft claims can be updated
- Dates must be in YYYY-MM-DD format

### Design Decisions

1. **Tool Wrapper Pattern**: Each tool function wraps the underlying `claims_tools` function, providing a clean separation between agent logic and business logic.

2. **Explicit Confirmation Required**: The instructions emphasize requiring user confirmation before drafting and submitting to prevent accidental actions.

3. **Error Handling**: Errors are returned as JSON strings, which the agent can parse and present to users naturally.

---

## 2. claims_tools.py

### Purpose
Core business logic layer that handles all database operations and claim management functionality. Provides the actual implementation of claim CRUD operations.

### Database Schema

**Table: `claims`**
```sql
CREATE TABLE claims (
    claim_id TEXT PRIMARY KEY,
    employee_id TEXT NOT NULL,
    status TEXT NOT NULL,  -- 'draft' or 'submitted'
    created_at TEXT,
    data JSON  -- Stores: medical_provider, receipt_no, receipt_date, 
               --         receipt_amount, diagnosis, gst_inclusive
)
```

**Design Note**: Using JSON blob for flexible schema allows adding fields without schema migrations.

### Key Functions

#### Database Management

**`_get_db()`** (Context Manager)
- Returns SQLite connection with `sqlite3.Row` factory
- Ensures proper connection cleanup via context manager
- Database file: `data/claims_poc.db` (created in data directory)

**`_init_db()`**
- Initializes database table on module import
- Called automatically when module is imported

#### Helper Functions

**`_generate_claim_id() -> str`**
- Generates unique claim IDs in format: `claim-{random 5-digit number}`
- Collision detection: Checks database before returning
- Retry logic: Up to 10 attempts before raising RuntimeError
- **Optimization Opportunity**: Consider UUID or timestamp-based IDs for better scalability

**`_validate_date(date_str: str) -> bool`**
- Validates date format: YYYY-MM-DD
- Returns boolean (doesn't raise exceptions)

#### Core Tool Functions

**`list_claims(employee_id: str) -> str`**
- Returns all claims for an employee as JSON
- Merges database columns with JSON data blob
- Error handling: Skips corrupted JSON entries silently
- Returns: `{"employee_id": str, "claims": [array]}`

**`draft_medical_claim(...) -> str`**
- Creates a new draft claim
- Validates date format before creation
- Generates unique claim_id
- Stores claim details in JSON blob
- Error handling:
  - Invalid date format → Returns error JSON
  - Database integrity errors → Returns error JSON
- Returns: `{"status": "draft", "message": str, "claim_id": str, "details": dict}`

**`update_medical_claim(employee_id, claim_id, field, value) -> str`**
- Updates a single field in a draft claim
- Validations:
  - Field name must be in valid_fields set
  - Claim must exist
  - Claim must be in "draft" status
  - Date format validation for receipt_date
  - Number validation for receipt_amount
- Type conversions:
  - `receipt_amount`: Converts to float
  - `gst_inclusive`: Converts string to boolean ("true", "1", "yes" → True)
  - Other fields: Stored as strings
- Returns: `{"status": "updated", "message": str, "current_data": dict}`

**`submit_medical_claim(employee_id, claim_id) -> str`**
- Submits a draft claim for processing
- **Race Condition Protection**: Uses atomic UPDATE with WHERE clause
  ```sql
  UPDATE claims SET status = 'submitted' 
  WHERE claim_id = ? AND status = 'draft'
  ```
- Checks `rowcount` to detect if status changed between SELECT and UPDATE
- Error handling:
  - Claim not found
  - Claim already submitted
  - Race condition detected
- Prints system message to stdout (for logging/debugging)
- Returns: `{"status": "submitted", "message": str, "employee_id": str}`

### Error Handling Strategy

All functions return JSON strings, even for errors:
```json
{"error": "Error message here"}
```

This allows the agent to parse and present errors naturally to users.

### Security & Data Integrity

1. **SQL Injection Prevention**: All queries use parameterized statements (`?` placeholders)
2. **Race Condition Protection**: Atomic updates in `submit_medical_claim`
3. **Data Validation**: Date format, field names, and types are validated
4. **Status Enforcement**: Only draft claims can be updated

### Known Limitations

1. **Database Location**: Database file is created in current working directory (not configurable)
2. **No Indexes**: Database lacks indexes on frequently queried columns (employee_id, status)
3. **No Transactions**: Some operations could benefit from explicit transactions
4. **Print Statements**: Uses `print()` for logging (should use proper logging framework)
5. **No Connection Pooling**: Each operation opens/closes a connection (fine for low concurrency)

---

## 3. test_claims_agent.ipynb

### Purpose
Comprehensive test suite for validating the claims agent system. Tests both direct tool functions and agent interactions.

### Test Structure

#### Section 1: Direct Tool Testing (Tests 1-10)
Tests the underlying `claims_tools` functions directly:

1. **Test 1**: List claims (empty state)
2. **Test 2**: Create draft claim
3. **Test 3**: Verify claim appears in list
4. **Test 4**: Update claim amount
5. **Test 5**: Update claim diagnosis
6. **Test 6**: Error - Update non-existent claim
7. **Test 7**: Error - Invalid date format
8. **Test 8**: Submit claim
9. **Test 9**: Error - Update submitted claim (should fail)
10. **Test 10**: Error - Resubmit claim (should fail)

#### Section 2: Agent Interaction Testing (Tests 11-15)
Tests natural language interactions with the agent:

11. **Test 11**: Agent - List claims query
12. **Test 12**: Agent - Create draft with receipt simulation
13. **Test 13**: Agent - Update draft claim
14. **Test 14**: Agent - Submit claim
15. **Test 15**: Full workflow simulation (draft → update → submit)

#### Section 3: Error Handling Tests (Tests 16-17)
Tests agent's error handling:

16. **Test 16**: Agent - Invalid date format handling
17. **Test 17**: Agent - Non-existent claim update

#### Section 4: Summary and Verification
- Final claims summary
- Verification of all stored claims

#### Section 5: Cleanup (Optional)
- Commented code for cleaning up test data

### Test Coverage

✅ **Covered**:
- All 4 tool functions
- Success paths
- Error paths
- Agent natural language interactions
- Full workflow end-to-end
- Error handling

⚠️ **Not Covered** (Potential Additions):
- Concurrent access testing
- Large dataset performance
- Edge cases (very long strings, special characters)
- Database corruption recovery
- Claim ID collision handling (rare but possible)

### Running the Tests

1. **Prerequisites**:
   - OpenAI API key set in environment (`OPENAI_API_KEY`)
   - Project dependencies installed
   - Database will be created automatically

2. **Execution**:
   - Run cells sequentially
   - Each test is independent (except workflow tests)
   - Can run individual test cells for debugging

3. **Expected Output**:
   - JSON responses for direct tool tests
   - Natural language responses for agent tests
   - Clear error messages for error tests

---

## Optimization Opportunities

### Performance Optimizations

1. **Database Indexes**
   ```python
   # Add to _init_db():
   conn.execute("CREATE INDEX IF NOT EXISTS idx_employee_id ON claims(employee_id)")
   conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON claims(status)")
   conn.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON claims(created_at)")
   ```

2. **Connection Pooling**
   - For higher concurrency, consider connection pooling
   - Current implementation is fine for low-medium traffic

3. **Caching**
   - Cache recent claims list for frequently accessed employee_ids
   - Consider TTL-based cache for draft claims

### Code Quality Improvements

1. **Logging**
   - Replace `print()` statements with proper logging
   - Use structured logging (JSON format)
   - Add log levels (DEBUG, INFO, WARNING, ERROR)

2. **Configuration Management**
   - Move database path to configuration
   - Make employee_id configurable (currently hardcoded)
   - Add environment-based configuration

3. **Type Safety**
   - Add type hints to all functions
   - Consider using Pydantic models for data validation
   - Add mypy type checking

4. **Error Handling**
   - Create custom exception classes
   - Add more specific error types
   - Improve error messages with context

### Agent Optimization

1. **Instructions Refinement**
   - Test different instruction formats for better agent behavior
   - Add examples of good interactions
   - Consider few-shot examples in instructions

2. **Tool Descriptions**
   - Enhance tool docstrings with more examples
   - Add parameter validation hints
   - Include common error scenarios

3. **Response Formatting**
   - Standardize JSON response format
   - Add response schemas
   - Consider structured output mode (if supported by model)

### Database Improvements

1. **Schema Evolution**
   - Add migration system for schema changes
   - Version the schema
   - Add schema validation on startup

2. **Data Integrity**
   - Add foreign key constraints (if needed)
   - Add check constraints for status values
   - Add NOT NULL constraints where appropriate

3. **Backup & Recovery**
   - Add database backup functionality
   - Add data export/import capabilities
   - Consider adding audit logging

---

## Usage Examples

### Example 1: Basic Workflow

```python
from src.agents.smol_claims_agent import claims_smol_agent

# User provides receipt information
response = claims_smol_agent.run(
    "I have a medical receipt from ABC Clinic. "
    "Receipt number R-12345, dated 2025-01-15, "
    "amount $85.50, diagnosis: Common cold. "
    "GST is included. Please create a draft - I confirm all details."
)
# Agent creates draft and returns claim_id

# User wants to correct amount
response = claims_smol_agent.run(
    "Actually, the amount for claim-12345 should be $90.00. Can you fix it?"
)
# Agent updates the claim

# User submits
response = claims_smol_agent.run(
    "Yes, please submit claim-12345 now."
)
# Agent submits the claim
```

### Example 2: Direct Tool Usage

```python
from src.tools import claims_tools as ct
import json

# Create draft
result = ct.draft_medical_claim(
    employee_id="mark_tan",
    medical_provider="XYZ Hospital",
    receipt_no="R-54321",
    receipt_date="2025-01-20",
    receipt_amount=120.00,
    diagnosis="Annual checkup",
    gst_inclusive=True
)
data = json.loads(result)
claim_id = data["claim_id"]

# Update claim
result = ct.update_medical_claim(
    employee_id="mark_tan",
    claim_id=claim_id,
    field="receipt_amount",
    value="125.00"
)

# Submit claim
result = ct.submit_medical_claim("mark_tan", claim_id)
```

---

## Known Limitations & Issues

### Current Limitations

1. **Hardcoded Employee ID**: Employee ID is hardcoded as "mark_tan" in instructions
   - **Impact**: Agent assumes all users are mark_tan
   - **Fix**: Make employee_id dynamic or pass as context

2. **Database Location**: Database created in current working directory
   - **Impact**: May cause issues in different execution contexts
   - **Fix**: Use absolute path or configuration

3. **No Authentication**: No user authentication or authorization
   - **Impact**: Any employee_id can access any claims
   - **Fix**: Add authentication layer

4. **Limited Error Recovery**: Some errors don't provide recovery guidance
   - **Impact**: Users may not know how to fix issues
   - **Fix**: Enhance error messages with actionable guidance

5. **No Rate Limiting**: No protection against abuse
   - **Impact**: Could be overwhelmed by rapid requests
   - **Fix**: Add rate limiting middleware

### Potential Issues

1. **Claim ID Collisions**: While rare, collisions are possible
   - Current mitigation: 10 retry attempts
   - Better solution: Use UUID or timestamp-based IDs

2. **Database Locking**: SQLite may have issues with concurrent writes
   - Current mitigation: Context managers ensure proper cleanup
   - Better solution: Use connection pooling or PostgreSQL for production

3. **JSON Parsing Errors**: Corrupted JSON in database
   - Current mitigation: Skip corrupted entries silently
   - Better solution: Add data validation and repair mechanisms

---

## Future Improvements

### Short-term (1-2 weeks)

1. ✅ Add database indexes for performance
2. ✅ Replace print statements with logging
3. ✅ Make employee_id configurable
4. ✅ Add comprehensive error messages
5. ✅ Add unit tests for tool functions

### Medium-term (1-2 months)

1. Add authentication and authorization
2. Implement proper logging system
3. Add database migration system
4. Create API wrapper for HTTP access
5. Add monitoring and metrics
6. Implement claim status workflow (draft → submitted → approved → rejected)

### Long-term (3+ months)

1. Multi-tenant support
2. Integration with actual backend systems
3. Receipt OCR integration
4. Email notifications
5. Dashboard for claim management
6. Analytics and reporting
7. Mobile app support

---

## Handover Notes

### For New Developers

1. **Start Here**: Read this document, then examine `test_claims_agent.ipynb` for examples
2. **Key Files**:
   - `src/agents/smol_claims_agent.py` - Agent layer
   - `src/tools/claims_tools.py` - Business logic layer
   - `src/tests/test_claims_agent.ipynb` - Test suite
3. **Database**: SQLite file `data/claims_poc.db` is created automatically
4. **Dependencies**: See `pyproject.toml` for required packages

### For Optimization Work

1. **Performance**: Start with database indexes (see Optimization section)
2. **Agent Behavior**: Modify `CLAIMS_INSTRUCTIONS` in `smol_claims_agent.py`
3. **Tool Behavior**: Modify functions in `claims_tools.py`
4. **Testing**: Add new test cases to `test_claims_agent.ipynb`

### For Production Deployment

1. **Security**: Add authentication before deploying
2. **Database**: Consider PostgreSQL for production
3. **Logging**: Implement proper logging system
4. **Monitoring**: Add health checks and metrics
5. **Backup**: Implement database backup strategy
6. **Configuration**: Move hardcoded values to configuration

### Common Tasks

**Adding a New Field to Claims**:
1. Update `draft_medical_claim()` to accept new parameter
2. Add field to `claim_details` dict
3. Add field to `valid_fields` in `update_medical_claim()`
4. Update tool docstrings
5. Update test notebook

**Changing Agent Behavior**:
1. Modify `CLAIMS_INSTRUCTIONS` in `smol_claims_agent.py`
2. Test with various scenarios in notebook
3. Iterate based on agent responses

**Debugging Issues**:
1. Check database directly: `sqlite3 data/claims_poc.db`
2. Run individual test cells in notebook
3. Check agent tool calls in notebook output
4. Review error JSON responses

---

## Quick Reference

### Tool Functions Summary

| Function | Purpose | Key Validations |
|----------|---------|----------------|
| `list_claims()` | List all claims for employee | None |
| `draft_medical_claim()` | Create draft claim | Date format (YYYY-MM-DD) |
| `update_medical_claim()` | Update draft claim field | Field name, claim status, date format, amount type |
| `submit_medical_claim()` | Submit draft claim | Claim exists, status is "draft" |

### Claim Status Flow

```
[No Claim] → draft_medical_claim() → [Draft]
                                         ↓
                                    update_medical_claim()
                                         ↓
                                    submit_medical_claim() → [Submitted]
                                                                    ↓
                                                              (Final State)
```

### Valid Update Fields

- `medical_provider` (string)
- `receipt_no` (string)
- `receipt_date` (string, YYYY-MM-DD format)
- `receipt_amount` (string, converted to float)
- `diagnosis` (string)
- `gst_inclusive` (string: "true"/"false"/"1"/"yes" → boolean)

---

## Contact & Support

For questions or issues:
1. Review this documentation
2. Check test notebook for examples
3. Examine code comments in source files
4. Review agent instructions for behavior expectations

---

**Last Updated**: 2025-01-XX  
**Version**: 1.0  
**Maintainer**: [Your Name/Team]

