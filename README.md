# Network MIDI Hub

## Description
A client/server interface to connect multiple clients to a centralized MIDI server. 

![Midi Hub Diagram 1](midi-hub-diagram.jpg)

All the MIDI messages received on the client, will be forwared to the server and that will be retransmitted to all the connected clients minus the sender. Locally the client spawn a virtual midi device to allow easy connection with any compatible midi app (DAW, Pd, Max, Supercollider, ...)

![Midi Hub Diagram 2](midi-hub-diagram-2.jpg)

## Usage

### Client

When you have an environment with pipenv you can run it by:

```pipenv run python client.py```

Docker is not yet an option as this application spawns MIDI ports that are not shared on the host system. Hopefully using pipenv makes it quite portable.

### Server

```pipenv run python server.py```

## Development

For now is based in TCP sockets, probably will be more performant in latency using UDP.

### Pipenv

The requirements are created using pipenv. In order to use the same environment you can run:

```pipenv sync && pipenv shell```

To update the requirements you can modify the Pipfile and run

```docker run --rm -v `pwd`:/workspace -e PIPENV_PIPFILE=Pipfile 3amigos/pipenv-all bash -c "pipenv lock -r > requirements.txt"```
