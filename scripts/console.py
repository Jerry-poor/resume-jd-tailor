import sys


def safe_print(*parts: object, sep: str = " ", end: str = "\n") -> None:
    text = sep.join(str(p) for p in parts) + end
    try:
        sys.stdout.write(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8", errors="backslashreplace"))
