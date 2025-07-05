import os
import gc # For garbage collection
import json # To save detailed output
import torch # For torch.cuda.is_available()
import whisperx

def transcribe_audio(audio_path: str, transcription_output_path: str, language: str, log_callback) -> bool:
    """
    Transcribes audio using WhisperX, performs word-level alignment,
    and saves the detailed transcription data (including word timestamps) to a JSON file.
    """
    log_callback(f"  Transcribing audio from {os.path.basename(audio_path)} using WhisperX...")
    try:
        # Use CPU to avoid CUDA/cuDNN issues in non-configured environments
        device = "cpu"
        batch_size = 16 # Adjust based on available RAM
        compute_type = "int8" # Use int8 for faster CPU computation

        log_callback(f"  Loading WhisperX model (medium, device={device}, compute_type={compute_type})...")
        # The language parameter is now passed to model.transcribe() for better results
        model = whisperx.load_model("medium", device=device, compute_type=compute_type)

        # Load audio
        audio = whisperx.load_audio(audio_path)

        # 1. Transcribe with original whisper
        log_callback(f"  Running WhisperX transcription for language: '{language}'...")
        # Pass language to the transcribe method
        result = model.transcribe(audio, batch_size=batch_size, language=language)
        
        # Clean up the main model to free up memory before loading the alignment model
        del model
        gc.collect()

        # 2. Align whisper output
        log_callback("  Loading alignment model...")
        try:
            model_a, metadata = whisperx.load_align_model(language_code=language, device=device)
        except Exception as e:
            log_callback(f"  Warning: Could not load alignment model for language '{language}'. {e}")
            log_callback("  Word-level timestamps will not be available. Subtitles cannot be generated.")
            # Fallback to saving just the transcription text
            transcription_text = "\n".join([segment['text'] for segment in result["segments"]])
            # Ensure the output path has a .txt extension for the fallback
            fallback_path = os.path.splitext(transcription_output_path)[0] + ".txt"
            with open(fallback_path, "w", encoding="utf-8") as f:
                f.write(transcription_text)
            log_callback(f"  Basic transcription saved to {fallback_path}")
            return False # Return False as the full process (with alignment) failed

        log_callback("  Aligning transcription for word-level timestamps...")
        result = whisperx.align(result["segments"], model_a, metadata, audio, device, return_char_alignments=False)

        # The result now contains word-level timestamps: result["word_segments"]
        # Save the detailed result to a JSON file
        with open(transcription_output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        
        log_callback(f"  Detailed transcription with word timestamps saved to {transcription_output_path}")

        # Clean up alignment model
        del model_a
        gc.collect()

        return True
    except Exception as e:
        log_callback(f"  Error transcribing audio with WhisperX: {e}")
        log_callback("  Ensure whisperx, torch, and all dependencies are installed correctly.")
        return False