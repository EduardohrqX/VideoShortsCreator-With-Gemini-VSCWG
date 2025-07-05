import re
import json
import google.generativeai as genai

def analyze_transcription_with_gemini(transcription_text: str, gemini_api_key: str, custom_prompt: str = None, log_callback=None) -> list | None:
    """
    Analyzes transcription text using the Gemini API to identify video highlights.
    Returns a list of highlight dictionaries.
    """
    if log_callback:
        log_callback("  Analyzing transcription with Gemini API...")
    try:
        genai.configure(api_key=gemini_api_key)
        # ALTERAÇÃO AQUI: Usando 'gemini-1.5-flash' em vez de 'gemini-pro'
        model = genai.GenerativeModel('gemini-2.0-flash') 

        # The full prompt is passed directly, including duration constraints and pitch analysis results.
        prompt_to_use = custom_prompt

        response = model.generate_content(prompt_to_use)
        
        # Extract JSON part from Gemini's response, as it might be wrapped in markdown or other text.
        json_match = re.search(r'\[.*\]', response.text, re.DOTALL)
        if json_match:
            json_string = json_match.group(0)
            try:
                highlights = json.loads(json_string)
                if log_callback:
                    log_callback("  Gemini analysis complete.")
                return highlights
            except json.JSONDecodeError as json_e:
                if log_callback:
                    log_callback(f"  Error decoding JSON from Gemini response: {json_e}")
                    log_callback(f"  Gemini raw response (JSON part): {json_string}")
                return None
        else:
            if log_callback:
                log_callback("  Could not find valid JSON in Gemini response.")
                log_callback(f"  Gemini raw response: {response.text}")
            return None
    except Exception as e:
        if log_callback:
            log_callback(f"  Error analyzing transcription with Gemini: {e}")
            log_callback("  Ensure Gemini API key is correct and API is accessible. Check API rate limits.")
        return None