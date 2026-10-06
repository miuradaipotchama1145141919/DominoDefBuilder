# DominoDefBuilder

DominoDefBuilder builds Domino sound source definition XML files from maintainable YAML source files.

## Installation

Requires Python 3.10 or newer.

```
pip install DominoDefBuilder
```

For development:

```
pip install -e ".[dev]"
pytest -q
```

## CLI

The primary command is `def`. The same command is also installed as `dominodef`, which is handy where `def` is awkward to type or conflicts with something else.

```
def list
def validate
def build
def build example/gm2
def new acme/synth
```

Global options such as `--modules DIR` go before the command. Generated XML and `manifest.json` are written to `dist` by default.

## Example

The repository contains one GM2 showcase module. It exists to demonstrate the supported Domino definition features and acts as a reference for projects that want to create their own module source.

The builder does not require a fixed collection of modules. A project can contain one module or many modules.

### GitHub Actions

Example workflows for validating, building, and releasing modules live in [`examples/github-workflows`](examples/github-workflows). They are samples to copy into your own module project, not CI for this repository.

## Publishing the package

The package is published to PyPI by `.github/workflows/pypi.yml` using Trusted Publishing. To publish a release, update `__version__` and push a matching tag, such as `v0.4.0`. The workflow runs the tests, builds the package, and publishes it to PyPI.

## License

UNLICENSE
