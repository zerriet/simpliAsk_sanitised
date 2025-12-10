"""
Audit Trail System for Agent Workflows

Simulates Apache Kafka-style audit logging using SQLite.
Provides a clean, structured way to log all agent interactions, tool calls, and responses.
"""

import sqlite3
import json
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path
import threading

# Thread-local storage for database connections
_local = threading.local()


class AuditTrail:
    """Manages audit trail logging to SQLite database."""
    
    def __init__(self, db_path: str = "audit_trail.db"):
        """
        Initialize the audit trail system.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(_local, 'connection'):
            _local.connection = sqlite3.connect(
                self.db_path,
                check_same_thread=False,
                timeout=10.0
            )
            _local.connection.row_factory = sqlite3.Row
        return _local.connection
    
    def _init_database(self):
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # Main audit log table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                user_message TEXT,
                agent_response TEXT,
                employee_id TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Tool calls table (for detailed tool execution tracking)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tool_calls (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_log_id INTEGER,
                tool_name TEXT NOT NULL,
                tool_params TEXT,
                tool_result TEXT,
                execution_time_ms REAL,
                success BOOLEAN,
                error_message TEXT,
                FOREIGN KEY (audit_log_id) REFERENCES audit_log(id)
            )
        """)
        
        # Agent delegation table (tracks manager -> specialist routing)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_delegations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                audit_log_id INTEGER,
                from_agent TEXT NOT NULL,
                to_agent TEXT NOT NULL,
                delegation_reason TEXT,
                FOREIGN KEY (audit_log_id) REFERENCES audit_log(id)
            )
        """)
        
        # Create indexes for common queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id ON audit_log(session_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON audit_log(timestamp)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_agent_name ON audit_log(agent_name)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_employee_id ON audit_log(employee_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_log_id ON tool_calls(audit_log_id)
        """)
        
        conn.commit()
    
    def log_request(
        self,
        session_id: str,
        agent_name: str,
        user_message: str,
        employee_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Log a user request to an agent.
        
        Args:
            session_id: Unique session/conversation identifier
            agent_name: Name of the agent handling the request
            user_message: The user's input message
            employee_id: Employee ID if available
            metadata: Additional metadata as dictionary
            
        Returns:
            audit_log_id: The ID of the created audit log entry
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.utcnow().isoformat()
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            INSERT INTO audit_log (
                session_id, timestamp, agent_name, event_type,
                user_message, employee_id, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session_id, timestamp, agent_name, "request",
            user_message, employee_id, metadata_json
        ))
        
        conn.commit()
        return cursor.lastrowid
    
    def log_response(
        self,
        audit_log_id: int,
        agent_response: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log an agent's response to a request.
        
        Args:
            audit_log_id: The audit log ID from the original request
            agent_response: The agent's response text
            metadata: Additional metadata
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute("""
            UPDATE audit_log
            SET agent_response = ?, metadata = ?
            WHERE id = ?
        """, (agent_response, metadata_json, audit_log_id))
        
        conn.commit()
    
    def log_tool_call(
        self,
        audit_log_id: int,
        tool_name: str,
        tool_params: Optional[Dict[str, Any]] = None,
        tool_result: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ):
        """
        Log a tool call execution.
        
        Args:
            audit_log_id: The audit log ID this tool call belongs to
            tool_name: Name of the tool that was called
            tool_params: Parameters passed to the tool
            tool_result: Result returned by the tool
            execution_time_ms: Execution time in milliseconds
            success: Whether the tool call succeeded
            error_message: Error message if the call failed
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        params_json = json.dumps(tool_params) if tool_params else None
        
        cursor.execute("""
            INSERT INTO tool_calls (
                audit_log_id, tool_name, tool_params, tool_result,
                execution_time_ms, success, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            audit_log_id, tool_name, params_json, tool_result,
            execution_time_ms, success, error_message
        ))
        
        conn.commit()
    
    def log_delegation(
        self,
        audit_log_id: int,
        from_agent: str,
        to_agent: str,
        delegation_reason: Optional[str] = None
    ):
        """
        Log agent delegation (manager -> specialist).
        
        Args:
            audit_log_id: The audit log ID this delegation belongs to
            from_agent: Name of the agent doing the delegation
            to_agent: Name of the agent being delegated to
            delegation_reason: Reason for delegation (optional)
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO agent_delegations (
                audit_log_id, from_agent, to_agent, delegation_reason
            ) VALUES (?, ?, ?, ?)
        """, (audit_log_id, from_agent, to_agent, delegation_reason))
        
        conn.commit()
    
    def get_session_history(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit history for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of records to return
            
        Returns:
            List of audit log entries with tool calls
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM audit_log
            WHERE session_id = ?
            ORDER BY timestamp DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, (session_id,))
        rows = cursor.fetchall()
        
        results = []
        for row in rows:
            entry = dict(row)
            
            # Get tool calls for this entry
            cursor.execute("""
                SELECT * FROM tool_calls
                WHERE audit_log_id = ?
                ORDER BY id
            """, (entry['id'],))
            tool_calls = [dict(tc) for tc in cursor.fetchall()]
            entry['tool_calls'] = tool_calls
            
            # Get delegations for this entry
            cursor.execute("""
                SELECT * FROM agent_delegations
                WHERE audit_log_id = ?
            """, (entry['id'],))
            delegations = [dict(d) for d in cursor.fetchall()]
            entry['delegations'] = delegations
            
            # Parse JSON fields
            if entry['metadata']:
                entry['metadata'] = json.loads(entry['metadata'])
            for tc in tool_calls:
                if tc['tool_params']:
                    tc['tool_params'] = json.loads(tc['tool_params'])
            
            results.append(entry)
        
        return results
    
    def get_employee_audit_trail(
        self,
        employee_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit trail for a specific employee.
        
        Args:
            employee_id: Employee identifier
            limit: Maximum number of records to return
            
        Returns:
            List of audit log entries
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT * FROM audit_log
            WHERE employee_id = ?
            ORDER BY timestamp DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, (employee_id,))
        rows = cursor.fetchall()
        
        return [dict(row) for row in rows]
    
    def close(self):
        """Close database connections."""
        if hasattr(_local, 'connection'):
            _local.connection.close()
            delattr(_local, 'connection')


# Global audit trail instance
_audit_trail = None


def get_audit_trail(db_path: str = "audit_trail.db") -> AuditTrail:
    """
    Get or create the global audit trail instance.
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        AuditTrail instance
    """
    global _audit_trail
    if _audit_trail is None:
        _audit_trail = AuditTrail(db_path)
    return _audit_trail


def reset_audit_trail():
    """Reset the global audit trail instance (useful for testing)."""
    global _audit_trail
    if _audit_trail is not None:
        _audit_trail.close()
    _audit_trail = None


def generate_session_id() -> str:
    """Generate a unique session ID for a conversation."""
    return f"session_{uuid.uuid4().hex[:12]}"

