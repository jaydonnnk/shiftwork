"""Fail closed when a serialized learner-visible surface contains a private needle."""

import base64
import json


def _decoded_parts(surface: object) -> list[str]:
    parts: list[str] = []
    if isinstance(surface, dict):
        for key, value in surface.items():
            if isinstance(value, str) and key.endswith("_base64"):
                try:
                    parts.append(base64.b64decode(value, validate=True).decode("utf-8", errors="replace"))
                except (ValueError, UnicodeError):
                    pass
            parts.extend(_decoded_parts(value))
    elif isinstance(surface, (list, tuple)):
        for value in surface:
            parts.extend(_decoded_parts(value))
    elif isinstance(surface, bytes):
        parts.append(surface.decode("utf-8", errors="replace"))
    elif isinstance(surface, str) and ";base64," in surface:
        try:
            parts.append(base64.b64decode(surface.split(";base64,", 1)[1], validate=True).decode("utf-8", errors="replace"))
        except (ValueError, UnicodeError):
            pass
    return parts


def serialized_contains(surface: object, needle: str) -> bool:
    if not needle:
        return False
    serialized = json.dumps(surface, ensure_ascii=False, sort_keys=True, default=str)
    serialized += "\n" + "\n".join(_decoded_parts(surface))
    forms = {needle, needle.replace("\\", "/"),
             base64.b64encode(needle.encode("utf-8")).decode("ascii")}
    for ensure_ascii in (False, True):
        escaped = needle
        for _ in range(3):
            escaped = json.dumps(escaped, ensure_ascii=ensure_ascii)[1:-1]
            forms.add(escaped)
    return any(form and form in serialized for form in forms)


def assert_public_safe(surface: object, needles: tuple[str, ...]) -> None:
    if any(serialized_contains(surface, needle) for needle in needles if needle):
        raise ValueError("public surface contains private material")
