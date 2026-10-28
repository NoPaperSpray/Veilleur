# Contribuer à Veilleur

Les rapports de bugs, corrections et améliorations de documentation sont les bienvenus. Le projet est encore jeune : si tu veux proposer un gros changement, ouvre d'abord une issue pour en discuter.

## Signaler un problème

Ouvre une issue avec les étapes pour reproduire le bug, ce que tu attendais, ce qui s'est passé et ta version de Windows et de Python. Retire les tokens, identifiants privés, messages Discord et autres infos sensibles avant de partager des logs ou captures.

## Proposer une modification

1. Fork le dépôt et crée une branche pour ton changement.
2. Installe les dépendances : `py -3.11 -m pip install -r requirements.txt`.
3. Lance les tests hors ligne : `py -3.11 -m unittest -v test_core`.
4. Ouvre une pull request en expliquant le problème, ta solution et les vérifications effectuées.

Les tests utilisent une API Discord simulée. N'utilise jamais le token de quelqu'un d'autre ni un serveur réel pour tester des suppressions sans autorisation. Veilleur doit conserver l'aperçu, l'approbation humaine locale et la sauvegarde avant toute modification Discord. Précise aussi les limites de restauration si ton changement touche au retour arrière.

---

# Contributing to Veilleur

Bug reports, fixes, and documentation improvements are welcome. For a larger change, please open an issue first so we can discuss it.

When reporting a bug, include reproduction steps, expected and actual behavior, and your Windows and Python versions. Remove tokens, private IDs, Discord messages, and other sensitive data from logs and screenshots.

Fork the repository, create a branch, install dependencies with `py -3.11 -m pip install -r requirements.txt`, and run `py -3.11 -m unittest -v test_core`. Then open a pull request describing the change and how you tested it.

Tests use a fake Discord API. Do not use someone else's token or perform destructive tests on a real server without authorization. Keep the preview, local human approval, and pre-execution backup for all Discord changes, and document any rollback limitations.
