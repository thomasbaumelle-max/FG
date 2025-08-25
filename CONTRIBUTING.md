# Guide de contribution

Pour exécuter uniquement les tests affectés par vos modifications, utilisez le script :

```
make fast-test
```

Ce script lance `pytest --testmon -m "not slow"` afin d’exécuter uniquement les tests touchés
tout en évitant ceux marqués comme lents.
