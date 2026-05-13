"""
Prompt injection detector.
Detects common prompt injection and jailbreak patterns.
"""

from __future__ import annotations
import re
from ..exceptions import PromptInjectionError

# Patterns that indicate prompt injection attempts
INJECTION_PATTERNS: list[tuple[str, str]] = [
    # Instruction override attempts
    (r"ignore\s+(all\s+)?(previous|prior|above|earlier)\s+instructions?", "instruction override"),
    (r"disregard\s+(all\s+)?(previous|prior|above)\s+instructions?", "instruction override"),
    (r"forget\s+(all\s+)?(previous|prior|above)\s+instructions?", "instruction override"),
    (r"you\s+are\s+now\s+(?:a\s+)?(?:different|new|another|an?\s+)", "persona override"),

    # System prompt extraction
    (r"(print|repeat|show|reveal|tell me|output)\s+(your\s+)?(system\s+prompt|instructions?|prompt)", "system prompt extraction"),
    (r"what\s+(are\s+)?your\s+(system\s+)?(prompt|instructions?)", "system prompt extraction"),

    # Role/DAN jailbreaks
    (r"\bDAN\b", "DAN jailbreak"),
    (r"do\s+anything\s+now", "DAN jailbreak"),
    (r"jailbreak", "jailbreak attempt"),
    (r"developer\s+mode", "developer mode jailbreak"),

    # Instruction injection via context
    (r"</?(system|user|assistant|human|ai)>", "XML injection"),
    (r"\[INST\]|\[/INST\]", "instruction tag injection"),
    (r"<\|im_start\|>|<\|im_end\|>", "special token injection"),

    # Task hijacking
    (r"new\s+task\s*:", "task hijacking"),
    (r"actual\s+instructions?\s*:", "task hijacking"),
    (r"real\s+instructions?\s*:", "task hijacking"),
]

_COMPILED = [(re.compile(pattern, re.IGNORECASE), label) for pattern, label in INJECTION_PATTERNS]


def check_prompt_injection(text: str) -> list[str]:
    """
    Returns list of detected injection pattern labels.
    Empty list means clean.
    """
    detected = []
    for pattern, label in _COMPILED:
        if pattern.search(text):
            if label not in detected:
                detected.append(label)
    return detected


def enforce_no_injection(text: str):
    """Raise PromptInjectionError if injection is detected."""
    detected = check_prompt_injection(text)
    if detected:
        raise PromptInjectionError(detected[0])
