"""Trilingual (EN / हिन्दी / ಕನ್ನಡ / romanized) phrase bank for datagen.

datagen composes each incident description from a cause phrase + an urgency phrase (which
carries that tier's cue words) + an optional closure phrase, in one of four language styles.
This gives the text-only severity model real multilingual, tier-aligned text to learn from,
so cue_severe/serious/moderate/minor separate the bands in every language.
"""
from __future__ import annotations

LANG_WEIGHTS = [("en", 0.45), ("hi", 0.25), ("kn", 0.18), ("hinglish", 0.12)]

CAUSE_PHRASES = {
    "breakdown": {
        "en": ["vehicle breakdown blocking lane", "truck broke down on the road"],
        "hi": ["गाड़ी खराब होकर रास्ते में रुकी", "ट्रक सड़क पर खराब हो गया"],
        "kn": ["ವಾಹನ ಕೆಟ್ಟು ರಸ್ತೆಯಲ್ಲಿ ನಿಂತಿದೆ", "ಟ್ರಕ್ ರಸ್ತೆಯಲ್ಲಿ ಕೆಟ್ಟಿದೆ"],
        "hinglish": ["gaadi kharab hokar ruki", "truck road par kharab"],
    },
    "accident": {
        "en": ["accident reported", "vehicle collision"],
        "hi": ["दुर्घटना हुई है", "गाड़ियों की टक्कर"],
        "kn": ["ಅಪಘಾತ ಸಂಭವಿಸಿದೆ", "ವಾಹನಗಳ ಡಿಕ್ಕಿ"],
        "hinglish": ["accident hua hai", "gaadiyon ki takkar"],
    },
    "tree_fall": {
        "en": ["tree fallen across the road", "branch down on carriageway"],
        "hi": ["पेड़ सड़क पर गिर गया", "डाली सड़क पर गिरी"],
        "kn": ["ಮರ ರಸ್ತೆಗೆ ಬಿದ್ದಿದೆ", "ಕೊಂಬೆ ರಸ್ತೆಗೆ ಬಿದ್ದಿದೆ"],
        "hinglish": ["ped road par gir gaya", "daali road par giri"],
    },
    "water_logging": {
        "en": ["water logging on the stretch", "road flooded with water"],
        "hi": ["सड़क पर पानी भर गया", "बारिश से जलभराव"],
        "kn": ["ರಸ್ತೆಯಲ್ಲಿ ನೀರು ನಿಂತಿದೆ", "ಮಳೆಯಿಂದ ನೀರು ತುಂಬಿದೆ"],
        "hinglish": ["road par paani bhar gaya", "barish se jalbharav"],
    },
    "pot_holes": {
        "en": ["pothole on the road", "damaged road surface"],
        "hi": ["सड़क पर गड्ढा है", "सड़क टूटी हुई है"],
        "kn": ["ರಸ್ತೆಯಲ್ಲಿ ಗುಂಡಿ ಬಿದ್ದಿದೆ", "ರಸ್ತೆ ಹಾಳಾಗಿದೆ"],
        "hinglish": ["road par gaddha hai", "road tooti hai"],
    },
    "public_event": {
        "en": ["public event procession", "rally on the road"],
        "hi": ["जुलूस निकल रहा है", "रैली सड़क पर"],
        "kn": ["ಮೆರವಣಿಗೆ ನಡೆಯುತ್ತಿದೆ", "ರ್ಯಾಲಿ ರಸ್ತೆಯಲ್ಲಿ"],
        "hinglish": ["juloos nikal raha", "rally road par"],
    },
    "others": {
        "en": ["incident reported", "obstruction on the road"],
        "hi": ["कोई घटना हुई है", "सड़क पर रुकावट"],
        "kn": ["ಘಟನೆ ವರದಿಯಾಗಿದೆ", "ರಸ್ತೆಯಲ್ಲಿ ಅಡಚಣೆ"],
        "hinglish": ["incident hua hai", "road par rukawat"],
    },
}

