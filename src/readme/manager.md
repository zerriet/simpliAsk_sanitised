# Manager Agent System Documentation

## Overview

The Manager Agent System is the central coordination layer for the SimpliAsk HR system, built using `smolagents`. It acts as an intelligent router that delegates user requests to specialized agents (leave, claims, and device specialists) based on the nature of the request. The manager maintains conversation context, handles clarification requests, and ensures proper delegation to the appropriate specialist.

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interaction                          │
│              (Natural Language Queries)                     │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│              manager_agent.py                                │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  CodeAgent (hr_manager)                               │  │
│  │  - Model: gpt-4.1-mini (via smol_base)               │  │
│  │  - Instructions: manager_instructions                  │  │
│  │  - Tools: [] (delegates via managed_agents)           │  │
│  │  - Managed Agents: 3 specialist agents                 │  │
│  └──────────────────────────────────────────────────────┘  │
└───────┬───────────────┬───────────────┬─────────────────────┘
        │               │               │
        ▼               ▼               ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ leave_smol_ │ │claims_smol_   │ │device_smol_ │
│   agent      │ │   agent       │ │   agent      │
│              │ │               │ │              │
│ (leave_      │ │ (claims_      │ │ (device_     │
│  specialist) │ │  specialist)  │ │  specialist)  │
└──────────────┘ └──────────────┘ └──────────────┘
```

---

## 1. manager_agent.py

### Purpose

The manager agent serves as the main entry point for all HR-related requests. It intelligently routes requests to the appropriate specialist agent based on the user's intent, maintains conversation context across multiple turns, and handles clarification when information is missing.

### Key Components

#### Agent Configuration

- **Name**: `hr_manager`
- **Model**: `gpt-4.1-mini` (via `get_smol_model()` from `smol_base.py`)
- **Framework**: `smolagents.CodeAgent`
- **Tools**: `[]` (empty - delegates to managed agents)
- **Managed Agents**: 3 specialist agents
  - `leave_smol_agent` (leave_specialist)
  - `claims_smol_agent` (claims_specialist)
  - `device_smol_agent` (device_specialist)

#### Agent Instructions (`manager_instructions`)

The manager follows a structured set of rules for delegation and coordination:

**1. Available Specialists**

- **`leave_specialist`**: Handles leave-related requests
  - Leave balance inquiries
  - Drafting and submitting leave requests (annual, medical, family leave)
  - Checking leave request status
  - Listing draft leave requests
  - **Key Requirements**: For creating leave requests, needs `start_date` (YYYY-MM-DD), `end_date` (YYYY-MM-DD), and `leave_type`

- **`claims_specialist`**: Handles medical reimbursement claims
  - Listing past medical claims
  - Drafting medical claims from receipt information
  - Updating draft claims
  - Submitting medical claims
  - **Key Requirements**: For creating claims, needs `medical_provider`, `receipt_date` (YYYY-MM-DD), `receipt_amount`, `receipt_no`, `diagnosis`, and `gst_inclusive` (boolean)

- **`device_specialist`**: Handles IT device requests
  - Browsing available devices
  - Drafting and submitting device requests
  - Checking device request status
  - Listing draft device requests
  - **Key Requirements**: For device requests, needs `device_name` (or `device_id`)

**2. Delegation Rules**

1. **Context Awareness**
   - Reads entire conversation history to understand context
   - Combines information from multiple messages (e.g., "Dec 8th" earlier, "Medical leave" now)
   - Maintains conversation continuity across multiple turns

2. **Clarification**
   - Uses `final_answer()` to ask for clarification when information is missing
   - Be specific about what information is needed
   - Doesn't delegate to specialists with incomplete information

3. **Delegation**
   - Delegates to appropriate specialist based on user's request
   - Lets specialist handle detailed workflow (drafting, confirmation, submission)
   - Trusts specialist's instructions and tools

4. **Code Restrictions**
   - **NEVER uses `print()`** - causes crashes in this environment
   - Uses `final_answer()` to communicate with user directly when needed

**3. Workflow Examples**

- User: "I want to apply for 5 days of annual leave starting Dec 4th"
  → Delegate to `leave_specialist` (they will handle asking for end date if needed)

- User: "Check my leave balance"
  → Delegate to `leave_specialist`

- User: "I need a new keyboard"
  → Delegate to `device_specialist` (they will show available devices)

- User: "Submit this medical claim" (with receipt details)
  → Delegate to `claims_specialist` (they will extract and confirm details)

**4. Current Employee Context**

- Default Employee ID: `mark_tan`
- All specialists are configured to use this employee ID by default

### Implementation Details

#### Code Structure

```python
from smolagents import CodeAgent
from src.agents.smol_base import get_smol_model

