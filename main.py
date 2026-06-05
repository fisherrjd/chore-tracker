import os
from pathlib import Path

import uvicorn


def run():
    # Tell chore_tracker where the project root lives regardless of where
    # the package ends up installed (e.g. Nix store).
    os.environ.setdefault("CHORE_BASE", str(Path(__file__).parent))
    uvicorn.run("chore_tracker.main:app", host="0.0.0.0", port=3030, reload=True)


if __name__ == "__main__":
    run()
