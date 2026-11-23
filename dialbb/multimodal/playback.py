"""Convert client playback positions into the spoken prefix of a system utterance."""

from decimal import Decimal, ROUND_HALF_UP
import math
import re


def get_spoken_string(
    text: str, language_code: str, completed_units: object, segment_count: int,
) -> str | None:
    """Estimate the spoken prefix using character counts (Japanese) or words (English).

    Each TTS segment has equal weight, as in the previous completion calculation.
    Return None for invalid positions; an empty string means nothing was spoken.
    """
    if (isinstance(completed_units, bool)
            or not isinstance(completed_units, (int, float))
            or not math.isfinite(completed_units)
            or segment_count <= 0
            or not 0 <= completed_units <= segment_count):
        return None
    if completed_units == segment_count:
        return text
    words = list(re.finditer(r'\S+', text)) if language_code.split('-')[0] == 'en' else None
    length = len(words) if words is not None else len(text)
    # Decimal preserves half-up rounding at boundaries such as 50 * 0.29.
    kept = int((Decimal(length) * Decimal(str(completed_units)) / Decimal(segment_count))
               .quantize(Decimal('1'), rounding=ROUND_HALF_UP))
    end = (words[kept - 1].end() if kept else 0) if words is not None else kept
    return text[:end]
