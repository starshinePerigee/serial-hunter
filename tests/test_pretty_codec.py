import pytest

from serialhunter import pretty_codec


def test_error_decode():
    str1 = "this is a bad character: 0123456789".encode("ascii")
    str2 = "0123456789".encode("ascii")
    bad_char = (129).to_bytes(1, "little")
    bad_str = str1 + bad_char + str2

    decoded_str = bad_str.decode("ascii", "uxreplace")

    assert "this is a bad character:" in decoded_str
    assert "0123456789˟810123456789" in decoded_str
