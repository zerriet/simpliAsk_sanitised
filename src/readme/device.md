# Device Agent System Documentation

## Overview

The Device Agent System is an employee device request management solution built using `smolagents`. It enables bank staff to request IT peripherals and devices (cables, mice, keyboards, monitors, etc.) through natural language interactions, with the agent handling device catalog browsing, draft creation, and submission workflows.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interaction                          │
│              (Natural Language Queries)                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              smol_device_agent.py                            │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  ToolCallingAgent (device_specialist)                │  │
│  │  - Model: gpt-4.1-mini (via smol_base)               │  │
│  │  - Instructions: DEVICE_INSTRUCTIONS                  │  │
│  │  - Tools: 6 tool functions                            │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              device_tools.py                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tool Functions (6):                                  │  │
│  │  - get_available_devices()                           │  │
│  │  - draft_device_request()                            │  │
│  │  - submit_draft_device_request()                      │  │
│  │  - submit_device_request() (direct)                   │  │
│  │  - list_device_drafts()                               │  │
│  │  - check_device_request_status()                      │  │
│  └──────────────────────────────────────────────────────┘  │
│                       │                                      │
│                       ▼                                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  In-Memory Data Stores (Prototype)                   │  │
│  │  - device_db: Available devices (list)               │  │
│  │  - device_requests_db: Submitted requests (dict)     │  │
│  │  - device_drafts_db: Draft requests (dict)           │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. smol_device_agent.py

### Purpose
The agent layer that provides natural language interface for device request management. It wraps the underlying tool functions and provides intelligent routing, device validation, and workflow management.

### Key Components

#### Agent Configuration
- **Name**: `device_specialist`
- **Model**: `gpt-4.1-mini` (via `get_smol_model()` from `smol_base.py`)
- **Framework**: `smolagents.ToolCallingAgent`
- **Tools**: 6 tool functions (see below)

#### Tool Functions

1. **`get_available_devices_tool() -> str`**
   - Returns list of all available devices with id, name, and cost
   - No parameters required
   - Returns JSON string with device catalog
   - **Use Case**: When user asks "What devices can I request?" or needs to browse options

2. **`draft_device_request_tool(employee_id, device_id, device_name) -> str`**
   - Creates a draft device request before final submission
   - Parameters:
     - `employee_id` (str): Employee identifier (e.g., "mark_tan")
     - `device_id` (int): Device ID from catalog
     - `device_name` (str): Device name (must match catalog)
   - Validates device exists and name matches
   - **Important**: Agent must verify device_id and device_name match before calling

3. **`submit_draft_device_request_tool(employee_id, draft_id) -> str`**
   - Submits a previously created draft
   - Parameters:
     - `employee_id` (str): Employee identifier
     - `draft_id` (str): Draft ID (format: "draft-{5-digit}")
   - **Preferred method** for submission workflow
   - **Important**: Agent must wait for explicit user approval before calling

4. **`submit_device_request_tool(employee_id, device_id, device_name) -> str`**
   - Direct submission without draft (alternative method)
   - Parameters: Same as `draft_device_request_tool`
   - Only used when user explicitly wants to skip draft step
   - Less preferred than draft → submit workflow

5. **`list_device_drafts_tool(employee_id) -> str`**
   - Lists all draft device requests for an employee
   - Shows draft status, device details, and cost
   - Useful for reviewing saved drafts before submission

6. **`check_device_request_status_tool(request_id) -> str`**
   - Checks status of submitted device request
   - Parameters:
     - `request_id` (str): Request ID (format: "MW{5-digit number}")
   - Returns: pending, approved, or rejected (currently only "pending" implemented)
   - Includes device details and cost in response

#### Agent Instructions (`DEVICE_INSTRUCTIONS`)

The agent follows a structured workflow with strict rules:

