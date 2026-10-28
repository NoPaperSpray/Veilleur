<!-- mcp-name: io.github.NoPaperSpray/veilleur -->

# Veilleur — Discord MCP server

[![Tests](https://github.com/NoPaperSpray/Veilleur/actions/workflows/tests.yml/badge.svg)](https://github.com/NoPaperSpray/Veilleur/actions/workflows/tests.yml) [![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

[Lire en français](README.md)

Veilleur is a local Model Context Protocol (MCP) server that lets an AI client manage a Discord server through a Discord bot. It can plan channel and role changes, adjust permissions, and prepare messages or embeds. Before any change, you review the plan and approve it in a window on your computer.

This project was built with help from AI.

## How it works

Ask your MCP client something like:

> Create a welcome category, a read-only rules channel, and a moderator role.

Veilleur prepares a plan. The AI shows you the proposed actions, then opens a local approval window after you agree. Once you approve the plan in that window, Veilleur saves a local snapshot and the AI can execute it.

You can also ask for a rollback. It creates another plan that you must review and approve. **A rollback is not a perfect undo:** recreated channels and roles receive new IDs, and deleted messages cannot be recovered.

## Features

- Create, edit, and delete Discord channels, categories, and roles; manage permission overwrites.
- Add or remove member roles, look up members, change nicknames, and manage timeouts.
- Prepare messages and embeds, including edits to the bot's own messages.
- Group changes in one plan, keep execution logs, and prepare a rollback from local snapshots.
- Run a read-only diagnostic of the bot's server-level permissions.

The bot needs the appropriate Discord permissions. It can only manage roles below its own role. Your Discord server must already exist. Some channel types and member searches depend on the server's features and enabled intents.

## Setup on Windows

You need Python 3.11 with the `py` launcher and Tkinter, a Discord server where you can invite a bot, and an MCP client that supports **stdio**. Veilleur runs on your PC and needs an Internet connection to reach Discord.

### 1. Create and invite the bot

1. Create an application and bot in the [Discord Developer Portal](https://discord.com/developers/applications).
2. In **Bot**, generate a token and keep it private.
3. In **OAuth2 → URL Generator**, select `bot` and the permissions you need, then use the generated link to invite it.
4. Move the bot's role above the roles it needs to manage in your server settings.
5. Enable Developer Mode in Discord, right-click your server, and copy its ID.

### 2. Install Veilleur

Download or clone this repository and open PowerShell in its folder:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\installer.ps1
```

The installer creates the Python environment and, if they do not exist, `.env` and `config.json`. Put the bot token in `.env`:

```env
DISCORD_BOT_TOKEN=your_token
```

Put your server ID in `config.json`, keeping it as a quoted string:

```json
{
  "guild_id": "123456789012345678"
}
```

Both files are excluded by `.gitignore`. If your token is exposed, regenerate it in the Discord Developer Portal.

### 3. Connect your MCP client

For Codex, run this from the project folder:

```powershell
$pythonDiscord = (Resolve-Path .\.venv\Scripts\python.exe).Path
$serveurDiscord = (Resolve-Path .\server.py).Path
codex mcp add discord-local -- $pythonDiscord $serveurDiscord
```

Restart Codex to load the tools. If `discord-local` is already configured with these paths, you do not need to add it again.

For another stdio MCP client, set the command to the absolute path of `.venv\Scripts\python.exe` and the argument to the absolute path of `server.py`. Configuration differs between clients. The approval window must be able to open in your Windows session.


### Install from Python source

Run `python -m pip install .` from a checkout to install the `veilleur-discord-mcp` command. The package accepts `DISCORD_BOT_TOKEN` and `DISCORD_GUILD_ID` environment variables. Plans and backups default to `%LOCALAPPDATA%\Veilleur` on Windows; set `VEILLEUR_HOME` to choose another directory. Keep credentials private in your MCP client's local configuration.

The existing `python server.py` entry point still uses `.env`, `config.json`, and `data/` in the checkout. Its data is separate from the installed package's default directory.

## Approval and backup limits

An approval applies to one exact plan, for ten minutes, and can be used once. If the server or a target changes before execution, you need a new preview. Veilleur warns before channel deletion and checks whether its last message changed between preview and execution; this does not detect every possible change to the channel.

Snapshots are stored in `data/` and can contain private server information. They only cover what the bot can see and do not include all messages or all member role assignments. Deleted messages and attachments are not restored. External links, threads, invites, and integrations are not automatically repaired. A rollback may overwrite changes made since the snapshot, so review its plan too.

The approval mechanism applies to Veilleur's MCP tools. It does not protect the token from another program that can access your Windows files or Discord account.

## Troubleshooting

- **The MCP client cannot see Veilleur:** check the Python and `server.py` paths, then restart the client.
- **The approval window does not open:** ask the AI for the plan ID, then run `.\.venv\Scripts\python.exe approve.py PLAN_ID` from the project folder.
- **HTTP 401:** check the token in `.env`.
- **HTTP 403:** check the bot's permissions and role position. Member searches and message content may also require intents in the Discord Developer Portal.
- **The bot appears offline:** Veilleur uses the HTTP API and does not maintain a Gateway connection.

You can ask the AI to run `diagnostic` for server-level bot permissions. It does not calculate channel-specific overrides or discover channels the bot cannot see.

## Tests and further details

The offline tests do not use your token:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

The [detailed manual](LISEZ-MOI.md) and [AI tool guide](GUIDE-IA.md) are currently in French. Restart MCP clients after updating the program so they load the new version.

## Contributing

Found a bug or have an idea? Open an issue. See [CONTRIBUTING.md](CONTRIBUTING.md) for pull requests. Veilleur is released under the [MIT license](LICENSE).
