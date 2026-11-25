import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from pathlib import Path
from types import SimpleNamespace
import pygame as pg
from desert_art import DesertArt
from desert_level import RIVER,WATER_Y
from gpu_render import SCALE
from rendering import pixel


class RiverReflectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init();pg.display.set_mode((1,1))
        cls.art=DesertArt.__new__(DesertArt)
        cls.art.water=DesertArt.make_water(Path(__file__).resolve().parents[1]/'assets/desert-water-v1.png')

    @classmethod
    def tearDownClass(cls):
        del cls.art
        pg.quit()

    def test_reflection_spans_the_whole_river_without_repeating_at_256_pixels(self):
        image=self.art.water
        self.assertEqual(image.get_size(),(pixel((RIVER[1]-RIVER[0]+290)*SCALE),128*48))
        first=image.subsurface((300,0,256,128))
        following=image.subsurface((556,0,256,128))
        self.assertNotEqual(pg.image.tobytes(first,'RGB'),pg.image.tobytes(following,'RGB'))

    def test_scrolling_preserves_reflection_across_former_tile_edges(self):
        a=pg.Surface((1920,1080));b=a.copy()
        self.art.river(SimpleNamespace(native=a),800,.7)
        self.art.river(SimpleNamespace(native=b),810,.7)
        y=pixel(WATER_Y*SCALE)
        self.assertEqual(pg.image.tobytes(a.subsurface((15,y,1905,120)),'RGB'),
                         pg.image.tobytes(b.subsurface((0,y,1905,120)),'RGB'))

    def test_animation_loop_has_no_abrupt_reflection_reset(self):
        image=self.art.water
        points=[(x,y) for x in range(90,image.get_width()-90,137) for y in range(5,125,11)]
        changes=[]
        for frame in range(48):
            following=(frame+1)%48
            changes.append(sum(abs(image.get_at((x,frame*128+y))[c]-
                                   image.get_at((x,following*128+y))[c])
                               for x,y in points for c in range(3)))
        self.assertLessEqual(changes[-1],max(changes[:-1])*1.5)

    def test_waves_visibly_deform_the_reflection(self):
        image=self.art.water
        points=[(x,y) for x in range(30,image.get_width()-30,23) for y in range(5,120,7)]
        change=sum(abs(image.get_at((x,y))[c]-image.get_at((x,y+12*128))[c])
                   for x,y in points for c in range(3))/(len(points)*3)
        self.assertGreater(change,8,'The water should visibly move over a quarter cycle.')

    def test_surface_contour_undulates_gently_and_moves_with_the_waves(self):
        image=self.art.water
        profiles=[]
        for frame in range(48):
            profile=[next(y for y in range(10) if image.get_at((x,frame*128+y)).a>127)
                     for x in range(0,image.get_width(),31)]
            self.assertGreaterEqual(max(profile)-min(profile),4)
            self.assertGreaterEqual(min(profile),1)
            self.assertLessEqual(max(profile),7)
            profiles.append(profile)
        self.assertNotEqual(profiles[0],profiles[12])
        for frame,profile in enumerate(profiles):
            self.assertLessEqual(max(abs(a-b) for a,b in zip(profile,profiles[(frame+1)%48])),1)
