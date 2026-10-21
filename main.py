import os
from pathlib import Path

import uvicorn


def run():
    # Tell chore_tracker where the project root lives regardless of where
    # the package ends up installed (e.g. Nix store).
    os.environ.setdefault("CHORE_BASE", str(Path(__file__).parent))
    # CHORE_PORT lets a local dev run sit beside the k3s pod, which already
    # exposes 3030 on this host.
    port = int(os.environ.get("CHORE_PORT", "3030"))
    uvicorn.run("chore_tracker.main:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    run()
