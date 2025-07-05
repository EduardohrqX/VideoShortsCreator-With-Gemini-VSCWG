import google.generativeai as genai
import json
import re

def stylize_transcription(transcription_data: dict, gemini_api_key: str, add_emojis: bool, log_callback) -> dict | None:
    """
    Analyzes the transcription text with Gemini to add style tags and optional emojis for subtitles.

    Args:
        transcription_data: The original transcription data from WhisperX.
        gemini_api_key: The user's Google Gemini API key.
        add_emojis: Boolean indicating whether to request emojis in the analysis.
        log_callback: Function to log messages to the GUI.

    Returns:
        A dictionary with the stylized word segments or None if an error occurs.
    """
    log_callback("  Styling transcription for subtitles with Gemini...")
    
    # Reconstruct the plain text from the segments for Gemini analysis
    if "segments" in transcription_data:
        plain_text = "\n".join([segment['text'].strip() for segment in transcription_data["segments"]])
    else:
        log_callback("  Error: Cannot stylize transcription, 'segments' key missing.")
        return None

    try:
        genai.configure(api_key=gemini_api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # --- Construct the specialized prompt for Gemini ---
        emoji_instruction = ""
        if add_emojis:
            emoji_instruction = "Additionally, for words with strong emotional or visual content, add a relevant emoji in an 'emoji' field."

        prompt = f"""
        Analyze the following text. Your task is to process it for video subtitles by assigning a style tag to each word.
        Use the following style tags:
        - 'normal': For regular words.
        - 'highlight': For keywords, important concepts, or emotionally charged words that should be visually emphasized.
        - 'impact': For words that need extra emphasis, like exclamations or words describing a strong action.

        {emoji_instruction}

        The original text is provided below. Respond ONLY with a JSON object containing a single key, "styled_words", which is a list of objects. 
        Each object in the list must represent a word and have the following keys: "word" (the actual word as a string) and "style" (one of 'normal', 'highlight', or 'impact').
        If you are adding emojis, include the "emoji" key with the emoji character as a string.

        Example with emojis:
        [ 
            {{"word": "This", "style": "normal"}}, 
            {{"word": "is", "style": "normal"}}, 
            {{"word": "absolutely", "style": "highlight"}}, 
            {{"word": "insane!", "style": "impact", "emoji": "🤯"}}
        ]

        Example without emojis:
        [ 
            {{"word": "How", "style": "normal"}}, 
            {{"word": "to", "style": "normal"}}, 
            {{"word": "make", "style": "normal"}}, 
            {{"word": "the", "style": "normal"}}, 
            {{"word": "perfect", "style": "highlight"}}, 
            {{"word": "pancakes", "style": "normal"}}
        ]

        Ensure the number of words in your response exactly matches the number of words in the original text.
        Do not include any extra text, explanations, or markdown formatting in your response. The output must be a valid JSON object.

        Original Text:
        ---
        {plain_text}
        ---
        """

        response = model.generate_content(prompt)
        
        # Extract JSON from the response
        json_match = re.search(r'\{\s*"styled_words"\s*:\s*\[.*?\]\s*\}', response.text, re.DOTALL)
        if json_match:
            json_string = json_match.group(0)
            try:
                styled_data = json.loads(json_string)
                # --- Merge styled data with original transcription data ---
                original_words = transcription_data.get("word_segments", [])
                styled_words = styled_data.get("styled_words", [])

                if len(original_words) != len(styled_words):
                    log_callback(f"  Warning: Word count mismatch between original ({len(original_words)}) and styled ({len(styled_words)}) transcriptions. Cannot apply styles.")
                    return transcription_data # Return original data

                for i, original_word_info in enumerate(original_words):
                    original_word_info['style'] = styled_words[i].get('style', 'normal')
                    if 'emoji' in styled_words[i]:
                        original_word_info['emoji'] = styled_words[i]['emoji']
                
                log_callback("  Successfully applied styles to transcription.")
                return transcription_data # Return the modified original data

            except json.JSONDecodeError as json_e:
                log_callback(f"  Error decoding JSON from Gemini styling response: {json_e}")
                log_callback(f"  Gemini raw response (JSON part): {json_string}")
                return None
        else:
            log_callback("  Could not find valid JSON in Gemini styling response.")
            log_callback(f"  Gemini raw response: {response.text}")
            return None

    except Exception as e:
        log_callback(f"  Error during subtitle styling with Gemini: {e}")
        return None
