"""Start the server.

    .venv/bin/python serve.py            # http://127.0.0.1:8000

`/` is the landing page and `/operator` is the console — the console moved off
`/` when the login went in.

Everything except `/`, `/login`, `/logout` and `/healthz` is behind a single
shared password, read from `ROCKET_APP_PASSWORD` (this loads `.env`). With it
unset the server still starts and still serves the landing page, but no
sign-in can succeed and every page behind it stays closed. That is the
intended failure: the runs behind the login are a named third party's
unreleased creative and their real ad outcomes.

Set `ROCKET_AUTH_SECRET` too on anything longer-lived than a local session —
without it cookies are signed with a per-process random key, so every restart
signs everyone out.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent


def main() -> None:
    ap = argparse.ArgumentParser(description="Rocket server.")
    ap.add_argument("--host", default="127.0.0.1",
                    help="Bind address. Default localhost.")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--reload", action="store_true", help="Auto-reload on edit.")
    args = ap.parse_args()

    # Before the app is imported: `server.app` builds its Auth from the
    # environment at import time, so a .env loaded afterwards would be read
    # too late and the server would come up with no password set.
    load_dotenv(REPO_ROOT / ".env")

    if not os.environ.get("ROCKET_APP_PASSWORD", "").strip():
        print("# ROCKET_APP_PASSWORD is not set — no one can sign in. Add it "
              "to .env (it is gitignored) to open the server.")
    uvicorn.run("server.app:app", host=args.host, port=args.port,
                reload=args.reload)


if __name__ == "__main__":
    main()