**GENERAL RULES:**
- **MUST NOT** make up or assume device information
- **MUST** use `get_available_devices_tool` to show available devices
- **MUST** verify device_id and device_name match before creating draft
- **MUST** only call `draft_device_request_tool` after user has clearly selected a device

**WORKFLOW:**
1. **DEVICE SELECTION**:
   - Use `get_available_devices_tool` when user wants to see options
   - Present device list clearly with id, name, and cost
   - Help user identify correct device_id and device_name

2. **DRAFT CREATION**:
   - Gather: employee_id, device_id, device_name
   - Ensure device_id and device_name match (tool validates this)
   - Create draft using `draft_device_request_tool`
   - Present draft details (draft_id, device cost) clearly to user

3. **SUBMISSION**:
   - **PREFERRED**: Use `submit_draft_device_request_tool` with draft_id
   - **ALTERNATIVE**: Use `submit_device_request_tool` only if user explicitly skips draft
   - **MUST NOT** submit without explicit user approval

4. **DRAFT MANAGEMENT**:
   - Use `list_device_drafts_tool` to show saved drafts
   - Note: Drafts cannot be modified; user must create new draft

5. **STATUS CHECKING**:
   - Use `check_device_request_status_tool` for status queries
   - Agent should infer request_id from conversation context if possible

**OUTPUT STYLE:**
- Always include request_id or draft_id in responses
- Summarize tool outputs in natural language
- Clearly show draft_id and device cost for user reference
- Format device lists clearly with name, ID, and cost

#### Important Rules
- Current Employee ID: `mark_tan` (hardcoded in instructions)
- Device ID and Name Validation: Tool validates that device_id exists and device_name matches
- Request ID Format: `MW{5-digit number}` (e.g., "MW42176")
- Draft ID Format: `draft-{5-digit number}` (e.g., "draft-90845")

### Design Decisions

1. **Two Submission Methods**: 
   - Preferred: Draft → Submit workflow (preserves all information, allows review)
   - Alternative: Direct submit (for quick submissions when user is certain)
   - This provides flexibility while encouraging best practices

2. **Device Validation**: 
   - Tool validates device exists and name matches before creating draft
   - Prevents errors from mismatched device_id/device_name
   - Reduces need for corrections later

3. **Explicit Approval Required**: 
   - Agent cannot submit without clear user approval
   - Prevents accidental submissions
   - Follows principle of least surprise

4. **No Draft Modification**: 
   - Drafts cannot be edited (simpler implementation)
   - Users create new draft if changes needed
   - Keeps data model simple

5. **Device Catalog First**: 
   - Agent should show available devices when user is unsure
   - Ensures user selects from valid options
   - Prevents invalid device requests

---

## 2. device_tools.py

### Purpose
Core business logic layer that handles all device request functionality. Provides the actual implementation of device operations using in-memory data structures (prototype implementation).

### Data Structures

#### Device Catalog (`device_db`)
```python
device_db = [
    {"id": 1, "name": "2M HDMI Cable", "cost": 6.50},
    {"id": 2, "name": "Wireless Mouse", "cost": 15.00},
    {"id": 3, "name": "Mechanical Keyboard", "cost": 45.00},
    {"id": 4, "name": "27-inch Monitor", "cost": 230.00},
    {"id": 5, "name": "USB-C Hub", "cost": 25.50},
    {"id": 6, "name": "External Hard Drive 1TB", "cost": 65.00},
    {"id": 7, "name": "Laptop Stand", "cost": 30.00},
    {"id": 8, "name": "Webcam 1080p", "cost": 40.00}
]
```
- List of dictionaries with device information
- Each device has: `id` (int), `name` (str), `cost` (float)
- **Note**: This is a prototype; production would use a database or external catalog service

#### Device Requests Database (`device_requests_db`)
- Dictionary: `request_id → request_data`
- Stores submitted device requests
- Request ID format: `MW{5-digit number}` (e.g., "MW42176")
- Request data structure:
  ```python
  {
      "employee_id": str,
      "device_id": int,
      "device_name": str,
      "device_cost": float,
      "status": str  # Currently only "pending"
  }
  ```
