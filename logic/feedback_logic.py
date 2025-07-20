# In: logic/feedback_logic.py

from dataclasses import dataclass
from typing import List, Optional
from .audio_models import AzurePronunciationReport, WordResult, PhonemeResult

# --- Step 1: Define the FeedbackPoint dataclass ---
@dataclass
class FeedbackPoint:
    """
    A simple data structure to hold a single, actionable point of feedback
    extracted from a detailed pronunciation report.
    """
    word: str
    phoneme: str
    accuracy_score: float
    transcript_of_sentence: str  # The full sentence in which the error occurred

# --- Step 2: Implement the feedback selection function ---
def find_actionable_feedback_point(
    reports: List[AzurePronunciationReport], 
    score_threshold: int = 60
) -> Optional[FeedbackPoint]:
    """
    Analyzes a list of recent pronunciation reports to find the single most
    actionable point of feedback.

    Args:
        reports: A list of AzurePronunciationReport objects from recent turns.
        score_threshold: The accuracy score below which a phoneme is considered an error.

    Returns:
        A FeedbackPoint object if a suitable error is found, otherwise None.
    """
    lowest_score = 101  # Start with a score higher than any possible score
    actionable_point = None

    for report in reports:
        # Ensure we are working with a successful report
        if not report or not report.primary_result:
            continue
        
        sentence_transcript = report.display_text
        words: List[WordResult] = report.primary_result.words

        for word in words:
            if not word.phonemes:
                continue
            
            for phoneme in word.phonemes:
                # Check if the phoneme has a score and if it's below our threshold
                if phoneme.assessment and phoneme.assessment.accuracy_score < score_threshold:
                    # If this is the worst-scoring phoneme we've found so far, it becomes our new target
                    if phoneme.assessment.accuracy_score < lowest_score:
                        lowest_score = phoneme.assessment.accuracy_score
                        actionable_point = FeedbackPoint(
                            word=word.word,
                            phoneme=phoneme.phoneme,
                            accuracy_score=lowest_score,
                            transcript_of_sentence=sentence_transcript
                        )

    return actionable_point