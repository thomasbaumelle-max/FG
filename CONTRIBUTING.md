# Guide de contribution

Pour exécuter uniquement les tests affectés par vos modifications, utilisez :

```
make fast
```

Ce script lance `pytest --testmon` afin d’exécuter uniquement les tests touchés
tout en évitant ceux marqués comme lents.

Pour relancer seulement les tests ayant échoué lors de la précédente exécution :

```
make lf
```

Cela déclenche `pytest --lf`.

Avant de valider vos modifications, exécutez également :

```
make precommit-test
```

Cette commande lance une suite de tests rapide
(`pytest --maxfail=1 -q -m "not slow and not worldgen and not combat and not serial"`)
utilisée par le hook pre-commit pour détecter les régressions.

La configuration `pytest` inclut également `--durations=20` afin d'afficher les vingt tests les plus lents.
Consultez cette liste après vos exécutions et tenez à jour le fichier
[docs/test_durations.md](docs/test_durations.md) pour orienter l'optimisation des tests.
