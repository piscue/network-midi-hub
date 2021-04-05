import re
import sys
import mido
import time
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


def check_multiple_messages(msg):
    # not optimal regex, just match notes
    pattern = r'(\S*\s\S*=\d*\s\S*=\d*\s\S*=\d*\stime=\d*)'
    matches = re.findall(pattern, msg)
    if len(matches) > 0:
        return matches
    else:
        return [msg]


def parse_received_data(data, messages_to_output):
    try:
        messages = check_multiple_messages(data.decode('utf-8'))
        for msg in messages:
            midi_message = mido.parse_string(msg)
            messages_to_output.append(midi_message)
    except ValueError as e:
        print(e)
    return messages_to_output


def service_connection(key, mask, messages_to_send, messages_to_output):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        try:
            recv_data = sock.recv(1024)
            if recv_data:
                print("received:", repr(recv_data.decode('utf-8')))
                messages_to_output = parse_received_data(recv_data,
                                                         messages_to_output)
        except ConnectionResetError as e:
            print(e)
    if mask & selectors.EVENT_WRITE:
        if messages_to_send:
            for msg in messages_to_send:
                data = types.SimpleNamespace(
                    outb=bytes(str(msg), 'utf-8')
                )
                print("sending", repr(data.outb.decode('utf-8')))
                try:
                    sent = sock.send(data.outb)
                    data.outb = data.outb[sent:]
                except BrokenPipeError as e:
                    print(e)
                    break
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
    try:
        while True:
            # checking new midi messages on midi_input
            for msg in input_midi.iter_pending():
                if vars.thru:
                    messages_to_output.append(msg)
                messages_to_send.append(msg)
            # sending received messages to midi_output
            if len(messages_to_output) > 0:
                for message in messages_to_output:
                    output_midi.send(message)
                messages_to_output = []

            events = sel.select(timeout=1)
            # communication with the server
            for key, mask in events:
                messages_to_output = service_connection(key,
                                                        mask,
                                                        messages_to_send,
                                                        messages_to_output)
                messages_to_send = []
            if not sel.get_map():
                break
            time.sleep(0.002)
    except KeyboardInterrupt:
        print("caught keyboard interrupt, exiting")
    finally:
        sel.close()


if __name__ == "__main__":
    main()