- Status: Currently only "pending" (approval/rejection not implemented)

#### Device Drafts Database (`device_drafts_db`)
- Dictionary: `draft_id → draft_data`
- Stores draft device requests
- Draft ID format: `draft-{5-digit number}` (e.g., "draft-90845")
- Draft data structure:
  ```python
  {
      "draft_id": str,
      "employee_id": str,
      "device_id": int,
      "device_name": str,
      "device_cost": float,
      "status": str  # "draft" or "submitted"
  }
  ```
- Status: "draft" or "submitted"

### Helper Functions

**`_get_device_by_id(device_id: int) -> Optional[Dict[str, Any]]`**
- Retrieves device information by ID from `device_db`
- Returns device dictionary if found, `None` otherwise
- Used for validation before creating drafts/requests

**`_generate_request_id() -> str`**
- Generates unique request ID: `MW{random 5-digit}`
- Collision detection: Checks `device_requests_db` before returning
- Retry logic: Up to 10 attempts before raising `RuntimeError`
- **Optimization Opportunity**: Consider UUID or timestamp-based IDs for production

### Core Tool Functions

**`get_available_devices() -> str`**
- Returns list of all available devices
- No parameters required
- Returns JSON string with formatted device list (indented)
- Format: Array of device objects with `id`, `name`, and `cost`

**`draft_device_request(employee_id: str, device_id: int, device_name: str) -> str`**
- Creates a draft device request
- Validations (in order):
  1. Employee ID not empty/whitespace
  2. Device ID is positive integer
  3. Device name not empty/whitespace
  4. Device exists in catalog (by ID)
  5. Device name matches catalog entry
- Generates unique draft_id with collision checking
- Stores draft in `device_drafts_db`
- Includes device cost in draft data
- Returns: `{"status": "draft", "message": str, "draft_id": str, "draft": dict}`

**`submit_draft_device_request(employee_id: str, draft_id: str) -> str`**
- Submits a draft for processing
- Validations:
  - Draft must exist
  - Draft must belong to employee
  - Draft status must be "draft" (not already submitted)
- Generates new request_id using `_generate_request_id()`
- Moves data from `device_drafts_db` to `device_requests_db`
- Marks draft status as "submitted"
- Returns: `{"status": "success", "request_id": str, "message": str}`

**`submit_device_request(employee_id: str, device_id: int, device_name: str) -> str`**
- Direct submission without draft (alternative method)
- Same validations as `draft_device_request()`
- Generates request_id and stores directly in `device_requests_db`
- Skips draft step entirely
- Returns: `{"status": "success", "request_id": str, "message": str}`

**`list_device_drafts(employee_id: str) -> str`**
- Lists all draft device requests for an employee
- Filters `device_drafts_db` by employee_id
- Returns all drafts (both "draft" and "submitted" status)
- Returns: `{"employee_id": str, "drafts": [list of draft dicts]}`

**`check_device_request_status(request_id: str) -> str`**
- Checks status of submitted device request
- Validations:
  - Request must exist in `device_requests_db`
- Returns request details including:
  - request_id, status, employee_id
  - device_id, device_name, device_cost
- Returns: `{"request_id": str, "status": str, ...}` or error JSON

### Error Handling

All functions return JSON strings with error information:
- Format: `{"error": "Error message"}`
- Functions never raise exceptions (except `_generate_request_id()` on collision failure)
- Error messages are descriptive and actionable
- Common errors:
  - "Employee ID cannot be empty"
  - "Device ID must be a positive integer"
  - "Device with ID {id} not found"
  - "Device name mismatch. Expected '{expected}', got '{got}'"
  - "Draft not found"
  - "Draft does not belong to this employee"
  - "Draft is already {status}"
  - "Request not found"

