import mido


def input_midi_port():
    with mido.open_input('vmidi input', virtual=True) as inport:
        for msg in inport:
            print(msg)


def main():
    input_midi_port()

if __name__ == "__main__":
    main()
