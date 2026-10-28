# Veilleur

Veilleur est un serveur MCP pour gérer un serveur Discord avec une IA. Il tourne en local et passe par un bot Discord pour créer des salons, modifier des rôles, envoyer des embeds, etc.

L'idée : tu dis à l'IA ce que tu veux, elle prépare les changements, et tu valides avant qu'ils soient appliqués. Ça évite de lui laisser les clés du serveur sans savoir ce qu'elle va en faire.

J'ai créé ce projet avec l'aide d'une IA.

## Comment ça marche ?

Tu peux par exemple demander :

> Crée une catégorie Accueil avec un règlement en lecture seule et un rôle Modérateur.

L'IA te montre les actions prévues. Si ça te va, une fenêtre s'ouvre sur ton PC : tu coches la case et tu valides. Veilleur sauvegarde alors la structure du serveur et l'IA lance les changements.

Tu peux demander un retour arrière si le résultat ne te plaît pas. **Attention : ce n'est pas un Ctrl+Z parfait.** Un salon supprimé peut être recréé, mais ses messages sont perdus et il aura un nouvel ID. Détails dans [Sauvegardes](#sauvegardes).

## Ce qu'il peut faire

- Créer, modifier et supprimer des salons, catégories et rôles ; gérer leurs permissions.
- Ajouter ou retirer des rôles, chercher des membres, modifier des surnoms et gérer des timeouts.
- Envoyer des messages et des embeds, ou modifier les messages envoyés par le bot.
- Grouper plusieurs actions, sauvegarder la structure et préparer un retour arrière.

Le bot a besoin des permissions Discord correspondantes et ne peut gérer que les rôles placés sous le sien. Le serveur Discord doit déjà exister.

## Installation

### 1. Prérequis

- Windows, Python 3.11 et le lanceur `py`. L'interface de validation utilise Tkinter, généralement inclus avec Python.
- Un serveur Discord sur lequel tu peux inviter un bot.
- Un client IA qui prend en charge les serveurs MCP en **stdio**, comme Codex.
- Une connexion Internet : le programme tourne sur ton PC, mais il doit contacter Discord.

### 2. Créer le bot

1. Crée une application sur le [portail développeur Discord](https://discord.com/developers/applications).
2. Dans l'onglet **Bot**, génère un token et garde-le pour la suite. Ne le poste nulle part.
3. Dans **OAuth2 → URL Generator**, sélectionne `bot` et les permissions nécessaires, puis ouvre le lien pour inviter le bot.
4. Dans les paramètres Discord de ton serveur, place son rôle au-dessus des rôles qu'il doit gérer.
5. Active le mode développeur dans Discord, puis fais un clic droit sur ton serveur → **Copier l'identifiant du serveur**.

### 3. Configurer Veilleur

Télécharge ou clone le dépôt, puis ouvre PowerShell dans son dossier :

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\installer.ps1
```

L'installateur crée l'environnement Python ainsi que `.env` et `config.json` s'ils n'existent pas encore.

Ouvre `.env` et mets ton token après le `=` :

```env
DISCORD_BOT_TOKEN=ton_token
```

Dans `config.json`, mets l'ID de ton serveur entre guillemets :

```json
{
  "guild_id": "123456789012345678"
}
```

Ces deux fichiers sont ignorés par Git. Si ton token a fuité, régénère-le sur le portail Discord.

### 4. Connecter ton client IA

Pour Codex, lance ces commandes dans le dossier du projet :

```powershell
$pythonDiscord = (Resolve-Path .\.venv\Scripts\python.exe).Path
$serveurDiscord = (Resolve-Path .\server.py).Path
codex mcp add discord-local -- $pythonDiscord $serveurDiscord
```

Redémarre Codex, puis essaie : « Lis mon serveur Discord et propose une organisation. » Si `discord-local` est déjà configuré avec ces chemins, pas besoin de l'ajouter à nouveau.

Pour un autre client MCP compatible stdio, utilise le chemin absolu de `.venv\Scripts\python.exe` comme commande et celui de `server.py` comme argument. La config dépend du client. La fenêtre de validation doit pouvoir s'ouvrir dans ta session Windows.

## Validation et sauvegardes

Un plan doit être approuvé dans la fenêtre locale avant de pouvoir être exécuté. L'accord vaut pour ce plan précis, pendant 10 minutes et pour une seule exécution. Si le serveur ou une cible change entre-temps, il faut préparer un nouveau plan.

Avant l'exécution, Veilleur sauvegarde la structure, les rôles, certains paramètres et les membres ou messages directement concernés. Les fichiers sont stockés dans `data/` et peuvent contenir des infos privées.

La restauration a des limites : les éléments recréés ont de nouveaux IDs ; les messages supprimés, pièces jointes et réactions ne reviennent pas. Les liens externes, fils, invitations et intégrations ne sont pas réparés automatiquement. Les affectations d'un rôle supprimé ne sont pas non plus sauvegardées pour tous les membres.

Un retour arrière passe lui aussi par un aperçu et peut écraser des modifications faites depuis la sauvegarde. En cas d'erreur ou de réponse réseau perdue, consulte le journal avant de relancer quoi que ce soit.

La validation s'applique aux outils MCP de Veilleur. Elle ne protège pas ton token contre un programme qui aurait accès à tes fichiers ou à ton compte Discord.

## Dépannage

- **Le client ne voit pas Veilleur** : vérifie les chemins de Python et de `server.py`, puis redémarre le client.
- **La fenêtre ne s'ouvre pas** : demande l'ID du plan à l'IA, puis lance `.\.venv\Scripts\python.exe approve.py ID_DU_PLAN` dans le dossier du projet.
- **Erreur 401** : vérifie le token dans `.env`.
- **Erreur 403** : vérifie les permissions et la position du rôle du bot. Certaines recherches de membres et lectures de messages peuvent aussi demander des intents sur le portail Discord.
- **Le bot est hors ligne** : c'est normal. Veilleur utilise l'API HTTP sans connexion Gateway.

Pour plus de détails : [manuel complet](LISEZ-MOI.md) et [guide des outils pour l'IA](GUIDE-IA.md).

## Tests

Les tests tournent hors ligne et n'utilisent pas ton token :

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_core
```

Après une mise à jour du programme, redémarre tes clients MCP pour qu'ils chargent la nouvelle version.
