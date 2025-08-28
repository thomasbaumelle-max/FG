import json
import itertools
from pathlib import Path

MIN_HGAP = 50
MIN_VGAP = 80

def test_building_bounding_boxes_spacing():
    path = Path("assets/towns/towns_red_knights.json")
    data = json.loads(path.read_text())
    bboxes = {}
    for b in data["buildings"]:
        xs = [p[0] for p in b["hotspot"]]
        ys = [p[1] for p in b["hotspot"]]
        bboxes[b["id"]] = (min(xs), min(ys), max(xs), max(ys))
    violations = []
    for (id1, bb1), (id2, bb2) in itertools.combinations(bboxes.items(), 2):
        minx1, miny1, maxx1, maxy1 = bb1
        minx2, miny2, maxx2, maxy2 = bb2
        if maxx1 <= minx2:
            hgap = minx2 - maxx1
        elif maxx2 <= minx1:
            hgap = minx1 - maxx2
        else:
            hgap = -1
        if maxy1 <= miny2:
            vgap = miny2 - maxy1
        elif maxy2 <= miny1:
            vgap = miny1 - maxy2
        else:
            vgap = -1
        if hgap < MIN_HGAP and vgap < MIN_VGAP:
            violations.append((id1, id2, hgap, vgap))
    assert not violations, f"Building bounding boxes overlap or are too close: {violations}"
