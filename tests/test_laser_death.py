import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import math
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from scorpion import LaserBolt
from savegame import capture,restore,validate
from support import finish_respawn
from laser_death import pose_position
import tower_level


class LaserDeathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def collide(self,level=3,angle=0,sign=1,ground=True,lives=3):
        g=self.g;g.new_game();g.start_level(level);g.state='play';g.lives=lives
        x,y=(350.,620. if ground else 320.) if level==3 else tower_level.START
        g.hero=Hero(x,y);g.hero.grounded=ground;g.hero.face=-sign;g.invuln=0
        dx=math.cos(math.radians(angle))*sign;dy=-math.sin(math.radians(angle))
        g.laser_bolts=[LaserBolt(x-dx*80,y-27-dy*80,dx*660,dy*660)]
        for _ in range(40):
            g.update(STEP,0,False,False)
            if g.hero_death.active:break
        self.assertTrue(g.hero_death.active);self.assertEqual(g.hero_death.kind,'laser')
        self.assertEqual(g.laser_bolts,[])
        return dx,dy

    def test_real_bolts_recoil_in_both_directions_and_at_all_firing_angles(self):
        g=self.g
        for angle in (0,30,60,90):
            for sign in (-1,1):
                self.collide(angle=angle,sign=sign,ground=False)
                x=g.hero.x
                self.assertAlmostEqual(g.hero.vx,math.cos(math.radians(angle))*sign*280)
                self.assertLess(g.hero.vy,0)
                for _ in range(20):g.update(STEP,-sign,True,True,fire=True,down=True)
                if angle!=90:self.assertGreater((g.hero.x-x)*sign,0)
                self.assertFalse(g.hero.floating);self.assertFalse(g.solar.active)
                finish_respawn(g);self.assertEqual((g.lives,g.deaths),(2,1))

    def test_ground_and_tower_impacts_finish_collapse_before_resurrection(self):
        g=self.g
        for level in (3,4):
            self.collide(level=level)
            while g.hero_death.active:g.update(STEP,1,True,True,fire=True)
            self.assertGreaterEqual(g.hero_death.elapsed,1.4-1e-9)
            self.assertIsNotNone(g.hero_death.landed_at)
            self.assertGreaterEqual(g.hero_death.elapsed,g.hero_death.landed_at+.5-1e-9)
            self.assertEqual(pose_position(g.hero_death,g.hero_death.elapsed),15)
            self.assertTrue(g.resurrection.active);finish_respawn(g)
            self.assertEqual(g.energy.value,60)

    def test_airborne_death_waits_for_a_late_landing_and_the_collapse(self):
        g=self.g;self.collide(ground=False,angle=45)
        with patch.object(g.hero,'update'):
            g.hero.grounded=False
            for _ in range(180):g.update(STEP,0,False,False)
        self.assertTrue(g.hero_death.active);self.assertFalse(g.resurrection.active)
        self.assertEqual(pose_position(g.hero_death,g.hero_death.elapsed),7)
        finish_respawn(g);self.assertEqual((g.lives,g.deaths),(2,1))

    def test_vibration_changes_strength_pause_save_and_last_life_are_preserved(self):
        g=self.g
        with patch.object(g.gamepads,'rumble') as rumble:
            self.collide(lives=1)
            rumble.assert_called_once_with('death',duration=180)
            for _ in range(36):g.update(STEP,0,False,False)
            self.assertIn('laser_fall',[call.args[0] for call in rumble.call_args_list])
            g.enter_menu('pause');data=capture(g)
            for _ in range(10):g.update(STEP,1,True,True)
            self.assertEqual(capture(g),data)
            restore(g,data);self.assertEqual(capture(g),data)
            g.resume_from_menu();self.assertEqual(rumble.call_args.args,('laser_fall',))
            finish_respawn(g)
            self.assertEqual((g.state,g.lives,g.deaths),('game_over',0,1));self.assertFalse(g.resurrection.active)
            g.time=.1
            with patch.object(g.laser_death_sprites,'draw',wraps=g.laser_death_sprites.draw) as draw:
                g.draw(1,present=False);draw.assert_called_once()
        bad=copy.deepcopy(data);bad['hero_death']['landed_at']=bad['hero_death']['elapsed']+1
        with self.assertRaises(ValueError):validate(bad)
        g.new_game();old=capture(g);del old['hero_death']['landed_at'];restore(g,old)
        self.assertIsNone(g.hero_death.landed_at)

    def test_protection_occlusion_and_other_hazards_keep_their_priority(self):
        g=self.g;g.new_game();g.start_level(3);g.state='play';g.invuln=2
        g.hero=Hero(350,620);g.hero.grounded=True;g.laser_bolts=[LaserBolt(340,590,660,0)]
        g.update(STEP,0,False,False);self.assertFalse(g.hero_death.active)
        g.invuln=0;g.hero=Hero(350,900);g.laser_bolts=[LaserBolt(340,870,660,0)]
        g.update(STEP,0,False,False)
        self.assertTrue(g.hero_death.active);self.assertEqual(g.hero_death.kind,'pit')
        self.assertFalse(g.resurrection.active)

    def test_preloaded_poses_and_smoke_are_read_only_during_render(self):
        g=self.g;self.collide()
        with patch('pygame.image.load',side_effect=AssertionError('runtime load')),\
             patch('pygame.transform.smoothscale',side_effect=AssertionError('runtime scale')),\
             patch('pygame.transform.flip',side_effect=AssertionError('runtime mirror')):
            for face in (-1,1):
                g.hero_death.hero_face=face
                for i in range(65):
                    g.hero_death.elapsed=i/64*1.4;g.hero_death.previous_elapsed=max(0,g.hero_death.elapsed-STEP)
                    g.hero_death.landed_at=.3 if g.hero_death.elapsed>=.3 else None
                    before=capture(g);g.draw(.5,present=False);self.assertEqual(capture(g),before)

    def test_save_during_resurrection_keeps_a_body_that_fell_into_a_pit(self):
        from temple_level import FLOORS
        g=self.g;g.new_game();g.start_level(3);g.state='play'
        x=(FLOORS[0][1]+FLOORS[1][0])/2
        g.hero=Hero(x,610);g.laser_bolts=[LaserBolt(x-5,583,660,0)]
        g.update(STEP,0,False,False)
        self.assertEqual(g.hero_death.kind,'laser')
        while g.hero_death.active:g.update(STEP,0,False,False)
        self.assertTrue(g.resurrection.active);self.assertGreater(g.hero.y,1000)
        data=capture(g);validate(data);restore(g,data)
        self.assertTrue(g.resurrection.active);finish_respawn(g)
        self.assertEqual((g.lives,g.deaths),(2,1))
