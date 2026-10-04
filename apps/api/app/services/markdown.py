"""Protect literal Markdown code while processing editorial prose."""
import re
from dataclasses import dataclass

@dataclass(frozen=True)
class Fence:
    start: int
    end: int
    language: str
    closed: bool


def fences(text: str) -> list[Fence]:
    result = []
    opening = None
    offset = 0
    for line in text.splitlines(keepends=True):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})([^\n]*)", line)
        if opening is None and match:
            marker, info = match.groups()
            if marker[0] != "`" or "`" not in info:
                opening = (offset, marker, info.strip())
        elif opening and match:
            marker, info = match.groups()
            if marker[0] == opening[1][0] and len(marker) >= len(opening[1]) and not info.strip():
                result.append(Fence(opening[0], offset + len(line), opening[2], True))
                opening = None
        offset += len(line)
    if opening:
        result.append(Fence(opening[0], len(text), opening[2], False))
    return result


def without_fenced_code(text: str) -> str:
    for block in reversed(fences(text)):
        text = text[:block.start] + "\n" + text[block.end:]
    return text


def transform_prose(text: str, transform) -> str:
    parts = []
    offset = 0
    # Inline literals also must not be interpreted as editorial reference markers.
    inline = re.compile(r"(`+)(?!`)(.+?)(?<!`)\1(?!`)", re.DOTALL)
    def process(prose):
        position = 0
        chunks = []
        for match in inline.finditer(prose):
            chunks.extend((transform(prose[position:match.start()]), match.group()))
            position = match.end()
        chunks.append(transform(prose[position:]))
        return "".join(chunks)
    for block in fences(text):
        parts.extend((process(text[offset:block.start]), text[block.start:block.end]))
        offset = block.end
    parts.append(process(text[offset:]))
    return "".join(parts)
