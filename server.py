import argparse
import socket
import selectors
import time
import types
import traceback


sel = selectors.DefaultSelector()

# HTTP request methods — data starting with one of these is not MIDI (#10)
_HTTP_METHODS = (
    b'GET ', b'POST ', b'HEAD ', b'PUT ', b'DELETE ',
    b'PATCH ', b'OPTIONS ', b'CONNECT ', b'TRACE ',
)


def looks_like_http(data: bytes) -> bool:
    """Return True if data looks like an HTTP request rather than MIDI."""
    return bool(data) and any(data.startswith(m) for m in _HTTP_METHODS)


def get_args():
    parser = argparse.ArgumentParser(description='Get vars')
    parser.add_argument('--bind', '-b', default='0.0.0.0')
    parser.add_argument('--port', '-p', type=int, default=8141)
    return parser.parse_args()


def accept_wrapper(sock, sockets):
    conn, addr = sock.accept()
    print("accepted connection from", addr)
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"", validated=False)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)
    sockets.append(conn)
    return sockets


def send_to_mix_minus(sock, sockets, data):
    for socks in sockets:
        # not sending messages to the sender
        if socks != sock:
            data_socks = data
            try:
                sent = socks.send(data_socks)
            except BrokenPipeError:
                print(traceback.format_exc())
    try:
        # mark data as sent
        if 'sent' in locals():
            data = data[sent:]
    except UnboundLocalError:
        print(traceback.format_exc())
    return data


def _close_connection(sock, data, sockets):
    """Unregister and close a client socket, removing it from the pool."""
    print("closing connection to", data.addr)
    sel.unregister(sock)
    sock.close()
    if sock in sockets:
        sockets.remove(sock)
    return sockets


def service_connection(key, mask, sockets):
    sock = key.fileobj
    data = key.data
    # receive
    if mask & selectors.EVENT_READ:
        try:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                # Reject non-MIDI connections on first data received (#10)
                if not data.validated:
                    if looks_like_http(recv_data):
                        print("dropping non-MIDI connection from", data.addr)
                        return _close_connection(sock, data, sockets)
                    data.validated = True
                # not accumulating data, just keeping the latest
                data.outb = recv_data
            else:
                sockets = _close_connection(sock, data, sockets)
        except ConnectionResetError:
            print(traceback.format_exc())
    # send
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            data.outb = send_to_mix_minus(sock, sockets, data.outb)
            data.outb = None
    return sockets


def main():
    vars = get_args()
    host, port = vars.bind, vars.port
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    lsock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    lsock.bind((host, port))
    lsock.listen()
    print("listening on", (host, port))
    lsock.setblocking(False)
    sel.register(lsock, selectors.EVENT_READ, data=None)
    sockets = []

    try:
        while True:
            events = sel.select(timeout=None)
            for key, mask in events:
                if key.data is None:
                    sockets = accept_wrapper(key.fileobj, sockets)
                else:
                    sockets = service_connection(key, mask, sockets)
            # avoid cpu burn
            time.sleep(0.002)
    except KeyboardInterrupt:
        print("keyboard interrupt, exiting")
    finally:
        for sock in sockets:
            sock.close()
        lsock.close()
        sel.close()


if __name__ == "__main__":
    main()
