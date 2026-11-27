import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from hero_death import SWORD_DURATION,SWORD_LAND
from sword_death import pose_index
from savegame import capture,restore,validate


class SwordDeathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def strike(self,side=-1,lives=3,level=5):
        g=self.g;g.new_game();g.start_level(level);g.state='play';g.sound_on=False;g.lives=lives;g.invuln=0
        enemy=g.hoplites[0];enemy.facing=enemy.previous_facing=side
        g.hero=Hero(enemy.x+side*65,enemy.y);g.hero.face=-side;g.hero.grounded=True
        for _ in range(90):
            g.update(STEP,0,False,False)
            if g.hero_death.active:break
        self.assertTrue(g.hero_death.active)
        self.assertEqual((g.hero_death.kind,g.hero_death.index,g.lives,g.deaths),('sword',0,lives-1,1))
        return enemy

    def finish(self):
        g=self.g
        for _ in range(120*10):
            g.update(STEP,0,False,False)
            if g.state=='game_over' or not (g.hero_death.active or g.resurrection.active):return
        self.fail('Sword death did not finish')

    def test_real_sword_contact_recoils_away_both_directions_then_resurrects(self):
        g=self.g
        for side in (-1,1):
            with self.subTest(side=side):
                enemy=self.strike(side);x=g.hero.x
                self.assertEqual((g.hero_death.facing,g.hero_death.hero_face),(side,-side))
                self.assertEqual(enemy.state,'attack')
                for _ in range(50):g.update(STEP,-side,True,True,fire=True,drop=True)
                self.assertGreater((g.hero.x-x)*side,0)
                self.assertFalse(g.hero.floating);self.assertFalse(g.solar.active)
                self.assertEqual(enemy.state,'alert')
                self.assertIsNotNone(g.hero_death.landed_at)
                self.finish();self.assertEqual((g.lives,g.deaths,g.state),(2,1,'play'))

    def test_airborne_body_waits_for_landing_before_ground_collapse(self):
        g=self.g;g.new_game();g.start_level(5);g.state='play';g.sound_on=False
        enemy=g.hoplites[0];g.hero=Hero(enemy.x-10,-1200)
        g.kill_hero(hoplite=enemy)
        for _ in range(round(SWORD_DURATION/STEP)+1):g.update(STEP,1,True,True)
        self.assertTrue(g.hero_death.active)
        self.assertIsNone(g.hero_death.landed_at)
        self.assertLessEqual(pose_index(g.hero_death),26)
        restore(g,capture(g));g.state='play'
        self.finish();self.assertEqual((g.lives,g.deaths),(2,1))

    def test_pause_and_save_resume_the_pose_attacker_and_remaining_rumble(self):
        g=self.g;self.strike(level=8)
        for _ in range(60):g.update(STEP,0,False,False)
        g.enter_menu('pause');data=capture(g)
        for _ in range(20):g.update(STEP,1,True,True,fire=True)
        self.assertEqual(capture(g),data)
        restore(g,data);self.assertEqual(capture(g),data)
        with patch.object(g.gamepads,'rumble') as rumble:
            g.resume_from_menu()
            self.assertTrue(rumble.called)
            self.assertGreater(rumble.call_args.kwargs['duration'],0)
            self.assertLess(rumble.call_args.kwargs['duration'],1650)
        self.finish();self.assertEqual((g.lives,g.deaths),(2,1))

    def test_invalid_attacker_and_landing_time_are_rejected(self):
        g=self.g;self.strike();data=capture(g)
        for index in (-1,len(g.hoplites)):
            bad=copy.deepcopy(data);bad['hero_death']['index']=index
            with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(data);bad['hoplites'][0]['alive']=False;bad['hoplites'][0]['state']='dead'
        with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(data);bad['hero_death']['landed_at']=.01
        with self.assertRaises(ValueError):validate(bad)

    def test_last_life_keeps_final_corpse_and_uses_the_specific_render_clip(self):
        g=self.g;self.strike(lives=1);self.finish()
        self.assertEqual((g.state,g.lives,g.deaths),('game_over',0,1))
        self.assertFalse(g.resurrection.active)
        self.assertEqual(pose_index(g.hero_death),63)
        with patch.object(g.sword_death_sprites,'draw',wraps=g.sword_death_sprites.draw) as sword,\
             patch.object(g.blade_death_sprites,'draw',side_effect=AssertionError('Wrong death clip')):
            g.draw(1,present=False);sword.assert_called_once()

    def test_all_preloaded_pose_directions_render_without_runtime_image_work(self):
        g=self.g;self.strike();before=capture(g)
        self.assertEqual(len(g.sword_death_sprites.images),1)
        with patch('pygame.image.load',side_effect=AssertionError('runtime load')),\
             patch('pygame.transform.smoothscale',side_effect=AssertionError('runtime scale')),\
             patch('pygame.transform.flip',side_effect=AssertionError('runtime mirror')):
            for face in (-1,1):
                g.hero_death.hero_face=face
                for tick in range(100):
                    g.hero_death.elapsed=tick/99*SWORD_DURATION
                    g.hero_death.previous_elapsed=max(0,g.hero_death.elapsed-STEP)
                    g.hero_death.landed_at=SWORD_LAND
                    snapshot=capture(g);g.draw(.5,present=False)
                    self.assertEqual(capture(g),snapshot)
        self.assertEqual(g.lives,before['lives'])


if __name__=='__main__':unittest.main()
