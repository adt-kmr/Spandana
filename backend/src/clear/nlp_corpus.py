"""Trilingual (EN / हिन्दी / ಕನ್ನಡ) citizen-report phrase corpus for MuRIL precompute.

Every phrase here is embedded once by `precompute_muril` and persisted in the sha1
cache, so /nlp/severity can serve these (and close paraphrases the frontend pins as
suggestions) with ZERO torch at runtime — a cache hit never loads the model.

Keyed by canonical EVENT_CAUSES value. Extend freely; re-run precompute after editing.
"""
from __future__ import annotations

CORPUS: dict[str, list[str]] = {
    "breakdown": [
        # English
        "vehicle breakdown blocking lane",
        "truck broke down on the road",
        "bus stalled in the middle of the road",
        "car broke down blocking traffic",
        # हिन्दी
        "गाड़ी खराब हो गई है और रास्ता बंद है",
        "ट्रक सड़क पर खराब हो गया",
        "बस बीच सड़क पर रुक गई",
        # Hinglish
        "gaadi kharab ho gayi lane block hai",
        "truck road par kharab ho gaya",
        # ಕನ್ನಡ
        "ವಾಹನ ಕೆಟ್ಟು ನಿಂತಿದೆ ರಸ್ತೆ ಬ್ಲಾಕ್ ಆಗಿದೆ",
        "ಟ್ರಕ್ ರಸ್ತೆಯಲ್ಲಿ ಕೆಟ್ಟು ನಿಂತಿದೆ",
        "ಬಸ್ ರಸ್ತೆ ಮಧ್ಯದಲ್ಲಿ ನಿಂತಿದೆ",
        # romanized Kannada
        "vahana kettu nintide raste block aagide",
    ],
    "accident": [
        "accident reported vehicles involved",
        "two vehicles collided",
        "bike accident with injuries",
        "major accident ambulance needed",
        "दुर्घटना हुई है वाहन शामिल हैं",
        "दो गाड़ियों की टक्कर हो गई",
        "एक्सीडेंट में लोग घायल हैं एम्बुलेंस चाहिए",
        "accident hua hai gaadiyan involved hain",
        "do gaadiyon ki takkar ho gayi",
        "ಅಪಘಾತ ಸಂಭವಿಸಿದೆ ವಾಹನಗಳು ಒಳಗೊಂಡಿವೆ",
        "ಎರಡು ವಾಹನಗಳು ಡಿಕ್ಕಿ ಹೊಡೆದಿವೆ",
        "ಅಪಘಾತದಲ್ಲಿ ಗಾಯಗೊಂಡಿದ್ದಾರೆ ಆಂಬುಲೆನ್ಸ್ ಬೇಕು",
        "apaghata sambhavibide gayagondiddare ambulance beku",
    ],
    "tree_fall": [
        "tree fallen across carriageway",
        "tree fell blocking the road",
        "branch fell on the road",
        "पेड़ सड़क पर गिर गया है",
        "पेड़ गिरने से रास्ता बंद है",
        "ped road par gir gaya hai",
        "ಮರ ರಸ್ತೆಗೆ ಬಿದ್ದಿದೆ",
        "ಮರ ಬಿದ್ದು ರಸ್ತೆ ಬ್ಲಾಕ್ ಆಗಿದೆ",
        "mara rastege biddide",
    ],
    "water_logging": [
        "water logging slowing traffic",
        "road flooded heavy water",
        "waterlogging after rain",
        "सड़क पर पानी भर गया है",
        "बारिश के बाद जलभराव हो गया",
        "road par paani bhar gaya hai",
        "ರಸ್ತೆಯಲ್ಲಿ ನೀರು ನಿಂತಿದೆ",
        "ಮಳೆಯ ನಂತರ ನೀರು ತುಂಬಿದೆ",
        "rasteyalli neeru nintide",
    ],
    "pot_holes": [
        "pothole causing slowdown",
        "big pothole on the road",
        "potholes damaging vehicles",
        "सड़क पर गड्ढा है",
        "बड़ा गड्ढा होने से गाड़ियां धीमी",
        "road par gaddha hai",
        "ರಸ್ತೆಯಲ್ಲಿ ಗುಂಡಿ ಬಿದ್ದಿದೆ",
        "ದೊಡ್ಡ ಗುಂಡಿ ಇದೆ ವಾಹನಗಳು ನಿಧಾನ",
        "rasteyalli gundi biddide",
    ],
    "public_event": [
        "public event procession",
        "rally blocking the road",
        "festival crowd on the road",
        "जुलूस के कारण रास्ता बंद है",
        "रैली से ट्रैफिक रुका हुआ है",
        "juloos ki wajah se road band hai",
        "ಮೆರವಣಿಗೆಯಿಂದ ರಸ್ತೆ ಬಂದ್ ಆಗಿದೆ",
        "ರ್ಯಾಲಿಯಿಂದ ಟ್ರಾಫಿಕ್ ನಿಂತಿದೆ",
        "meravanigeyinda raste band aagide",
    ],
    "others": [
        "incident reported",
        "traffic jam on the road",
        "road blocked unknown reason",
        "ट्रैफिक जाम लगा है",
        "किसी कारण से रास्ता बंद है",
        "traffic jam laga hai",
        "ಟ್ರಾಫಿಕ್ ಜಾಮ್ ಆಗಿದೆ",
        "ಯಾವುದೋ ಕಾರಣಕ್ಕೆ ರಸ್ತೆ ಬಂದ್ ಆಗಿದೆ",
        "traffic jam aagide",
    ],
    # Closure suffix mirrors datagen's "; road closure required" so closure phrasing is cached too.
    "_closure": [
        "road closure required",
        "रास्ता पूरी तरह बंद करना पड़ेगा",
        "raasta poori tarah band",
        "ರಸ್ತೆ ಸಂಪೂರ್ಣ ಬಂದ್ ಮಾಡಬೇಕು",
    ],
}

def all_phrases() -> list[str]:
    """Flat, de-duplicated list of every corpus phrase (order-stable)."""
    seen: set[str] = set()
    out: list[str] = []
    for phrases in CORPUS.values():
        for p in phrases:
            key = p.strip().lower()
            if key and key not in seen:
                seen.add(key)
                out.append(p)
    return out

# Reverse lookup: normalized phrase -> canonical cause (skips the non-cause "_closure" bucket).
_PHRASE_TO_CAUSE: dict[str, str] = {
    p.strip().lower(): cause
    for cause, phrases in CORPUS.items()
    if not cause.startswith("_")
    for p in phrases
}

def cause_for_phrase(text: str) -> str | None:
    """Return the canonical cause for an exact corpus phrase, else None (unknown/free text)."""
    return _PHRASE_TO_CAUSE.get((text or "").strip().lower())