# Each urgency phrase MUST contain that tier's cue words (see preprocessing tier lexicons).
URGENCY_PHRASES = {
"minor": {
"en": [
"minor issue, slight delay, all clear soon",
"small obstruction, traffic moving, no one hurt",
"minor problem, slight delay, nearly cleared",
"small matter, normal movement on the road",
"minor, traffic moving, all fine",
],
"hi": [
"मामूली बात, हल्की देरी, सब ठीक",
"छोटी सी दिक्कत, सामान्य, कोई परेशानी नहीं",
"मामूली रुकावट, हल्का धीमा, जल्दी साफ",
"छोटा मसला, यातायात सामान्य",
"हल्की समस्या, मामूली देरी",
],
"kn": [
"ಸಣ್ಣ ಸಮಸ್ಯೆ, ಸ್ವಲ್ಪ ವಿಳಂಬ, ಶೀಘ್ರ ಸರಿ",
"ಚಿಕ್ಕ ಅಡಚಣೆ, ಸಂಚಾರ ಸಾಮಾನ್ಯ",
"ಲಘು ಸಮಸ್ಯೆ, ಸ್ವಲ್ಪ ವಿಳಂಬ",
"ಸಣ್ಣ ವಿಷಯ, ಸಾಮಾನ್ಯ ಚಲನೆ",
"ಚಿಕ್ಕ ತೊಂದರೆ, ಎಲ್ಲ ಸರಿ",
],
"hinglish": [
"minor issue, slight delay, sab thik",
"small problem, traffic moving, normal",
"mamuli baat, thoda delay, jaldi clear",
"chhoti dikkat, traffic normal",
"minor hai, moving, all fine",
],
},
"moderate": {
"en": [
"lane partially blocked, congestion building, slow moving",
"traffic jam forming, partially blocked, long queue",
"road partially blocked, heavy congestion, diversion in place",
"slow traffic, tailback building, one lane stuck",
"congestion on the stretch, vehicles crawling",
],
"hi": [
"रास्ता आंशिक रूप से रुका, जाम लग रहा, धीमा",
"यातायात धीमा, भीड़ बढ़ रही, रुकावट",
"एक लेन रुकी, लंबा जाम, धीमी रफ्तार",
"सड़क पर भीड़, गाड़ियां रेंग रहीं",
"आंशिक रुकावट, जाम बढ़ रहा",
],
"kn": [
"ರಸ್ತೆ ಭಾಗಶಃ ಬ್ಲಾಕ್, ದಟ್ಟಣೆ ಹೆಚ್ಚುತ್ತಿದೆ, ನಿಧಾನ",
"ಟ್ರಾಫಿಕ್ ಜಾಮ್, ಭಾಗಶಃ ತಡೆ, ಉದ್ದ ಸಾಲು",
"ಒಂದು ಲೇನ್ ಬ್ಲಾಕ್, ನಿಧಾನ ಸಂಚಾರ",
"ರಸ್ತೆಯಲ್ಲಿ ದಟ್ಟಣೆ, ವಾಹನ ತೆವಳುತ್ತಿವೆ",
"ಭಾಗಶಃ ಅಡಚಣೆ, ಜಾಮ್ ಹೆಚ್ಚುತ್ತಿದೆ",
],
"hinglish": [
"lane partially blocked, jam lag raha, slow",
"traffic jam forming, congestion ho rahi",
"ek lane stuck, lamba jam, slow",
"road par bheed, gaadiyan reng rahi",
"partial rukawat, jam badh raha",
],
},
"serious": {
"en": [
"people injured, ambulance requested, lane blocked",
"collision with injuries, ambulance on the way",
"accident reported, several injured, traffic halted",
"crash with casualties, blood on road, ambulance needed",
"injured passengers, ambulance dispatched, road blocked",
],
"hi": [
"लोग घायल, एम्बुलेंस चाहिए, लेन रुकी",
"टक्कर में घायल, एम्बुलेंस आ रही",
"दुर्घटना, कई घायल, यातायात रुका",
"हादसे में घायल, खून बह रहा, एम्बुलेंस बुलाओ",
"घायल यात्री, एम्बुलेंस भेजी, सड़क रुकी",
],
"kn": [
"ಜನ ಗಾಯಗೊಂಡಿದ್ದಾರೆ, ಆಂಬುಲೆನ್ಸ್ ಬೇಕು, ಲೇನ್ ಬ್ಲಾಕ್",
"ಡಿಕ್ಕಿಯಲ್ಲಿ ಗಾಯ, ಆಂಬುಲೆನ್ಸ್ ಬರುತ್ತಿದೆ",
"ಅಪಘಾತ, ಹಲವರು ಗಾಯ, ಸಂಚಾರ ಸ್ತಬ್ಧ",
"ಅಪಘಾತದಲ್ಲಿ ಗಾಯ, ರಕ್ತ, ಆಂಬುಲೆನ್ಸ್ ಬೇಕು",
"ಗಾಯಗೊಂಡ ಪ್ರಯಾಣಿಕರು, ಆಂಬುಲೆನ್ಸ್ ಕಳುಹಿಸಿ",
],
"hinglish": [
"log injured, ambulance chahiye, lane blocked",
"collision me injured, ambulance aa rahi",
"accident, kai injured, traffic ruka",
"hadse me injured, khoon, ambulance bulao",
"injured passengers, ambulance bheji, road blocked",
],
},
"severe": {
"en": [
"fatal crash, multiple people dead, fire reported",
"vehicle overturned, passengers trapped, critical injuries",
"head-on collision, severe damage, one dead at the scene",
"tanker caught fire, explosion risk, people trapped",
"major accident, several critical, ambulances on site",
"car flipped over, victims trapped inside, road fully blocked",
],
"hi": [
"भीषण दुर्घटना, कई घायल, गाड़ी पलट गई",
"गंभीर हादसा, लोग फंसे हैं, आग लग गई",
"घातक टक्कर, एक की मौत, एम्बुलेंस चाहिए",
"गाड़ी में आग, लोग अंदर फंसे, हालत गंभीर",
"भयानक एक्सीडेंट, कई घायल, रास्ता बंद",
"गंभीर रूप से घायल, मौके पर मौत, टक्कर",
],
"kn": [
"ಭೀಕರ ಅಪಘಾತ, ಹಲವರು ಗಾಯ, ವಾಹನ ಪಲ್ಟಿ",
"ಗಂಭೀರ ಅಪಘಾತ, ಜನ ಸಿಲುಕಿದ್ದಾರೆ, ಬೆಂಕಿ",
"ಮಾರಣಾಂತಿಕ ಡಿಕ್ಕಿ, ಒಬ್ಬರ ಸಾವು, ಆಂಬುಲೆನ್ಸ್",
"ವಾಹನಕ್ಕೆ ಬೆಂಕಿ, ಜನ ಒಳಗೆ ಸಿಲುಕಿ, ಗಂಭೀರ",
"ಭೀಕರ ಅಪಘಾತ, ಹಲವರು ಗಾಯ, ರಸ್ತೆ ಬಂದ್",
"ಗಂಭೀರ ಗಾಯ, ಸ್ಥಳದಲ್ಲೇ ಸಾವು, ಡಿಕ್ಕಿ",
],
"hinglish": [
"fatal crash, kai log dead, fire",
"gaadi overturned, log trapped, critical injuries",
"head-on collision, severe damage, ek dead",
"tanker me fire, explosion risk, log trapped",
"major accident, several critical, ambulance on site",
"car flip, log trapped, road fully blocked",
],
},
}

