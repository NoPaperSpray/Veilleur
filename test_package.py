"""Packaging and configuration tests; no live Discord requests."""
import asyncio
import importlib
import json
import os
from pathlib import Path
import sys
import tempfile
import tomllib
import unittest
from unittest.mock import patch

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from veilleur.settings import load_settings


class MetadataTests(unittest.TestCase):
    def test_registry_manifest_matches_package(self):
        root = Path(__file__).resolve().parent
        manifest = json.loads((root / "server.json").read_text(encoding="utf-8"))
        metadata = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]
        package = manifest["packages"][0]
        self.assertEqual(manifest["name"], "io.github.NoPaperSpray/veilleur")
        self.assertEqual(metadata["version"], manifest["version"])
        self.assertEqual(metadata["version"], package["version"])
        self.assertEqual(metadata["name"], package["identifier"])
        self.assertIn("mcp-name: " + manifest["name"], (root / metadata["readme"]).read_text(encoding="utf-8"))
        variables = {v["name"]: v for v in package["environmentVariables"]}
        self.assertTrue(variables["DISCORD_BOT_TOKEN"]["isSecret"])


class SettingsTests(unittest.TestCase):
    def test_env_only_configuration_uses_user_data_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"LOCALAPPDATA": tmp, "DISCORD_BOT_TOKEN": "fake", "DISCORD_GUILD_ID": "123"}
            with patch.dict(os.environ, env, clear=True):
                root, token, guild = load_settings()
                self.assertEqual(root, Path(tmp, "Veilleur").resolve())
                self.assertEqual((token, guild), ("fake", "123"))

    def test_checkout_config_and_dotenv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config.json").write_text(json.dumps({"guild_id": "123"}), encoding="utf-8")
            (root / ".env").write_text("DISCORD_BOT_TOKEN=fake\n", encoding="utf-8")
            with patch.dict(os.environ, {"VEILLEUR_HOME": tmp}, clear=True):
                self.assertEqual(load_settings(), (root.resolve(), "fake", "123"))

    def test_environment_takes_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "config.json").write_text(json.dumps({"guild_id": "111"}), encoding="utf-8")
            (root / ".env").write_text("DISCORD_BOT_TOKEN=old\n", encoding="utf-8")
            env = {"VEILLEUR_HOME": tmp, "DISCORD_BOT_TOKEN": "new", "DISCORD_GUILD_ID": "222"}
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(load_settings(), (root.resolve(), "new", "222"))

    def test_approval_does_not_read_or_require_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"VEILLEUR_HOME": tmp, "DISCORD_GUILD_ID": "123"}
            with patch.dict(os.environ, env, clear=True):
                self.assertEqual(load_settings(require_token=False)[1:], ("", "123"))

    def test_invalid_guild_rejected(self):
        env = {"VEILLEUR_HOME": tempfile.gettempdir(), "DISCORD_BOT_TOKEN": "fake", "DISCORD_GUILD_ID": "not-a-number"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValueError):
                load_settings()


class ProtocolTests(unittest.TestCase):
    def test_approval_process_does_not_receive_bot_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            env = {"VEILLEUR_HOME": tmp, "DISCORD_BOT_TOKEN": "fake", "DISCORD_GUILD_ID": "123"}
            with patch.dict(os.environ, env):
                server = importlib.import_module("veilleur.server")
                with patch.object(server.service, "plan", return_value={"status": "pending"}), \
                     patch.object(server.subprocess, "Popen") as launch:
                    server.ouvrir_approbation("plan")
                    args, kwargs = launch.call_args
                    self.assertEqual(args[0][1:3], ["-m", "veilleur.approve"])
                    self.assertNotIn("DISCORD_BOT_TOKEN", kwargs["env"])
                    self.assertEqual(kwargs["env"]["DISCORD_GUILD_ID"], "123")

    def test_installed_module_starts_with_environment(self):
        async def check():
            with tempfile.TemporaryDirectory() as tmp:
                env = {**os.environ, "VEILLEUR_HOME": tmp, "DISCORD_BOT_TOKEN": "fake", "DISCORD_GUILD_ID": "123"}
                params = StdioServerParameters(command=sys.executable, args=["-m", "veilleur.server"], env=env, cwd=Path(__file__).parent)
                async with stdio_client(params) as (reader, writer):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        result = await session.list_tools()
                        names = {tool.name for tool in result.tools}
                        self.assertIn("preparer_plan", names)
                        self.assertIn("executer_plan", names)
                        self.assertNotIn("approuver", names)
        asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
