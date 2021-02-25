# vmidi

## Description

## Usage

## Pipenv

The requirements are created using pipenv. In order to use the same environment you can run:

```pipenv shell```

To update the requirements you can modify the Pipfile and run

```docker run --rm -v `pwd`:/workspace -e PIPENV_PIPFILE=Pipfile 3amigos/pipenv-all bash -c "pipenv lock -r > requirements.txt"```
