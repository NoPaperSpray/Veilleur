# Veilleur

**Un serveur MCP local pour gérer Discord avec une IA, sans lui laisser le dernier mot.**

Veilleur relie un client compatible MCP à un bot Discord. Tu décris ce que tu veux faire, l'IA prépare les changements et tu les vérifies avant qu'ils soient appliqués. Le programme tourne sur ton ordinateur ; il communique avec Discord par Internet.

> Veilleur s'appelait auparavant AiMcp. Si tu l'utilisais déjà, tu peux garder ton dossier et ta configuration MCP `discord-local` : les chemins des fichiers n'ont pas changé.

## À quoi ça ressemble ?

Tu peux demander à ton IA :

> « Prépare une catégorie Accueil, un salon règlement en lecture seule et un rôle Modérateur. »

Elle lit d'abord le serveur, puis te présente un plan. Si tu es d'accord, elle ouvre une fenêtre sur ton PC. Tu y relis les actions et tu cliques sur **Approuver ce plan**. Veilleur prend alors une sauvegarde locale et l'IA peut lancer l'exécution.

Tu peux aussi lui demander de préparer un retour arrière. Il faudra examiner et approuver ce nouveau plan : une sauvegarde permet de réparer une partie des dégâts, mais Discord n'a pas de bouton magique pour ressusciter les messages supprimés.

## Ce que Veilleur sait faire

- Créer, modifier et supprimer des salons, catégories et rôles ; ajuster leurs permissions.
- Attribuer ou retirer des rôles, consulter des membres, modifier des surnoms et gérer des timeouts.
- Préparer des messages texte ou des embeds, puis les publier après validation.
- Préparer plusieurs actions liées dans un seul plan et garder un journal de leur exécution.
- Sauvegarder la structure du serveur et préparer une restauration ou un retour arrière.

Les actions restent soumises aux permissions du bot et à la hiérarchie des rôles Discord. Le serveur Discord doit déjà exister. Certains types de salons et certaines recherches de membres dépendent également des fonctionnalités et intents activés sur Discord.

## Installation sur Windows

Il te faut Python **3.11** avec le lanceur `py` et Tcl/Tk, une connexion Internet et un client compatible MCP en transport stdio. Tcl/Tk est normalement inclus dans l'installateur Python pour Windows.

### 1. Crée ton bot Discord

1. Sur le [portail développeur Discord](https://discord.com/developers/applications), crée une application et son bot.
2. Dans **Bot**, génère un token. Garde-le pour l'étape suivante et ne le partage pas.
3. Dans **OAuth2 → URL Generator**, sélectionne `bot`, puis les permissions nécessaires aux actions que tu comptes utiliser. Ouvre le lien généré et invite le bot sur ton serveur.
4. Dans les paramètres de ton serveur, place le rôle du bot au-dessus des rôles qu'il devra gérer.
5. Dans Discord, active le mode développeur, puis fais un clic droit sur ton serveur et copie son identifiant.

### 2. Installe Veilleur

Ouvre PowerShell dans le dossier du projet et lance :

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\installer.ps1
```

L'installateur crée l'environnement Python et les fichiers de configuration s'ils n'existent pas déjà. Il ne remplace pas ton token ou ta configuration existante.

Dans `.env`, colle le token après le signe `=` :

```env
DISCORD_BOT_TOKEN=ton_token
```

Dans `config.json`, remplace la valeur par l'identifiant numérique de ton serveur, en gardant les guillemets :

```json
{
  "guild_id": "123456789012345678"
}
```

Ces deux fichiers sont locaux et exclus par `.gitignore`. Si tu exposes ton token, régénère-le sur le portail Discord.

### 3. Connecte ton IA

Pour **Codex**, toujours dans le dossier du projet :

```powershell
$pythonDiscord = (Resolve-Path .\.venv\Scripts\python.exe).Path
$serveurDiscord = (Resolve-Path .\server.py).Path
codex mcp add discord-local -- $pythonDiscord $serveurDiscord
```

Redémarre ensuite Codex pour charger les outils. Si `discord-local` est déjà configuré avec ces chemins, inutile de l'ajouter une seconde fois.

Pour un autre client MCP compatible **stdio**, renseigne comme commande le chemin absolu de `.venv\Scripts\python.exe` et comme argument celui de `server.py`. La façon d'ajouter le serveur dépend du client. Veilleur doit s'exécuter dans ta session Windows pour que tu puisses voir la fenêtre d'approbation.

Essaie ensuite : « Lis mon serveur Discord et propose-moi une organisation. » Une demande de lecture ne change rien sur Discord.

## Avant de cliquer sur Approuver

La fenêtre affiche les actions et l'état du serveur avant modification. L'approbation s'applique à ce plan précis, pendant dix minutes et pour une seule exécution. Si le serveur ou une cible a changé entre l'aperçu et l'exécution, Veilleur demande un nouveau plan.

Si une action échoue, l'exécution s'arrête et le journal indique où elle en est. Une réponse réseau perdue peut laisser le résultat d'une action incertain : consulte le journal avant de tenter quoi que ce soit à nouveau.

La validation empêche les outils MCP de lancer une modification sans ton accord local. Elle ne protège pas ton token contre un autre programme qui aurait accès à tes fichiers Windows ou à ton compte Discord.

## Sauvegardes et retour arrière

Avant chaque plan exécuté, Veilleur sauvegarde la structure du serveur, les rôles, certains paramètres et les membres ou messages directement ciblés. Les fichiers sont dans `data/` ; ils peuvent contenir des informations privées.

Une restauration peut recréer des salons et des rôles, mais leurs identifiants changent. Les messages supprimés, leurs pièces jointes et leurs réactions ne sont pas rétablis. Les liens externes, fils, invitations, intégrations et affectations d'un rôle à tous les membres ne sont pas entièrement restaurés non plus. Un retour arrière peut écraser des changements faits depuis la sauvegarde : lis son aperçu avant de l'approuver.

## Si ça coince

- **Le client ne voit pas Veilleur** : vérifie les chemins de l'environnement Python et de `server.py`, puis redémarre le client MCP.
- **La fenêtre de validation n'apparaît pas** : demande à l'IA l'ID du plan, puis lance `.\.venv\Scripts\python.exe approve.py ID_DU_PLAN` depuis le dossier du projet.
- **Discord renvoie 401** : vérifie le token dans `.env`.
- **Discord renvoie 403** : vérifie les permissions et la position du rôle du bot. Certaines fonctions de recherche ou de lecture peuvent demander des intents dans le portail Discord.
- **Le bot apparaît hors ligne** : c'est normal ; Veilleur utilise l'API HTTP et n'ouvre pas de connexion Gateway.

## Pour aller plus loin

Le [manuel détaillé](LISEZ-MOI.md) explique les sauvegardes, les fichiers et les erreurs. Le [guide pour l'IA](GUIDE-IA.md) décrit les outils MCP et le format des plans. Les tests hors ligne se lancent avec :

```powershell
.\.venv\Scripts\python.exe -m unittest -v test_core
```

Après modification de Veilleur, redémarre les clients MCP : un ancien processus peut continuer à utiliser le code chargé avant la mise à jour.

Ce projet a ete developpe avec une aide IA.
