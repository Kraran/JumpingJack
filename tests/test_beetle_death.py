import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from hero_death import BEETLE_DURATION,BEETLE_STUN,DURATION
from savegame import capture,restore,validate
from support import finish_respawn


class BeetleDeathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.new_game();self.g.state='play'

    def collide(self,level=1,lives=3,ground=False):
        g=self.g;g.new_game();g.start_level(level);g.state='play';g.lives=lives
        enemy=g.beetle_motions[0]
        if ground:
            enemy.x=enemy.px=300.;enemy.y=enemy.py=593.
            g.hero=Hero(325,620);g.hero.grounded=True
            with patch.object(enemy,'update'):g.update(STEP,0,False,False)
        else:
            g.hero=Hero(enemy.x+25,enemy.y+27)
            g.update(STEP,0,False,False)
        self.assertTrue(g.hero_death.active);self.assertEqual(g.hero_death.kind,'beetle')
        return enemy

    def test_real_beetle_contacts_animate_in_every_level_and_cost_one_life(self):
        g=self.g
        for level in range(1,5):
            with self.subTest(level=level):
                source=self.collide(level)
                self.assertEqual((g.lives,g.deaths),(2,1));self.assertNotIn(source.index,g.dead_beetles)
                finish_respawn(g)
                self.assertEqual((g.lives,g.deaths,g.state),(2,1,'play'))
                self.assertEqual(g.energy.value,60);self.assertGreater(g.invuln,0)
                self.assertFalse(g.hero_death.active);self.assertFalse(g.resurrection.active)

    def test_ground_collapse_and_air_fall_ignore_commands_and_keep_world_collisions(self):
        g=self.g
        for ground in (False,True):
            with self.subTest(ground=ground):
                self.collide(ground=ground);x,y=g.hero.x,g.hero.y
                for _ in range(10):g.update(STEP,1,True,True,fire=True,down=True)
                self.assertEqual((g.hero.x,g.hero.y),(x,y));self.assertFalse(g.solar.active)
                for _ in range(70):g.update(STEP,-1,True,True,fire=True)
                self.assertEqual(g.hero.x,x);self.assertEqual(g.deaths,1)
                if ground:self.assertEqual(g.hero.y,620);self.assertTrue(g.hero.grounded)
                else:self.assertGreater(g.hero.y,y)

    def test_rumble_spans_animation_and_last_life_waits_before_game_over(self):
        g=self.g
        with patch.object(g.gamepads,'rumble') as rumble,patch.object(g,'sound') as sound:
            self.collide(lives=1)
            rumble.assert_called_once_with('death',duration=1200)
            self.assertEqual(g.state,'play');self.assertEqual(g.lives,0)
            finish_respawn(g)
            self.assertEqual(g.state,'game_over');self.assertFalse(g.resurrection.active)
            self.assertEqual([c.args for c in rumble.call_args_list],[('death',),('game_over',)])
            self.assertEqual(sum(c.args==('game_over',) for c in sound.call_args_list),1)
            with patch.object(g.beetle_death_sprites,'draw',wraps=g.beetle_death_sprites.draw) as corpse:
                g.draw(1,present=False);corpse.assert_called_once()

    def test_later_generic_death_does_not_reuse_the_previous_electrocution(self):
        g=self.g;self.collide();finish_respawn(g)
        g.hero.y=900;g.update(STEP,0,False,False)
        self.assertTrue(g.hero_death.active);self.assertEqual(g.hero_death.kind,'pit')
        while g.hero_death.active:g.update(STEP,0,False,False)
        self.assertTrue(g.resurrection.active)

    def test_pause_and_save_preserve_electrocution_and_old_crocodile_slots(self):
        g=self.g;self.collide(lives=1)
        for _ in range(40):g.update(STEP,0,False,False)
        g.enter_menu('pause');data=json.loads(json.dumps(capture(g)))
        for _ in range(20):g.update(STEP,1,True,True,fire=True)
        self.assertEqual(json.loads(json.dumps(capture(g))),data)
        restore(g,data);self.assertEqual(json.loads(json.dumps(capture(g))),data)
        g.resume_from_menu();finish_respawn(g);self.assertEqual(g.state,'game_over')
        bad=json.loads(json.dumps(data));bad['dead_beetles']=[bad['hero_death']['index']]
        with self.assertRaises(ValueError):validate(bad)
        g.new_game();old=capture(g);del old['hero_death']['kind'];restore(g,old)
        self.assertEqual(g.hero_death.kind,'crocodile');self.assertEqual(g.hero_death.duration,DURATION)

    def test_protection_and_environmental_death_do_not_trigger_electrocution(self):
        g=self.g;enemy=g.beetle_motions[0];g.hero=Hero(enemy.x,enemy.y+27);g.invuln=2
        g.update(STEP,0,False,False);self.assertEqual(g.deaths,0);self.assertFalse(g.hero_death.active)
        g.invuln=0;g.hero=Hero(300,900);enemy.x=enemy.px=300.;enemy.y=enemy.py=873.
        with patch.object(enemy,'update'):g.update(STEP,0,False,False)
        self.assertTrue(g.hero_death.active);self.assertEqual(g.hero_death.kind,'pit')
        self.assertFalse(g.hero_death.electrical);self.assertFalse(g.resurrection.active)

    def test_every_pose_is_prepared_and_drawing_does_not_change_saved_state(self):
        g=self.g;self.collide(ground=True)
        with patch('pygame.transform.rotate',side_effect=AssertionError('runtime rotation')),\
             patch('pygame.transform.smoothscale',side_effect=AssertionError('runtime scaling')),\
             patch('pygame.transform.flip',side_effect=AssertionError('runtime flip')):
            for face in (-1,1):
                g.hero_death.hero_face=face
                for i in range(72):
                    t=i/72*BEETLE_DURATION
                    g.hero_death.elapsed=t;g.hero_death.previous_elapsed=max(0,t-STEP)
                    before=json.loads(json.dumps(capture(g)))
                    g.draw(.5,present=False)
                    self.assertEqual(json.loads(json.dumps(capture(g))),before)
