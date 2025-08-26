import os
os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')

import pygame

from core.buildings import Town


def test_recruit_requires_prereqs():
    pygame.init()
    town = Town()
    town.built_structures.add('archer_camp')
    assert 'Archer' not in town.recruitable_units('archer_camp')
    town.built_structures.add('archery_range')
    units = town.recruitable_units('archer_camp')
    assert 'Archer' in units
