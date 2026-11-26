import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
import pygame as pg
from main import Game
from solar_gauge import FRAMES,PERIOD


class HorusGaugeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def pixels(self):return pg.image.tobytes(self.g.capture(),'RGB')

    def test_all_energy_states_and_animation_frames_use_prepared_images(self):
        g=self.g;g.new_game();before=vars(g.energy).copy()
        with patch('pygame.image.load',side_effect=AssertionError('runtime load')),\
             patch('pygame.transform.smoothscale',side_effect=AssertionError('runtime resize')),\
             patch('pygame.transform.flip',side_effect=AssertionError('runtime mirror')):
            for low in (False,True):
                for fraction in (0,.001,.15,.3,.6,1):
                    for frame in range(FRAMES):g.solar_gauge.draw(g.canvas,fraction,frame/FRAMES*PERIOD,low)
        self.assertEqual(vars(g.energy),before)
        samples=[]
        for fraction,low,time in ((.6,False,0),(.6,False,.4),(.6,True,0),(0,True,0)):
            g.native_canvas.begin();g.solar_gauge.draw(g.canvas,fraction,time,low)
            samples.append(self.pixels())
        self.assertEqual(len(set(samples)),4)

    def test_pause_freezes_light_without_using_the_ui_clock(self):
        g=self.g;g.new_game();g.energy.reset(60)
        g.previous_elapsed=g.elapsed=1.;g.enter_menu('pause')
        images=[]
        for time in (1.,20.,300.):
            g.time=time;g.native_canvas.begin();g.draw_solar_gauge(1)
            images.append(self.pixels())
        self.assertEqual(len(set(images)),1)
        g.elapsed=g.previous_elapsed=1.4
        g.native_canvas.begin();g.draw_solar_gauge(1)
        self.assertNotEqual(self.pixels(),images[0])
