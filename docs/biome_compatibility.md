# Biome Compatibility Rules

`assets/biome_compatibility.json` lists which biome symbols may be placed next
 to each other during continent generation.  The file stores a JSON object mapping
 each biome letter to a list of allowed neighbouring letters.

Example:

```json
{
  "G": ["G", "F"],
  "F": ["G", "F"]
}
```

`mapgen.continents.generate_continent_map` loads this file by default and
converts the lists to sets for faster lookups.  Custom rule sets can be supplied
via the ``biome_compatibility`` parameter when calling the function.
