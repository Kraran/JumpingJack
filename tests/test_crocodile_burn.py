import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
import pygame as pg
from main import Game,Hero,STEP
from crocodile import Crocodile,BURN_TIME


class CrocodileBurnTests(unittest.TestCase):
    def enemy(self):return Crocodile(500,400,700,0,1200)

    def test_ignition_is_immediate_nondangerous_and_only_starts_once(self):
        enemy=self.enemy();hero=Hero(500,620)
        self.assertTrue(enemy.ignite());self.assertFalse(enemy.alive)
        self.assertFalse(enemy.hits(hero));self.assertEqual(enemy.state,'burn')
        enemy.update(.2,hero);before=enemy.death_timer
        self.assertFalse(enemy.ignite());self.assertEqual(enemy.death_timer,before)

    def test_body_stops_and_final_ashes_persist(self):
        enemy=self.enemy();enemy.state='lunge';enemy.ignite();x=enemy.x;face=enemy.facing
        for _ in range(500):self.assertIsNone(enemy.update(STEP,Hero(500,620)))
        self.assertEqual((enemy.x,enemy.px,enemy.facing),(x,x,face))
        self.assertEqual(enemy.death_timer,BURN_TIME)
        self.assertFalse(enemy.alive)

    def test_reset_restores_the_animal_and_clears_burning(self):
        enemy=self.enemy();enemy.ignite();enemy.update(.8,Hero());enemy.reset()
        self.assertTrue(enemy.alive);self.assertEqual(enemy.death_timer,0)
        self.assertEqual(enemy.state,'patrol')


class CrocodileBurnGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.reset();self.g.state='play'

    def test_ray_ignites_without_beetle_explosion_or_gold_burst(self):
        self.g.hero=Hero(700,620);self.g.hero.grounded=True;self.g.invuln=10
        with patch.object(self.g,'burst') as burst:
            for tick in range(24):self.g.update(STEP,0,False,False,fire=tick==0)
        self.assertFalse(self.g.crocodiles[0].alive)
        self.assertEqual(self.g.crocodiles[0].state,'burn')
        self.assertFalse(self.g.beetle_deaths);burst.assert_not_called()

    def test_all_24_burning_poses_play_then_last_ash_pose_is_held(self):
        enemy=self.g.crocodiles[0];enemy.ignite();sprites=self.g.crocodile_sprites
        seen=[]
        for _ in range(160):
            enemy.update(STEP,self.g.hero)
            seen.append(sprites.burn.index(sprites.sample(enemy,1)))
        self.assertEqual(sorted(set(seen)),list(range(24)))
        self.assertEqual(seen,sorted(seen))
        enemy.update(5,self.g.hero)
        self.assertIs(sprites.sample(enemy,.5),sprites.burn[-1])

    def test_ash_and_fire_keep_a_common_ground_contact(self):
        for pose in self.g.crocodile_sprites.burn:
            self.assertEqual(pose.pivot,(219,180))
            for image in pose.images:
                self.assertEqual(image.get_bounding_rect(min_alpha=32).bottom,181)

    def test_pause_freezes_the_combustion(self):
        enemy=self.g.crocodiles[0];enemy.ignite();enemy.update(.4,self.g.hero)
        self.g.state='pause';before=enemy.death_timer
        with patch.object(self.g,'close'),patch('main.pg.event.get',return_value=[]):self.g.run(frames=2)
        self.assertEqual(enemy.death_timer,before)

    def test_death_preserves_ashes_restart_restores_crocodiles(self):
        enemy=self.g.crocodiles[0];enemy.ignite();enemy.update(2,self.g.hero)
        self.g.hero.y=900;self.g.update(STEP,0,False,False)
        self.assertFalse(enemy.alive);self.assertEqual(enemy.death_timer,1.2)
        self.g.reset()
        self.assertTrue(all(enemy.alive and enemy.death_timer==0 for enemy in self.g.crocodiles))

    def test_dead_crocodile_is_drawn_without_live_body_shadow(self):
        enemy=self.g.crocodiles[0];enemy.ignite();self.g.cam=self.g.prev_cam=500
        with patch('main.draw.ellipse') as shadow:
            self.g.draw_crocodiles(500,1)
        # The other two living crocodiles are outside this viewport.
        shadow.assert_not_called()


if __name__=='__main__':unittest.main()
