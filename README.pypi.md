# Veilleur — Discord MCP server

<!-- mcp-name: io.github.NoPaperSpray/veilleur -->

Veilleur is a Windows-local Discord Model Context Protocol (MCP) server. An AI client prepares changes to Discord channels, roles, permissions, and messages; the user approves each plan in a local window before it runs. Veilleur keeps local snapshots and can prepare a rollback.

Veilleur uses a Discord bot token and needs the bot to be invited to an existing server. The bot's permissions and role hierarchy still apply. Deleted messages cannot be restored; recreated channels and roles receive new IDs. A rollback also requires approval.

For installation, configuration, and the limits of backups, see the [English README](https://github.com/NoPaperSpray/Veilleur/blob/main/README.en.md) or the [French README](https://github.com/NoPaperSpray/Veilleur).

Veilleur was developed with help from AI.
