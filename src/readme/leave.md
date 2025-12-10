# Leave Agent System Documentation

## Overview

The Leave Agent System is an employee leave management solution built using `smolagents`. It enables bank staff to apply for leave (annual, medical, and family leave) through natural language interactions, with the agent handling balance checks, draft creation, and submission workflows.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interaction                          │
│              (Natural Language Queries)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              smol_leave_agent.py                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ToolCallingAgent (leave_specialist)                  │  │
│  │  - Model: gpt-4.1-mini (via smol_base)               │  │
│  │  - Instructions: LEAVE_INSTRUCTIONS                    │  │
│  │  - Tools: 6 tool functions                            │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              leave_tools.py                                 │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tool Functions (6):                                  │  │
│  │  - get_leave_balance()                                │  │
│  │  - draft_leave_request()                              │  │
│  │  - submit_draft_leave_request()                       │  │
│  │  - submit_leave_request() (direct)                    │  │
│  │  - list_leave_drafts()                                │  │
│  │  - check_leave_status()                                │  │
│  └──────────────────────────────────────────────────────┘  │
│                       │                                      │
│                       ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  In-Memory Data Stores (Prototype)                    │  │
│  │  - db: Leave balances (dict)                          │  │
│  │  - leave_requests_db: Submitted requests (dict)      │  │
│  │  - leave_drafts_db: Draft requests (dict)            │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. smol_leave_agent.py

### Purpose
The agent layer that provides natural language interface for leave management. It wraps the underlying tool functions and provides intelligent routing, date validation, and workflow management.

### Key Components

#### Agent Configuration
- **Name**: `leave_specialist`
- **Model**: `gpt-4.1-mini` (via `get_smol_model()` from `smol_base.py`)
- **Framework**: `smolagents.ToolCallingAgent`
- **Tools**: 6 tool functions (see below)

#### Tool Functions

1. **`get_leave_balance_tool(employee_id: str, leave_type: str)`**
   - Checks remaining leave balance for an employee
   - Leave types: "annual", "medical", "family"
   - Returns JSON string with balance and unit

2. **`draft_leave_request_tool(employee_id, leave_type, start_date, end_date)`**
   - Creates a draft leave request with date range
   - Automatically calculates number of days
   - Validates leave balance before creating draft
   - **Important**: Agent must have both start_date and end_date before calling

3. **`submit_draft_leave_request_tool(employee_id, draft_id)`**
   - Submits a previously created draft
   - **Preferred method** for submission workflow
   - **Important**: Agent must wait for explicit user approval before calling

4. **`submit_leave_request_tool(employee_id, leave_type, days)`**
   - Direct submission without draft (alternative method)
   - Only used when user explicitly wants to skip draft step
   - Less preferred than draft → submit workflow

5. **`list_leave_drafts_tool(employee_id)`**
   - Lists all draft leave requests for an employee
   - Shows draft status, dates, and leave type
   - Useful for reviewing saved drafts

6. **`check_leave_status_tool(request_id)`**
   - Checks status of submitted leave request
   - Returns: pending, approved, or rejected (currently only "pending" implemented)
   - Request ID format: "MW{5-digit number}"

#### Agent Instructions (`LEAVE_INSTRUCTIONS`)

The agent follows a structured workflow with strict rules:

**GENERAL RULES:**
- **MUST NOT** make up or assume dates
- **MUST** ask for start date if user mentions days but no dates
- **MUST** confirm both start_date and end_date before creating draft
- **MUST** resolve ambiguity (e.g., dates imply 8 days but user said 7)

**WORKFLOW:**
1. **DRAFT CREATION**:
   - Gather: leave type, start_date, end_date
   - Create draft using `draft_leave_request_tool`
   - Draft automatically calculates days and checks balance
   - Present draft_id to user clearly

2. **SUBMISSION**:
   - **PREFERRED**: Use `submit_draft_leave_request_tool` with draft_id
   - **ALTERNATIVE**: Use `submit_leave_request_tool` only if user explicitly skips draft
   - **MUST NOT** submit without explicit user approval

