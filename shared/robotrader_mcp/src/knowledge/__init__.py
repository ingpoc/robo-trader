"""
Knowledge Management - Session persistence and learning accumulation

Provides persistent storage for Claude Code sessions to build on previous knowledge
instead of starting from zero each time.
"""

from .session_db import SessionKnowledgeDB, get_knowledge_db
from .manager import SessionKnowledgeManager, get_knowledge_manager

__all__ = [
    'SessionKnowledgeDB',
    'get_knowledge_db',
    'SessionKnowledgeManager',
    'get_knowledge_manager'
]