# Import specialist agents
from src.agents.smol_leave_agent import leave_smol_agent
from src.agents.smol_device_agent import device_smol_agent
from src.agents.smol_claims_agent import claims_smol_agent

manager_agent = CodeAgent(
    tools=[],  # No direct tools - delegates to managed agents
    managed_agents=[leave_smol_agent, claims_smol_agent, device_smol_agent],
    model=get_smol_model(),
    name="hr_manager",
    description="The main HR interface that coordinates specialist agents...",
    instructions=manager_instructions
)
```

#### Key Design Decisions

1. **No Direct Tools**: Manager doesn't have domain-specific tools. It relies entirely on delegation to specialist agents.

2. **CodeAgent Framework**: Uses `CodeAgent` instead of `ToolCallingAgent` because it's designed for managing and coordinating other agents.

3. **Default Tools**: `CodeAgent` automatically provides default tools like `final_answer()` for direct user communication.

4. **Context Preservation**: The manager maintains conversation history to enable multi-turn interactions where information is provided incrementally.

### How It Works

1. **User Query Reception**: Manager receives natural language query from user
2. **Intent Recognition**: Analyzes query to determine which specialist should handle it
3. **Context Building**: Combines current query with conversation history
4. **Information Check**: Verifies if required information is present
5. **Clarification or Delegation**:
   - If information missing → Uses `final_answer()` to ask for clarification
   - If information complete → Delegates to appropriate specialist
6. **Response Return**: Returns specialist's response to user

---

## 2. test_manager_agent.ipynb

### Purpose

The test notebook provides comprehensive testing for the manager agent, verifying:
- Correct delegation to each specialist
- Context awareness across multiple turns
- Clarification handling
- Error handling
- Complete workflow execution

### Test Structure

#### Setup (Cells 0-2)

1. **Cell 0**: Markdown introduction describing test coverage
2. **Cell 1**: Environment setup
   - Project root detection
   - Python path configuration
   - Environment variable loading (OPENAI_API_KEY)
3. **Cell 2**: Manager agent import and configuration verification
   - Verifies agent name, description
   - Lists managed agents
   - Shows tool count (may include default tools)

#### Test Section 1: Delegation to Leave Specialist (Cells 3-9)

**Test 1.1: Check Leave Balance**
- Verifies manager delegates leave balance queries to `leave_specialist`
- Query: "How many days of annual leave do I have left?"

**Test 1.2: Create Leave Request with Complete Information**
- Verifies manager delegates complete leave requests
- Query: "I want to apply for 3 days of annual leave from 2025-12-15 to 2025-12-17"

**Test 1.3: Leave Request with Missing Information**
- Verifies manager asks for clarification or delegates to specialist who will ask
- Query: "I want to apply for 5 days of annual leave" (missing dates)

#### Test Section 2: Delegation to Device Specialist (Cells 10-14)

**Test 2.1: Browse Available Devices**
- Verifies manager delegates device browsing to `device_specialist`
- Query: "What devices can I request?"

**Test 2.2: Request a Specific Device**
- Verifies manager delegates device requests
- Query: "I need a new wireless mouse"

#### Test Section 3: Delegation to Claims Specialist (Cells 15-19)

**Test 3.1: List Past Claims**
- Verifies manager delegates claims listing to `claims_specialist`
- Query: "Show me all my medical claims"

**Test 3.2: Create Medical Claim**
- Verifies manager delegates medical claim creation
- Query: Includes receipt details (provider, date, amount, etc.)

#### Test Section 4: Context Awareness (Cells 20-24)

**Test 4.1: Multi-turn Leave Request**
- Tests context preservation across multiple turns
- Turn 1: "I want to take leave starting December 8th"
- Turn 2: "It's for medical leave"
- Turn 3: "Until December 10th"
- Expected: Manager combines information from all turns

**Test 4.2: Switching Between Different Request Types**
- Tests context switching between different specialists
- Sequence: Leave balance → Device request → Claims listing
- Expected: Manager correctly routes each request to appropriate specialist

#### Test Section 5: Error Handling and Edge Cases (Cells 25-31)

**Test 5.1: Ambiguous Request**
- Tests handling of vague requests
- Query: "I need help"
- Expected: Manager asks for clarification or offers options

**Test 5.2: Invalid Date Format**
- Tests delegation of invalid input handling
- Query: "I want to apply for leave from 12/15/2025 to 12/20/2025"
- Expected: Manager delegates, specialist handles validation

**Test 5.3: Request for Non-existent Resource**
- Tests error handling for invalid IDs
- Query: "What's the status of my leave request ABC123?"
- Expected: Manager delegates, specialist handles error

#### Test Section 6: Complete Workflow Tests (Cells 32-36)

**Test 6.1: Complete Leave Workflow**
- End-to-end test of leave request through manager
- Step 1: Check balance
- Step 2: Create draft with dates
- Expected: Manager coordinates complete workflow

**Test 6.2: Complete Device Workflow**
- End-to-end test of device request through manager
- Step 1: Browse devices
- Step 2: Request specific device
- Expected: Manager coordinates complete workflow

#### Test Section 7: Summary and Test Results (Cells 37-38)

**Test Summary Cell**
- Automated verification of:
  1. Manager agent configuration (name, managed agents count)
  2. Delegation to leave_specialist
  3. Delegation to device_specialist
  4. Delegation to claims_specialist
- Reports passed/failed tests
- Provides test results summary

### Running the Tests

1. **Prerequisites**:
   - Jupyter notebook environment
   - `OPENAI_API_KEY` environment variable set
   - All dependencies installed (smolagents, python-dotenv, etc.)

2. **Execution**:
   - Run cells sequentially from top to bottom
   - Each test cell can be run independently
   - Summary cell (Cell 38) provides overall test status

3. **Expected Output**:
   - Each test prints user query and manager response
   - Summary shows count of passed/failed tests
   - All core functionality tests should pass

### Test Coverage

✅ **Delegation Tests**: All three specialists tested
✅ **Context Awareness**: Multi-turn conversations tested
✅ **Clarification**: Missing information handling tested
✅ **Error Handling**: Invalid inputs and edge cases tested
✅ **Workflow Tests**: Complete end-to-end workflows tested
✅ **Configuration**: Agent setup and structure verified

---

## 3. Key Features

### 3.1 Intelligent Routing

The manager automatically determines which specialist should handle each request based on:
- Keywords in the query (leave, device, claim, etc.)
- Request type (inquiry, creation, status check)
- Required information availability

### 3.2 Context Preservation

The manager maintains conversation history, enabling:
- **Multi-turn interactions**: User can provide information incrementally
- **Context combination**: "Dec 8th" + "Medical leave" = complete request
- **Conversation continuity**: Follow-up questions reference previous context

### 3.3 Clarification Handling

When required information is missing:
- Manager uses `final_answer()` to ask specific questions
- Doesn't delegate incomplete requests
- Provides clear guidance on what's needed

### 3.4 Error Resilience

- Delegates error handling to specialists (they know best how to validate)
- Handles ambiguous requests gracefully
- Provides helpful error messages

---

## 4. Usage Examples

### Example 1: Simple Leave Balance Check

```
User: "How many days of annual leave do I have?"
Manager: [Delegates to leave_specialist]
Response: "You have 14 days of annual leave remaining."
```

### Example 2: Multi-turn Leave Request

```
User: "I want to take leave starting December 8th"
Manager: "What type of leave would you like to apply for?"

