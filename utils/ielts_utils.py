from logic.ielts_models import IELTSFeedback, IELTSFinalReport 

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

def format_transcript_text(answers_dict):
    """
    Formats the user's answers with explicit part labels for clarity.
    This helps the LLM clearly distinguish between the different parts of the test.
    """
    full_transcript = []
    for part_num in range(1, 4):
        part_key = f"part{part_num}"
        if answers_for_part := answers_dict.get(part_key):
            # Create a header for the part
            part_header = f"--- START OF PART {part_num} TRANSCRIPT ---"
            part_footer = f"--- END OF PART {part_num} TRANSCRIPT ---"
            # Join the Q&A pairs for this part
            part_content = "\n\n".join(answers_for_part)
            # Add the full block to our list
            full_transcript.append(f"{part_header}\n{part_content}\n{part_footer}")

    return "\n\n".join(full_transcript) if full_transcript else "No answers were recorded."

def format_prior_feedback_summary(feedback_dict):
    """
    Formats the dictionary of stored IELTSFeedback objects into a clean,
    human-readable string for the final prompt.
    """
    prior_feedback_summary = []
    for part_num in range(1, 4):
        part_key = f"part{part_num}"
        if report := feedback_dict.get(part_key):
            # We only extract the most critical summary points to keep the input clean.
            summary_header = f"Prior Feedback Summary for Part {part_num}:"
            positive_highlight = f"- Positive Highlight: {report.overall_summary.positive_highlight}"
            key_improvement_area = f"- Key Improvement Area: {report.overall_summary.key_improvement_area}"
            
            prior_feedback_summary.append(f"{summary_header}\n{positive_highlight}\n{key_improvement_area}")
        else:
            # If no feedback was generated for this part, we note that
            prior_feedback_summary.append(f"--- NO PRIOR FEEDBACK FOR PART {part_num} ---")

    if not prior_feedback_summary:
        return "No prior feedback was generated."
    
    return "\n\n".join(prior_feedback_summary)

def format_prior_feedback(feedback_dict: dict) -> str:
    """
    Formats the dictionary of stored IELTSFeedback objects into a comprehensive,
    human-readable string for the final prompt by reusing the display formatter.
    """
    prior_feedback_full_text = []
    for part_num in range(1, 4):
        part_key = f"part{part_num}"
        if report := feedback_dict.get(part_key):
            # Create a clear header for each part's feedback
            header = f"--- START OF PRIOR FEEDBACK FOR PART {part_num} ---\n"
            footer = f"\n--- END OF PRIOR FEEDBACK FOR PART {part_num} ---"
            
            # Reuse our existing formatting function to get the full report text
            report_text = format_feedback_for_display(report)
            
            prior_feedback_full_text.append(f"{header}{report_text}{footer}")
        else:
            # If no feedback was generated for this part, we note that
            prior_feedback_full_text.append(f"--- NO PRIOR FEEDBACK FOR PART {part_num} ---")

    if not prior_feedback_full_text:
        return "No prior feedback was generated for any part."
    
    return "\n\n".join(prior_feedback_full_text)

def format_final_report_for_display(report: IELTSFinalReport) -> str:
    """Converts the final comprehensive report object into a readable Markdown string."""
    
    # --- The Disclaimer ---
    disclaimer = "> **Disclaimer:** This is an AI-generated estimate for practice purposes only. It is not an official IELTS score."

    summary = report.holistic_summary
    scores = report.estimated_scores
    
    display_text = f"""
    {disclaimer}

    # Final Comprehensive Report

    ## Overall Estimated Band Score: {report.overall_band_score}

    ### Holistic Summary
    - **Key Strengths:** {summary.strengths}
    - **Areas to Improve:** {summary.areas_to_improve}

    ---

    ## Detailed Score Breakdown

    ### Fluency and Coherence
    - **Score:** {scores.fluency_and_coherence.score}
    - **Justification:** {scores.fluency_and_coherence.justification}
    - **Suggestion:** {scores.fluency_and_coherence.suggestion}

    ### Lexical Resource (Vocabulary)
    - **Score:** {scores.lexical_resource.score}
    - **Justification:** {scores.lexical_resource.justification}
    - **Suggestion:** {scores.lexical_resource.suggestion}

    ### Grammatical Range and Accuracy
    - **Score:** {scores.grammatical_range_and_accuracy.score}
    - **Justification:** {scores.grammatical_range_and_accuracy.justification}
    - **Suggestion:** {scores.grammatical_range_and_accuracy.suggestion}

    ### Pronunciation (Inferred)
    - **Assessment:** {scores.pronunciation.assessment}
    - **Suggestion:** {scores.pronunciation.suggestion}
    """
    return display_text