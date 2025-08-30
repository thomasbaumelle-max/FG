# Écran de ville

Ce fichier décrit la façon de définir et d'afficher une scène de ville.

Chaque faction possède désormais **un unique manifeste** placé dans
`assets/towns/<faction>/town.json`. Les chemins d'images qu'il contient sont
relatifs à ce dossier et l'ensemble des assets de la faction y est regroupé.

## Schéma JSON

Le manifeste d'une scène de ville est un objet JSON contenant les champs suivants :

* `size` – tableau `[largeur, hauteur]` en pixels de la surface de rendu.
* `layers` – liste de calques dessinés dans l'ordre. Chaque élément possède :
  * `id` – identifiant unique du calque.
  * `image` – chemin vers l'image du calque.
  * `parallax` – **optionnel** coefficient de parallaxe.
* `buildings` – liste des bâtiments de la ville. Chaque entrée contient :
  * `id` – identifiant unique du bâtiment.
  * `layer` – identifiant du calque sur lequel dessiner le bâtiment.
  * `pos` – coordonnées `[x, y]` du coin supérieur gauche.
  * `states` – dictionnaire associant un nom d'état (`"built"`, `"unbuilt"`, etc.) à l'image correspondante.
  * `hotspot` – **optionnel** polygone cliquable sous forme de liste de points `[[x1, y1], [x2, y2], ...]`.
  * `tooltip` – **optionnel** texte d'aide affiché au survol.
  * `z_index` – **optionnel** entier permettant de régler l'ordre d'affichage.
  * `cost` – **optionnel** dictionnaire de ressources nécessaires à la construction.
  * `prereq` – **optionnel** liste d'identifiants de bâtiments requis.
  * `dwelling` – **optionnel** unités produites chaque jour.
  * `desc` – **optionnel** description textuelle du bâtiment.
  * `image` – **optionnel** chemin vers l'icône du bâtiment.

Les chemins d'image sont pré‑chargés si un gestionnaire d'assets est fourni.

## Exemple de manifeste et d’assets

```json
{
  "size": [1920, 1080],
  "layers": [
    {"id": "sky", "image": "layers/00_sky.png", "parallax": 0.2},
    {"id": "foreground", "image": "layers/90_foreground.png"}
  ],
  "buildings": [
    {
      "id": "barracks",
      "layer": "foreground",
      "pos": [240, 600],
      "states": {
        "unbuilt": "buildings_scaled/barracks_unbuilt.png",
        "built": "buildings_scaled/barracks_built.png"
      },
      "cost": {"wood": 5, "stone": 5},
      "prereq": ["tavern"],
      "tooltip": "Caserne"
    }
  ]
}
```

Arborescence correspondante :

```
assets/
└── towns/
    └── red_knights/
        ├── layers/
        │   ├── 00_sky.png
        │   └── 90_foreground.png
        └── buildings_scaled/
            ├── barracks_unbuilt.png
            └── barracks_built.png
```

## `load_town_scene`

La fonction `load_town_scene(path, assets)` lit le manifeste et renvoie une instance de `TownScene`. Tous les chemins d'images sont chargés via l'`AssetManager` passé en argument. Sans gestionnaire, les images ne sont pas préchargées et les ressources manquantes sont ignorées.

```python
from loaders.asset_manager import AssetManager
from loaders.town_scene_loader import load_town_scene

assets = AssetManager(repo_root=".")
scene = load_town_scene("assets/towns/red_knights/town.json", assets)
```

## `TownSceneRenderer`

Le `TownSceneRenderer` dessine une scène sur une surface `pygame`. Il est initialisé avec la scène chargée et le même gestionnaire d'assets :

```python
from render.town_scene_renderer import TownSceneRenderer
import pygame

renderer = TownSceneRenderer(scene, assets)
surface = pygame.Surface(scene.size)
renderer.draw(surface, {"barracks": "built"})
```

La méthode `draw(surface, states)` blitte les calques puis les bâtiments selon la carte d'états fournie. Les bâtiments non listés utilisent l'état `"unbuilt"` par défaut.