3. **DRAFT MANAGEMENT**:
   - Use `list_leave_drafts_tool` to show saved drafts
   - Note: Drafts cannot be modified; user must create new draft

4. **STATUS CHECKING**:
   - Use `check_leave_status_tool` for status queries
   - Agent should infer request_id from conversation context if possible

**OUTPUT STYLE:**
- Always include request_id or draft_id in responses
- Summarize tool outputs in natural language
- Clearly show draft_id for user reference

#### Important Rules
- Current Employee ID: `mark_tan` (hardcoded in instructions)
- Date format: YYYY-MM-DD (strictly enforced)
- Leave types: annual, medical, family (case-insensitive)
- Days calculation: Inclusive of both start and end dates

### Design Decisions

1. **Two Submission Methods**: 
   - Preferred: Draft → Submit workflow (preserves all information)
   - Alternative: Direct submit (for quick submissions)
   - This provides flexibility while encouraging best practices

2. **Date Validation First**: 
   - Agent must gather dates before creating draft
   - Prevents errors and ensures accurate day calculations
   - Reduces need for corrections later

3. **Explicit Approval Required**: 
   - Agent cannot submit without clear user approval
   - Prevents accidental submissions
   - Follows principle of least surprise

4. **No Draft Modification**: 
   - Drafts cannot be edited (simpler implementation)
   - Users create new draft if changes needed
   - Keeps data model simple

---

## 2. leave_tools.py

### Purpose
Core business logic layer that handles all leave management functionality. Provides the actual implementation of leave operations using in-memory data structures (prototype implementation).

### Data Structures

#### Leave Balance Database (`db`)
```python
db = {
    "mark_tan": {"annual": 14, "medical": 14, "family": 3},
    "jane_doe": {"annual": 2, "medical": 10, "family": 0}
}
```
- Simple dictionary structure
- Employee ID → Leave type → Balance (days)
- **Note**: This is a prototype; production would use a database

#### Leave Requests Database (`leave_requests_db`)
- Dictionary: `request_id → request_data`
- Stores submitted leave requests
- Request ID format: `MW{5-digit number}` (e.g., "MW19740")
- Status: Currently only "pending" (approval/rejection not implemented)

#### Leave Drafts Database (`leave_drafts_db`)
- Dictionary: `draft_id → draft_data`
- Stores draft leave requests
- Draft ID format: `draft-{5-digit number}` (e.g., "draft-61654")
- Status: "draft" or "submitted"

### Helper Functions

