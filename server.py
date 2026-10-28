"""Keep the original MCP entry point working for existing installations."""
import os
from pathlib import Path

os.environ.setdefault("VEILLEUR_HOME", str(Path(__file__).resolve().parent))
from veilleur.server import main  # noqa: E402

if __name__ == "__main__":
    main()
