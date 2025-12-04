from smolagents import ToolCallingAgent, tool
from src.agents.smol_base import get_smol_model
from src.tools import common_tools as ct


@tool
def get_available_agents_tool() -> str:
    """
    Return a list of all available agents and the workflows they support.

    Args:
        None

    Returns:
        str: A JSON string containing a list of agents with id, feature name, and description.
    """
    return ct.get_available_agents()


COMMON_INSTRUCTIONS = """
You are a helpful HR assistant for bank staff. You are tasked with helping staff with general requests
and listing workflows you can support them with.
Current Employee ID: mark_tan.

Whenever you call a tool, always include the output in your natural language response.
"""

common_smol_agent = ToolCallingAgent(
    tools=[get_available_agents_tool],
    model=get_smol_model(),
    instructions=COMMON_INSTRUCTIONS,
)
