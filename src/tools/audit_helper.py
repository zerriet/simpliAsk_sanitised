"""
Helper functions for integrating audit trail logging into agent workflows.
"""

import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
from src.tools.audit_trail import get_audit_trail, generate_session_id

# Global session tracking (can be reset for new conversations)
_current_session = None


def get_or_create_session() -> str:
    """
    Get the current session ID or create a new one.
    
    Returns:
        Current session ID string
    """
    global _current_session
    if _current_session is None:
        _current_session = generate_session_id()
    return _current_session


def reset_session():
    """Reset the current session (useful for new conversations)."""
    global _current_session
    _current_session = None


def extract_employee_id_from_message(message: str) -> Optional[str]:
    """
    Try to extract employee_id from a message or context.
    This is a simple heuristic - you may want to enhance this.
    """
    # Default employee ID as per manager_agent.py
    return "mark_tan"


def log_agent_interaction(
    session_id: str,
    agent_name: str,
    user_message: str,
    agent_response: str,
    employee_id: Optional[str] = None,
    tool_calls: Optional[list] = None,
    delegations: Optional[list] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Log a complete agent interaction (request + response).
    
    Args:
        session_id: Session identifier
        agent_name: Name of the agent
        user_message: User's input
        agent_response: Agent's response
        employee_id: Employee ID if available
        tool_calls: List of tool calls made (each as dict with tool_name, params, result, etc.)
        delegations: List of delegations (each as dict with from_agent, to_agent, reason)
        metadata: Additional metadata
    """
    audit = get_audit_trail()
    
    # Extract employee_id if not provided
    if not employee_id:
        employee_id = extract_employee_id_from_message(user_message)
    
    # Log the request
    audit_log_id = audit.log_request(
        session_id=session_id,
        agent_name=agent_name,
        user_message=user_message,
        employee_id=employee_id,
        metadata=metadata
    )
    
    # Log delegations
    if delegations:
        for delegation in delegations:
            audit.log_delegation(
                audit_log_id=audit_log_id,
                from_agent=delegation.get('from_agent', agent_name),
                to_agent=delegation.get('to_agent'),
                delegation_reason=delegation.get('reason')
            )
    
    # Log tool calls
    if tool_calls:
        for tool_call in tool_calls:
            audit.log_tool_call(
                audit_log_id=audit_log_id,
                tool_name=tool_call.get('tool_name', 'unknown'),
                tool_params=tool_call.get('params'),
                tool_result=tool_call.get('result'),
                execution_time_ms=tool_call.get('execution_time_ms'),
                success=tool_call.get('success', True),
                error_message=tool_call.get('error_message')
            )
    
    # Log the response
    audit.log_response(
        audit_log_id=audit_log_id,
        agent_response=agent_response,
        metadata=metadata
    )
    
    return audit_log_id


def with_audit_logging(
    agent_name: str,
    session_id: Optional[str] = None,
    extract_employee_id: Optional[Callable[[str], Optional[str]]] = None
):
    """
    Decorator to automatically log agent interactions.
    
    Usage:
        @with_audit_logging(agent_name="hr_manager")
        def my_agent_function(message, history):
            # ... agent logic ...
            return response
    
    Args:
        agent_name: Name of the agent
        session_id: Optional session ID (will generate if not provided)
        extract_employee_id: Optional function to extract employee_id from message
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Extract message from args/kwargs
            message = args[0] if args else kwargs.get('message', '')
            history = args[1] if len(args) > 1 else kwargs.get('history', [])
            
            # Generate session_id if not provided
            current_session_id = session_id or generate_session_id()
            
            # Extract employee_id
            employee_id = None
            if extract_employee_id:
                employee_id = extract_employee_id(message)
            else:
                employee_id = extract_employee_id_from_message(message)
            
            # Track tool calls (if agent provides them)
            tool_calls = []
            delegations = []
            
            # Execute the agent function
            start_time = time.time()
            try:
                response = func(*args, **kwargs)
                success = True
                error_message = None
            except Exception as e:
                response = f"Error: {str(e)}"
                success = False
                error_message = str(e)
            execution_time = (time.time() - start_time) * 1000  # Convert to ms
            
            # Log the interaction
            # Note: For full tool call tracking, you'd need to hook into smolagents
            # This is a simplified version that logs the interaction
            log_agent_interaction(
                session_id=current_session_id,
                agent_name=agent_name,
                user_message=str(message),
                agent_response=str(response),
                employee_id=employee_id,
                tool_calls=tool_calls,
                delegations=delegations,
                metadata={
                    'execution_time_ms': execution_time,
                    'success': success,
                    'error': error_message
                }
            )
            
            return response
        return wrapper
    return decorator

