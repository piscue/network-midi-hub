import os
import sys
import pytest

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, _ROOT)

from client import (  # noqa: E402
    matches_transport,
    check_transports,
    check_messages,
    review_data,
    receive_messages,
    get_args,
)


# ---------------------------------------------------------------------------
# get_args
# ---------------------------------------------------------------------------

def test_get_args_defaults(monkeypatch):
    monkeypatch.setattr('sys.argv', ['client.py'])
    args = get_args()
    assert args.host == '127.0.0.1'
    assert args.port == 8141
    assert args.thru is False


def test_get_args_custom(monkeypatch):
    monkeypatch.setattr(
        'sys.argv', ['client.py', '--host', '10.0.0.1', '-p', '9000']
    )
    args = get_args()
    assert args.host == '10.0.0.1'
    assert args.port == 9000


# ---------------------------------------------------------------------------
# matches_transport / check_transports
# ---------------------------------------------------------------------------

def test_matches_transport():
    matches = matches_transport('[111]')
    assert len(matches) == 1
    matches = matches_transport('[111][112]')
    assert len(matches) == 2
    assert matches == ['[111]', '[112]']
    # TODO messages between transport messages


def test_check_transports():
    msg_list = check_transports('[204][205]', [])
    assert len(msg_list) == 2


# ---------------------------------------------------------------------------
# check_messages / review_data
# ---------------------------------------------------------------------------

def test_check_messages_single():
    msgs = check_messages('[144, 60, 100]', [])
    assert msgs == ['[144, 60, 100]']


def test_check_messages_multiple():
    msgs = check_messages('[144, 60, 100][128, 60, 0]', [])
    assert len(msgs) == 2


def test_review_data_mixed():
    # both transport ([nnn]) and message ([a, b, c]) in one chunk
    result = review_data('[204][144, 60, 100]')
    assert '[204]' in result
    assert '[144, 60, 100]' in result


# ---------------------------------------------------------------------------
# receive_messages — #16: empty recv must raise ConnectionResetError
# ---------------------------------------------------------------------------

class _FakeSock:
    """Minimal socket stub for unit tests."""
    def __init__(self, data):
        self._data = data

    def recv(self, size):
        return self._data


def test_receive_messages_empty_recv_raises():
    """Empty recv (server closed) must raise ConnectionResetError."""
    with pytest.raises(ConnectionResetError):
        receive_messages(_FakeSock(b''), [])


def test_receive_messages_returns_parsed_msgs():
    """Valid MIDI bytes should be parsed and appended to output_msgs."""
    # note_on channel=0 note=60 velocity=100 → bytes [144, 60, 100]
    output = receive_messages(_FakeSock(b'[144, 60, 100]'), [])
    assert len(output) == 1
