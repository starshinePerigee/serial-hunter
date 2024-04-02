import pytest

from typing import Union

import serialhunter
from serialhunter.pretty_unicode_codec import decode_pretty, encode_pretty


def mangle_newlines(data: Union[str, bytes]) -> Union[str, bytes]:
    """
    Pretty unicode is not reversible, because it converts all newlines to \n and eats sequential newlines.
    This isn't a perfect replication, but it's close enough for most test cases
    """

    hack_r = "\r"
    hack_n = "\n"
    if isinstance(data, bytes):
        hack_r, hack_n = (c.encode("ascii") for c in (hack_r, hack_n))
    return data.replace(hack_r, hack_n).replace(hack_n + hack_n, hack_n)


@pytest.fixture
def bad_string():
    str1 = "this is a bad character: 0123456789".encode("ascii")
    str2 = "0123456789".encode("ascii")
    bad_char = (129).to_bytes(1, "little")
    return str1 + bad_char + str2


class TestXCodeEscapeErrors:

    def test_error_decode(self, bad_string):
        decoded_str = bad_string.decode("ascii", "uxreplace")

        assert "this is a bad character:" in decoded_str
        assert "0123456789˟810123456789" in decoded_str

    def test_error_decode_multiple(self, bad_string):
        bad_string += (129).to_bytes(1, "little") * 4
        decoded_str = bad_string.decode("ascii", errors="uxreplace") + "x"
        assert decoded_str[-14:] == "9" + "˟81" * 4 + "x"

    def test_error_encode_ascii(self):
        bad_str = "this is a unicode string: 0123456789🐋0123456789"
        encoded_str = bad_str.encode("ascii", "uxreplace")
        assert b"0123456789x0001f40b0123456789" in encoded_str
        assert b"this is a unicode string" in encoded_str


@pytest.fixture
def every_byte_pair():
    return b"".join([i.to_bytes(1, "little") for i in range(256)])


@pytest.fixture
def every_ascii_string(every_byte_pair):
    return every_byte_pair[:128].decode("ascii")


class TestEncodeDecodeMapping:
    def test_encode_coverage(self, every_ascii_string):
        encoded = encode_pretty(every_ascii_string)
        assert b"abcd" in encoded
        assert b"\n" in encoded
        assert len(every_ascii_string) == len(encoded)

    def test_decode_coverage(self, every_byte_pair):
        decoded = decode_pretty(every_byte_pair)
        assert "abcd" in decoded
        assert "\n" in decoded
        assert serialhunter.BYTESTRING_CHARACTER + "ff" in decoded

    def test_decode_encode(self, every_byte_pair):
        twisted_str = encode_pretty(decode_pretty(every_byte_pair))
        assert twisted_str == mangle_newlines(every_byte_pair)

    def test_encode_decode(self, every_ascii_string):
        """Unlike encoding decoded data, decoding encoded data is nonreversible - because the whole point
        of pretty codec is replacing ugly characters with unicode equivalents. Still, it shouldn't barf.
        """
        twisted_str = decode_pretty(encode_pretty(every_ascii_string))
        assert "ABCDEFGHIJKLMNOPQRSTUVWXYZ" in twisted_str
