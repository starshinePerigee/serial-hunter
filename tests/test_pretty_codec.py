import pytest

from serialhunter import x_code_escape_errors


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
