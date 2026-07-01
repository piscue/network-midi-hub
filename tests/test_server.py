import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, _ROOT)

from server import looks_like_http  # noqa: E402


# ---------------------------------------------------------------------------
# looks_like_http — #10: server should detect HTTP requests
# ---------------------------------------------------------------------------

def test_http_get():
    assert looks_like_http(b'GET / HTTP/1.1\r\n') is True


def test_http_post():
    assert looks_like_http(b'POST /api HTTP/1.1\r\n') is True


def test_http_head():
    assert looks_like_http(b'HEAD / HTTP/1.0\r\n') is True


def test_http_put():
    assert looks_like_http(b'PUT /resource HTTP/1.1\r\n') is True


def test_http_delete():
    assert looks_like_http(b'DELETE /resource HTTP/1.1\r\n') is True


def test_http_options():
    assert looks_like_http(b'OPTIONS * HTTP/1.1\r\n') is True


def test_http_connect():
    assert looks_like_http(b'CONNECT example.com:443 HTTP/1.1\r\n') is True


def test_midi_note_on():
    # Wire format for a note_on: [status, note, velocity]
    assert looks_like_http(b'[144, 60, 100]') is False


def test_midi_transport():
    # Single-byte MIDI message (e.g. clock = 248)
    assert looks_like_http(b'[248]') is False


def test_empty_data():
    assert looks_like_http(b'') is False


def test_arbitrary_binary():
    assert looks_like_http(b'\x00\x01\x02\x03') is False
