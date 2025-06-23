# In: ielts_questions.py

"""
IELTS Questions Module

This module provides a comprehensive question bank for IELTS Speaking test simulation.
Maintains full compatibility with gradio_app.py while adding improved error handling,
validation, and enhanced question sets.
"""

import random
import logging
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Enhanced question bank with more variety and better structure
IELTS_QUESTIONS = [
    {
        "part1": {
            "topic": "Work/Study",
            "questions": [
                "Do you work or are you a student?",
                "What subject are you studying?",
                "Why did you choose that subject?",
                "What do you like most about your studies?",
                "What are your future career plans?",
                "How do you balance work and personal life?"
            ]
        },
        "part2": {
            "topic": "Describe a website you use often",
            "cue_card": (
                "You should say:\n"
                "• What the website is\n"
                "• How you found out about it\n"
                "• What you use it for\n"
                "• How often you visit it\n\n"
                "and explain why you use it so often."
            )
        },
        "part3": {
            "topic": "Technology and the Internet",
            "questions": [
                "What are some of the advantages of the internet?",
                "Do you think older people have difficulty using the internet?",
                "How has social media changed how we communicate?",
                "What are the dangers of sharing personal information online?",
                "How do you think the internet will change in the future?",
                "Should there be more regulation of the internet?"
            ]
        }
    },
    {
        "part1": {
            "topic": "Hometown",
            "questions": [
                "Where is your hometown?",
                "What do you like most about your hometown?",
                "Has your hometown changed much since you were a child?",
                "What kind of jobs do people in your hometown do?",
                "Would you like to move away from your hometown?",
                "What would you show a visitor to your hometown?"
            ]
        },
        "part2": {
            "topic": "Describe a memorable trip you have taken",
            "cue_card": (
                "You should say:\n"
                "• Where you went\n"
                "• Who you went with\n"
                "• What you did there\n"
                "• How long you stayed\n\n"
                "and explain why it was so memorable."
            )
        },
        "part3": {
            "topic": "Travel and Tourism",
            "questions": [
                "Why do you think people like to travel?",
                "What are the benefits of traveling to other countries?",
                "Do you think it's better to travel alone or with others? Why?",
                "How does tourism affect local communities?",
                "What problems can tourism cause?",
                "How has technology changed the way people travel?"
            ]
        }
    },
    {
        "part1": {
            "topic": "Food",
            "questions": [
                "What's your favourite food?",
                "Do you enjoy cooking?",
                "What is a traditional meal in your country?",
                "How have people's eating habits changed in recent years?",
                "Do you prefer eating at home or in restaurants?",
                "What food from other countries do you like?"
            ]
        },
        "part2": {
            "topic": "Describe a skill that was difficult for you to learn",
            "cue_card": (
                "You should say:\n"
                "• What the skill was\n"
                "• When you learned it\n"
                "• Why you learned it\n"
                "• How you learned it\n\n"
                "and explain why it was difficult for you to learn."
            )
        },
        "part3": {
            "topic": "Skills and Learning",
            "questions": [
                "What skills do you think are most important for children to learn today?",
                "Is it more important to learn practical skills or academic subjects?",
                "How has technology changed the way we learn new skills?",
                "What is the best age for a person to learn a new skill?",
                "Should the government pay for people to learn new skills?",
                "How do you think education will change in the future?"
            ]
        }
    },
    {
        "part1": {
            "topic": "Hobbies and Free Time",
            "questions": [
                "What do you like to do in your free time?",
                "Have your hobbies changed since you were a child?",
                "Do you prefer indoor or outdoor activities?",
                "How much free time do you have?",
                "Do you think hobbies are important?",
                "What new hobby would you like to try?"
            ]
        },
        "part2": {
            "topic": "Describe a person who has influenced you",
            "cue_card": (
                "You should say:\n"
                "• Who this person is\n"
                "• How you know them\n"
                "• What they are like\n"
                "• How they influenced you\n\n"
                "and explain why their influence was important to you."
            )
        },
        "part3": {
            "topic": "Role Models and Influence",
            "questions": [
                "Who do you think has the most influence on young people today?",
                "Is it important for children to have role models?",
                "How can parents be good role models for their children?",
                "Do you think celebrities should be role models?",
                "How has social media changed the concept of role models?",
                "What qualities make someone a good role model?"
            ]
        }
    },
    {
        "part1": {
            "topic": "Shopping",
            "questions": [
                "Do you enjoy shopping?",
                "How often do you go shopping?",
                "Do you prefer shopping online or in stores?",
                "What do you usually buy when you go shopping?",
                "Have your shopping habits changed over the years?",
                "Do you think people buy too many things they don't need?"
            ]
        },
        "part2": {
            "topic": "Describe a gift you gave to someone",
            "cue_card": (
                "You should say:\n"
                "• Who you gave it to\n"
                "• What the gift was\n"
                "• When you gave it\n"
                "• Why you chose this gift\n\n"
                "and explain how the person felt when they received it."
            )
        },
        "part3": {
            "topic": "Gift-giving and Celebrations",
            "questions": [
                "What kinds of gifts are popular in your country?",
                "Do you think expensive gifts are always better?",
                "How important is gift-giving in maintaining relationships?",
                "Have gift-giving traditions changed in your country?",
                "Should children receive gifts for good behavior?",
                "What is the difference between giving gifts and charity?"
            ]
        }
    },
    {
        "part1": {
            "topic": "Weather and Seasons",
            "questions": [
                "What's the weather like in your country?",
                "What's your favorite season and why?",
                "How does weather affect your mood?",
                "Do you prefer hot or cold weather?",
                "Has the weather in your country changed over the years?",
                "What do you like to do in different seasons?"
            ]
        },
        "part2": {
            "topic": "Describe a book that you enjoyed reading",
            "cue_card": (
                "You should say:\n"
                "• What the book was about\n"
                "• When you read it\n"
                "• Why you chose to read it\n"
                "• How long it took you to read\n\n"
                "and explain why you enjoyed reading it."
            )
        },
        "part3": {
            "topic": "Reading and Books",
            "questions": [
                "Do you think people read less nowadays than in the past?",
                "What are the benefits of reading books?",
                "Should children be encouraged to read more?",
                "Do you think e-books will replace traditional books?",
                "How important are libraries in modern society?",
                "What types of books are most popular in your country?"
            ]
        }
    }
]

