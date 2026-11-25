import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
import pygame as pg
from gpu_render import NativeCanvas
from loading import LoadingScreen,LoadingCancelled
from main import Game


class LoadingScreenTests(unittest.TestCase):
    def setUp(self):
        pg.init();self.screen=pg.display.set_mode((1920,1080));pg.event.clear()
        self.canvas=NativeCanvas();self.loading=LoadingScreen()
    def tearDown(self):self.canvas.release();pg.quit()

    def test_screen_presents_real_stage_progress_without_regressing(self):
        with patch.object(self.canvas,'present',wraps=self.canvas.present) as present:
            self.loading.show(self.canvas,self.screen,.4,'Animations du héros')
            self.assertEqual(self.loading.progress,.4)
            self.loading.show(self.canvas,self.screen,.2,'Transfert des textures')
            self.assertEqual(self.loading.progress,.4)
            self.loading.show(self.canvas,self.screen,1.,'Prêt')
            self.assertEqual(self.loading.progress,1.)
            self.assertEqual(present.call_count,3)

    def test_escape_and_window_close_cancel_the_loading(self):
        for event in (pg.event.Event(pg.KEYDOWN,key=pg.K_ESCAPE),pg.event.Event(pg.QUIT)):
            pg.event.post(event)
            with self.assertRaises(LoadingCancelled):self.loading.show(self.canvas,self.screen,0,'Chargement')

    def test_loading_consumes_keys_and_release_does_not_clear_game_textures(self):
        pg.event.post(pg.event.Event(pg.KEYDOWN,key=pg.K_RETURN))
        self.loading.show(self.canvas,self.screen,.8,'Préparation du menu')
        self.assertEqual(pg.event.get(pg.KEYDOWN),[])
        sentinel=object();self.canvas.textures[-1]=sentinel
        self.loading.release(self.canvas)
        self.assertFalse(self.loading.active);self.assertIs(self.canvas.textures[-1],sentinel)
        with patch.object(self.canvas,'present',side_effect=AssertionError('loader still active')):
            self.loading.show(self.canvas,self.screen,1,'Prêt')

    def test_headless_mode_never_presents_a_loading_frame(self):
        loading=LoadingScreen(enabled=False)
        with patch.object(self.canvas,'present',side_effect=AssertionError('unexpected frame')):
            loading.show(self.canvas,self.screen,.9,'Textures')
        self.assertEqual(loading.progress,.9)


class LoadingStartupTests(unittest.TestCase):
    def test_cancel_during_first_stage_closes_the_partially_initialized_game(self):
        close_game=Game.close
        with patch.object(LoadingScreen,'show',side_effect=LoadingCancelled),\
             patch.object(Game,'close',autospec=True,side_effect=close_game) as close:
            with self.assertRaises(LoadingCancelled):Game(True)
        close.assert_called_once();self.assertFalse(pg.get_init())

    def test_stages_wrap_real_initialization_and_finish_without_advancing_play(self):
        stages=[];show=LoadingScreen.show
        def record(loader,canvas,screen,progress,label):
            stages.append((progress,label));show(loader,canvas,screen,progress,label)
        with patch.object(LoadingScreen,'show',record):game=Game(True)
        try:
            self.assertEqual(stages[0][0],0);self.assertEqual(stages[-1][0],1)
            self.assertEqual([p for p,label in stages],sorted(p for p,label in stages))
            self.assertIn('Préparation des animations du héros…',[label for p,label in stages])
            self.assertEqual((game.state,game.elapsed,game.hero.x,game.lives),('title',0,160,3))
            self.assertFalse(game.loading.active)
        finally:game.close()
