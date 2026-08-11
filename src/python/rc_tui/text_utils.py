from wcwidth import wcswidth, wcwidth


def display_width(text: str) -> int:
    return max(0, wcswidth(text))


def truncate_to_width(text: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    w = 0
    result = []
    for ch in text:
        cw = max(0, wcwidth(ch))
        if w + cw > max_width:
            break
        w += cw
        result.append(ch)
    return "".join(result)


def split_by_width(text: str, width: int) -> list[str]:
    if width <= 0:
        return [text]
    result = []
    w = 0
    chunk = []
    for ch in text:
        cw = max(0, wcwidth(ch))
        if w + cw > width and chunk:
            result.append("".join(chunk))
            chunk = []
            w = 0
        if cw > 0:
            w += cw
            chunk.append(ch)
        elif cw == 0 and chunk:
            chunk.append(ch)
    if chunk:
        result.append("".join(chunk))
    if not result:
        return [""]
    return result


def wrap_by_width(text: str, max_width: int) -> list[str]:
    """
    Display-width-aware word wrap.
    Wraps at word boundaries (whitespace), respecting display width of each char.
    Falls back to char-wrap if a single word is wider than max_width.
    """
    if max_width <= 0:
        return [text]
    result = []
    for line in text.split("\n"):
        if display_width(line) <= max_width:
            result.append(line)
            continue
        words = line.split(" ")
        current = ""
        current_w = 0
        for word in words:
            word_w = display_width(word)
            sep_w = display_width(" ") if current else 0
            if current_w + sep_w + word_w > max_width:
                if current:
                    result.append(current)
                # If the word itself is wider than max_width, char-wrap it
                if word_w > max_width:
                    for chunk in split_by_width(word, max_width):
                        result.append(chunk)
                    current = ""
                    current_w = 0
                else:
                    current = word
                    current_w = word_w
            else:
                if current:
                    current += " "
                    current_w += 1
                current += word
                current_w += word_w
        if current:
            result.append(current)
    if not result:
        return [""]
    return result