def _validate_question_structure(question_set: Dict[str, Any]) -> bool:
    """
    Validate that a question set has the correct structure.
    
    Args:
        question_set: Dictionary containing IELTS question set
        
    Returns:
        True if valid, False otherwise
    """
    try:
        required_parts = ['part1', 'part2', 'part3']
        
        # Check all parts exist
        for part in required_parts:
            if part not in question_set:
                logger.warning(f"Missing part: {part}")
                return False
            
            if not isinstance(question_set[part], dict):
                logger.warning(f"Part {part} is not a dictionary")
                return False
            
            # Check required keys for each part
            if 'topic' not in question_set[part]:
                logger.warning(f"Missing topic in {part}")
                return False
        
        # Validate part1 and part3 have questions
        for part in ['part1', 'part3']:
            if 'questions' not in question_set[part]:
                logger.warning(f"Missing questions in {part}")
                return False
            
            questions = question_set[part]['questions']
            if not isinstance(questions, list) or len(questions) == 0:
                logger.warning(f"Invalid questions format in {part}")
                return False
        
        # Validate part2 has cue_card
        if 'cue_card' not in question_set['part2']:
            logger.warning("Missing cue_card in part2")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error validating question structure: {str(e)}")
        return False

def _validate_question_bank() -> bool:
    """
    Validate the entire question bank structure.
    
    Returns:
        True if all question sets are valid, False otherwise
    """
    try:
        if not isinstance(IELTS_QUESTIONS, list) or len(IELTS_QUESTIONS) == 0:
            logger.error("Question bank is not a valid non-empty list")
            return False
        
        for i, question_set in enumerate(IELTS_QUESTIONS):
            if not _validate_question_structure(question_set):
                logger.error(f"Invalid question set at index {i}")
                return False
        
        logger.info(f"Question bank validation successful: {len(IELTS_QUESTIONS)} question sets")
        return True
        
    except Exception as e:
        logger.error(f"Error validating question bank: {str(e)}")
        return False

def get_random_ielts_test() -> Dict[str, Any]:
    """
    Selects a random, complete IELTS test from the question bank.
    
    Returns:
        Dictionary containing a complete IELTS test with part1, part2, and part3
        
    Raises:
        ValueError: If question bank is invalid or empty
    """
    try:
        # Validate question bank if not already done
        if not _validate_question_bank():
            raise ValueError("Question bank validation failed")
        
        if not IELTS_QUESTIONS:
            raise ValueError("Question bank is empty")
        
        # Select random question set
        selected_test = random.choice(IELTS_QUESTIONS)
        
        # Create a deep copy to avoid modifying the original
        test_copy = {
            "part1": {
                "topic": selected_test["part1"]["topic"],
                "questions": selected_test["part1"]["questions"].copy()
            },
            "part2": {
                "topic": selected_test["part2"]["topic"],
                "cue_card": selected_test["part2"]["cue_card"]
            },
            "part3": {
                "topic": selected_test["part3"]["topic"],
                "questions": selected_test["part3"]["questions"].copy()
            }
        }
        
        logger.info(f"Selected IELTS test: Part 1 - {test_copy['part1']['topic']}")
        return test_copy
        
    except Exception as e:
        logger.error(f"Error getting random IELTS test: {str(e)}")
        # Return a fallback question set to maintain compatibility
        fallback_test = {
            "part1": {
                "topic": "General Questions",
                "questions": [
                    "Can you tell me your name?",
                    "Where are you from?",
                    "What do you do for work or study?",
                    "What are your hobbies?"
                ]
            },
            "part2": {
                "topic": "Describe something important to you",
                "cue_card": (
                    "You should say:\n"
                    "• What it is\n"
                    "• Why it is important to you\n"
                    "• How you use it\n\n"
                    "and explain why it matters to you."
                )
            },
            "part3": {
                "topic": "General Discussion",
                "questions": [
                    "How do you think technology affects our daily lives?",
                    "What changes would you like to see in your community?",
                    "How important is education in today's world?",
                    "What role does family play in people's lives?"
                ]
            }
        }
        logger.info("Using fallback question set due to error")
        return fallback_test
    
# Initialize validation on module import
if __name__ != "__main__":
    # Validate question bank when module is imported
    if not _validate_question_bank():
        logger.warning("Question bank validation failed during import")