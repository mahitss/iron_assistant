"""Command normalization preserving raw input and cleaning benign artifacts (Spec 6, 7, 8, 100)."""

import re


class CommandNormalizer:
    """Normalizes harmless formatting while strictly preserving semantic meaning and raw input."""

    # Benign speech-to-text conversational fillers and hesitations
    SPEECH_FILLERS = re.compile(r"\b(uh+|um+|ah+|er+|like(?=,)|you know)\b", re.IGNORECASE)

    # Wake-word prefixes at the beginning of commands
    WAKE_WORDS = re.compile(r"^(hey\s+kairo|kairo|ok\s+kairo|hello\s+kairo)[\s,:\-]*", re.IGNORECASE)

    @classmethod
    def normalize(cls, raw_text: str) -> tuple[str, str]:
        """
        Normalize input string.
        Returns:
            (original_text, normalized_text)
        Strictly preserves original_text unaltered.
        """
        if raw_text is None:
            raw_text = ""

        original = raw_text
        clean = raw_text.strip()

        # 1. Strip leading wake word prefixes for cleaner intent parsing
        text = cls.WAKE_WORDS.sub("", clean).strip()
        if not text:
            text = clean

        # 2. Clean benign speech-to-text fillers and trailing commas
        text = re.sub(r"\b(uh+|um+|ah+|er+|like|you\s+know)\b[\s,]*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"^[\s,]+", "", text)
        text = re.sub(r",\s*,+", ",", text)

        # 3. Collapse duplicate consecutive identical words from stutters (e.g. "the the" -> "the")
        text = re.sub(r"\b([a-zA-Z]+)\s+\1\b", r"\1", text, flags=re.IGNORECASE)

        # 4. Collapse multiple whitespace and normalize tabs/newlines
        text = re.sub(r"\s+", " ", text).strip()

        # 5. Clean unnecessary repeated punctuation (e.g. "???" -> "?", "!!!" -> "!")
        text = re.sub(r"\?+", "?", text)
        text = re.sub(r"!+", "!", text)
        text = re.sub(r"^[\s,]+", "", text).strip()

        return original, text
