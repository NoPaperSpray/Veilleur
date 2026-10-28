"""Configuration paths for a checkout or an installed package."""
import json
import os
from pathlib import Path

from dotenv import load_dotenv


def load_settings(require_token=True):
    configured_home = os.getenv("VEILLEUR_HOME")
    if configured_home:
        root = Path(configured_home).expanduser().resolve()
    else:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / ".local" / "share")
        root = (base / "Veilleur").resolve()
    # The approval window needs the server ID, not the bot token.
    if require_token:
        load_dotenv(root / ".env", override=False)
    guild = os.getenv("DISCORD_GUILD_ID", "").strip()
    if not guild:
        config_path = root / "config.json"
        if not config_path.is_file():
            raise ValueError("Définis DISCORD_GUILD_ID ou configure guild_id dans config.json")
        config = json.loads(config_path.read_text(encoding="utf-8-sig"))
        guild = str(config.get("guild_id", "")).strip()
    if not guild.isdecimal():
        raise ValueError("Identifiant Discord invalide")
    token = os.getenv("DISCORD_BOT_TOKEN", "").strip() if require_token else ""
    if require_token and not token:
        raise ValueError("Définis DISCORD_BOT_TOKEN ou renseigne-le dans .env")
    return root, token, guild
