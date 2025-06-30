# In: logic/ielts_models.py

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum, auto


#  Define a SessionPhase Enum
# This creates a set of named constants to represent the session's state.
# It's safer and more descriptive than using simple strings or booleans.
class SessionPhase(Enum):
    IN_PROGRESS = auto()        # The user is actively answering questions
    PART_ENDED = auto()         # A part has just finished, user can get feedback or continue
    GENERATING_FEEDBACK = auto()  # App is calling the LLM (prevents other actions).
    TEST_COMPLETED = auto()     # The entire test is over


# Define the IELTSState dataclass
@dataclass
class IELTSState:
    """
    A structured class to hold all the state information for a single
    IELTS test session. Using a dataclass gives us type safety and
    makes our code easier to read and debug.
    """
    # We define the 'fields' of our state as class attributes with type hints.
    # This acts as our blueprint.
    
    questions: Optional[Dict[str, Any]] = None
    current_part: int = 0
    current_question_index: int = 0
    test_started: bool = False
    current_question_text: str = ""
    answers: List[str] = field(default_factory=list)
    session_phase: SessionPhase = SessionPhase.IN_PROGRESS
    feedback_reports: list[str] = field(default_factory=list)

    # This is a derived property that calculates the questions for the current part.
    @property
    def is_last_question_of_part(self) -> bool:
        """Checks if the current question is the last one in the current part."""
        if not self.test_started or self.current_part == 0:
            return False

        try:
            # Construct the key for the questions dictionary, e.g., 'part1'
            part_key = f"part{self.current_part}"
            
            # Get the list of questions for the current part
            questions_in_part = self.questions[part_key]["questions"] # type: ignore
            
            # The part is finished if the current index is the last valid index
            return self.current_question_index == len(questions_in_part) - 1
        except (KeyError, TypeError):
            # If questions are not loaded or the key is wrong, it's not finished.
            return False
