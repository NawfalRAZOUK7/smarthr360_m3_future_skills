#!/usr/bin/env python
"""Pick an available port for the dev server.

Strategy:
- Prefer PORT env if free; otherwise fall back to a list of common choices.
- Prints the chosen port to stdout.
"""

from __future__ import annotations

import os
import socket
from typing import Iterable

DEFAULT_PORT = 8000
FALLBACK_PORTS = (8001, 8002, 8080, 5000)


def is_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("0.0.0.0", port)) != 0


def pick_port(candidates: Iterable[int]) -> int:
    for port in candidates:
        if is_free(port):
            return port
    raise RuntimeError("No free port found in candidate list.")


def main() -> None:
    env_port = os.getenv("PORT")
    candidates = []
    if env_port:
        try:
            candidates.append(int(env_port))
        except ValueError:
            pass
    candidates.append(DEFAULT_PORT)
    candidates.extend(FALLBACK_PORTS)
    port = pick_port(candidates)
    print(port)


if __name__ == "__main__":
    main()
