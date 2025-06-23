def clean_text_for_speech(text):
    """Removes Markdown characters from text for cleaner TTS output."""
    if not text:
        return ""
    text = text.replace('*', '')
    text = text.replace('#', '')
    text = text.replace('_', '')
    return text