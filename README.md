# vmidi

## Description

## Usage

Docker is not yet an option as this application spawns MIDI ports that are not shared on the host system. Hopefully using pipenv makes it quite portable.

When you have an environment with pipenv you can run it by:

```pipenv run python main.py```

## Pipenv

The requirements are created using pipenv. In order to use the same environment you can run:

```pipenv sync && pipenv shell```

To update the requirements you can modify the Pipfile and run

```docker run --rm -v `pwd`:/workspace -e PIPENV_PIPFILE=Pipfile 3amigos/pipenv-all bash -c "pipenv lock -r > requirements.txt"```
