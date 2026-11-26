import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from temple_art import TORCH_X,FLAME_FRAMES,FLAME_PERIOD


class TempleFireTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        self.g.new_game();self.g.start_level(3);self.g.state='play'

    def test_each_visible_flame_frame_has_a_hot_core(self):
        art=self.g.temple_art
        self.assertEqual(len(art.flame_masks),FLAME_FRAMES)
        for mask in art.flame_masks:self.assertGreater(mask.count(),100)
        self.assertEqual(art.flame_frame(0),art.flame_frame(FLAME_PERIOD))

    def test_contact_with_every_torch_is_lethal_in_all_animation_frames(self):
        art=self.g.temple_art
        for i in range(FLAME_FRAMES):
            for x in TORCH_X:self.assertTrue(art.flame_hits(Hero(x,390),(i+.25)*FLAME_PERIOD/FLAME_FRAMES))

    def test_smoke_halo_and_brazier_support_are_not_lethal(self):
        art=self.g.temple_art
        for i in range(FLAME_FRAMES):
            time=(i+.25)*FLAME_PERIOD/FLAME_FRAMES
            for x,y in ((650,300),(710,390),(650,480)):
                self.assertFalse(art.flame_hits(Hero(x,y),time),(i,x,y))

    def test_fast_horizontal_and_vertical_crossings_cannot_tunnel(self):
        art=self.g.temple_art;hero=Hero(800,380);hero.px=500
        self.assertTrue(art.flame_hits(hero,0))
        hero=Hero(650,450);hero.py=280
        self.assertTrue(art.flame_hits(hero,0))

    def test_crouched_body_can_pass_below_the_flames(self):
        art=self.g.temple_art;hero=Hero(650,435)
        self.assertTrue(art.flame_hits(hero,0))
        hero.crouch=hero.previous_crouch=1.
        self.assertFalse(art.flame_hits(hero,0))

    def test_contact_costs_one_life_and_triggers_death_vibration(self):
        from support import finish_respawn
        g=self.g;g.hero=Hero(650,390);g.invuln=100
        with patch.object(g.gamepads,'rumble') as rumble:g.update(STEP,0,False,False)
        self.assertEqual(g.lives,2);self.assertEqual(g.deaths,1)
        self.assertEqual(sum(call.args==('death',) for call in rumble.call_args_list),1)
        finish_respawn(g)
        self.assertEqual(g.hero.x,g.checkpoint[0])

    def test_last_life_ends_in_game_over(self):
        from support import finish_respawn
        g=self.g;g.hero=Hero(650,390);g.lives=1
        g.update(STEP,0,False,False)
        self.assertEqual(g.state,'play');self.assertTrue(g.hero_death.active)
        finish_respawn(g)
        self.assertEqual((g.state,g.lives),('game_over',0))

    def test_other_levels_do_not_have_temple_flame_collisions(self):
        g=self.g
        for level in (1,2):
            g.start_level(level);g.hero=Hero(650,390);g.invuln=100
            g.update(STEP,0,False,False);self.assertEqual(g.lives,3)
