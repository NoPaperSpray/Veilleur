# Veilleur — consignes de travail

Le projet se trouve dans ce dossier. Le token est dans `.env` : ne jamais lire son contenu dans un outil qui l'affiche, le journaliser ni le copier dans un message.

L'utilisateur exige un aperçu par défaut et son approbation avant toute modification Discord. Utiliser `preparer_plan` ou les outils produisant des aperçus ; montrer les actions à l'utilisateur. Après son accord, utiliser `ouvrir_approbation` et laisser l'utilisateur valider dans la fenêtre locale, puis `executer_plan`. Ne jamais cliquer à sa place, fabriquer/modifier un fichier de `data/approvals/`, réactiver les anciens outils ou appeler l'API directement pour contourner cette validation.

La sauvegarde et la lecture seules sont autorisées sans approbation Discord. Les tests hors ligne utilisent exclusivement des API simulées, des identifiants factices et des dossiers temporaires. Leur simulation d'approbation est limitée à ces dossiers et ne doit jamais être appliquée aux vrais plans.

Après une modification du programme, exécuter les tests `test_core.py`. Tester toute mutation réelle uniquement après validation humaine de son plan. Une ancienne session MCP peut conserver l'ancien code : redémarrer les clients après mise à jour.

Ne pas annoncer une restauration totale. Voir les limites du README : messages supprimés, identifiants, fils, intégrations et affectations de rôles non enregistrées. Pour une exécution partielle ou incertaine, inspecter le journal et préparer une restauration explicite, jamais rejouer automatiquement.

Pour les outils MCP, exemples de plans et procédure détaillée, lire aussi `GUIDE-IA.md`.
