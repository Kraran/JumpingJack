import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
import pygame as pg
from gpu_render import NativeCanvas,DesignCanvas
from main import level
from pit_darkness import PitDarkness,pit_regions


class PitDarknessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init();pg.display.set_mode((1,1));cls.shade=PitDarkness.load()
    @classmethod
    def tearDownClass(cls):pg.quit()

    def test_level_progression_and_depth_use_preloaded_smooth_gradients(self):
        native=NativeCanvas();canvas=DesignCanvas(native)
        brightness=[]
        for stage in (1,2,3):
            native.surface.fill((255,255,255))
            self.shade.draw(canvas,((100,200),),stage,0)
            brightness.append(native.surface.get_at(canvas.point((150,650))).r)
            self.assertEqual(native.surface.get_at(canvas.point((150,620))).r,255)
            self.assertEqual(native.surface.get_at(canvas.point((150,715))).r,0)
            self.assertEqual(native.surface.get_at(canvas.point((90,690))).r,255)
            self.assertEqual(native.surface.get_at(canvas.point((150,619))).r,255)
        self.assertTrue(255>brightness[0]>brightness[1]>brightness[2]>0)
        for image in self.shade.images:
            alpha=[image.get_at((0,y)).a for y in range(image.get_height())]
            self.assertEqual(alpha,sorted(alpha));self.assertLessEqual(max(b-a for a,b in zip(alpha,alpha[1:])),8)

    def test_regions_follow_ground_gaps_without_shading_water_or_rocks(self):
        self.assertEqual(pit_regions(level(1)[0],1)[0],(1220,1400))
        self.assertEqual(pit_regions(level(3)[0],3)[0],(1700,1920))
        self.assertEqual(pit_regions(level(2)[0],2),())
        self.assertEqual(pit_regions(level(4)[0],4),())

    def test_camera_clipping_keeps_the_shadow_inside_each_opening(self):
        native=NativeCanvas();canvas=DesignCanvas(native);native.surface.fill((255,255,255))
        self.shade.draw(canvas,((100,200),),3,150)
        self.assertEqual(native.surface.get_at(canvas.point((0,710))).r,0)
        self.assertEqual(native.surface.get_at(canvas.point((49,710))).r,0)
        self.assertEqual(native.surface.get_at(canvas.point((51,710))).r,255)

    def test_temple_shaft_has_opaque_recessed_stones_and_a_visible_depth_gradient(self):
        from pathlib import Path
        from temple_art import TempleArt
        stone=pg.image.load(str(Path(__file__).resolve().parents[1]/'assets/sandstone.png')).convert()
        stone=pg.transform.smoothscale(stone,(256,256))
        stone.fill((165,151,126),special_flags=pg.BLEND_RGB_MULT)
        wall=TempleArt.make_pit_wall(stone,330)
        self.assertEqual(pg.mask.from_surface(wall,254).count(),wall.get_width()*wall.get_height())
        colors={tuple(wall.get_at((x,20)))[:3] for x in range(30,300)}
        self.assertGreater(len(colors),15)
        self.assertNotEqual(wall.get_at((3,20)),wall.get_at((120,20)))
        native=NativeCanvas();canvas=DesignCanvas(native)
        native.surface.fill((255,0,255))
        native.blit(wall,(0,930));self.shade.draw(canvas,((0,220),),3,0)
        # Actual textured pixels must survive near the lip, fade lower down,
        # then become black, without leaking the room/magenta behind the shaft.
        near=[native.surface.get_at((x,945)).r for x in range(30,300)]
        mid=[native.surface.get_at((x,990)).r for x in range(30,300)]
        deep=[native.surface.get_at((x,1065)).r for x in range(30,300)]
        self.assertGreater(max(near)-min(near),8)
        self.assertGreater(sum(near),sum(mid));self.assertGreater(sum(mid),sum(deep))
        self.assertEqual(max(deep),0)
