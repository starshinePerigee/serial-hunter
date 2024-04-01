"""
This codec converts from a string of bytes that is "probably" ASCII to a prettier, human-readable unicode text stream
that shows whitespace.

For instance, important control characters (such as NULL) are shown as "␀" and space is shown as "·".
Specific glyphs were chosen for compatibility with cosette's character map:
https://github.com/slavfox/Cozette/blob/main/img/charmap.txt

Non-ascii bytes are shown as hex numbers prefixed by "˟", such as ˟F8

When printing to terminal, serial-hunter makes a second pass that then specifically handles newlines,
replacing port-dependent "newline" with os.newline

Reference https://pymotw.com/3/codecs/index.html#defining-a-custom-encoding
"""

from typing import Union
import codecs


def x_code_escape_errors(e: Union[UnicodeDecodeError, UnicodeEncodeError]):
    if isinstance(e.object, str):
        # we are encoding a string
        # re-encoding with backslashreplace isn't great for performance
        # but also I'm not sure if this code path will ever get used?

        cross_char = "˟".encode(e.encoding, errors="ignore")
        if not cross_char:
            cross_char = b"x"

        re_encoded_str = e.object.encode(e.encoding, errors="backslashreplace")
        re_encoded_str = re_encoded_str.replace(b"\\U", cross_char)
        return re_encoded_str, e.end

    sub = "˟" + e.object[e.start : e.end].hex().upper()
    return sub, e.end


codecs.register_error("uxreplace", x_code_escape_errors)
