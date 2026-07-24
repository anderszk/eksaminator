"""Delivery metrics computed from Whisper segment output."""
from app.services.grading import FILLERS_NO, SOFT_FILLERS


def compute_delivery_metrics(
    segments: list[dict],
    transcript: str,
    duration_s: float,
) -> dict:
    duration_ms = int(duration_s * 1000)

    words = transcript.split()
    wpm = (len(words) / duration_s * 60) if duration_s > 0 else 0.0

    # Filler count: soft fillers weighted 0.5
    transcript_lower = transcript.lower()
    transcript_words = [w.strip(".,!?;:") for w in transcript_lower.split()]
    hard_count = sum(1 for w in transcript_words if w in FILLERS_NO and w not in SOFT_FILLERS)
    soft_count = sum(1 for w in transcript_words if w in SOFT_FILLERS)
    filler_count = hard_count + int(soft_count * 0.5)
    filler_rate = filler_count / max(len(words), 1)

    # Pause gaps between segments
    longest_pause_ms = 0
    for i in range(1, len(segments)):
        gap_ms = int((segments[i]["start"] - segments[i - 1]["end"]) * 1000)
        if gap_ms > longest_pause_ms:
            longest_pause_ms = gap_ms

    time_to_first_word_ms = int(segments[0]["start"] * 1000) if segments else 0

    return {
        "duration_ms": duration_ms,
        "wpm": round(wpm, 1),
        "filler_count": filler_count,
        "filler_rate": round(filler_rate, 4),
        "longest_pause_ms": longest_pause_ms,
        "time_to_first_word_ms": time_to_first_word_ms,
    }
