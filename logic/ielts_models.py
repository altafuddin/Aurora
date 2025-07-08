# In: logic/ielts_models.py

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum, auto
from pydantic import BaseModel, Field


# Define a SessionPhase Enum
# This creates a set of named constants to represent the session's state.
class SessionPhase(Enum):
    IN_PROGRESS = auto()        # The user is actively answering questions
    PART_ENDED = auto()         # A part has just finished, user can get feedback or continue
    GENERATING_FEEDBACK = auto()  # App is calling the LLM (prevents other actions).
    TEST_COMPLETED = auto()     # The entire test is over

# --- Pydantic Models for Structured LLM Feedback ---
class FeedbackCriterion(BaseModel):
    """A model to hold the detailed feedback for a single criterion (e.g., Fluency)."""
    name: str = Field(..., description="The name of the criterion, e.g., 'Fluency and Coherence'")
    strength: str = Field(..., description="The specific strength identified by the LLM.")
    improvement_area: str = Field(..., description="The specific area for improvement.")

class OverallSummary(BaseModel):
    """A model for the overall summary section of the feedback."""
    part_assessed: str = Field(..., description="The part of the test being assessed, e.g., 'Part 1'")
    positive_highlight: str = Field(..., description="A key area where the user performed well.")
    key_improvement_area: str = Field(..., description="The single most important area for the user to improve.")

class DetailedFeedback(BaseModel):
    """A model that contains the detailed breakdown for all four criteria."""
    fluency_and_coherence: FeedbackCriterion
    lexical_resource: FeedbackCriterion
    grammatical_range_and_accuracy: FeedbackCriterion
    pronunciation_inferred: FeedbackCriterion

class IELTSFeedback(BaseModel):
    """
    The main, top-level model for the entire feedback report.
    Our application will try to parse the LLM's JSON response into this model.
    """
    overall_summary: OverallSummary = Field(..., description="The overall summary of the feedback.")
    detailed_feedback: DetailedFeedback = Field(..., description="The detailed feedback for each criterion.")

class HolisticSummary(BaseModel):
    """A structured summary of the user's overall performance."""
    strengths: str = Field(..., description="A paragraph summarizing the key strengths demonstrated across the test, citing specific examples.")
    areas_to_improve: str = Field(..., description="A paragraph outlining the main areas for improvement with actionable suggestions.")

class Score(BaseModel):
    """A model to hold an estimated score and its justification."""
    score: float = Field(..., description="The estimated score from 1.0 to 9.0, in 0.5 increments.")
    justification: str = Field(..., description="A brief, data-driven justification for the assigned score.")
    suggestion: str = Field(..., description="One single, actionable suggestion for this specific criterion.")

class PronunciationFeedback(BaseModel):
    """A model to provide feedback on pronunciation without a score."""
    assessment: str = Field(..., description="Qualitative analysis inferred from transcript.")
    suggestion: str = Field(..., description="One single, actionable suggestion a user can practice to improve general clarity or awareness.")

class EstimatedScores(BaseModel):
    """A container for the scores of all four criteria."""
    fluency_and_coherence: Score
    lexical_resource: Score
    grammatical_range_and_accuracy: Score
    pronunciation: PronunciationFeedback

class IELTSFinalReport(BaseModel):
    """
    The main, top-level model for the final comprehensive test report.
    This structure directly maps to the desired final JSON output.
    """
    holistic_summary: HolisticSummary
    overall_band_score: float = Field(..., description="The overall band score, calculated as the average of the three scorable criteria (Fluency, Lexical Resource, Grammar), and rounded to the nearest 0.5 band.")
    estimated_scores: EstimatedScores

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
    answers: Dict[str, List[str]] = field(default_factory=lambda: {"part1": [], "part2": [], "part3": []})
    session_phase: SessionPhase = SessionPhase.IN_PROGRESS
    feedback_reports: Dict[str, Optional[IELTSFeedback]] = field(default_factory=lambda: {"part1": None, "part2": None, "part3": None})
    final_report: Optional[IELTSFinalReport] = None
    
    # This is a derived property that calculates the questions for the current part.
    @property
    def is_last_question_of_part(self) -> bool:
        """Checks if the current question is the last one in the current part."""
        if not self.test_started or self.current_part == 0:
            return False

        try:
            # part 2 has only one question
            if self.current_part == 2:
                return True
            # Construct the key for the questions dictionary, e.g., 'part1'
            part_key = f"part{self.current_part}"
            
            # Get the list of questions for the current part
            questions_in_part = self.questions[part_key]["questions"] # type: ignore
            
            # The part is finished if the current index is the last valid index
            return self.current_question_index == len(questions_in_part) - 1
        except (KeyError, TypeError):
            # If questions are not loaded or the key is wrong, it's not finished.
            return False
