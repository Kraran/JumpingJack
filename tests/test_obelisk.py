import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP,level,WORLD
from obelisk import Obelisk,CHECKPOINT_X,GROUND_Y,RESPAWN,ACTIVATION_TIME,ACTIVATION_FRAMES,LOOP_FRAMES


class ObeliskTests(unittest.TestCase):
    def test_midpoint_and_spawn_are_supported_by_ground(self):
        self.assertEqual(CHECKPOINT_X,WORLD/2)
        for x in (CHECKPOINT_X,RESPAWN[0]):
            self.assertTrue(any(p.ground and p.x+15<x<p.x+p.w-15 and p.y==GROUND_Y for p in level()[0]))

    def test_activation_requires_ground_and_happens_once(self):
        beacon=Obelisk();hero=Hero(CHECKPOINT_X,GROUND_Y-180);hero.grounded=True
        self.assertFalse(beacon.update(STEP,hero))
        hero.y=GROUND_Y;hero.grounded=False
        self.assertFalse(beacon.update(STEP,hero))
        hero.grounded=True
        self.assertTrue(beacon.update(STEP,hero))
        self.assertFalse(beacon.update(STEP,hero))

    def test_activation_advances_into_permanent_loop_with_interpolation(self):
        beacon=Obelisk();hero=Hero(CHECKPOINT_X,GROUND_Y);hero.grounded=True
        self.assertIsNone(beacon.frame());beacon.update(STEP,hero)
        seen=[]
        for _ in range(600):
            beacon.update(STEP,hero);seen.append(beacon.frame(.5))
        self.assertEqual(set(seen[:140]),set(range(ACTIVATION_FRAMES-2)))
        self.assertTrue(all(ACTIVATION_FRAMES<=i<ACTIVATION_FRAMES+LOOP_FRAMES for i in seen[150:]))


class ObeliskGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.reset();self.g.state='play';self.g.invuln=10

    def test_old_checkpoints_do_not_activate(self):
        for x in (2800,5400,8050):
            self.g.hero=Hero(x,GROUND_Y);self.g.update(STEP,0,False,False)
            self.assertEqual(self.g.check_index,0);self.assertFalse(self.g.obelisk.active)

    def test_death_preserves_activation_but_restart_resets_it(self):
        from support import finish_respawn
        self.g.hero=Hero(CHECKPOINT_X,GROUND_Y)
        self.g.update(STEP,0,False,False)
        self.assertTrue(self.g.obelisk.active)
        self.g.obelisk.clock=ACTIVATION_TIME+2
        self.g.hero.y=900;self.g.update(STEP,0,False,False)
        finish_respawn(self.g)
        self.assertEqual((self.g.hero.x,self.g.hero.y),RESPAWN)
        self.assertTrue(self.g.obelisk.active)
        self.assertGreater(self.g.obelisk.clock,ACTIVATION_TIME)
        self.g.reset();self.assertFalse(self.g.obelisk.active)

    def test_light_reveal_starts_at_bottom_and_loops_have_sparks(self):
        sprites=self.g.obelisk_sprites
        self.assertEqual(sprites.base.get_at((0,0)).a,0)
        def alpha_at(index,x,y):
            return sprites.atlas.get_at((index%8*160+x,index//8*256+y)).a
        self.assertEqual(alpha_at(1,80,73),0)
        self.assertGreater(alpha_at(1,80,229),0)
        self.assertGreater(alpha_at(ACTIVATION_FRAMES,80,73),0)
        self.assertNotEqual(alpha_at(ACTIVATION_FRAMES,80,140),alpha_at(ACTIVATION_FRAMES+6,80,140))

    def test_draw_does_not_advance_animation(self):
        self.g.hero=Hero(CHECKPOINT_X,GROUND_Y);self.g.update(STEP,0,False,False)
        self.g.cam=self.g.prev_cam=4200
        clock=self.g.obelisk.clock
        with patch.object(self.g.obelisk_sprites,'draw',wraps=self.g.obelisk_sprites.draw) as render:
            for alpha in (0,.5,1):self.g.draw(alpha)
            self.assertEqual(render.call_count,3)
        self.assertEqual(self.g.obelisk.clock,clock)


if __name__=='__main__':unittest.main()
