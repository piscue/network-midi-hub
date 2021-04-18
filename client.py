import re
import time
import types
import socket
import argparse
import selectors
import mido


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
    return sock


def matches_transport(data):
    pattern = r'(\[\d\d\d\])'
    return re.findall(pattern, data)


def is_transport(data):
    matches = matches_transport(data)
    if len(matches) > 0:
        return True
    return False


def check_multiple_transports(data, msg_list):
    matches = matches_transport(data)
    if len(matches) > 0:
        for msg in matches:
            msg_list.append(msg)
    else:
        msg_list.append(data)
    return msg_list


def check_multiple_messages(data, msg_list):
    pattern = r'(\[\d*,\s\d+,\s\d*\])'
    matches = re.findall(pattern, data)
    if len(matches) > 0:
        for msg in matches:
            msg_list.append(msg)
    else:
        msg_list.append(data)
    return msg_list


def review_data(data):
    msg_list = []
    if is_transport(data):
        msg_list = check_multiple_transports(data, msg_list)
    msg_list = check_multiple_messages(data, msg_list)
    return msg_list


def midify_msg(msg, output_msgs):
    mido_msg = mido.Message.from_bytes(eval(msg))
    str_msg = str(mido_msg)
    print(f'received: {str_msg}')
    output_msgs.append(mido_msg)
    return output_msgs


def parse_received_data(data, output_msgs):
    try:
        data_decoded = repr(data.decode('utf-8'))
        msg_list = review_data(data_decoded)
        for msg in msg_list:
            output_msgs = midify_msg(msg, output_msgs)
    except ValueError as e:
        # print(f'ValueError: {e}')
        pass
    return output_msgs


def receive_messages(sock, output_msgs):
    try:
        recv_data = sock.recv(1024)
        if recv_data:
            output_msgs = parse_received_data(recv_data, output_msgs)
    except ConnectionResetError as e:
        print(e)
    return output_msgs


def send_message(msg, data, sock):
    data = types.SimpleNamespace(
        outb=bytes(str(msg.bytes()), 'utf-8')
    )
    try:
        sent = sock.send(data.outb)
        data.outb = data.outb[sent:]
        print(f'sent: {msg}')
    except BrokenPipeError as e:
        print(e)


def server_con(key, mask, send_msgs, output_msgs):
    sock = key.fileobj
    data = key.data
    if mask & selectors.EVENT_READ:
        output_msgs = receive_messages(sock, output_msgs)
    if mask & selectors.EVENT_WRITE:
        if send_msgs:
            for msg in send_msgs:
                send_message(msg, data, sock)
    return output_msgs


def main():
    args = get_args()
    host, port = args.host, args.port
    input_midi = mido.open_input('network midi hub input', virtual=True)
    output_midi = mido.open_output('network midi hub output', virtual=True)
    sock = start_connection(host, int(port))
    send_msgs = []
    output_msgs = []
    try:
        while True:
            # checking new midi messages on midi_input
            for msg in input_midi.iter_pending():
                if args.thru:
                    output_msgs.append(msg)
                send_msgs.append(msg)
            # sending received messages to midi_output
            if len(output_msgs) > 0:
                for message in output_msgs:
                    output_midi.send(message)
                output_msgs = []

            events = sel.select(timeout=1)
            # communication with the server
            for key, mask in events:
                try:
                    output_msgs = server_con(key, mask, send_msgs, output_msgs)
                    send_msgs = []
                except LookupError or BrokenPipeError as e:
                    print(e)
                    print('restarting connection to the server')
                    print(host, port)
                    sel.unregister(sock)
                    sock.close()
                    sock = start_connection(host, int(port))
            if not sel.get_map():
                break
            time.sleep(0.002)
    except KeyboardInterrupt:
        print("caught keyboard interrupt, exiting")
    finally:
        sel.close()


if __name__ == "__main__":
    main()
