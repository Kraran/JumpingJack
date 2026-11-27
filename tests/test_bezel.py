import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame as pg
from bezel import BezelArt,margins,cover_crop
from bezel_catalog import MODES,LABELS,TEXTS,ROWS,theme_for
from rendering import integer_viewport
from settings import Settings
from localization import CODES,translate

ROOT=Path(__file__).resolve().parents[1]


class BezelGeometryTests(unittest.TestCase):
    def test_margins_partition_every_unused_pixel_without_covering_game(self):
        for output in ((1920,1080),(2560,1080),(3440,1440),(5120,1440),(3840,1080),
                       (5120,2160),(1920,1200),(1280,720),(8192,1080)):
            with self.subTest(output=output):
                size,pos=integer_viewport(output,(1920,1080));game=pg.Rect(pos,size)
                bounds=pg.Rect(0,0,*output);pieces=margins(output,game)
                for _,rect in pieces:
                    self.assertTrue(bounds.contains(rect));self.assertFalse(rect.colliderect(game))
                for i,(_,rect) in enumerate(pieces):
                    self.assertFalse(any(rect.colliderect(other) for _,other in pieces[i+1:]))
                self.assertEqual(sum(r.w*r.h for _,r in pieces)+game.clip(bounds).w*game.clip(bounds).h,output[0]*output[1])

    def test_cover_keeps_aspect_and_inner_edges_across_narrow_and_superwide_panels(self):
        area=pg.Rect(887,0,887,887)
        for dimensions in ((1,1080),(320,1080),(960,1080),(1600,1440),(3136,1080),(1920,80)):
            for side in ('left','right','top','bottom'):
                dest=pg.Rect((0,0),dimensions);source=cover_crop(area,dest,side)
                self.assertTrue(area.contains(source))
                self.assertTrue(source.w==area.w or source.h==area.h)
                self.assertLessEqual(abs(source.w-source.h*dest.w/dest.h),max(1.,dest.w/dest.h))
                if side=='left':self.assertEqual(source.right,area.right)
                if side=='right':self.assertEqual(source.left,area.left)
                if side=='top':self.assertEqual(source.top,area.top)
                if side=='bottom':self.assertEqual(source.bottom,area.bottom)

    def test_auto_follows_all_eight_levels_and_manual_modes_stay_fixed(self):
        for level in range(1,9):
            self.assertEqual(theme_for('auto',level),'egypt' if level<5 else 'greece')
            self.assertIsNone(theme_for('none',level))
            for manual in ('egypt','greece','solar'):self.assertEqual(theme_for(manual,level),manual)

    def test_persisted_modes_validate_and_old_files_default_to_auto(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json'
            for value in (*MODES,'invalid',None,[],{},True,4):
                path.write_text(json.dumps({'language':'fr','bezel':value}),encoding='utf-8')
                expected=value if isinstance(value,str) and value in MODES else 'auto'
                choices=Settings.load(path);self.assertEqual(choices.bezel,expected)
                choices.save(path);self.assertEqual(Settings.load(path).bezel,expected)
            path.write_text('{"language":"fr"}',encoding='utf-8')
            self.assertEqual(Settings.load(path).bezel,'auto')
        self.assertEqual(set(ROWS),set(CODES)-{'fr'})
        for code in CODES:
            for source in TEXTS:self.assertTrue(translate(source,code))

    def test_software_bezels_fill_margins_but_never_touch_game_pixels(self):
        pg.init();pg.display.set_mode((1,1))
        try:
            art=BezelArt(ROOT/'assets/bezels');self.assertEqual(set(art.images),{'egypt','greece','solar'})
            for output in ((2560,1080),(3840,1080),(1920,1200)):
                size,pos=integer_viewport(output,(1920,1080));viewport=pg.Rect(pos,size)
                for theme in (*art.images,None):
                    target=pg.Surface(output);target.fill((1,2,3))
                    art.draw_software(target,theme,viewport)
                    self.assertEqual(target.get_at(viewport.center)[:3],(1,2,3))
                    for _,rect in margins(output,viewport):
                        self.assertEqual(target.get_at(rect.center)[:3]==(1,2,3),theme is None)
        finally:pg.quit()


class BezelMenuTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from main import Game
        cls.game=Game(True)
    @classmethod
    def tearDownClass(cls):cls.game.close()

    def test_keyboard_controller_mouse_and_return_persist_selection(self):
        from gamepad import PadSnapshot
        game=self.game
        with tempfile.TemporaryDirectory() as directory:
            game.settings_path=Path(directory)/'settings.json'
            game.enter_menu('settings');game.menu.selected['settings']=7
            game.menu_key(pg.K_RETURN);self.assertEqual(game.state,'bezels')
            game.menu.selected['bezels']=4;game.handle_pad(PadSnapshot(confirm_pressed=True))
            self.assertEqual(Settings.load(game.settings_path).bezel,'solar')
            game.menu.pointer('bezels',game.menu.rectangles('bezels')[2].center)
            game.menu_action('activate');self.assertEqual(game.settings.bezel,'egypt')
            game.start_level(7);game.state='play';game.set_bezel('auto');game.draw(present=False)
            self.assertEqual(game.native_canvas.bezel_theme,'greece')
            game.start_level(2);game.draw(present=False)
            self.assertEqual(game.native_canvas.bezel_theme,'egypt')
            game.enter_menu('bezels');game.menu_key(pg.K_ESCAPE)
            self.assertEqual(game.state,'settings')
            game.enter_menu('bezels');game.menu.selected['bezels']=len(MODES);game.menu_action('activate')
            self.assertEqual(game.state,'settings')
        game.settings_path=None

    def test_every_settings_row_stays_above_footer_and_every_bezel_renders(self):
        game=self.game
        self.assertLessEqual(game.menu.rectangles('settings')[-1].bottom,648)
        for mode in MODES:
            game.set_bezel(mode);game.enter_menu('bezels');game.draw(present=False)
        self.assertEqual(len(LABELS),5)
