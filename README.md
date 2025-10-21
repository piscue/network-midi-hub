# Network MIDI Hub

## Description
A client/server interface to connect multiple clients to a centralized MIDI server. 

![Midi Hub Diagram 1](midi-hub-diagram.jpg)

All the MIDI messages received on the client will be forwarded to the server, which will then retransmit them to all connected clients except the sender. Locally, the client spawns a virtual MIDI device to allow easy connection with any compatible MIDI app (DAW, Pd, Max, SuperCollider, ...)

![Midi Hub Diagram 2](midi-hub-diagram-2.jpg)

## Usage

TLDR;

If you want to kickstart and run it, just download the binaries and execute them

### Binaries

In the _dist_ folder you will find the binaries for macOS (Mojave or higher) and Windows.

Check instructions for the Windows Client, as it needs extra care.

### Client

#### Non binaries - OSX
Install pipenv and pyenv on your system (mac instructions assuming brew installed):

```
brew install pyenv pipenv
```

run a sync:

```
pipenv sync
```

When you have an environment with pipenv you can run it by:

```
pipenv run python client.py
```

#### Windows Client
Windows does not support spawning virtual MIDI ports without a third-party application. A workaround is to use [loopMidi](http://www.tobias-erichsen.de/software/loopmidi.html).

Once installed, open loopMidi and remove any existing ports, then add the ports as shown in this image:

![loopMidi Setup](loopMidi-setup.jpg)

Then configure your DAW/Audio MIDI ports similar to this:

![Ableton MIDI Setup](ableton-midi-setup.jpg)

Don't be confused by input/output _dyslexia_. If it doesn't work at first, try switching to the opposite in your application.

The client automatically detects if it's running on Windows and switches to this specific configuration.

Check the 'Development' section below if you prefer not to run the binaries and want to set up your Python environment manually.


### Server

By default, the server runs on port 8141 and listens on 0.0.0.0.

The server can also be run using Docker:

```bash
docker build -t network-midi-hub-server .
docker run -p 8141:8141 --rm network-midi-hub-server
```

## Development

### TODO

[See Issues](https://github.com/piscue/network-midi-hub/issues)

### Pipenv

The requirements are created using pipenv. In order to use the same environment you can run:

```
pipenv sync && pipenv shell
```

To update the requirements you can modify the Pipfile and run

```bash
pipenv lock --python 3.9 -d
pipenv requirements > requirements.txt
pipenv requirements --dev-only > requirements-dev.txt
```

### pyinstaller

#### macOS / Linux:

Linux specific:

```bash
# Install pyenv build dependencies
sudo apt-get install -y build-essential libssl-dev zlib1g-dev libbz2-dev \
libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev libncursesw5-dev \
xz-utils tk-dev libffi-dev liblzma-dev git

# Install ALSA and JACK libraries
sudo apt install libasound2-dev libjack-dev
```

Set up a Python environment with CPython shared-library enabled:

```bash
env PYTHON_CONFIGURE_OPTS="--enable-shared" pyenv install 3.9.5
```

Activate the environment and install dependencies:
```bash
pipenv sync --dev
```

Create executables for the client and server:
```bash
pipenv run pyinstaller -F --noconfirm --hiddenimport mido.backends.rtmidi client.py
pipenv run pyinstaller -F --noconfirm --hiddenimport mido.backends.rtmidi server.py
```

#### Windows 10

Install pyenv-win and pipenv.

Set up a Python environment with CPython shared-library enabled:
```cmd
set PYTHON_CONFIGURE_OPTS '--enable-shared'
pyenv install 3.9.5
```

Activate the environment and install modules:
```cmd
py -m pipenv --python %USERPROFILE%\.pyenv\pyenv-win\versions\3.9.5\python.exe shell
pip install -r requirements-dev.txt
```

Create the Windows executable:

```cmd
pyinstaller -F --noconfirm --hiddenimport mido.backends.rtmidi client.py
```
