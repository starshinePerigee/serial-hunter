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

import codecs


def unicode_x_escape_errors(e: UnicodeDecodeError):
    sub = "˟" + e.object[e.start : e.end].hex()
    return sub, e.end


codecs.register_error("uxreplace", unicode_x_escape_errors)


if __name__ == "__main__":
    str1 = "this is a bad character: 0123456789".encode("ascii")
    str2 = "0123456789".encode("ascii")
    bad_char = (129).to_bytes(1, "little")

    bad_str = str1 + bad_char + str2

    print(bad_str.decode("ascii", "uxreplace"))
