from smolagents import (
    CodeAgent,
    ToolCallingAgent,
    InferenceClientModel,
    WebSearchTool
)
from src.agents.smol_base import get_smol_model

# Import your existing "worker" agents
from src.agents.smol_leave_agent import leave_smol_agent
from src.agents.smol_device_agent import device_smol_agent
from src.agents.smol_claims_agent import claims_smol_agent


manager_instructions = manager_instructions = """
You are the **SimpliAsk HR Manager**. Delegate requests to these specialists:

### SPECIALISTS & REQUIREMENTS
1. `leave_specialist`: **REQUIRES 'start_date', 'end_date', 'leave_type'.**
2. `claims_specialist`: **REQUIRES 'medical_provider', 'receipt_date', 'receipt_amount'.**
3. `device_specialist`: **REQUIRES 'device_name'.**

### RULES
1. **MEMORY**: Read previous messages. If the user said "Dec 8th" before, and "Medical" now, combine them.
2. **NO PRINT**: Never use `print()`. It causes a crash.
3. **CLARIFY**: If missing requirements, use `final_answer("Question")`.
"""

manager_agent = CodeAgent(
    tools=[], # The manager doesn't need low-level tools, it delegates to agents
    managed_agents=[leave_smol_agent, claims_smol_agent, device_smol_agent],
    model=get_smol_model(),
    name="hr_manager",
    description="The main HR interface that coordinates specialist agents.",
    instructions=manager_instructions
)