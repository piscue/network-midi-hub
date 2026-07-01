"""
End-to-end tests: client1 <-> server <-> client2

These tests use raw TCP sockets that speak the same wire protocol as client.py,
so no real MIDI hardware or virtual MIDI ports are needed.  The server is
started as a subprocess on an ephemeral port for each test.
"""
import socket
import subprocess
import sys
import time
import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _free_port() -> int:
    """Return an unused TCP port."""
    with socket.socket() as s:
        s.bind(('', 0))
        return s.getsockname()[1]


def _connect(
    port: int, timeout: float = 2.0, retries: int = 10
) -> socket.socket:
    """Connect to the local server, retrying on ECONNREFUSED."""
    for attempt in range(retries):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect(('127.0.0.1', port))
            s.settimeout(timeout)
            return s
        except ConnectionRefusedError:
            s.close()
            if attempt == retries - 1:
                raise
            time.sleep(0.1)
    raise ConnectionRefusedError(f"Could not connect to 127.0.0.1:{port}")


def _recv_all(sock: socket.socket, wait: float = 0.3) -> bytes:
    """Read any available data from *sock*, waiting up to *wait* seconds."""
    time.sleep(wait)
    data = b''
    sock.settimeout(0.1)
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
    except (socket.timeout, OSError):
        pass
    return data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def server():
    """Start server.py on an ephemeral port; yield (port, proc); then stop."""
    port = _free_port()
    proc = subprocess.Popen(
        [sys.executable, 'server.py', '-p', str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    # Give the server a moment to bind and listen
    time.sleep(0.25)
    assert proc.poll() is None, "server failed to start"
    yield port, proc
    proc.terminate()
    try:
        proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()


# ---------------------------------------------------------------------------
# Core relay
# ---------------------------------------------------------------------------

def test_relay_client1_to_client2(server):
    """A message sent by client1 is received by client2."""
    port, _ = server
    c1 = _connect(port)
    c2 = _connect(port)
    time.sleep(0.05)  # let the server register both connections

    midi_msg = b'[144, 60, 100]'
    c1.sendall(midi_msg)

    received = _recv_all(c2)
    c1.close()
    c2.close()

    assert midi_msg in received, (
        f"client2 should have received {midi_msg!r}, got {received!r}"
    )


def test_relay_multiple_messages(server):
    """Multiple messages from client1 all reach client2."""
    port, _ = server
    c1 = _connect(port)
    c2 = _connect(port)
    time.sleep(0.05)

    messages = [b'[144, 60, 100]', b'[128, 60, 0]', b'[176, 64, 127]']
    for m in messages:
        c1.sendall(m)
        time.sleep(0.01)

    received = _recv_all(c2)
    c1.close()
    c2.close()

    for m in messages:
        assert m in received, (
            f"Expected {m!r} in relay output, got {received!r}"
        )


def test_no_self_relay(server):
    """A client does NOT receive its own messages back."""
    port, _ = server
    c1 = _connect(port)
    c2 = _connect(port)
    time.sleep(0.05)

    c1.sendall(b'[144, 60, 100]')

    # c2 should get the message
    received_c2 = _recv_all(c2)
    assert b'[144, 60, 100]' in received_c2

    # c1 should NOT receive its own message
    received_c1 = _recv_all(c1, wait=0.1)
    assert b'[144, 60, 100]' not in received_c1, (
        "Server must not echo a message back to its sender"
    )

    c1.close()
    c2.close()


def test_relay_bidirectional(server):
    """Relay works in both directions: c1→c2 and c2→c1."""
    port, _ = server
    c1 = _connect(port)
    c2 = _connect(port)
    time.sleep(0.05)

    c1.sendall(b'[144, 60, 100]')
    recv_c2 = _recv_all(c2)
    assert b'[144, 60, 100]' in recv_c2

    c2.sendall(b'[128, 60, 0]')
    recv_c1 = _recv_all(c1)
    assert b'[128, 60, 0]' in recv_c1

    c1.close()
    c2.close()


# ---------------------------------------------------------------------------
# #10 — server drops HTTP / non-MIDI connections
# ---------------------------------------------------------------------------

def test_http_connection_dropped(server):
    """An HTTP request causes the server to drop that connection."""
    port, _ = server
    c_http = _connect(port)
    c_midi = _connect(port)
    time.sleep(0.05)

    c_http.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')
    time.sleep(0.2)  # give server time to detect and close

    # The HTTP client connection should be closed by the server
    c_http.settimeout(0.5)
    try:
        data = c_http.recv(1024)
        assert data == b'', (
            "Server should close the HTTP connection (empty read)"
        )
    except (ConnectionResetError, OSError):
        pass  # server closed forcefully — also acceptable

    c_http.close()
    c_midi.close()


def test_http_garbage_not_relayed(server):
    """HTTP garbage sent by one client must NOT reach other MIDI clients."""
    port, _ = server
    c_midi = _connect(port)
    c_http = _connect(port)
    time.sleep(0.05)

    c_http.sendall(b'GET / HTTP/1.1\r\nHost: localhost\r\n\r\n')

    # Give server time to reject the HTTP connection
    received = _recv_all(c_midi, wait=0.3)

    # The MIDI client should not have received HTTP garbage
    assert b'GET' not in received, (
        f"HTTP garbage must not be relayed to MIDI clients, got: {received!r}"
    )
    assert b'HTTP' not in received, (
        f"HTTP garbage must not be relayed to MIDI clients, got: {received!r}"
    )

    c_midi.close()
    c_http.close()


# ---------------------------------------------------------------------------
# #16 — receive-only client reconnects after server restart
# ---------------------------------------------------------------------------

def test_receive_only_client_reconnects_after_server_restart():
    """
    A client that only receives should reconnect after the server restarts
    and continue receiving messages.

    This test exercises the #16 fix at the TCP level:
    - c2 connects (receive-only role)
    - server is killed and restarted on the same port
    - c2 (via client.py reconnect logic) should reconnect
    - after reconnect, a message from c1 should reach c2 again

    Note: because client.py's full reconnect loop is part of main(), this
    test verifies the TCP-level behaviour: empty recv on a clean server close
    signals disconnect, which the real client uses to reconnect.  We confirm
    the server correctly sends an empty close on shutdown.
    """
    port = _free_port()

    # --- First server instance ---
    proc1 = subprocess.Popen(
        [sys.executable, 'server.py', '-p', str(port)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    time.sleep(0.25)

    c_sender = _connect(port)
    c_receiver = _connect(port)
    time.sleep(0.05)

    # Verify relay works with first server instance
    c_sender.sendall(b'[144, 60, 100]')
    received = _recv_all(c_receiver)
    assert b'[144, 60, 100]' in received, (
        "Relay should work before server restart"
    )

    # Shut down server — c_receiver should get an empty read (EOF)
    proc1.terminate()
    proc1.wait(timeout=3)

    # The receiver should detect the EOF within a short window
    c_receiver.settimeout(1.0)
    try:
        eof_data = c_receiver.recv(1024)
        assert eof_data == b'', (
            "Empty recv (EOF) signals the server closed — client.py uses this "
            "to trigger reconnect (#16)"
        )
    except (ConnectionResetError, OSError):
        pass  # OS-level reset also signals disconnect

    c_sender.close()
    c_receiver.close()

    # --- Second server instance on the same port ---
    proc2 = subprocess.Popen(
        [sys.executable, 'server.py', '-p', str(port)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
    )
    time.sleep(0.25)

    c1 = _connect(port)
    c2 = _connect(port)
    time.sleep(0.05)

    c1.sendall(b'[144, 61, 80]')
    received2 = _recv_all(c2)
    assert b'[144, 61, 80]' in received2, (
        "Relay should work after server restart"
        " (simulates successful reconnect)"
    )

    c1.close()
    c2.close()
    proc2.terminate()
    proc2.wait(timeout=3)


# ---------------------------------------------------------------------------
# #18 — connecting to a bogus host/port fails gracefully
# ---------------------------------------------------------------------------

def test_connection_refused_is_detected():
    """
    Connecting to a port with nothing listening should fail, not appear
    to succeed.  We test the socket-level primitive used by start_connection.
    """
    free = _free_port()
    # Nothing is listening on *free* — the OS will ECONNREFUSED immediately
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(('127.0.0.1', free))

    # Wait for the socket to become writable (connect attempt resolved)
    import selectors
    sel = selectors.DefaultSelector()
    sel.register(sock, selectors.EVENT_WRITE)
    events = sel.select(timeout=2.0)
    assert events, "Socket should become writable within 2 seconds"

    err = sock.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
    assert err != 0, (
        f"SO_ERROR should be non-zero for a refused connection, got {err}"
    )
    sel.close()
    sock.close()
