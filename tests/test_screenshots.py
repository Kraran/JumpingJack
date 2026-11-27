import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import pygame as pg
from screenshots import Screenshots,save_png
from localization import CODES,translate
from screenshots_catalog import TEXTS,ROWS


class ScreenshotStoreTests(unittest.TestCase):
    def test_timestamp_collision_never_overwrites_previous_png(self):
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'captures';image=pg.Surface((16,12));image.fill('red')
            first=save_png(image,target,'2026-11-27_01-00-00_000000')
            image.fill('blue');second=save_png(image,target,'2026-11-27_01-00-00_000000')
            self.assertNotEqual(first,second)
            self.assertEqual(pg.image.load(str(first)).get_at((0,0))[:3],(255,0,0))
            self.assertEqual(pg.image.load(str(second)).get_at((0,0))[:3],(0,0,255))

    def test_async_write_finishes_before_shutdown_and_notice_expires(self):
        with tempfile.TemporaryDirectory() as directory:
            manager=Screenshots(Path(directory)/'captures',clock=lambda:10.)
            self.assertFalse(manager.directory.exists());manager.request()
            self.assertTrue(manager.requested)
            manager.submit(pg.Surface((12,8)));manager.close()
            self.assertTrue(manager.last_path.is_file());self.assertFalse(manager.requested)
            self.assertIn('captures/',manager.notice)
            manager.clock=lambda:14.;self.assertIsNone(manager.notice)
            manager.close()

    def test_failed_encoding_removes_partial_file_and_reports_error(self):
        with tempfile.TemporaryDirectory() as directory:
            manager=Screenshots(directory)
            with patch('screenshots.pg.image.save',side_effect=pg.error('encoder unavailable')):
                manager.submit(pg.Surface((12,8)));manager.close()
            self.assertEqual(list(Path(directory).iterdir()),[])
            self.assertIn('encoder unavailable',manager.error)
            self.assertEqual(manager.notice,TEXTS[2])

    def test_unwritable_destination_is_nonfatal(self):
        with tempfile.TemporaryDirectory() as directory:
            destination=Path(directory)/'not-a-directory';destination.write_text('preserved')
            manager=Screenshots(destination);manager.submit(pg.Surface((12,8)));manager.close()
            self.assertIsNotNone(manager.error);self.assertIsNone(manager.last_path)
            self.assertEqual(destination.read_text(),'preserved')
        self.assertEqual(set(ROWS),set(CODES)-{'fr'})
        for code in CODES:
            for source in TEXTS:self.assertTrue(translate(source,code))


class ScreenshotGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from main import Game
        cls.game=Game(True)
    @classmethod
    def tearDownClass(cls):cls.game.close()
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        g=self.game;g.new_game();g.state='title';g.settings_path=None
        g.screenshots=Screenshots(Path(self.directory.name)/'captures')
    def tearDown(self):
        self.game.screenshots.close();self.directory.cleanup()

    def frame(self,events=()):
        from gamepad import PadSnapshot
        g=self.game
        with patch.object(g,'close'),patch.object(g.pacer,'wait'),\
             patch('main.pg.event.get',return_value=list(events)),\
             patch.object(g.gamepads,'poll',return_value=PadSnapshot()):g.run(frames=1)

    def test_f12_works_in_menus_play_death_and_results_without_starting_an_action(self):
        g=self.game
        for state in ('title','settings','bezels','play','pause','win','game_over'):
            with self.subTest(state=state):
                g.state=state;g.pending_activity=False;g.menu.code='LV'
                before=len(list(g.screenshots.directory.glob('*.png')))
                if state=='play':
                    g.rest.state='seated';g.rest.progress=g.rest.previous_progress=1.
                self.frame([pg.event.Event(pg.KEYDOWN,key=pg.K_F12)])
                g.screenshots.close()
                self.assertEqual(len(list(g.screenshots.directory.glob('*.png'))),before+1)
                self.assertEqual(g.state,state);self.assertFalse(g.pending_jump)
                self.assertEqual(g.menu.code,'LV')
                if state=='play':self.assertTrue(g.rest.active)

    def test_full_output_png_contains_bezel_and_exact_game_pixels(self):
        from rendering import integer_viewport
        g=self.game;g.state='play';g.settings.bezel='solar'
        g.screen=pg.display.set_mode((2560,1080))
        try:
            self.frame([pg.event.Event(pg.KEYDOWN,key=pg.K_F12)])
            g.screenshots.close();image=pg.image.load(str(g.screenshots.last_path))
            self.assertEqual(image.get_size(),(2560,1080))
            size,pos=integer_viewport(image.get_size(),(1920,1080))
            self.assertEqual(pg.image.tobytes(image.subsurface(pg.Rect(pos,size)),'RGB'),pg.image.tobytes(g.capture(),'RGB'))
            self.assertNotEqual(image.get_at((100,500))[:3],(10,17,22))
        finally:g.screen=pg.display.set_mode((1920,1080));g.settings.bezel='auto'

    def test_no_capture_on_normal_frame_or_keyboard_repeat(self):
        g=self.game
        with patch.object(g.native_canvas,'present',wraps=g.native_canvas.present) as present:
            self.frame();self.frame([pg.event.Event(pg.KEYDOWN,key=pg.K_F12,repeat=True)])
        self.assertFalse(any(call.kwargs.get('capture') for call in present.call_args_list))
        self.assertFalse(g.screenshots.directory.exists())

    def test_gpu_readback_failure_keeps_game_rendering(self):
        g=self.game;present=g.native_canvas.present
        def reject_capture(screen,**kwargs):
            if kwargs.get('capture'):raise pg.error('readback failed')
            return present(screen)
        with patch.object(g.native_canvas,'present',side_effect=reject_capture):
            self.frame([pg.event.Event(pg.KEYDOWN,key=pg.K_F12)])
        self.assertIn('readback failed',g.screenshots.error)
        self.assertEqual(g.state,'title')
