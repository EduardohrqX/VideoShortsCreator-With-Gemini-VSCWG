import re

def clean_punctuation(transcription_data: dict, remove_punctuation_flag: bool, log_callback) -> dict:
    """
    Removes punctuation from each word in the transcription data if remove_punctuation_flag is True.
    Accented characters are preserved.
    """
    if not remove_punctuation_flag:
        log_callback("  Punctuation removal skipped as per user setting.")
        return transcription_data

    log_callback("  Cleaning punctuation from transcription...")
    if not transcription_data or "segments" not in transcription_data:
        log_callback("  Warning: Cannot clean transcription, 'segments' not found.")
        return transcription_data

    # Regex to find and remove common punctuation, keeping letters, numbers, and accents.
    punctuation_re = re.compile(r"[.,!?;:]+")

    for segment in transcription_data["segments"]:
        if "words" in segment:
            for word_info in segment["words"]:
                if 'word' in word_info:
                    original_word = word_info['word']
                    cleaned_word = punctuation_re.sub("", original_word)
                    if original_word != cleaned_word:
                        log_callback(f"    Cleaned '{original_word}' to '{cleaned_word}'")
                        word_info['word'] = cleaned_word
    
    log_callback("  Punctuation cleaning complete.")
    return transcription_data
