import sys
import mido
import types
import socket
import argparse
import selectors

sel = selectors.DefaultSelector()

def get_args():
    parser = argparse.ArgumentParser(description='Get vars')
    parser.add_argument('--thru', '-t', action='store_true')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', '-p', default=8141, type=int)
    parser.parse_args()
    return parser.parse_args()


def start_connection(host, port):
    server_addr = (host, port)
    print(f'starting connection to {server_addr}')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(server_addr)
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(sock, events)


def service_connection(key, mask, messages_to_send, messages_to_output):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        recv_data = sock.recv(1024)  # Should be ready to read
        if recv_data:
            print("received", repr(recv_data), "from connection")
            midi_message = mido.parse_string(recv_data.decode('utf-8'))
            messages_to_output.append(midi_message)
            # data.recv_total += len(recv_data)
        # if not recv_data or data.recv_total == data.msg_total:
        #     print("closing connection")
        #     sel.unregister(sock)
        #     sock.close()
    if mask & selectors.EVENT_WRITE:
        # if not data.outb and data.messages:
        #     data.outb = data.messages.pop(0)
        if messages_to_send:
            for msg in messages_to_send:
                data = types.SimpleNamespace(
                    outb=bytes(str(msg), 'utf-8')
                )
                print("sending", repr(data.outb), "to connection")
                sent = sock.send(data.outb)
                data.outb = data.outb[sent:]
                print(data)
    return messages_to_output


def main():
    vars = get_args()
    host, port = vars.host, vars.port
    input_midi = mido.open_input('vmidi input', virtual=True)
    output_midi = mido.open_output('vmidi output', virtual=True)
    start_connection(host, int(port))
    data_to_send = []
    messages_to_send = []
    messages_to_output = []
    data = None
    try:
        while True:
            for msg in input_midi.iter_pending():
                if vars.thru:
                    messages_to_output.append(msg)
                data_to_send.append(msg)
                print(msg)
            if len(messages_to_output) > 0:
                for message in messages_to_output:
                    output_midi.send(message)
                messages_to_output = []

            events = sel.select(timeout=1)
            if len(data_to_send) > 0:
               messages_to_send = data_to_send
               data_to_send = []
            if events:
                for key, mask in events:
                    messages_to_output = service_connection(key,
                                                            mask,
                                                            messages_to_send,
                                                            messages_to_output)
                    messages_to_send = None
            if not sel.get_map():
                break
    except KeyboardInterrupt:
        print("caught keyboard interrupt, exiting")
    finally:
        sel.close()


if __name__ == "__main__":
    main()