### Type Hints and Documentation

- All functions have type hints (`-> str` for return types)
- All functions have docstrings
- Helper functions are prefixed with `_` (private convention)
- Uses `typing` module for type annotations (`Dict`, `Any`, `Optional`)

---

## 3. test_device_agent.ipynb

### Purpose
Comprehensive test suite for the Device Agent System. Tests both direct tool functions and agent interactions, including error handling, edge cases, and complete workflows.

### Test Structure

The notebook is organized into 6 main sections:

#### Section 1: Direct Tool Testing
Tests the underlying tool functions directly (bypassing the agent):

1. **Test 1.1: Get Available Devices**
   - Verifies `get_available_devices()` returns all 8 devices
   - Checks JSON format and structure

2. **Test 1.2: Create Draft Device Request**
   - Tests draft creation with valid inputs
   - Extracts `draft_id` for use in subsequent tests
   - Verifies draft structure and data

3. **Test 1.3: List Device Drafts**
   - Tests listing all drafts for an employee
   - Verifies draft count and structure

4. **Test 1.4: Submit Draft Device Request**
   - Tests submitting a draft
   - Extracts `request_id` for use in subsequent tests
   - Verifies request creation

5. **Test 1.5: Check Device Request Status**
   - Tests status checking with valid request_id
   - Verifies returned status and request details

6. **Test 1.6: Direct Submit (Alternative Method)**
   - Tests direct submission without draft
   - Verifies alternative workflow path

#### Section 2: Error Handling Tests
Tests various error cases and validation:

1. **Test 2.1: Invalid Device ID**
   - Tests with non-existent device ID (999)
   - Verifies error message

2. **Test 2.2: Device Name Mismatch**
   - Tests with correct device_id but wrong device_name
   - Verifies validation catches mismatch

3. **Test 2.3: Empty Employee ID**
   - Tests with empty string employee_id
   - Verifies validation

4. **Test 2.4: Invalid Request ID (Status Check)**
   - Tests status check with non-existent request_id
   - Verifies error handling

5. **Test 2.5: Invalid Draft ID (Submit Draft)**
   - Tests submitting non-existent draft
   - Verifies error handling

6. **Test 2.6: Negative Device ID**
   - Tests with negative device_id
   - Verifies validation

#### Section 3: Agent Interaction Tests
Tests the agent's ability to handle user queries:

1. **Test 3.1: Agent - List Available Devices**
   - User query: "What devices are available for request?"
   - Verifies agent calls correct tool and formats response

2. **Test 3.2: Agent - Create Draft Request**
   - User query: "I would like to request a 27-inch Monitor. Please create a draft for me."
   - Verifies agent workflow: get devices → create draft → present to user

3. **Test 3.3: Agent - Check Request Status**
   - User query: "What is the status of my device request {request_id}?"
   - Verifies agent calls status check tool correctly

4. **Test 3.4: Agent - List My Drafts**
   - User query: "Show me all my draft device requests"
   - Verifies agent lists drafts and summarizes results

#### Section 4: Full Workflow Tests
Tests complete end-to-end workflows:

1. **Test 4.1: Complete Workflow - Draft to Submit**
   - Multi-step workflow:
     1. User asks about devices
     2. User requests specific device
     3. User confirms and submits draft
   - Verifies entire preferred workflow path

2. **Test 4.2: Direct Submit Workflow**
   - User explicitly requests direct submission
   - Verifies alternative workflow path

#### Section 5: Edge Cases and Validation
Tests edge cases and boundary conditions:

1. **Test 5.1: Multiple Drafts**
   - Creates multiple drafts for same employee
   - Verifies all drafts are stored and listed correctly

2. **Test 5.2: Submit Already Submitted Draft**
   - Attempts to submit a draft that's already been submitted
   - Verifies error handling prevents duplicate submission

3. **Test 5.3: Wrong Employee ID for Draft Submission**
   - Attempts to submit draft with wrong employee_id
   - Verifies security validation

