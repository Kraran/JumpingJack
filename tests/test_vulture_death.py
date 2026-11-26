import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from savegame import capture,restore,validate
from support import finish_respawn
from terrain import sand_height


class VultureDeathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.new_game();self.g.state='play'

    def collide(self,level=1,air=False,lives=3):
        g=self.g;g.new_game();g.start_level(level);g.state='play';g.lives=lives
        y=300 if air else sand_height(160) if level==2 else 620
        g.hero=Hero(160,y);g.hero.grounded=not air
        enemy=g.vultures[-1]
        enemy.x=enemy.px=135.;enemy.y=enemy.py=y-70
        enemy.vx=160.;enemy.vy=650.;enemy.state='dive';enemy.timer=enemy.previous_timer=0.
        enemy.target=(160.,float(y-27));enemy.dive_angle=75
        g.update(STEP,0,False,False)
        self.assertTrue(g.hero_death.active);self.assertEqual(g.hero_death.kind,'vulture')
        return enemy

    def test_real_dive_uses_shared_poses_and_resurrects_once_on_both_levels(self):
        g=self.g
        for level in (1,2):
            for air in (False,True):
                with self.subTest(level=level,air=air):
                    enemy=self.collide(level,air)
                    self.assertTrue(g.hero_death.electrical);self.assertEqual(g.hero_death.duration,1.2)
                    self.assertEqual((g.hero_death.x,g.hero_death.y),(enemy.x,enemy.y))
                    self.assertEqual(g.hero_death.index,enemy.index)
                    x,y=g.hero.x,g.hero.y
                    for _ in range(60):g.update(STEP,1,True,True,fire=True)
                    self.assertEqual(g.hero.x,x);self.assertFalse(g.solar.active)
                    if air:self.assertGreater(g.hero.y,y)
                    finish_respawn(g)
                    self.assertEqual((g.lives,g.deaths,g.state),(2,1,'play'))
                    self.assertEqual(g.energy.value,60);self.assertTrue(g.vultures[enemy.index].alive)

    def test_last_life_feedback_and_corpse_use_the_same_electrocution(self):
        g=self.g
        with patch.object(g.gamepads,'rumble') as rumble:
            self.collide(lives=1);rumble.assert_called_once_with('death',duration=1200)
            self.assertEqual(g.state,'play');self.assertEqual(g.lives,0)
            finish_respawn(g)
            self.assertEqual(g.state,'game_over');self.assertFalse(g.resurrection.active)
            self.assertEqual(rumble.call_args.args,('game_over',))
        with patch.object(g.beetle_death_sprites,'draw',wraps=g.beetle_death_sprites.draw) as shared:
            g.draw(1,present=False);shared.assert_called_once()

    def test_pause_save_and_validation_keep_the_vulture_as_the_arc_source(self):
        g=self.g;self.collide(level=2,air=True,lives=1)
        for _ in range(38):g.update(STEP,0,False,False)
        g.enter_menu('pause');data=json.loads(json.dumps(capture(g)))
        for _ in range(10):g.update(STEP,1,True,True)
        self.assertEqual(json.loads(json.dumps(capture(g))),data)
        restore(g,data);self.assertEqual(json.loads(json.dumps(capture(g))),data)
        bad=json.loads(json.dumps(data));bad['vultures'][bad['hero_death']['index']]['alive']=False
        with self.assertRaises(ValueError):validate(bad)
        bad=json.loads(json.dumps(data));bad['hero_death']['index']=99
        with self.assertRaises(ValueError):validate(bad)
        g.resume_from_menu();finish_respawn(g);self.assertEqual(g.state,'game_over')
