import os
import time
import numpy as np
import librosa
import soundfile as sf # Used by librosa internally
import torch # For torch.cuda.is_available()

from moviepy import VideoFileClip, AudioFileClip

def extract_audio(video_path: str, audio_output_path: str, log_callback) -> bool:
    """Extracts audio from a video file and saves it as WAV."""
    log_callback(f"  Extracting audio from {os.path.basename(video_path)}...")
    try:
        video_clip = VideoFileClip(video_path)
        audio_clip = video_clip.audio
        # Use pcm_s16le codec for compatibility with librosa and WhisperX
        audio_clip.write_audiofile(audio_output_path, codec="pcm_s16le")
        audio_clip.close()
        video_clip.close() # Ensure video clip is closed to free resources
        log_callback(f"  Audio extracted to {audio_output_path}")
        return True
    except Exception as e:
        log_callback(f"  Error extracting audio from {os.path.basename(video_path)}: {e}")
        log_callback("  Ensure FFmpeg is installed and accessible in your system's PATH.")
        return False

def analyze_pitch(audio_path: str, log_callback) -> dict | None:
    """
    Analyzes pitch from an audio file using librosa's pYIN algorithm.
    Returns overall pitch stats and segments with high pitch activity.
    """
    log_callback(f"  Analyzing pitch from {os.path.basename(audio_path)}...")
    try:
        # Explicitly set torch device to CPU for this function
        torch.device("cpu")

        y, sr = librosa.load(audio_path, sr=None) # Load with original sample rate
        
        # Estimate pitch using pYIN
        f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), fmax=librosa.note_to_hz('C5'), sr=sr)
        
        # Replace NaNs (unvoiced frames) with 0 for calculations.
        # Ensure f0_filled is a numpy array for numerical operations.
        f0_filled = np.nan_to_num(f0)

        # Filter out zero values (unvoiced segments) for meaningful pitch statistics.
        voiced_f0_values = f0_filled[f0_filled > 0]

        # Calculate overall pitch statistics
        overall_avg_pitch = np.mean(voiced_f0_values) if len(voiced_f0_values) > 0 else 0
        overall_pitch_std = np.std(voiced_f0_values) if len(voiced_f0_values) > 0 else 0

        # Identify segments with high pitch activity (e.g., above average + 1 std dev)
        # This is a simplified approach; more sophisticated methods exist.
        high_pitch_threshold = overall_avg_pitch + overall_pitch_std
        
        # Simple segmentation: iterate through pitch values
        # Convert segment_length_frames to samples
        segment_duration_sec = 0.5
        segment_length_samples = int(segment_duration_sec * sr) # 0.5 second segments
        high_pitch_segments = []
        
        for i in range(0, len(f0_filled), segment_length_samples):
            segment_f0 = f0_filled[i : i + segment_length_samples]
            
            # Consider only voiced segments for average/std dev
            voiced_segment_f0 = segment_f0[segment_f0 > 0] 
            
            if len(voiced_segment_f0) > 0: # Ensure there's voiced data in the segment
                avg_segment_pitch = np.mean(voiced_segment_f0)
                std_segment_pitch = np.std(voiced_segment_f0)
                
                if avg_segment_pitch > high_pitch_threshold: # If average pitch is above threshold
                    start_time_sec = librosa.frames_to_time(i, sr=sr)
                    end_time_sec = librosa.frames_to_time(i + segment_length_samples, sr=sr)
                    
                    high_pitch_segments.append({
                        'start_time': time.strftime('%H:%M:%S', time.gmtime(start_time_sec)),
                        'end_time': time.strftime('%H:%M:%S', time.gmtime(end_time_sec)),
                        'avg_pitch': avg_segment_pitch,
                        'std_pitch': std_pitch
                    })
        
        log_callback("  Pitch analysis complete.")
        return {
            'overall_avg_pitch': overall_avg_pitch,
            'overall_pitch_std': overall_pitch_std,
            'high_pitch_segments': high_pitch_segments
        }

    except Exception as e:
        log_callback(f"  Error during pitch analysis: {e}")
        log_callback("  Ensure librosa and numpy are installed. Pitch analysis is experimental.")
        return None