#### Section 6: Summary and Cleanup
- Test summary and notes
- Production considerations
- Cleanup recommendations

### Running the Tests

1. **Prerequisites**:
   - Jupyter notebook environment
   - Python dependencies installed
   - OpenAI API key set in environment (`.env` file)
   - Project root in Python path

2. **Execution**:
   - Run cells sequentially from top to bottom
   - Some tests depend on variables from previous tests (e.g., `draft_id`, `request_id`)
   - Agent tests require API calls (may incur costs)

3. **Expected Outputs**:
   - Direct tool tests: JSON responses with success/error messages
   - Agent tests: Natural language responses with tool call traces
   - Error tests: JSON error messages
   - Workflow tests: Multi-step interactions with intermediate states

### Test Coverage

The test suite covers:
- ✅ All 6 tool functions
- ✅ All error conditions
- ✅ Agent interaction patterns
- ✅ Complete workflows (draft → submit)
- ✅ Edge cases (multiple drafts, duplicate submission, wrong employee)
- ✅ Validation logic (device ID, name matching, empty fields)

### Notes for Production

The notebook includes notes about production considerations:
- Current implementation uses in-memory storage (data lost on restart)
- Production should use persistent database
- Need proper cleanup between test runs
- Request status updates (approved/rejected) not yet implemented
- Consider adding more comprehensive error handling

---

## Key Differences from Leave Agent

While the Device Agent follows similar patterns to the Leave Agent, there are key differences:

1. **No Date/Time Logic**: 
   - Device requests don't involve dates or day calculations
   - Simpler validation (just device_id and device_name matching)

2. **Device Catalog**: 
   - Fixed catalog of 8 devices (vs. dynamic leave balances)
   - Device information includes cost (important for budget tracking)

3. **No Balance Checking**: 
   - No equivalent to leave balance validation
   - Device requests are always allowed (subject to manager approval)

4. **Simpler Workflow**: 
   - No date range calculations
   - No automatic day counting
   - Focus is on device selection and validation

---

## Production Considerations

### Current Limitations (Prototype)

1. **In-Memory Storage**:
   - All data lost on restart
   - Not suitable for production
   - **Solution**: Migrate to SQLite (like claims) or PostgreSQL

2. **No Request Status Updates**:
   - Requests remain "pending" forever
   - No approval/rejection mechanism
   - **Solution**: Add status update functions and manager interface

3. **Hardcoded Employee ID**:
   - Agent instructions hardcode "mark_tan"
   - **Solution**: Make employee_id dynamic (from session/authentication)

4. **No Cost Tracking**:
   - Device cost stored but not aggregated
   - No budget checking
   - **Solution**: Add budget validation and cost aggregation

5. **No Device Inventory**:
   - No tracking of available stock
   - **Solution**: Add inventory management

### Recommended Enhancements

1. **Database Migration**:
   ```python
   # Similar to claims_tools.py structure
   - SQLite database for persistence
   - Context manager for connections
   - Proper schema with indexes
   ```

2. **Request Status Management**:
   ```python
   - update_device_request_status(request_id, new_status)
   - list_all_requests(employee_id, status_filter)
   - manager approval workflow
   ```

3. **Cost and Budget**:
   ```python
   - check_budget(employee_id, device_cost)
   - get_total_pending_cost(employee_id)
   - department budget limits
   ```

4. **Device Inventory**:
   ```python
   - check_device_availability(device_id)
   - update_inventory(device_id, quantity)
   - low stock alerts
   ```

5. **Enhanced Validation**:
   ```python
   - employee_exists(employee_id)
   - device_category_restrictions
   - approval workflow rules
   ```

---

## File Structure

```
src/
├── agents/
│   └── smol_device_agent.py      # Agent layer (natural language interface)
├── tools/
│   └── device_tools.py            # Business logic layer (core functions)
├── tests/
│   └── test_device_agent.ipynb    # Comprehensive test suite
└── readme/
    └── device.md                  # This documentation file
```

