# Legacy Asset Listing

This file serves as a summary of all the assets necessary
for the project. This folder is divided into subfolders for categories such as buildings, units, vfx, etc.

Town screen art is now stored under `assets/towns/<faction>/` where each
faction keeps a `town.json` manifest and all related images (layers,
buildings, icons).

## File names for units images
"swordsman.png"
"archer.png"
"mage.png"
"dragon.png"
"cavalry.png"
"priest.png"
"units.png"

## Filenames for creature images
"fumet_lizard_0.png"
"shadowleaf_wolf_0.png"
"boar_raven_0.png"
"hurlombe_0.png"

## Filenames for images of the world map
"hero.png"
"portrait_hero.png"

## Filenames for visual combat effects
"fireball.png"
"arrow.png"
"chain_lightning.png"
"ice_wall.png"
"heal.png"
"focus.png"
"shield_block.png"
"charge.png"
"dragon_breath.png"
"highlight.png"
"active_unit_overlay.png"
"melee_range_overlay.png"
"ranged_range_overlay.png"

### VFX Manifest

Visual effects are described in `assets/vfx/vfx.json`. Each entry contains the
asset identifier, the image path and animation metadata:

```json
{
  "id": "fireball",
  "image": "vfx/fireball.png",
  "frame_width": 64,
  "frame_height": 64,
  "frame_time": 0.05
}
```

`frame_width` and `frame_height` specify how the spritesheet is sliced while
`frame_time` controls the duration of each frame. Static images can simply use
their full dimensions with any reasonable `frame_time`.

## Filenames of treasure/resources on the world map
"treasure.png"

## Filenames for item and skill images
"iron_sword.png"
"leather_armor.png"
"potion.png"
"ring_luck.png"
"amulet_phoenix.png"
"skill_combat.png"
"skill_magic.png"

## Filenames for building images
"mine.png"
"sawmill.png"
"crystal_mine.png"
"town.png"

## Filenames for base terrain images
"hills.png"
"swamp.png"
"jungle.png"
"ice.png"
"grass.png"
"forest.png"
"desert.png"
"obstacle.png"
"mountain.png"
"ocean.png"

## Filenames for oriented coast images
"coast_east.png"
"coast_north.png"
"coast_south.png"
"coast_west.png"
"coast_east_north.png"
"coast_east_south.png"
"coast_east_west.png"
"coast_north_south.png"
"coast_north_west.png"
"coast_south_west.png"
"coast_east_north_south.png"
"coast_east_north_west.png"
"coast_east_south_west.png"
"coast_north_south_west.png"
"coast_east_north_south_west.png"

## Filenames for music files
"attack.wav"
"move.wav"
"victory.wav"
"title_theme.ogg"

