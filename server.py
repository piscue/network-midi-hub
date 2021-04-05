import argparse
import sys
import socket
import selectors
import time
import types
# share queue or other mechanism to share messages to all the clients minus one


sel = selectors.DefaultSelector()


def get_args():
    parser = argparse.ArgumentParser(description='Get vars')
    parser.add_argument('--bind', '-b', default='0.0.0.0')
    parser.add_argument('--port', '-p', type=int, default=8141)
    return parser.parse_args()


def accept_wrapper(sock, sockets):
    conn, addr = sock.accept()
    print("accepted connection from", addr)
    conn.setblocking(False)
    data = types.SimpleNamespace(addr=addr, inb=b"", outb=b"")
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(conn, events, data=data)
    sockets.append(conn)
    print(sockets)
    return sockets



def service_connection(key, mask, sockets):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        try:
            recv_data = sock.recv(1024)  # Should be ready to read
            if recv_data:
                # data.outb += recv_data
                # not acumulating data, instead of appending
                data.outb = recv_data
            else:
                print("closing connection to", data.addr)
                sel.unregister(sock)
                # print(sock)
                # print(sockets)
                sock.close()
                if sock in sockets:
                    sockets.remove(sock)
        except ConnectionResetError as e:
            print(e)
    if mask & selectors.EVENT_WRITE:
        if data.outb:
            print(data.outb)
            for socks in sockets:
                if socks != sock:
                    data_socks = data.outb
                    try:
                        sent = socks.send(data_socks)
                    except BrokenPipeError as e:
                        print(e)
            try:
                data.outb = data.outb[sent:]
            except UnboundLocalError as e:
                # print('failed to mark as sent, probably only one client')
                # print(e)
                pass
    return sockets


def main():
    vars = get_args()
    host, port = vars.bind, vars.port
    lsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
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