---

## Quick Reference

### Tool Functions Summary

| Function | Purpose | Parameters | Returns |
|----------|---------|------------|---------|
| `get_available_devices()` | List device catalog | None | JSON array of devices |
| `draft_device_request()` | Create draft request | employee_id, device_id, device_name | Draft JSON with draft_id |
| `submit_draft_device_request()` | Submit draft | employee_id, draft_id | Success JSON with request_id |
| `submit_device_request()` | Direct submit | employee_id, device_id, device_name | Success JSON with request_id |
| `list_device_drafts()` | List employee drafts | employee_id | JSON with drafts array |
| `check_device_request_status()` | Check request status | request_id | Status JSON or error |

### ID Formats

- **Request ID**: `MW{5-digit}` (e.g., "MW42176")
- **Draft ID**: `draft-{5-digit}` (e.g., "draft-90845")
- **Device ID**: Integer 1-8 (from catalog)

### Common Workflows

**Preferred Workflow (Draft → Submit)**:
1. User: "What devices are available?"
2. Agent: Shows device catalog
3. User: "I want a Mechanical Keyboard"
4. Agent: Creates draft, shows draft_id and cost
5. User: "Yes, submit it"
6. Agent: Submits draft, returns request_id

**Alternative Workflow (Direct Submit)**:
1. User: "I need a Webcam 1080p immediately, submit it directly"
2. Agent: Submits directly, returns request_id

---

## Troubleshooting

### Common Issues

1. **"Device name mismatch" error**:
   - **Cause**: device_id and device_name don't match catalog
   - **Solution**: Agent should use `get_available_devices()` to verify before creating draft

2. **"Draft not found" error**:
   - **Cause**: Draft_id doesn't exist or was already submitted
   - **Solution**: Use `list_device_drafts()` to see available drafts

3. **"Request not found" error**:
   - **Cause**: Request_id doesn't exist
   - **Solution**: Verify request_id format (MW{5-digit}) and check it was created

4. **Agent not calling tools**:
   - **Cause**: Instructions not clear or query ambiguous
   - **Solution**: Be more explicit in user query or check agent instructions

### Debug Tips

1. **Check tool outputs directly**:
   ```python
   from src.tools import device_tools as dt
   result = dt.get_available_devices()
   print(json.loads(result))
   ```

2. **Verify agent tools**:
   ```python
   from src.agents.smol_device_agent import device_smol_agent
   print([tool.__name__ for tool in device_smol_agent.tools])
   ```

3. **Test with simple query**:
   ```python
   response = device_smol_agent.run("What devices can I request?")
   print(response)
   ```

---

## Learning Resources

### For New Developers

1. **Start with**: `test_device_agent.ipynb` - Run the tests to see how everything works
2. **Read**: `device_tools.py` - Understand the core business logic
3. **Study**: `smol_device_agent.py` - See how agent wraps tools
4. **Compare**: `leave.md` - See similar patterns in leave agent

### Key Concepts

1. **Agent-Tool Pattern**: Agent provides natural language interface, tools provide business logic
2. **Draft-Submit Workflow**: Preferred pattern for user review before submission
3. **Validation First**: Always validate inputs before processing
4. **Error Handling**: Return JSON errors, don't raise exceptions
5. **Type Safety**: Use type hints for better code clarity

---

## Version History

- **v1.0** (Current): Initial implementation
  - Basic device request workflow
  - Draft and submit functionality
  - Status checking
  - In-memory storage (prototype)

---

## Contact and Support

For questions or issues:
1. Review this documentation
2. Check `test_device_agent.ipynb` for examples
3. Compare with `leave.md` for similar patterns
4. Review code comments in source files

---

*Last Updated: Based on current codebase state*
*Documentation Version: 1.0*

