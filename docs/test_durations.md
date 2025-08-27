# Test durations

La configuration de `pytest` inclut l'option `--durations=20` pour lister les
vingt tests les plus lents. Cette section doit être mise à jour régulièrement
pour aider les contributeurs à identifier les tests à optimiser.

Exemple de sortie lors d'une exécution partielle :

```
$ pytest tests/test_coast_assets.py tests/test_caravan.py -q
.....
===================================================== slowest 20 durations =====================================================
0.16s call     tests/test_coast_assets.py::test_coast_assets_loaded
0.01s call     tests/test_caravan.py::test_townscreen_launches_caravan

(13 durations < 0.005s hidden.  Use -vv to show these durations.)
```

Les contributeurs sont encouragés à re-générer cette liste après des changements
importants et à examiner régulièrement les tests les plus lents afin de les
réduire ou les refactorer.
