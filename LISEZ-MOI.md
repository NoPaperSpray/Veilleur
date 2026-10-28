# Veilleur — manuel détaillé

Veilleur fonctionne sur ton PC et expose des outils MCP en stdio à Codex ou un autre client compatible. Il contacte Discord par Internet. Le bot peut apparaître hors ligne : aucune connexion Gateway n'est nécessaire.

## Utilisation simple

1. Demande à l'IA ce que tu veux faire, par exemple : « Prépare un serveur pour ma petite communauté DarkRP, avec un règlement en embed et un rôle Développeur. »
2. L'IA produit un **aperçu**. Rien ne change sur Discord. Tu peux demander des corrections ou annuler le plan.
3. Quand le résultat te convient, donne ton accord dans le chat. L'IA ouvre la fenêtre locale Veilleur : lis les actions, coche la case et clique **Approuver ce plan**.
4. L'IA peut alors exécuter uniquement ce plan pendant 10 minutes. Une sauvegarde est enregistrée avant la première modification.
5. Pour revenir en arrière, demande : « Prépare le retour arrière de la dernière opération. » Tu relis et approuves un nouveau plan.

La fenêtre n'envoie rien à Discord : elle autorise le plan, puis l'IA appelle `executer_plan`. Fermer/refuser la fenêtre n'autorise aucune exécution. Tu peux approuver depuis le dossier du projet avec `.\.venv\Scripts\python.exe approve.py ID_DU_PLAN` si la fenêtre n'apparaît pas.

## Fonctions disponibles

- Salons texte, vocaux, catégories, forums et, si Discord l'autorise, annonces/scènes ; renommage, déplacement, position, slowmode, limites vocales et suppression.
- Rôles : création, nom, couleur, permissions, affichage, ordre et suppression. Attribution et retrait aux membres.
- Permissions des salons par rôle ou membre ; suppression d'une dérogation. Calcul de masques pour les permissions courantes.
- Messages texte et embeds ; lecture, modification de ses messages et suppression selon les permissions du bot. Mentions automatiques désactivées.
- Recherche de membres, consultation de profils, surnoms et timeouts via `modifier_membre`.
- Paramètres sélectionnés du serveur : nom, description, vérification, notifications et salons système/AFK.
- Plans groupés avec références aux éléments qui seront créés, sauvegardes, historique et journaux détaillés.

Les neuf anciens outils ont été convertis : ils préparent un plan et ne modifient plus directement Discord. `catalogue_actions` décrit les actions et les champs disponibles dans `preparer_plan`.

## Protection des opérations

Tous les changements Discord exposés par ce MCP passent par `executer_plan`. Aucun outil MCP ne permet d'approuver un plan. L'approbation locale est liée au contenu exact par SHA-256, limitée à 10 minutes et à une seule exécution. Toute modification du plan invalide son empreinte. Si la structure ou un membre/message ciblé change depuis l'aperçu, il faut préparer un nouveau plan.

Une sauvegarde obligatoire précède l'exécution ; une erreur de sauvegarde bloque toute mutation. Les exécutions sont verrouillées entre les clients MCP. En cas d'erreur, le bot s'arrête à la première action échouée, garde le détail de ce qui a réussi et ne rejoue pas automatiquement les mutations dont la réponse aurait été perdue. Les modifications portent une raison dans le journal d'audit Discord lorsque l'API le permet.

Ces protections concernent l'utilisation des outils MCP. Un programme ou une IA ayant accès au token et aux fichiers locaux pourrait les contourner : ce n'est pas une isolation de sécurité contre les autres programmes de ta session Windows. Ne demande pas à l'IA d'appeler directement l'API Discord ou de fabriquer un fichier d'approbation. Laisse-lui utiliser les outils MCP.

## Sauvegarde et retour arrière : limites réelles

Les sauvegardes contiennent la structure des salons/catégories, les rôles et leurs permissions, les paramètres pris en charge et les états des membres/messages directement ciblés par un plan. Elles ne sauvegardent pas tous les membres ni l'historique complet des conversations.

Les salons que le bot ne peut pas voir peuvent manquer de la sauvegarde. Le diagnostic indique les permissions de base du bot ; il ne calcule pas les dérogations propres aux salons.

`preparer_restauration` compare une sauvegarde à l'état courant et prépare la réparation/recréation des éléments sauvegardés. Il préserve les ajouts postérieurs. `preparer_retour_arriere` utilise le journal d'une exécution entièrement terminée pour préparer en plus la suppression de ses créations connues et la restauration des messages qu'elle a modifiés. Relis les suppressions : un salon créé par une ancienne opération peut avoir reçu des messages depuis.

