# Publication de Veilleur

Ce document sert au propriétaire du dépôt. Il ne faut jamais publier un token Discord, un token PyPI ou les fichiers de `data/`.

## Première publication

1. Créer un compte sur [PyPI](https://pypi.org/) si nécessaire et activer les protections demandées par PyPI.
2. Dans la page **Publishing** du compte PyPI, ajouter un **pending publisher** GitHub Actions pour un nouveau projet :
   - nom du projet PyPI : `veilleur-discord-mcp` ;
   - propriétaire GitHub : `NoPaperSpray` ;
   - dépôt : `Veilleur` ;
   - fichier du workflow : `publish.yml` ;
   - environnement : `pypi`.
3. Dans GitHub, vérifier que le dépôt et l'environnement `pypi` ont les protections souhaitées. L'environnement peut demander une validation avant publication.
4. Depuis la branche `main`, lancer manuellement **Publish package and MCP registry** dans l'onglet Actions. Le workflow exécute les tests sous Windows, construit et vérifie les archives, puis utilise Trusted Publishing pour PyPI. Il publie ensuite `server.json` dans le registre MCP avec GitHub OIDC et vérifie la signature du programme `mcp-publisher`.
5. Vérifier les deux pages publiques : [PyPI](https://pypi.org/project/veilleur-discord-mcp/) et le [registre MCP](https://registry.modelcontextprotocol.io/). Ne pas annoncer l'inscription avant de l'avoir vérifiée.

Un pending publisher ne réserve pas le nom avant le premier envoi. La disponibilité doit être revérifiée au moment de publier. Aucun token PyPI n'est nécessaire dans les secrets GitHub avec cette méthode.

Si PyPI a réussi mais que le registre MCP a échoué, ne republie pas la même version PyPI : consulte les logs et relance uniquement le job MCP échoué si GitHub le permet.

## Versions suivantes

Mettre à jour ensemble la version de `pyproject.toml` et les deux versions dans `server.json`, vérifier le marqueur `mcp-name` dans `README.pypi.md`, relancer les tests, puis lancer le workflow manuellement depuis `main`. PyPI n'accepte pas de remplacer une distribution déjà publiée sous la même version.

Documentation officielle : [premier projet PyPI avec Trusted Publishing](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) et [publication automatisée dans le registre MCP](https://github.com/modelcontextprotocol/registry/blob/main/docs/modelcontextprotocol-io/github-actions.mdx).
