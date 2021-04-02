import mido
import argparse

def get_args():
    parser = argparse.ArgumentParser(description='Get vars')
    parser.add_argument('--thru', '-t', action='store_true')
    parser.parse_args()
    return parser.parse_known_args()


def main():
    vars, unknown_vars = get_args()
    input_midi = mido.open_input('vmidi input', virtual=True)
    output_midi = mido.open_output('vmidi output', virtual=True)
    messages_to_output = []
    while True:
        msg = input_midi.poll()
        for msg in input_midi.poll():
            if vars.thru:
                messages_to_output.append(msg)
        if len(messages_to_output) > 0:
            for message in messages_to_output:
                output_midi.send(message)
            messages_to_output = []


if __name__ == "__main__":
    main()
