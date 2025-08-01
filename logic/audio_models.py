# In: logic/audio_models.py

from pydantic import BaseModel, Field
from typing import List, Optional

# This file defines a robust, validated structure for the JSON data
# returned by the Azure Pronunciation Assessment API.

# --- Nested Assessment Models ---
# These small models capture the specific data points at each level.

class PhonemeAssessment(BaseModel):
    accuracy_score: float = Field(alias="AccuracyScore")
    error_type: str = Field("None", alias="ErrorType") 

class WordAssessment(BaseModel):
    accuracy_score: float = Field(alias="AccuracyScore")
    error_type: str = Field("None", alias="ErrorType")

class PronunciationAssessmentResult(BaseModel):
    accuracy_score: float = Field(alias="AccuracyScore")
    fluency_score: float = Field(alias="FluencyScore")
    prosody_score: Optional[float] = Field(None, alias="ProsodyScore")
    completeness_score: float = Field(alias="CompletenessScore")
    pron_score: float = Field(alias="PronScore")

# --- Core Result Models ---
# These models represent the actual linguistic units.

class PhonemeResult(BaseModel):
    phoneme: str = Field(alias="Phoneme")
    assessment: PhonemeAssessment = Field(alias="PronunciationAssessment")

class WordResult(BaseModel):
    word: str = Field(alias="Word")
    assessment: WordAssessment = Field(alias="PronunciationAssessment")
    phonemes: List[PhonemeResult] = Field(alias="Phonemes")
    # Syllables are optional as they are not critical for our primary goal
    syllables: Optional[List[dict]] = Field(None, alias="Syllables")

class NBestResult(BaseModel):
    confidence: float = Field(alias="Confidence")
    display: str = Field(alias="Display")
    assessment: PronunciationAssessmentResult = Field(alias="PronunciationAssessment")
    words: List[WordResult] = Field(alias="Words")

# --- Top-Level Container Model ---
class AzurePronunciationReport(BaseModel):
    """
    The main, top-level Pydantic model for the entire JSON object
    returned by the Azure Pronunciation Assessment service.
    """
    # These top-level fields are required for successful parsing.
    id: str = Field(alias="Id")
    recognition_status: str = Field(alias="RecognitionStatus")
    display_text: str = Field(alias="DisplayText")
    offset: int = Field(alias="Offset")
    duration: int = Field(alias="Duration")
    snr: Optional[float] = Field(None, alias="SNR")
    nbest: List[NBestResult] = Field(alias="NBest")

    @property
    def primary_result(self) -> Optional[NBestResult]:
        """Returns the first and most confident result from the NBest list."""
        if self.nbest:
            return self.nbest[0]
        return None