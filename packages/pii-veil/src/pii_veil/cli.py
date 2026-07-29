"""Command-line scrub: pii-veil "text with pii" [--regex].

Prints the masked text. Useful for a quick check or in a shell pipeline.
"""
from __future__ import annotations

import argparse

from .veil import Veil


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="pii-veil", description="Mask PII in text.")
    parser.add_argument("text", help="The text to scrub.")
    parser.add_argument("--regex", action="store_true", help="Force the regex backend (skip Presidio).")
    args = parser.parse_args(argv)

    veil = Veil(use_presidio=not args.regex)
    print(veil.scrub_text(args.text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
