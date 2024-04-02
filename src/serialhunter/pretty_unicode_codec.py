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


def encode_pretty(data: str, errors="strict") -> bytes:
    """Convert a string (possibly containing prettified values) into bytes"""
    out_bytes = bytes()
    skip_next = False
    skip_newlines = False
    escape_count = 0
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

    return out_bytes


def decode_pretty(data: bytes, errors="strict") -> str:
    out_str = ""
    was_newline = False
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
    return out_str


#
#
# class Codec(codecs.Codec):
#     def encode(self, data, errors="strict"):
#         """'40 41 42' -> b'@ab'"""
#         return serial.to_bytes([int(h, 16) for h in data.split()])
#
#     def decode(self, data, errors="strict"):
#         """b'@ab' -> '40 41 42'"""
#         return unicode(
#             "".join("{:02X} ".format(ord(b)) for b in serial.iterbytes(data))
#         )
#
#
# class IncrementalEncoder(codecs.IncrementalEncoder):
#     """Incremental hex encoder"""
#
#     def __init__(self, errors="strict"):
#         self.errors = errors
#         self.state = 0
#
#     def reset(self):
#         self.state = 0
#
#     def getstate(self):
#         return self.state
#
#     def setstate(self, state):
#         self.state = state
#
#     def encode(self, data, final=False):
#         """\
#         Incremental encode, keep track of digits and emit a byte when a pair
#         of hex digits is found. The space is optional unless the error
#         handling is defined to be 'strict'.
#         """
#         state = self.state
#         encoded = []
#         for c in data.upper():
#             if c in HEXDIGITS:
#                 z = HEXDIGITS.index(c)
#                 if state:
#                     encoded.append(z + (state & 0xF0))
#                     state = 0
#                 else:
#                     state = 0x100 + (z << 4)
#             elif c == " ":  # allow spaces to separate values
#                 if state and self.errors == "strict":
#                     raise UnicodeError("odd number of hex digits")
#                 state = 0
#             else:
#                 if self.errors == "strict":
#                     raise UnicodeError("non-hex digit found: {!r}".format(c))
#         self.state = state
#         return serial.to_bytes(encoded)
#
#
# class IncrementalDecoder(codecs.IncrementalDecoder):
#     """Incremental decoder"""
#
#     def decode(self, data, final=False):
#         return unicode(
#             "".join("{:02X} ".format(ord(b)) for b in serial.iterbytes(data))
#         )
#
#
# class StreamWriter(Codec, codecs.StreamWriter):
#     """Combination of hexlify codec and StreamWriter"""
#
#
# class StreamReader(Codec, codecs.StreamReader):
#     """Combination of hexlify codec and StreamReader"""
#
#
# def getregentry():
#     """encodings module API"""
#     return codecs.CodecInfo(
#         name="hexlify",
#         encode=hex_encode,
#         decode=hex_decode,
#         incrementalencoder=IncrementalEncoder,
#         incrementaldecoder=IncrementalDecoder,
#         streamwriter=StreamWriter,
#         streamreader=StreamReader,
#         # ~ _is_text_encoding=True,
#     )
