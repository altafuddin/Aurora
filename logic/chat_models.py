# In: logic/chat_models.py
from dataclasses import dataclass
from typing import Optional, Any

@dataclass
class ChatTurn:
    """Represents a single entry (by user or AI) in a chat conversation."""
    text: str
    # The following fields are only populated for user turns
    pronunciation_report: Optional[dict[str, Any]] = None
    feedback_tip: Optional[str] = None