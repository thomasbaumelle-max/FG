from mapgen.continents import required_coast_images


def test_required_coast_images():
    images = required_coast_images()
    assert "mask_n.png" in images
    assert "mask_ne.png" in images
