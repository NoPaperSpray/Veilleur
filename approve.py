"""Launch the approval window from a source checkout."""
import os
from pathlib import Path

os.environ.setdefault("VEILLEUR_HOME", str(Path(__file__).resolve().parent))
from veilleur.approve import *  # noqa: F401,F403,E402

if __name__ == "__main__":
    main()
