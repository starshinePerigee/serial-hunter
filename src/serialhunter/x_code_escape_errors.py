"""
This is a codec error handler that replaces on-ascii bytes are shown as hex numbers prefixed by "˟", such as ˟F8

This is mostly for use with the pretty unicode codec, to make reading raw serial data slightly friendlier.
"""

from typing import Union, Tuple
import codecs

from serialhunter import BYTESTRING_CHARACTER


def x_code_escape_errors(
    e: Union[UnicodeDecodeError, UnicodeEncodeError]
) -> Tuple[str, int]:
    if isinstance(e.object, str):
        # we are encoding a string
        # re-encoding with backslashreplace isn't great for performance
        # but also I'm not sure if this code path will ever get used?

        cross_char = BYTESTRING_CHARACTER.encode(e.encoding, errors="ignore")
        if not cross_char:
            cross_char = b"x"

        re_encoded_str = e.object.encode(e.encoding, errors="backslashreplace")
        re_encoded_str = re_encoded_str.replace(b"\\U", cross_char)
        return re_encoded_str, e.end

    sub = BYTESTRING_CHARACTER + e.object[e.start : e.end].hex().upper()
    return sub, e.end


codecs.register_error("uxreplace", x_code_escape_errors)
