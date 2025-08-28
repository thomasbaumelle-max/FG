# Écran de ville

Ce fichier décrit la façon de définir et d'afficher une scène de ville.

## Schéma JSON

Le manifeste d'une scène de ville est un objet JSON contenant les champs suivants :

* `size` – tableau `[largeur, hauteur]` en pixels de la surface de rendu.
* `layers` – liste de calques dessinés dans l'ordre. Chaque élément possède :
  * `id` – identifiant unique du calque.
  * `image` – chemin vers l'image de fond.
* `buildings` – liste des bâtiments de la ville. Chaque entrée contient :
  * `id` – identifiant unique du bâtiment.
  * `layer` – identifiant du calque sur lequel dessiner le bâtiment.
  * `pos` – coordonnées `[x, y]` du coin supérieur gauche.
  * `states` – dictionnaire associant un nom d'état (`"built"`, `"unbuilt"`, etc.) à l'image correspondante.
  * `hotspot` – **optionnel** rectangle cliquable `[x, y, largeur, hauteur]`.
  * `tooltip` – **optionnel** texte d'aide affiché au survol.

Les chemins d'image sont relatifs au répertoire `assets/` et seront pré‑chargés si un gestionnaire d'assets est fourni.

## Exemple de manifeste et d’assets

```json
{
  "size": [256, 192],
  "layers": [
    {"id": "bg", "image": "towns/grassland/background.png"},
    {"id": "decor", "image": "towns/grassland/decor.png"}
  ],
  "buildings": [
    {
      "id": "tavern",
      "layer": "decor",
      "pos": [80, 96],
      "states": {
        "unbuilt": "towns/grassland/tavern_unbuilt.png",
        "built": "towns/grassland/tavern_built.png"
      },
      "hotspot": [80, 96, 64, 64],
      "tooltip": "Taverne"
    }
  ]
}
```

Arborescence correspondante :

```
assets/
└── towns/
    └── grassland/
        ├── background.png
        ├── decor.png
        ├── tavern_unbuilt.png
        └── tavern_built.png
```

## `load_town_scene`

La fonction `load_town_scene(path, assets)` lit le manifeste et renvoie une instance de `TownScene`. Tous les chemins d'images sont chargés via l'`AssetManager` passé en argument. Sans gestionnaire, les images ne sont pas préchargées et les ressources manquantes sont ignorées.

```python
from loaders.asset_manager import AssetManager
from loaders.town_scene_loader import load_town_scene

assets = AssetManager(repo_root=".")
scene = load_town_scene("assets/towns/grassland/town.json", assets)
```

## `TownSceneRenderer`

Le `TownSceneRenderer` dessine une scène sur une surface `pygame`. Il est initialisé avec la scène chargée et le même gestionnaire d'assets :

```python
from render.town_scene_renderer import TownSceneRenderer
import pygame

renderer = TownSceneRenderer(scene, assets)
surface = pygame.Surface(scene.size)
renderer.draw(surface, {"tavern": "built"})
```

La méthode `draw(surface, states)` blitte les calques puis les bâtiments selon la carte d'états fournie. Les bâtiments non listés utilisent l'état `"unbuilt"` par défaut.
