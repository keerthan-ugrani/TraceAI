"""Allow ``python -m traceai`` to run the command-line interface."""

from traceai.cli import main

if __name__ == "__main__":  # pragma: no cover - exercised through subprocess
    main()
