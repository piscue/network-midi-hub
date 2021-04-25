import re
import time
import types
import socket
import argparse
import platform
import selectors
import traceback
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
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setblocking(False)
    sock.connect_ex(server_addr)
    print(f'connected to {host} on port {port}')
    events = selectors.EVENT_READ | selectors.EVENT_WRITE
    sel.register(sock, events)
    return sock


def matches_transport(data):
    pattern = r'(\[\d\d\d\])'
    return re.findall(pattern, data)


def check_transports(data, msg_list):
    matches = matches_transport(data)
    if len(matches) > 0:
        for msg in matches:
            msg_list.append(msg)
    return msg_list


def check_messages(data, msg_list):
    pattern = r'(\[\d*,\s\d+,\s\d*\])'
    matches = re.findall(pattern, data)
    if len(matches) > 0:
        for msg in matches:
            msg_list.append(msg)
    return msg_list


def review_data(data):
    msg_list = []
    msg_list = check_transports(data, msg_list)
    msg_list = check_messages(data, msg_list)
    return msg_list


def midify_msg(msg, output_msgs):
    mido_msg = mido.Message.from_bytes(eval(msg))
    str_msg = str(mido_msg)
    print(f'received: {str_msg}')
    output_msgs.append(mido_msg)
    return output_msgs


def parse_received_data(data, output_msgs):
    data_decoded = repr(data.decode('utf-8'))
    msg_list = review_data(data_decoded)
    for msg in msg_list:
        try:
            output_msgs = midify_msg(msg, output_msgs)
        except ValueError:
            print(traceback.format_exc())
            print(f'msg: : {msg}')
    return output_msgs


def receive_messages(sock, output_msgs):
    try:
        recv_data = sock.recv(1024)
        if recv_data:
            output_msgs = parse_received_data(recv_data, output_msgs)
    except ConnectionResetError:
        print(traceback.format_exc())
    return output_msgs


def send_message(msg, data, sock):
    data = types.SimpleNamespace(
        outb=bytes(str(msg.bytes()), 'utf-8')
    )
    try:
        sent = sock.send(data.outb)
        data.outb = data.outb[sent:]
        print(f'sent: {msg}')
    except BrokenPipeError:
        print(traceback.format_exc())


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


def open_midi_ports():
    if platform.system() == 'Windows':
        try:
            input_midi = mido.open_input('loopMIDI Port In 0')
            output_midi = mido.open_output('loopMIDI Port Out 2')
        except OSError:
            print('failed to open some midi ports')
            input_ports = mido.get_input_names()
            input_port = input(f'select input MIDI {input_ports}: ')
            input_midi = mido.open_input(input_port)
            output_ports = mido.get_output_names()
            output_port = input(f'select output MIDI {output_ports}: ')
            output_midi = mido.open_output(output_port)
    else:
        input_midi = mido.open_input('network midi hub input', virtual=True)
        output_midi = mido.open_output('network midi hub output', virtual=True)
    return input_midi, output_midi


def main():
    args = get_args()
    if args.host == '127.0.0.1':
        args.host = input('Host to connect [127.0.0.1]: ') or '127.0.0.1'
    host, port = args.host, args.port
    input_midi, output_midi = open_midi_ports()
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
                except (LookupError, BrokenPipeError):
                    print(traceback.format_exc())
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
