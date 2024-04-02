"""
This codec converts from a string of bytes that is "probably" ASCII to a prettier, human-readable unicode text stream
that shows whitespace and has line continuation.

For instance, important control characters (such as NULL) are shown as "␀" and space is shown as "·".
Specific glyphs were chosen for compatibility with cosette's character map:
https://github.com/slavfox/Cozette/blob/main/img/charmap.txt

Newlines work by printing both CR and LF as their respective symbols, then inserting a single LF character (\n)
On the encode side, all sequential CRs, LFs, and "↲"s are converted to single LF

Error codes from 0 to 256 are encoded, which makes sure we can pretty -> depretty, and also
handle any 8-bit encoding run with uxreplace error handling. Anything weirder is non-reversible and will
send junk data.

For valid ascii, encode("prettyascii") == encode("ascii") except for line terminators, which are single \ns always
"""

import codecs
from typing import Tuple

from serialhunter import BYTESTRING_CHARACTER, NEWLINE_CHARACTER

COLUMN_WIDTH = 80

ESCAPE_SEQUENCES = {n: f"{BYTESTRING_CHARACTER}{n:x}" for n in range(256)}
BASE_ASCII = {n: chr(n) for n in range(128)}
CHAR_UPDATE_DICT = {
    0x00: "␀",
    0x08: "␈",
    0x09: "\t→",
    0x0A: "␍",
    0x0B: "␋",
    0x0C: "␌",
    0x0D: "␊",
    0x0E: "␎",
    0x0F: "␏",
    0x1C: "␜",
    0x1D: "␝",
    0x1E: "␞",
    0x1F: "␟",
    0x20: "·",
    0x24: "␤",
    0x7F: "␡",
}

byte_to_chars = ESCAPE_SEQUENCES.copy()
byte_to_chars.update(BASE_ASCII)
byte_to_chars.update(CHAR_UPDATE_DICT)


# run dicts in order to overwrite

char_to_bytes = {
    char: byte.to_bytes(1, "little")
    for byte, char in list(byte_to_chars.items()) + list(BASE_ASCII.items())
    if len(char) == 1
}


def encode_pretty(
    data: str,
    skip_next=False,
    skip_newlines=False,
    escape_count=0,
) -> Tuple[bytes, bool, bool, int]:
    """Convert a string (possibly containing prettified values) into bytes"""
    out_bytes = bytes()
    escape_buffer = ""
    for i, c in enumerate(data):
        if skip_next:
            skip_next = False
            continue

        # check for line continuation:
        if c == NEWLINE_CHARACTER:
            skip_next = True
            continue

        # check for newline options:
        if c in ["\r", "\n", "␍", "␊"]:
            if not skip_newlines:
                out_bytes += b"\n"
                skip_newlines = True
            continue
        skip_newlines = False

        # check for escape strings (of the type ˟FF)
        if c == BYTESTRING_CHARACTER:
            # we have an escape string
            if escape_count > 0:
                raise UnicodeEncodeError(
                    __encoding="prettyascii",
                    __object=data,
                    __start=i - len(escape_buffer) - 1,
                    __end=i + 1,
                    __reason=f"Invalid escape char: {c} with buffer {escape_buffer}",
                )
            escape_count = 2
            continue
        if escape_count:
            escape_buffer += c
            escape_count -= 1
            if escape_count == 0:
                out_bytes += int(escape_buffer, 16).to_bytes(1, "little")
                escape_buffer = ""
            continue

        # check for tab symbol:
        if c == "→":
            continue

        out_bytes += char_to_bytes[c]

    return out_bytes, skip_next, skip_newlines, escape_count


def decode_pretty(data: bytes, was_newline=False) -> Tuple[str, bool]:
    out_str = ""
    # time_since_last_break = 0
    for b in data:
        is_newline = b in (10, 13)
        next_chars = byte_to_chars[b]

        # time_since_last_break += len(next_chars)
        # if time_since_last_break >= COLUMN_WIDTH:
        #     out_str += NEWLINE_CHARACTER + "\n"
        #     time_since_last_break = 0

        if not is_newline and was_newline:
            out_str += "\n"
            time_since_last_break = 0
        was_newline = is_newline

        out_str += next_chars
    return out_str, was_newline


def encode_pretty_fn(data: str, errors: "strict"):
    return encode_pretty(data)[0], len(data)


def decode_pretty_fn(data: bytes, errors: "strict"):
    return decode_pretty(data)[0], len(data)


class PrettyCodec(codecs.Codec):
    def encode(self, data, errors="strict"):
        return encode_pretty(data)

    def decode(self, data, errors="strict"):
        return decode_pretty(data)


class PrettyIncrementalEncoder(codecs.IncrementalEncoder):
    """Handles byte streams incrementally (byte by byte) with state management"""

    def __init__(self, errors="strict"):
        super().__init__(errors)
        self.skip_next = False
        self.skip_newlines = False
        self.escape_count = 0

    def reset(self):
        self.skip_next = False
        self.skip_newlines = False
        self.escape_count = 0

    def getstate(self):
        # reminder that since getstate and setstate must return int, we have to do some packing here:
        return (
            "",
            int(self.skip_next) + int(self.skip_newlines) * 2 + self.escape_count * 4,
        )

    def setstate(self, state: tuple):
        buffer_, statevars = state
        self.skip_next = bool(statevars % 2)
        self.skip_newlines = bool((statevars // 2) % 4)
        self.escape_count = statevars // 4

    def encode(self, data, final=False):
        return_bytes, self.skip_next, self.skip_newlines, self.escape_count = (
            encode_pretty(data, self.skip_next, self.skip_newlines, self.escape_count)
        )
        if final and self.escape_count:
            raise RuntimeError(
                "Error decoding - final escape character not followed by two valid hex characters!"
            )
        return return_bytes


class PrettyIncrementalDecoder(codecs.IncrementalDecoder):
    def __init__(self, errors="strict"):
        super().__init__(errors)
        self.was_newline = False

    def reset(self):
        self.was_newline = False

    def getstate(self):
        return b"", int(self.was_newline)

    def setstate(self, state):
        buffer_, statevars = state
        self.was_newline = bool(statevars)

    def decode(self, data, final=False):
        return_str, self.was_newline = decode_pretty(data, self.was_newline)
        return return_str


class StreamWriter(PrettyCodec, codecs.StreamWriter):
    """Implement a StreamWriter via multiple inheritance"""

    pass


class StreamReader(PrettyCodec, codecs.StreamReader):
    pass


def getregentry():
    return codecs.CodecInfo(
        name="prettyascii",
        encode=encode_pretty_fn,
        decode=decode_pretty_fn,
        incrementalencoder=PrettyIncrementalEncoder,
        incrementaldecoder=PrettyIncrementalDecoder,
        streamwriter=StreamWriter,
        streamreader=StreamReader,
    )


codecs.register(lambda c: getregentry() if c == "prettyascii" else None)
