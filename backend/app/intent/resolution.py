"""Safe Resolution Pipeline, Typo Normalization, and Entity Disambiguation (Task 48)."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger("kairo.intent.resolution")


class SafeResolver:
    """Safely normalizes references, corrects typos, and prevents silent semantic shifts (Spec 161, 162)."""

    # Common development tool and entity typos
    KNOWN_CORRECTIONS = {
        "pythn": "python",
        "dockr": "docker",
        "kubernets": "kubernetes",
        "posgres": "postgres",
        "postgre": "postgres",
        "reds": "redis",
        "gihtub": "github",
        "deply": "deploy",
        "delte": "delete",
    }

    @classmethod
    def correct_obvious_typos(cls, text: str) -> tuple[str, List[Dict[str, str]]]:
        """Enforce Spec 161, 162: Correct obvious typos only when confidence is high; preserve provenance."""
        words = text.split()
        corrected_words = []
        corrections_made = []

        for word in words:
            clean_word = word.lower().strip(",.!?\"'")
            if clean_word in cls.KNOWN_CORRECTIONS:
                target = cls.KNOWN_CORRECTIONS[clean_word]
                corrected_words.append(target)
                corrections_made.append({"original": word, "corrected": target, "confidence": "0.95"})
                logger.info("Corrected obvious typo '%s' -> '%s'", word, target)
            else:
                corrected_words.append(word)

        return " ".join(corrected_words), corrections_made
