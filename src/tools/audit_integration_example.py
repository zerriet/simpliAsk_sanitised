"""
Example integration of audit trail logging into the agent workflow.

This shows how to integrate audit logging into your dual_agent_smol.ipynb notebook.
"""

from src.tools.audit_trail import get_audit_trail, generate_session_id
from src.tools.audit_helper import log_agent_interaction, extract_employee_id_from_message
import re
import time


# Global session tracking (you can make this more sophisticated)
_current_session = None


def get_or_create_session():
    """Get current session ID or create a new one."""
    global _current_session
    if _current_session is None:
        _current_session = generate_session_id()
    return _current_session


def reset_session():
    """Reset the current session (useful for new conversations)."""
    global _current_session
    _current_session = None


def unified_chat_with_audit(message, history):
    """
    Enhanced unified_chat function with audit trail logging.
    
    This is a modified version of the unified_chat function from dual_agent_smol.ipynb
    that includes audit trail logging.
    """
    from src.agents.manager_agent import manager_agent
    
    # Build context (same as original)
    def build_context(message, history):
        """Build conversation context from message and history for the manager agent."""
        if not history:
            return message
        parts = []
        for h in history:
            if isinstance(h, dict):
                role = h.get('role', 'user')
                content = h.get('content', '')
                if isinstance(content, list):
                    text_parts = [item.get('text', '') for item in content if isinstance(item, dict)]
                    content = ' '.join(text_parts)
                parts.append(f"{role}: {content}")
            else:
                parts.append(str(h))
        parts.append(f"user: {message}")
        return "\n".join(parts)
    
    def clean_response(response):
        """Clean up verbose formatting from manager agent responses."""
        if not isinstance(response, str):
            return response
        
        original_response = response
        
        if "Here is the final answer from your managed agent" in response:
            cleaned = re.sub(
                r"Here is the final answer from your managed agent '[^']+':\s*", 
                "", 
                response, 
                flags=re.IGNORECASE
            )
            cleaned = re.sub(r'### \d+\. Task outcome \([^)]+\):\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r'### \d+\. Additional context[^\n]*:\s*', '', cleaned, flags=re.IGNORECASE)
            
            if "### 1. Task outcome (short version)" in original_response:
                short_match = re.search(
                    r'### 1\. Task outcome \(short version\):\s*(.+?)(?=\n\n### \d+\.|$)', 
                    original_response, 
                    re.DOTALL | re.IGNORECASE
                )
                if short_match:
                    short_content = short_match.group(1).strip()
                    if '\n' in short_content or '[' in short_content or '{' in short_content:
                        return short_content
                    detailed_match = re.search(
                        r'### 2\. Task outcome \(extremely detailed version\):\s*(.+?)(?=\n\n### \d+\.|$)', 
                        original_response, 
                        re.DOTALL | re.IGNORECASE
                    )
                    if detailed_match:
                        detailed_content = detailed_match.group(1).strip()
                        if len(short_content) < 100 and len(detailed_content) > len(short_content):
                            return detailed_content
                    return short_content
            
            return cleaned.strip()
        
        cleaned = re.sub(r'### \d+\. Task outcome \([^)]+\):\s*', '', response, flags=re.IGNORECASE)
        cleaned = re.sub(r'### \d+\. Additional context[^\n]*:\s*', '', cleaned, flags=re.IGNORECASE)
        
        summary_indicators = [
            r'A (comprehensive |full |complete )?list.*has been (compiled|retrieved|gathered)',
            r'has been (successfully )?(compiled|retrieved|gathered|created)',
        ]
        
        is_likely_summary = any(re.search(pattern, cleaned, re.IGNORECASE) for pattern in summary_indicators)
        
        if is_likely_summary and len(cleaned) < 150:
            print(f"--- WARNING: Response appears to be a summary without actual content ---")
            return cleaned.strip()
        
        return cleaned.strip()
    
    # Get session ID
    session_id = get_or_create_session()
    
    # Extract employee ID (default is mark_tan as per manager_agent.py)
    employee_id = extract_employee_id_from_message(message)
    
    # Build task context
    task = build_context(message, history)
    
    # Track execution
    start_time = time.time()
    tool_calls = []
    delegations = []
    
    try:
        # Run the manager agent
        print(f"--- SYSTEM: Request handled by manager agent (Session: {session_id})")
        response = manager_agent.run(task)
        
        # Clean response
        cleaned_response = clean_response(response)
        
        # Note: To capture actual tool calls and delegations, you would need to
        # hook into smolagents' execution. This is a simplified version.
        # For full tracking, you could:
        # 1. Use smolagents' callbacks/hooks if available
        # 2. Wrap the tool functions to log their execution
        # 3. Parse the agent's execution trace
        
        execution_time = (time.time() - start_time) * 1000
        
        # Log the interaction
        log_agent_interaction(
            session_id=session_id,
            agent_name="hr_manager",
            user_message=message,
            agent_response=cleaned_response,
            employee_id=employee_id,
            tool_calls=tool_calls,  # Would be populated from actual tool execution
            delegations=delegations,  # Would be populated from actual delegations
            metadata={
                'execution_time_ms': execution_time,
                'success': True,
                'original_response_length': len(response),
                'cleaned_response_length': len(cleaned_response)
            }
        )
        
        return cleaned_response
        
    except Exception as e:
        execution_time = (time.time() - start_time) * 1000
        error_message = str(e)
        
        # Log the error
        log_agent_interaction(
            session_id=session_id,
            agent_name="hr_manager",
            user_message=message,
            agent_response=f"Error: {error_message}",
            employee_id=employee_id,
            tool_calls=[],
            delegations=[],
            metadata={
                'execution_time_ms': execution_time,
                'success': False,
                'error': error_message
            }
        )
        
        raise


# Example: How to wrap tool functions to log their execution
def create_audited_tool(original_tool_func, tool_name: str):
    """
    Create an audited version of a tool function.
    
    Usage:
        from src.tools import leave_tools as lt
        
        # Original
        result = lt.draft_leave_request(employee_id, leave_type, start_date, end_date)
        
        # Audited version
        audited_draft = create_audited_tool(lt.draft_leave_request, "draft_leave_request")
        result = audited_draft(employee_id, leave_type, start_date, end_date)
    """
    from functools import wraps
    
    @wraps(original_tool_func)
    def wrapper(*args, **kwargs):
        audit = get_audit_trail()
        session_id = get_or_create_session()
        
        # Get the most recent audit log entry for this session
        conn = audit._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id FROM audit_log
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        """, (session_id,))
        row = cursor.fetchone()
        audit_log_id = row[0] if row else None
        
        # Execute tool
        start_time = time.time()
        try:
            result = original_tool_func(*args, **kwargs)
            success = True
            error_message = None
        except Exception as e:
            result = None
            success = False
            error_message = str(e)
            raise
        finally:
            execution_time = (time.time() - start_time) * 1000
            
            # Log tool call
            if audit_log_id:
                audit.log_tool_call(
                    audit_log_id=audit_log_id,
                    tool_name=tool_name,
                    tool_params={'args': args, 'kwargs': kwargs},
                    tool_result=str(result) if result else None,
                    execution_time_ms=execution_time,
                    success=success,
                    error_message=error_message
                )
        
        return result
    
    return wrapper