**Un retour arrière n'est jamais automatique ni total.** Les salons et rôles supprimés sont recréés avec de nouveaux identifiants. Les permissions, parents et références internes prises en charge sont remappés. Les liens externes, invitations, intégrations, fils et références d'autres bots ne sont pas réparés. Les messages supprimés et leurs pièces jointes, auteurs, dates ou réactions ne sont pas rétablis. Les affectations d'un rôle supprimé à tous les membres ne sont pas enregistrées ; seules celles des membres directement ciblés par le plan le sont. Les images/icônes, emojis et paramètres non exposés ne font pas partie de la restauration.

Une restauration peut rétablir d'anciens réglages et donc écraser des changements postérieurs. Elle exige toujours un aperçu et une approbation. Une opération interrompue ou incertaine exige d'examiner `journal_execution` puis de préparer explicitement une restauration de sa sauvegarde ; elle n'est jamais rejouée aveuglément.

Les sauvegardes commencent à la v2. Le wipe déjà effectué avant l'installation de cette version ne peut pas être annulé à partir d'une sauvegarde inexistante.

## Installation / connexion

Python 3.11+ sous Windows avec Tcl/Tk (inclus avec l'installateur standard) et un accès Internet sont nécessaires. Dans PowerShell, dans ce dossier :

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\installer.ps1
```

Dans `.env`, renseigne `DISCORD_BOT_TOKEN=...`. Dans `config.json`, renseigne l'identifiant du serveur. Ne colle jamais le token dans un chat. Les deux fichiers existants sont conservés par l'installateur. Crée/invite le bot depuis https://discord.com/developers/applications ; accorde uniquement les permissions correspondant aux opérations voulues et place son rôle au-dessus des rôles à gérer.

```powershell
$pythonDiscord = (Resolve-Path .\.venv\Scripts\python.exe).Path
$serveurDiscord = (Resolve-Path .\server.py).Path
codex mcp add discord-local -- $pythonDiscord $serveurDiscord
```

**Après une mise à jour, redémarre Codex et tous les autres clients MCP.** Une ancienne session garde son ancien processus Python et ses anciens outils jusqu'à son redémarrage. Aucun changement de configuration MCP n'est requis si les chemins sont identiques.

Pour tout autre client MCP stdio, utilise le chemin absolu de `.venv\Scripts\python.exe` comme commande et celui de `server.py` comme argument. Chaque client doit tourner localement dans une session Windows permettant de voir la fenêtre de validation.

La recherche de membres peut nécessiter l'activation de **SERVER MEMBERS INTENT**, et la lecture du contenu des messages peut nécessiter **MESSAGE CONTENT INTENT**, dans le portail Discord. Les permissions et la hiérarchie Discord restent applicables même après approbation. Les limites de débit sont respectées avec une attente bornée ; les mutations ne sont pas réessayées après une erreur réseau incertaine.

## Fichiers locaux et diagnostic

- `data/plans/` : plans exacts et leur état (`pending`, `cancelled`, `consumed`).
- `data/approvals/` : décisions prises dans la fenêtre locale.
- `data/backups/` : sauvegardes avant les opérations, et sauvegardes manuelles.
- `data/runs/` : journal de chaque exécution et ses étapes.
- `legacy/` : ancienne version du programme conservée lors de la mise à jour. Ne pas l'exécuter : elle ne possède pas le mode aperçu obligatoire.

Ces dossiers peuvent contenir des informations privées du serveur et ne doivent pas être publiés. Aucune suppression automatique des sauvegardes n'est prévue. Copier le dossier `data/` permet de conserver l'historique local. Les erreurs courantes sont 401 (token), 403 (permissions/hiérarchie/intents), approbation expirée (rouvrir la fenêtre) et état modifié depuis l'aperçu (recréer un plan).

Tests hors ligne, sans Discord et sans token :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -v
```

## Exemple de plan groupé pour l'IA

```json
[
  {"action":"creer_salon","params":{"name":"ACCUEIL","type":4},"ref":"accueil"},
  {"action":"creer_salon","params":{"name":"reglement","type":0,"parent_id":"@accueil"},"ref":"reglement"},
  {"action":"envoyer_message","params":{"salon_id":"@reglement","embeds":[{"title":"Règlement","description":"Respectez les autres joueurs.","color":10181046}]}},
  {"action":"permissions_salon","params":{"salon_id":"@reglement","cible_id":"ID_DU_SERVEUR","type":0,"allow":"1024","deny":"274877909056"}}
]
```

Remplacer `ID_DU_SERVEUR` par le véritable identifiant. `@reglement` et `@accueil` sont des références locales : elles seront remplacées après la création. Ce tableau doit être passé à `preparer_plan` ; il ne s'exécute jamais directement.

Documentation de référence : [API salons](https://github.com/discord/discord-api-docs/blob/main/developers/resources/channel.mdx), [API rôles et serveur](https://github.com/discord/discord-api-docs/blob/main/developers/resources/guild.mdx), [API messages et embeds](https://github.com/discord/discord-api-docs/blob/main/developers/resources/message.mdx).
