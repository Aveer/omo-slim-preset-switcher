from __future__ import annotations

import json


def strip_comments(text: str) -> str:
    out: list[str] = []
    i = 0
    in_string = False
    escaped = False
    line_comment = False
    block_comment = False

    while i < len(text):
        char = text[i]
        nxt = text[i + 1] if i + 1 < len(text) else ""

        if line_comment:
            if char in "\r\n":
                line_comment = False
                out.append(char)
            else:
                out.append(" ")
            i += 1
            continue

        if block_comment:
            if char == "*" and nxt == "/":
                out.extend((" ", " "))
                block_comment = False
                i += 2
                continue
            out.append(char if char in "\r\n" else " ")
            i += 1
            continue

        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            i += 1
            continue

        if char == '"':
            in_string = True
            out.append(char)
            i += 1
            continue

        if char == "/" and nxt == "/":
            out.extend((" ", " "))
            line_comment = True
            i += 2
            continue

        if char == "/" and nxt == "*":
            out.extend((" ", " "))
            block_comment = True
            i += 2
            continue

        out.append(char)
        i += 1

    return "".join(out)


def remove_trailing_commas(text: str) -> str:
    chars = list(text)
    i = 0
    in_string = False
    escaped = False

    while i < len(chars):
        char = chars[i]

        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            i += 1
            continue

        if char == '"':
            in_string = True
            i += 1
            continue

        if char == ",":
            j = i + 1
            while j < len(chars) and chars[j].isspace():
                j += 1
            if j < len(chars) and chars[j] in "}]":
                chars[i] = " "

        i += 1

    return "".join(chars)


def loads(text: str) -> dict[str, object]:
    value = json.loads(remove_trailing_commas(strip_comments(text)))
    if not isinstance(value, dict):
        raise ValueError("Configuration root must be a JSON object.")
    return value


def _skip_ws_and_comments(text: str, start: int) -> int:
    i = start
    while i < len(text):
        if text[i].isspace():
            i += 1
            continue
        if text.startswith("//", i):
            newline = text.find("\n", i + 2)
            i = len(text) if newline < 0 else newline + 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise ValueError("Unterminated block comment.")
            i = end + 2
            continue
        break
    return i


def _string_end(text: str, start: int) -> int:
    if start >= len(text) or text[start] != '"':
        raise ValueError("Expected JSON string.")

    i = start + 1
    escaped = False
    while i < len(text):
        char = text[i]
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif char == '"':
            return i + 1
        i += 1
    raise ValueError("Unterminated JSON string.")


def _top_level_string_value_span(
    text: str, property_name: str
) -> tuple[int, int] | None:
    i = 0
    depth = 0

    while i < len(text):
        char = text[i]

        if text.startswith("//", i):
            newline = text.find("\n", i + 2)
            i = len(text) if newline < 0 else newline + 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise ValueError("Unterminated block comment.")
            i = end + 2
            continue

        if char == '"':
            end = _string_end(text, i)
            if depth == 1:
                try:
                    key = json.loads(text[i:end])
                except json.JSONDecodeError:
                    key = None
                if key == property_name:
                    colon = _skip_ws_and_comments(text, end)
                    if colon < len(text) and text[colon] == ":":
                        value_start = _skip_ws_and_comments(text, colon + 1)
                        if value_start < len(text) and text[value_start] == '"':
                            return value_start, _string_end(text, value_start)
            i = end
            continue

        if char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
            if depth < 0:
                raise ValueError("Malformed JSON structure.")

        i += 1

    return None


def _top_level_string_member_span(
    text: str, property_name: str
) -> tuple[int, int] | None:
    i = 0
    depth = 0

    while i < len(text):
        char = text[i]

        if text.startswith("//", i):
            newline = text.find("\n", i + 2)
            i = len(text) if newline < 0 else newline + 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise ValueError("Unterminated block comment.")
            i = end + 2
            continue

        if char == '"':
            key_start = i
            end = _string_end(text, i)
            if depth == 1:
                try:
                    key = json.loads(text[i:end])
                except json.JSONDecodeError:
                    key = None
                if key == property_name:
                    colon = _skip_ws_and_comments(text, end)
                    if colon < len(text) and text[colon] == ":":
                        value_start = _skip_ws_and_comments(text, colon + 1)
                        if value_start < len(text) and text[value_start] == '"':
                            return key_start, _string_end(text, value_start)
            i = end
            continue

        if char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
            if depth < 0:
                raise ValueError("Malformed JSON structure.")

        i += 1

    return None


def _top_level_commas(text: str) -> list[int]:
    commas: list[int] = []
    i = 0
    depth = 0

    while i < len(text):
        char = text[i]
        if text.startswith("//", i):
            newline = text.find("\n", i + 2)
            i = len(text) if newline < 0 else newline + 1
            continue
        if text.startswith("/*", i):
            end = text.find("*/", i + 2)
            if end < 0:
                raise ValueError("Unterminated block comment.")
            i = end + 2
            continue
        if char == '"':
            i = _string_end(text, i)
            continue
        if char in "{[":
            depth += 1
        elif char in "}]":
            depth -= 1
        elif char == "," and depth == 1:
            commas.append(i)
        i += 1

    return commas


def remove_top_level_string(text: str, property_name: str) -> str:
    loads(text)
    span = _top_level_string_member_span(text, property_name)
    if span is None:
        return text

    member_start, value_end = span
    line_start = max(text.rfind("\n", 0, member_start), text.rfind("\r", 0, member_start)) + 1
    remove_start = (
        line_start
        if text[line_start:member_start].strip() == ""
        else member_start
    )

    after = _skip_ws_and_comments(text, value_end)
    if after < len(text) and text[after] == ",":
        remove_end = after + 1
        updated = text[:remove_start] + text[remove_end:]
    else:
        previous = [comma for comma in _top_level_commas(text) if comma < member_start]
        if previous:
            comma = previous[-1]
            updated = text[:comma] + text[comma + 1 : remove_start] + text[value_end:]
        else:
            updated = text[:remove_start] + text[value_end:]

    loads(updated)
    return updated


def set_top_level_string(text: str, property_name: str, value: str) -> str:
    loads(text)
    encoded = json.dumps(value, ensure_ascii=False)
    span = _top_level_string_value_span(text, property_name)

    if span is not None:
        start, end = span
        updated = text[:start] + encoded + text[end:]
        loads(updated)
        return updated

    start = _skip_ws_and_comments(text, 0)
    if start >= len(text) or text[start] != "{":
        raise ValueError("Configuration root must be a JSON object.")

    newline = "\r\n" if "\r\n" in text else "\n"
    first = _skip_ws_and_comments(text, start + 1)

    if first < len(text) and text[first] == "}":
        insertion = f'{newline}  "{property_name}": {encoded}{newline}'
    else:
        insertion = f'{newline}  "{property_name}": {encoded},'

    updated = text[: start + 1] + insertion + text[start + 1 :]
    loads(updated)
    return updated
