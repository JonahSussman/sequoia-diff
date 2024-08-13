# sequoia-diff

Named after the giant sequoias, this name implies strength, resilience, and the ability to handle large, complex structures, much like managing complex code structures in a diff tool.

## Development

Package built with setuptools using a [flat layout](https://setuptools.pypa.io/en/latest/userguide/package_discovery.html#flat-layout).

Install with:

```sh
python -m venv .venv
pip install -e .[dev]
```

## References

Diffing trees using the [Chawathe algorithm](https://doi.org/10.1145/235968.233366) and inspiration from the paper [Fine-grained and accurate source code differencing](https://doi.org/10.1145/2642937.2642982).