User: "It's for medical leave"
Manager: "How many days of medical leave do you need, or what is the end date?"

User: "Until December 10th"
Manager: [Delegates to leave_specialist with complete information]
Response: "I've created a draft leave request for 3 days of medical leave..."
```

### Example 3: Device Request

```
User: "I need a new keyboard"
Manager: [Delegates to device_specialist]
Response: [Device specialist shows available keyboards and creates draft]
```

### Example 4: Switching Context

```
User: "Check my annual leave balance"
Manager: [Delegates to leave_specialist]
Response: "You have 14 days of annual leave remaining."

User: "Actually, I also need a new mouse"
Manager: [Delegates to device_specialist]
Response: [Device specialist handles mouse request]
```

---

## 5. Integration with Specialist Agents

### 5.1 Leave Specialist Integration

- **Trigger Keywords**: "leave", "annual", "medical", "family", "vacation", "time off"
- **Delegation Points**: Balance checks, leave requests, status inquiries, draft management
- **Information Required**: start_date, end_date, leave_type

### 5.2 Claims Specialist Integration

- **Trigger Keywords**: "claim", "medical", "receipt", "reimbursement", "expense"
- **Delegation Points**: Claim listing, claim creation, claim updates, claim submission
- **Information Required**: medical_provider, receipt_date, receipt_amount, receipt_no, diagnosis, gst_inclusive

### 5.3 Device Specialist Integration

- **Trigger Keywords**: "device", "equipment", "peripheral", "mouse", "keyboard", "monitor", "cable"
- **Delegation Points**: Device browsing, device requests, status checks, draft management
- **Information Required**: device_name or device_id

---

## 6. Best Practices

### 6.1 For Developers

1. **Adding New Specialists**:
   - Import the specialist agent
   - Add to `managed_agents` list
   - Update `manager_instructions` with specialist details
   - Add test cases in test notebook

2. **Modifying Instructions**:
   - Keep instructions clear and specific
   - Include examples for each specialist
   - Document required information for each specialist
   - Update workflow examples when adding features

3. **Testing**:
   - Test each specialist delegation separately
   - Test context awareness with multi-turn conversations
   - Test error handling and edge cases
   - Verify complete workflows end-to-end

### 6.2 For Users

1. **Be Specific**: Provide as much information as possible in initial request
2. **Follow Prompts**: When manager asks for clarification, provide the requested information
3. **Context Awareness**: You can provide information across multiple messages
4. **Request Types**: Manager handles leave, device, and claims requests

---

## 7. Known Limitations

1. **No Direct Tool Access**: Manager cannot directly access tool functions - must delegate
2. **Context Window**: Conversation history is limited by model's context window
3. **Specialist Dependency**: Manager's effectiveness depends on specialist agents' capabilities
4. **Error Propagation**: Errors from specialists are passed through to user
5. **No Cross-Specialist Coordination**: Cannot coordinate requests that span multiple specialists

---

## 8. Future Enhancements

### Potential Improvements

1. **Priority Routing**: Handle urgent requests differently
2. **Request Batching**: Allow multiple requests in single query
3. **Cross-Specialist Queries**: Handle queries that need multiple specialists
4. **Analytics**: Track delegation patterns and common queries
5. **Caching**: Cache common queries (like leave balance) for faster responses
6. **User Preferences**: Remember user preferences (default leave type, etc.)
7. **Multi-Employee Support**: Handle requests for different employees
8. **Approval Workflow Integration**: Coordinate with approval systems

---

## 9. Troubleshooting

### Common Issues

**Issue**: Manager doesn't delegate correctly
- **Check**: Verify specialist agents are properly imported
- **Check**: Ensure specialist names match in instructions
- **Solution**: Review manager_instructions for correct specialist references

**Issue**: Context not preserved across turns
- **Check**: Verify conversation history is being maintained
- **Solution**: Ensure manager agent instance persists across turns

**Issue**: Manager asks for clarification unnecessarily
- **Check**: Review specialist requirements in instructions
- **Solution**: Update instructions to be more permissive or improve specialist handling

**Issue**: Errors not handled gracefully
- **Check**: Verify specialists return proper error formats
- **Solution**: Add error handling in manager instructions

---

## 10. Related Documentation

- **Leave Agent**: See `src/readme/leave.md` for leave specialist details
- **Device Agent**: See `src/readme/device.md` for device specialist details
- **Claims Agent**: See `src/readme/claims.md` for claims specialist details
- **Base Configuration**: See `src/agents/smol_base.py` for model configuration

---

## 11. Summary

The Manager Agent is the central coordination layer for SimpliAsk HR system. It provides:

- ✅ Intelligent routing to specialist agents
- ✅ Context-aware multi-turn conversations
- ✅ Clarification handling for incomplete requests
- ✅ Seamless user experience across all HR functions
- ✅ Extensible architecture for adding new specialists

The manager agent enables users to interact with the HR system using natural language, with the manager handling the complexity of routing and coordination behind the scenes.

