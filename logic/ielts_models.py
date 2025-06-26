# In: logic/ielts_models.py

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

# The @dataclass decorator is a special "instruction" to Python.
# It automatically generates essential methods for the class, like __init__(),
# which makes it perfect for storing data without writing a lot of boilerplate code.
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
    
    # We can provide default values for fields.
    current_part: int = 0
    current_question_index: int = 0
    test_started: bool = False
    current_question_text: str = ""

    # --- Important Learning Point for Dataclasses ---
    # For fields that are "mutable" (like a list or dictionary), we cannot
    # set a default like `answers: List[str] = []`. If we did, all separate
    # instances of this class would share the exact SAME list in memory.
    #
    # To fix this, we use `field(default_factory=list)`. This tells the
    # dataclass: "When you create a new IELTSState object, run the `list()`
    # function to create a fresh, empty list just for this object."
    answers: List[str] = field(default_factory=list)