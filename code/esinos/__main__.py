import sys

from .cli import main


if __name__ == "__main__":
    # Même encodage pour la console et les redirections sur les trois systèmes.
    for flux in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(flux, "reconfigure"):
            flux.reconfigure(encoding="utf-8")
    raise SystemExit(main())
