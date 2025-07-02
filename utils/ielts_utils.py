from logic.ielts_models import IELTSFeedback 

def format_feedback_for_display(report: IELTSFeedback) -> str:
    """Converts an IELTSFeedback object into a readable Markdown string."""
    
    # If we got a valid Pydantic object, format it into a nice Markdown report
    summary = report.overall_summary
    details = report.detailed_feedback
    # Using an f-string with triple quotes for a clean, multi-line template.
    display_text = f"""
        ## Overall Summary
        - **Part Assessed:** {summary.part_assessed}
        - **Positive Highlight:** {summary.positive_highlight}
        - **Key Area for Improvement:** {summary.key_improvement_area}

        ---

        ## Detailed Feedback

        ### Fluency and Coherence:
        - **Strength:** {details.fluency_and_coherence.strength}
        - **Area for Improvement:** {details.fluency_and_coherence.improvement_area}

        ### Lexical Resource (Vocabulary):
        - **Strength:** {details.lexical_resource.strength}
        - **Area for Improvement:** {details.lexical_resource.improvement_area}

        ### Grammatical Range and Accuracy:
        - **Strength:** {details.grammatical_range_and_accuracy.strength}
        - **Area for Improvement:** {details.grammatical_range_and_accuracy.improvement_area}

        ### Pronunciation (Inferred):
        - **Strength:** {details.pronunciation_inferred.strength}
        - **Area for Improvement:** {details.pronunciation_inferred.improvement_area}
        """
    return display_text