CLOSURE_PHRASES = {
    "en": ["road closure required, fully blocked", "road closed completely"],
    "hi": ["रास्ता पूरी तरह बंद", "सड़क बंद करनी पड़ेगी"],
    "kn": ["ರಸ್ತೆ ಸಂಪೂರ್ಣ ಬಂದ್", "ರಸ್ತೆ ಬಂದ್ ಮಾಡಬೇಕು"],
    "hinglish": ["road closure required, fully blocked", "raasta poori tarah band"],
}

def _pick_lang(rng) -> str:
    names = [l for l, _ in LANG_WEIGHTS]
    probs = [p for _, p in LANG_WEIGHTS]
    return names[int(rng.choice(len(names), p=probs))]

def compose_description(rng, cause: str, closure: bool, urgency: str) -> str:
    """Cause phrase + tier-aligned urgency phrase (+ optional closure), in one language style."""
    lang = _pick_lang(rng)
    cause_bank = CAUSE_PHRASES.get(cause, CAUSE_PHRASES["others"])[lang]
    urg_bank = URGENCY_PHRASES[urgency][lang]
    text = f"{rng.choice(cause_bank)}; {rng.choice(urg_bank)}"
    if closure:
        text += "; " + str(rng.choice(CLOSURE_PHRASES[lang]))
    return text
