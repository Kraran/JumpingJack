import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import MagicMock,patch
import pygame as pg
from main import Game,Platform,PLATFORM_WIDTHS,ROOT
from platform_sprites import SacredPlatforms
from gpu_render import SCALE,DesignCanvas


class SacredPlatformTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init();pg.display.set_mode((32,32))
        cls.sprites=SacredPlatforms(ROOT/'assets'/'sacred-platforms-v1.png',PLATFORM_WIDTHS)
    @classmethod
    def tearDownClass(cls):pg.quit()

    def test_all_five_sizes_share_one_native_hd_atlas_with_clean_alpha(self):
        self.assertEqual(len(self.sprites.images),1)
        self.assertEqual(self.sprites.atlas.get_size(),(540,240))
        for width,area in self.sprites.areas.items():
            self.assertEqual(area.size,(round(width*SCALE),48))
            bounds=self.sprites.atlas.subsurface(area).get_bounding_rect(min_alpha=32)
            self.assertEqual(bounds,pg.Rect(0,0,*area.size))

    def test_render_uses_cached_atlas_and_exact_collision_rectangle(self):
        native=MagicMock();canvas=DesignCanvas(native)
        with patch('pygame.image.load',side_effect=AssertionError('runtime load')),patch('pygame.transform.smoothscale',side_effect=AssertionError('runtime scale')):
            for width in PLATFORM_WIDTHS:
                platform=Platform(390,492,width,32)
                self.sprites.draw(canvas,platform,125.3333333)
                image,destination,source=native.blit.call_args.args
                self.assertIs(image,self.sprites.atlas)
                self.assertEqual(destination,canvas.rect((platform.x-125.3333333,platform.y,width,32)))
                self.assertEqual(destination.size,source.size)


class SacredPlatformGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def test_only_suspended_platforms_use_new_sprites_and_all_sizes_are_drawn(self):
        with patch.object(self.g.platform_sprites,'draw') as render:
            for width in PLATFORM_WIDTHS:self.g.platform(Platform(100,400,width,32),0)
            self.g.platform(Platform(0,620,1000,140,True),0)
        self.assertEqual(render.call_count,5)
