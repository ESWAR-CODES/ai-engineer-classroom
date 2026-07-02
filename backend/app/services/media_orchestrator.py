import re

def format_seconds_to_vtt_time(total_seconds: float) -> str:
    """Format seconds into HH:MM:SS.mmm WebVTT timestamp syntax."""
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    milliseconds = int(round((total_seconds % 1) * 1000))
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

def generate_vtt_subtitles(voice_script: str) -> str:
    """Parse text voice scripts and generate structured time-nested WebVTT subtitles."""
    # Split text script by typical punctuation boundary
    sentences = re.split(r'(?<=[.!?])\s+', voice_script.strip())
    
    vtt_lines = ["WEBVTT", ""]
    current_time_sec = 0.5  # Start offset
    
    for idx, sentence in enumerate(sentences):
        sentence_clean = sentence.strip()
        if not sentence_clean:
            continue
            
        # Estimate duration based on word count (approx 2.5 words per second)
        word_count = len(sentence_clean.split())
        duration = max(3.0, min(8.0, word_count / 2.5))  # Clamp duration
        
        start_sec = current_time_sec
        end_sec = current_time_sec + duration
        
        # Advance baseline current time for next loop
        current_time_sec = end_sec + 0.3
        
        start_time_str = format_seconds_to_vtt_time(start_sec)
        end_time_str = format_seconds_to_vtt_time(end_sec)
        
        vtt_lines.append(f"{idx + 1}")
        vtt_lines.append(f"{start_time_str} --> {end_time_str}")
        vtt_lines.append(sentence_clean)
        vtt_lines.append("")
        
    return "\n".join(vtt_lines)