**`_validate_date(date_str: str) -> bool`**
- Validates date format: YYYY-MM-DD
- Uses `datetime.strptime()` for validation
- Returns boolean (doesn't raise exceptions)

**`_calculate_days(start_date: str, end_date: str) -> int`**
- Calculates number of days between dates (inclusive)
- Formula: `(end - start).days + 1`
- Returns -1 on error

**`_generate_request_id() -> str`**
- Generates unique request ID: `MW{random 5-digit}`
- Collision detection: Checks `leave_requests_db` before returning
- Retry logic: Up to 10 attempts before raising RuntimeError
- **Optimization Opportunity**: Consider UUID or timestamp-based IDs

**`_validate_leave_type(leave_type: str) -> bool`**
- Validates leave type is one of: "annual", "medical", "family"
- Case-insensitive comparison

### Core Tool Functions

**`get_leave_balance(employee_id: str, leave_type: str) -> str`**
- Returns remaining leave days for employee
- Validations:
  - Leave type must be valid
  - Employee must exist
- Returns: `{"balance": int, "unit": "days"}` or error JSON

**`draft_leave_request(employee_id, leave_type, start_date, end_date) -> str`**
- Creates a draft leave request
- Validations (in order):
  1. Leave type format
  2. Date format (YYYY-MM-DD)
  3. Date logic (end_date >= start_date)
  4. Day calculation
  5. Employee existence
  6. Leave balance sufficiency
- Automatically calculates days from date range
- Generates unique draft_id
- Stores draft in `leave_drafts_db`
- Returns: `{"status": "draft", "message": str, "draft_id": str, "draft": dict}`

**`submit_draft_leave_request(employee_id, draft_id) -> str`**
- Submits a draft for processing
- Validations:
  - Draft must exist
  - Draft must belong to employee
  - Draft status must be "draft" (not already submitted)
- Generates new request_id
- Moves data from `leave_drafts_db` to `leave_requests_db`
- Marks draft status as "submitted"
- Returns: `{"status": "success", "request_id": str, "leave_status": str, "message": str}`

**`submit_leave_request(employee_id, leave_type, days) -> str`**
- Direct submission without draft (alternative method)
- Validations:
  - Leave type format
  - Days must be positive integer
  - Employee existence
  - Leave balance sufficiency
- Generates request_id
- Stores in `leave_requests_db` (no draft record)
- Returns: `{"status": "success", "request_id": str, "leave_status": str, "message": str}`

**`list_leave_drafts(employee_id) -> str`**
- Lists all drafts for an employee
- Filters by employee_id
- Returns all drafts regardless of status
- Returns: `{"employee_id": str, "drafts": [array]}`

**`check_leave_status(request_id) -> str`**
- Checks status of submitted request
- Returns full request details
- Returns: `{"request_id": str, "status": str, "employee_id": str, "leave_type": str, "days": int}` or error JSON

### Error Handling Strategy

All functions return JSON strings, even for errors:
```json
{"error": "Error message here"}
```

Common error scenarios:
- Invalid leave type → Lists valid types
- Invalid date format → Specifies required format (YYYY-MM-DD)
- End date before start date → Clear error message
- Insufficient balance → Shows requested vs available
- Employee not found → Generic error (security consideration)
- Draft/Request not found → Clear error with ID

### Security & Data Integrity

1. **Input Validation**: All inputs validated before processing
2. **Date Validation**: Strict YYYY-MM-DD format enforcement
3. **Balance Checking**: Prevents over-allocation of leave
4. **Employee Verification**: Checks employee exists before operations
5. **Draft Ownership**: Verifies draft belongs to employee before submission

### Known Limitations

1. **In-Memory Storage**: Data lost on restart (prototype only)
2. **No Persistence**: No database or file storage
3. **No Approval Workflow**: Status always "pending" (approval/rejection not implemented)
4. **No Draft Modification**: Drafts cannot be edited (must create new)
5. **Print Statements**: Uses `print()` for logging (should use proper logging)
6. **No Concurrency Protection**: No locking for concurrent access
7. **Hardcoded Employee Data**: Employee balances hardcoded in dictionary

---

## 3. test_leave_agent.ipynb

### Purpose
Comprehensive test suite for validating the leave agent system. Tests both direct tool functions and agent interactions with natural language queries.

### Test Structure

#### Section 1: Direct Tool Testing
Tests the underlying `leave_tools` functions directly:

1. **Test 1.1**: Get leave balance (annual, medical, family)
2. **Test 1.2**: Create draft leave request
3. **Test 1.3**: List leave drafts
4. **Test 1.4**: Submit draft leave request
5. **Test 1.5**: Check leave status
6. **Test 1.6**: Direct submit (alternative method)

#### Section 2: Error Handling Tests
Tests various error scenarios:

1. **Test 2.1**: Invalid leave type
2. **Test 2.2**: Invalid date format
3. **Test 2.3**: End date before start date
4. **Test 2.4**: Insufficient leave balance
5. **Test 2.5**: Non-existent employee
6. **Test 2.6**: Non-existent draft ID
7. **Test 2.7**: Non-existent request ID
8. **Test 2.8**: Invalid days (zero or negative)

#### Section 3: Edge Cases and Special Scenarios
Tests edge cases:

1. **Test 3.1**: Single day leave request (start_date == end_date)
2. **Test 3.2**: Multiple drafts for same employee
3. **Test 3.3**: Different employee (jane_doe)

#### Section 4: Agent Interaction Tests
Tests natural language interactions:

1. **Test 4.1**: Simple balance query
2. **Test 4.2**: Draft creation with dates provided
3. **Test 4.3**: Draft creation without dates (should ask)
4. **Test 4.4**: List drafts request
5. **Test 4.5**: Status check request

#### Section 5: Full Workflow Tests
Tests complete end-to-end workflows:

1. **Test 5.1**: Complete draft → submit workflow (using tools directly)
2. **Test 5.2**: Agent conversation workflow (simulated multi-turn conversation)

#### Section 6: Summary and Test Results
Automated test summary that verifies all core functions work correctly.

### Test Coverage

✅ **Covered**:
- All 6 tool functions
- Success paths
- Error paths (8 error scenarios)
- Edge cases (single day, multiple drafts, different employees)
- Agent natural language interactions
- Full workflow end-to-end
- Date validation
- Balance checking

⚠️ **Not Covered** (Potential Additions):
- Concurrent access testing
- Large dataset performance
- Date edge cases (leap years, month boundaries)
- Very long date ranges
- Special characters in employee IDs
- Request ID collision handling (rare but possible)
- Approval/rejection workflow (not yet implemented)

### Running the Tests

1. **Prerequisites**:
   - OpenAI API key set in environment (`OPENAI_API_KEY`)
   - Project dependencies installed
   - Jupyter notebook environment

2. **Execution**:
   - Run cells sequentially from top to bottom
   - Each test section is independent
   - Can run individual test cells for debugging
   - Agent tests require API calls (may incur costs)

3. **Expected Output**:
   - JSON responses for direct tool tests
   - Natural language responses for agent tests
   - Clear error messages for error tests
   - System print statements for draft/request creation

4. **Note on Agent Tests**:
   - Agent tests make actual API calls to OpenAI
   - Each test creates a new agent run (no conversation memory)
   - Tool calls are visible in notebook output
   - Response times vary (typically 1-5 seconds per test)

---

## Optimization Opportunities

### Performance Optimizations

1. **Data Persistence**
   - Replace in-memory dictionaries with database (SQLite or PostgreSQL)
   - Add database indexes on employee_id, request_id, draft_id
   - Implement connection pooling for concurrent access

2. **Caching**
   - Cache leave balances (refresh periodically)
   - Cache recent drafts list for frequently accessed employees
   - Consider TTL-based cache for draft requests

3. **ID Generation**
   - Replace random ID generation with UUID or timestamp-based IDs
   - Eliminates collision risk
   - Better for distributed systems

### Code Quality Improvements

1. **Logging**
   - Replace `print()` statements with proper logging framework
   - Use structured logging (JSON format)
   - Add log levels (DEBUG, INFO, WARNING, ERROR)
   - Log all operations for audit trail

2. **Configuration Management**
   - Move employee_id to configuration (currently hardcoded)
   - Make leave types configurable
   - Add environment-based configuration
   - Externalize leave balance data

3. **Type Safety**
   - Add comprehensive type hints
   - Consider using Pydantic models for data validation
   - Add mypy type checking
   - Use enums for leave types and statuses

4. **Error Handling**
   - Create custom exception classes
   - Add more specific error types
   - Improve error messages with actionable guidance
   - Add error recovery suggestions

### Agent Optimization

1. **Instructions Refinement**
   - Test different instruction formats for better agent behavior
   - Add more examples of good interactions
   - Consider few-shot examples in instructions
   - Add examples of error handling

2. **Tool Descriptions**
   - Enhance tool docstrings with more examples
   - Add parameter validation hints
   - Include common error scenarios
   - Add usage examples in docstrings

3. **Response Formatting**
   - Standardize JSON response format
   - Add response schemas
   - Consider structured output mode (if supported by model)
   - Improve date formatting in responses

### Data Model Improvements

1. **Database Schema** (for production)
   ```sql
   CREATE TABLE leave_balances (
       employee_id TEXT PRIMARY KEY,
       annual INTEGER NOT NULL,
       medical INTEGER NOT NULL,
       family INTEGER NOT NULL
   );
   
   CREATE TABLE leave_requests (
       request_id TEXT PRIMARY KEY,
       employee_id TEXT NOT NULL,
       leave_type TEXT NOT NULL,
       start_date DATE NOT NULL,
       end_date DATE NOT NULL,
       days INTEGER NOT NULL,
       status TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   
   CREATE TABLE leave_drafts (
       draft_id TEXT PRIMARY KEY,
       employee_id TEXT NOT NULL,
       leave_type TEXT NOT NULL,
       start_date DATE NOT NULL,
       end_date DATE NOT NULL,
       days INTEGER NOT NULL,
       status TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. **Status Workflow**
   - Implement approval/rejection workflow
   - Add status transitions: pending → approved/rejected
   - Add manager approval logic
   - Add status change notifications

3. **Data Integrity**
   - Add foreign key constraints
   - Add check constraints for status values
   - Add NOT NULL constraints where appropriate
   - Add unique constraints for request_id, draft_id

---

## Usage Examples

### Example 1: Basic Workflow (Preferred Method)

```python
from src.agents.smol_leave_agent import leave_smol_agent

# User asks about balance
response = leave_smol_agent.run("How many days of annual leave do I have?")
# Agent: "You have 14 days of annual leave left."

# User requests leave with dates
response = leave_smol_agent.run(
    "I would like to apply for 3 days of annual leave from 2025-12-15 to 2025-12-17"
)
# Agent creates draft and returns: "I've created a draft leave request for 3 days 
# of annual leave from 2025-12-15 to 2025-12-17. Your draft ID is draft-29082. 
# Would you like me to submit this leave request now?"

# User approves
response = leave_smol_agent.run("Yes, please submit it")
# Agent submits and returns: "Request ID #MW19740 submitted and pending manager review."
```

### Example 2: Workflow Without Dates

```python
# User mentions days but no dates
response = leave_smol_agent.run("I would like to apply for 5 days of annual leave")
# Agent: "Please provide the start date for your 5 days of annual leave (in YYYY-MM-DD format)."

# User provides start date
response = leave_smol_agent.run("2025-12-04")
# Agent: "You would like 5 days of annual leave starting on 2025-12-04. That would 
# typically run from 2025-12-04 to 2025-12-08 (5 days). Please confirm if these 
# dates are correct, or provide a different end date."

# User confirms
response = leave_smol_agent.run("Yes, those dates are correct")
# Agent creates draft and asks for submission approval
```

### Example 3: Direct Tool Usage

```python
from src.tools import leave_tools as lt
import json

# Check balance
result = lt.get_leave_balance("mark_tan", "annual")
balance_data = json.loads(result)
print(f"Balance: {balance_data['balance']} days")

# Create draft
result = lt.draft_leave_request(
    employee_id="mark_tan",
    leave_type="annual",
    start_date="2025-12-20",
    end_date="2025-12-22"
)
draft_data = json.loads(result)
draft_id = draft_data["draft_id"]

# Submit draft
result = lt.submit_draft_leave_request("mark_tan", draft_id)
submit_data = json.loads(result)
request_id = submit_data["request_id"]

# Check status
result = lt.check_leave_status(request_id)
status_data = json.loads(result)
print(f"Status: {status_data['status']}")
```

### Example 4: List and Review Drafts

```python
# List all drafts
response = leave_smol_agent.run("Show me all my draft leave requests")
# Agent lists all drafts with details

# Check status of submitted request
response = leave_smol_agent.run("What is the status of my leave request MW19740?")
# Agent: "The status of your leave request MW19740 is pending. It is for 7 days of annual leave."
```

---

## Known Limitations & Issues

### Current Limitations

1. **Hardcoded Employee ID**: Employee ID is hardcoded as "mark_tan" in instructions
   - **Impact**: Agent assumes all users are mark_tan
   - **Fix**: Make employee_id dynamic or pass as context

2. **In-Memory Storage**: All data stored in memory (dictionaries)
   - **Impact**: Data lost on restart, not suitable for production
   - **Fix**: Implement database persistence

3. **No Approval Workflow**: Status always "pending"
   - **Impact**: Cannot test approval/rejection scenarios
   - **Fix**: Implement manager approval workflow

4. **No Draft Modification**: Drafts cannot be edited
   - **Impact**: Users must create new draft for corrections
   - **Fix**: Add draft update functionality

5. **No Authentication**: No user authentication or authorization
   - **Impact**: Any employee_id can access any data
   - **Fix**: Add authentication layer

6. **Limited Error Recovery**: Some errors don't provide recovery guidance
   - **Impact**: Users may not know how to fix issues
   - **Fix**: Enhance error messages with actionable guidance

7. **No Rate Limiting**: No protection against abuse
   - **Impact**: Could be overwhelmed by rapid requests
   - **Fix**: Add rate limiting middleware

### Potential Issues

1. **Request ID Collisions**: While rare, collisions are possible
   - Current mitigation: 10 retry attempts
   - Better solution: Use UUID or timestamp-based IDs

2. **Concurrent Access**: No locking for concurrent operations
   - Current mitigation: In-memory (single process)
   - Better solution: Add database transactions and locking

3. **Date Calculation Edge Cases**: 
   - Leap years handled correctly by datetime
   - Month boundaries handled correctly
   - Timezone not considered (assumes local time)

4. **Balance Deduction**: Balance not automatically deducted on submission
   - **Impact**: Balance remains unchanged after leave submission
   - **Fix**: Deduct balance when request is approved (not on submission)

---

## Future Improvements

### Short-term (1-2 weeks)

1. ✅ Add database persistence (SQLite)
2. ✅ Replace print statements with logging
3. ✅ Make employee_id configurable
4. ✅ Add comprehensive error messages
5. ✅ Add unit tests for tool functions
6. ✅ Implement balance deduction on approval

### Medium-term (1-2 months)

1. Add authentication and authorization
2. Implement proper logging system
3. Add database migration system
4. Create API wrapper for HTTP access
5. Add monitoring and metrics
6. Implement approval/rejection workflow
7. Add email notifications for status changes
8. Implement leave balance deduction logic

### Long-term (3+ months)

1. Multi-tenant support
2. Integration with actual HR backend systems
3. Calendar integration for leave visualization
4. Manager dashboard for approval workflow
5. Analytics and reporting
6. Mobile app support
7. Leave policy enforcement (max consecutive days, blackout dates)
8. Leave accrual calculations

---

## Handover Notes

### For New Developers

1. **Start Here**: 
   - Read this document
   - Examine `test_leave_agent.ipynb` for examples
   - Run the test notebook to understand the system

2. **Key Files**:
   - `src/agents/smol_leave_agent.py` - Agent layer
   - `src/tools/leave_tools.py` - Business logic layer
   - `src/tests/test_leave_agent.ipynb` - Test suite

3. **Data Storage**: 
   - Currently in-memory (dictionaries)
   - Data lost on restart
   - Production needs database implementation

4. **Dependencies**: 
   - See `pyproject.toml` for required packages
   - Requires OpenAI API key for agent functionality

### For Optimization Work

1. **Performance**: 
   - Start with database implementation (see Optimization section)
   - Add indexes on frequently queried fields
   - Consider caching for leave balances

2. **Agent Behavior**: 
   - Modify `LEAVE_INSTRUCTIONS` in `smol_leave_agent.py`
   - Test changes in notebook before deploying
   - Iterate based on agent responses

3. **Tool Behavior**: 
   - Modify functions in `leave_tools.py`
   - Update tool docstrings when changing behavior
   - Add corresponding tests in notebook

4. **Testing**: 
   - Add new test cases to `test_leave_agent.ipynb`
   - Test both success and error paths
   - Test agent interactions with various phrasings

### For Production Deployment

1. **Security**: 
   - Add authentication before deploying
   - Implement authorization checks
   - Add input sanitization

2. **Database**: 
   - Implement proper database (PostgreSQL recommended)
   - Add database migrations
   - Set up backup strategy

3. **Logging**: 
   - Implement proper logging system
   - Add structured logging (JSON format)
   - Set up log aggregation

4. **Monitoring**: 
   - Add health checks
   - Implement metrics collection
   - Set up alerting

5. **Configuration**: 
   - Move hardcoded values to configuration
   - Use environment variables
   - Add configuration validation

### Common Tasks

**Adding a New Leave Type**:
1. Update `_validate_leave_type()` in `leave_tools.py`
2. Add leave type to `db` dictionary
3. Update tool docstrings
4. Update agent instructions if needed
5. Add test cases in notebook

**Changing Agent Behavior**:
1. Modify `LEAVE_INSTRUCTIONS` in `smol_leave_agent.py`
2. Test with various scenarios in notebook
3. Iterate based on agent responses
4. Document behavior changes

**Debugging Issues**:
1. Check in-memory data structures (use debugger or print)
2. Run individual test cells in notebook
3. Check agent tool calls in notebook output
4. Review error JSON responses
5. Check date format (must be YYYY-MM-DD)

**Implementing Database**:
1. Create database schema (see Optimization section)
2. Replace dictionary operations with database queries
3. Add connection management
4. Update all tool functions
5. Add migration scripts
6. Update tests to use database

---

## Quick Reference

### Tool Functions Summary

| Function | Purpose | Key Validations | Returns |
|----------|---------|----------------|---------|
| `get_leave_balance()` | Check leave balance | Leave type, employee exists | `{"balance": int, "unit": "days"}` |
| `draft_leave_request()` | Create draft | Date format, date logic, balance | `{"status": "draft", "draft_id": str, ...}` |
| `submit_draft_leave_request()` | Submit draft | Draft exists, belongs to employee, is draft | `{"status": "success", "request_id": str, ...}` |
| `submit_leave_request()` | Direct submit | Days > 0, balance sufficient | `{"status": "success", "request_id": str, ...}` |
| `list_leave_drafts()` | List drafts | None | `{"employee_id": str, "drafts": [array]}` |
| `check_leave_status()` | Check status | Request exists | `{"request_id": str, "status": str, ...}` |

### Leave Request Flow

```
[No Request] 
    ↓
get_leave_balance() → [Check Balance]
    ↓
draft_leave_request() → [Draft Created]
    ↓
submit_draft_leave_request() → [Request Submitted]
    ↓
check_leave_status() → [Status: pending/approved/rejected]
```

### Alternative Flow (Direct Submit)

```
[No Request]
    ↓
submit_leave_request() → [Request Submitted]
    ↓
check_leave_status() → [Status: pending/approved/rejected]
```

### Valid Leave Types

- `annual` - Annual leave
- `medical` - Medical leave
- `family` - Family leave

### Date Format

- **Required Format**: YYYY-MM-DD
- **Examples**: 
  - ✅ `2025-12-04` (valid)
  - ✅ `2025-01-15` (valid)
  - ❌ `2025/12/04` (invalid)
  - ❌ `12-04-2025` (invalid)
  - ❌ `Dec 4, 2025` (invalid)

### ID Formats

- **Draft ID**: `draft-{5-digit number}` (e.g., `draft-61654`)
- **Request ID**: `MW{5-digit number}` (e.g., `MW19740`)

### Status Values

- **Draft Status**: `"draft"` or `"submitted"`
- **Request Status**: `"pending"` (approval/rejection not yet implemented)

---

## Contact & Support

For questions or issues:
1. Review this documentation
2. Check test notebook (`test_leave_agent.ipynb`) for examples
3. Examine code comments in source files
4. Review agent instructions for behavior expectations
5. Run test notebook to verify functionality

---

**Last Updated**: 2025-01-XX  
**Version**: 1.0  
**Maintainer**: [Your Name/Team]

