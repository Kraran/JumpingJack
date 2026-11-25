import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from temple_exit import TempleExit,ENTRY_X,CENTER_X,APPROACH,TURN,CLIMB,DURATION,FOOT_Y
from savegame import capture,restore,validate


class TempleExitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        self.g.new_game();self.g.start_level(3);self.g.state='play';self.g.invuln=100

    def begin(self):
        g=self.g;g.hero=Hero(ENTRY_X,620);g.hero.grounded=True
        g.update(STEP,0,False,False);self.assertTrue(g.temple_exit.active)
        return g

    def test_entry_requires_grounded_hero_at_threshold_height(self):
        ending=TempleExit();hero=Hero(ENTRY_X,620)
        self.assertFalse(ending.can_start(hero));hero.grounded=True
        self.assertTrue(ending.can_start(hero));hero.x=ENTRY_X-1
        self.assertFalse(ending.can_start(hero));hero.x=ENTRY_X;hero.y=400
        self.assertFalse(ending.can_start(hero))

    def test_controlled_climb_is_centered_rises_each_step_and_finishes_after_fade(self):
        g=self.begin();previous_y=620;positions=[]
        for _ in range(650):
            g.update(STEP,-1,True,True,drop=True,fire=True,down=True)
            if g.temple_exit.elapsed>=APPROACH:
                self.assertAlmostEqual(g.hero.x,CENTER_X)
                self.assertLessEqual(g.hero.y,previous_y+1e-6);previous_y=g.hero.y
            positions.append(g.hero.y)
            self.assertFalse(g.solar.active);self.assertEqual(g.lives,3)
            if g.temple_exit.elapsed<APPROACH+TURN+CLIMB:self.assertEqual(g.state,'play')
            if g.state=='win':break
        self.assertEqual(g.state,'win');self.assertAlmostEqual(g.hero.y,FOOT_Y[-1])
        self.assertEqual(g.temple_exit.elapsed,DURATION)
        self.assertGreater(len(set(round(y,1) for y in positions)),100)

    def test_pause_freezes_cutscene_and_render_does_not_mutate_or_transform(self):
        g=self.begin()
        for _ in range(180):g.update(STEP,0,False,False)
        g.state='pause';before=json.loads(json.dumps(capture(g)))
        g.update(STEP,1,True,True)
        with patch('pygame.transform.smoothscale',side_effect=AssertionError('runtime scale')):
            g.draw(.4,present=False)
        self.assertEqual(json.loads(json.dumps(capture(g))),before)

    def test_save_and_load_resume_the_middle_of_the_stairs(self):
        g=self.begin()
        for _ in range(250):g.update(STEP,0,False,False)
        data=json.loads(json.dumps(capture(g)));restore(g,data)
        self.assertEqual(json.loads(json.dumps(capture(g))),data)
        for _ in range(400):
            if g.state=='win':break
            g.update(STEP,0,False,False)
        self.assertEqual(g.state,'win')

    def test_old_saves_get_an_inactive_ending_and_bad_ending_is_rejected(self):
        g=self.g;data=capture(g);del data['temple_exit'];restore(g,data)
        self.assertFalse(g.temple_exit.active)
        data=capture(g);data['temple_exit']['elapsed']=float('nan')
        with self.assertRaises(ValueError):validate(data)

    def test_exit_frames_are_invisible_before_win_and_fit_texture_limits(self):
        sprites=self.g.temple_exit_sprites;area=sprites.areas[-1]
        import pygame as pg
        self.assertEqual(pg.mask.from_surface(sprites.atlas.subsurface(area),0).count(),0)
        self.assertLessEqual(max(sprites.atlas.get_size()),4096)
