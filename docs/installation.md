# Installation

This project currently supports two practical ways to run `skill-hub`.

## Option 1: Wrapper Script From Checkout

This path does not require packaging tools such as `setuptools`.

From the repository root:

```bash
./bin/skill-hub --version
./bin/skill-hub --help
```

The wrapper exports `PYTHONPATH=src` for the current process and then runs:

```bash
python3 -m skill_hub_manager.cli
```

Use this path when:

- you are working directly from the Git checkout
- you are in a restricted or offline environment
- you want the simplest local developer workflow

## Option 2: Editable Install

On a normal machine with Python packaging prerequisites available:

```bash
python3 -m pip install -e .
skill-hub --version
```

This uses the console script declared in `pyproject.toml`.

Use this path when:

- you want `skill-hub` on your shell `PATH`
- you are using a normal online Python environment
- you want shell aliases or automation to call the installed command directly

## Current Limitation

In the current restricted environment used during development verification here, `pip install -e .` could not be fully verified because:

- the Python 3.14 virtual environment did not include `setuptools`
- build isolation attempted to download packaging dependencies from PyPI
- outbound package index access was unavailable

That affects installation verification in this environment, not the CLI runtime itself.

## Recommended Local Workflow

For local development and testing:

```bash
./bin/skill-hub --version
PYTHONPATH=src python3 -m unittest discover -s tests
```

For end-user installation on a normal workstation:

```bash
python3 -m pip install -e .
skill-hub --help
```
