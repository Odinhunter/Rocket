"""Start the operator server.

    .venv/bin/python serve.py            # http://127.0.0.1:8000

Binds to localhost by default. The sessions it records hold a named third
party's unpublished ad outcomes and their CTR/ROAS, so exposing this on a
network is a deliberate act: pass --host to do it, and put an access token in
front of it first (there is none yet — sessions are run in person, on this
machine, by the operator).
"""

from __future__ import annotations

import argparse

import uvicorn


def main() -> None:
    ap = argparse.ArgumentParser(description="Rocket operator server.")
    ap.add_argument("--host", default="127.0.0.1",
                    help="Bind address. Default localhost — see the module "
                         "docstring before changing it.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--reload", action="store_true", help="Auto-reload on edit.")
    args = ap.parse_args()

    if args.host not in ("127.0.0.1", "localhost"):
        print(f"# WARNING: binding to {args.host} — session records contain a "
              "contact's confidential ad outcomes and there is no auth in "
              "front of this server yet.")
    uvicorn.run("server.app:app", host=args.host, port=args.port,
                reload=args.reload)


if __name__ == "__main__":
    main()
