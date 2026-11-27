import os
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

import pygame as pg
from menu_music import MenuMusic,VOLUME,FADE_OUT,LOADING_FADE
from settings import Settings
from localization import CODES,translate

ASSET=Path(__file__).resolve().parents[1]/'assets/audio/menu-the-lone-flyer.ogg'


class MenuMusicTests(unittest.TestCase):
    def controller(self):
        music=Mock()
        controller=MenuMusic(ASSET,music=music,clock=lambda:0.)
        self.assertTrue(controller.available)
        return controller,music

    def test_loop_fades_without_restarting_between_pages(self):
        controller,music=self.controller()
        controller.update(True,0.)
        controller.update(True,.4)
        self.assertAlmostEqual(controller.volume,VOLUME/2)
        controller.update(True,.8)
        self.assertAlmostEqual(controller.volume,VOLUME)
        controller.update(True,3.)
        music.play.assert_called_once_with(loops=-1)
        music.pause.assert_not_called()

    def test_gameplay_fade_pauses_then_menu_resumes_same_stream(self):
        controller,music=self.controller()
        controller.update(True,0.);controller.update(True,1.)
        controller.update(False,2.)
        controller.update(False,2.+FADE_OUT/2)
        self.assertAlmostEqual(controller.volume,VOLUME/2)
        music.pause.assert_not_called()
        controller.update(False,2.+FADE_OUT)
        music.pause.assert_called_once()
        controller.update(True,5.);controller.update(True,6.)
        music.unpause.assert_called_once()
        music.play.assert_called_once()
        self.assertAlmostEqual(controller.volume,VOLUME)

    def test_quick_return_reverses_fade_without_a_volume_jump(self):
        controller,music=self.controller()
        controller.update(True,0.);controller.update(True,1.)
        controller.update(False,2.);controller.update(True,2.+FADE_OUT/2)
        self.assertAlmostEqual(controller.volume,VOLUME/2)
        controller.update(True,4.)
        self.assertAlmostEqual(controller.volume,VOLUME)
        music.pause.assert_not_called();music.play.assert_called_once()
        controller.close();music.stop.assert_called_once();music.unload.assert_called_once()

    def test_missing_asset_and_audio_errors_are_nonfatal(self):
        music=Mock()
        controller=MenuMusic(ASSET.with_name('missing.ogg'),music=music)
        controller.update(True);self.assertFalse(controller.available)
        music.load.assert_not_called()
        music.load.side_effect=pg.error('no decoder')
        controller=MenuMusic(ASSET,music=music)
        controller.update(True)
        self.assertFalse(controller.available);self.assertEqual(controller.error,'no decoder')

    def test_setting_is_independent_persisted_and_backwards_compatible(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json'
            path.write_text('{"sound":false,"language":"fr"}',encoding='utf-8')
            settings=Settings.load(path)
            self.assertTrue(settings.music);self.assertFalse(settings.sound)
            settings.music=False;settings.save(path)
            self.assertEqual(Settings.load(path),settings)
            path.write_text('{"music":"false","language":"fr"}',encoding='utf-8')
            self.assertTrue(Settings.load(path).music)
        for code in CODES:
            self.assertTrue(translate('Musique des menus',code))
            if code!='fr':self.assertNotEqual(translate('Musique des menus',code),'Musique des menus')

    def test_real_asset_streams_loops_pauses_and_unloads(self):
        pg.mixer.init()
        try:
            controller=MenuMusic(ASSET)
            self.assertTrue(controller.available,controller.error)
            controller.update(True,0.);controller.update(True,1.)
            self.assertTrue(pg.mixer.music.get_busy())
            # Decode the end and cross the actual Ogg wrap without waiting 100 seconds.
            pg.mixer.music.set_pos(99.98)
            pg.time.wait(200)
            self.assertTrue(pg.mixer.music.get_busy())
            controller.update(False,2.);controller.update(False,2.+FADE_OUT)
            self.assertFalse(pg.mixer.music.get_busy())
            controller.update(True,5.)
            self.assertTrue(pg.mixer.music.get_busy())
            controller.close();self.assertFalse(pg.mixer.music.get_busy())
        finally:pg.mixer.quit()

    def test_loading_uses_autonomous_mixer_fade_and_never_restarts_at_title(self):
        controller,music=self.controller()
        controller.start_loading(.7)
        music.play.assert_called_once_with(loops=-1,fade_ms=round(LOADING_FADE*1000))
        self.assertAlmostEqual(controller.volume,VOLUME*.7)
        controller.update(True,10.,volume=.7)
        music.play.assert_called_once();music.pause.assert_not_called()

    def test_live_music_volume_does_not_restart_stream_or_break_fade_out(self):
        controller,music=self.controller()
        controller.update(True,0.);controller.update(True,1.)
        controller.update(True,2.,volume=.4);controller.update(True,3.,volume=.4)
        self.assertAlmostEqual(controller.volume,VOLUME*.4)
        controller.update(False,4.,volume=.4)
        controller.update(False,5.,volume=.4)
        self.assertAlmostEqual(controller.volume,VOLUME*.2)
        controller.update(False,6.,volume=.4)
        music.pause.assert_called_once();music.play.assert_called_once()

    def test_volume_validation_and_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'settings.json'
            for value,expected in ((-10,0),(110,100),(35,35),(True,100),('40',100),(None,100)):
                import json
                path.write_text(json.dumps({'language':'fr','sound_volume':value,'music_volume':value}),encoding='utf-8')
                settings=Settings.load(path)
                self.assertEqual((settings.sound_volume,settings.music_volume),(expected,expected))
                settings.save(path);self.assertEqual(Settings.load(path),settings)
