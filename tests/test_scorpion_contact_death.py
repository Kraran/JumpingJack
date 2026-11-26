import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP
from scorpion import LaserBolt
from savegame import capture,restore,validate
from support import finish_respawn
import tower_level


class ScorpionContactDeathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def stage(self,level=3,lives=3):
        g=self.g;g.new_game();g.start_level(level);g.state='play';g.lives=lives
        x,y=(350.,620.) if level==3 else tower_level.START
        g.hero=Hero(x,y);g.hero.grounded=True;g.invuln=0
        enemy=g.scorpions[0];enemy.x=enemy.px=x+40;enemy.y=y
        enemy.facing=-1;enemy.state=enemy.previous_state='recoil'
        enemy.timer=enemy.previous_timer=0.
        return enemy

    def test_contact_reuses_electrocution_and_costs_one_life_in_temple_and_tower(self):
        g=self.g
        for level in (3,4):
            with self.subTest(level=level):
                enemy=self.stage(level);g.update(STEP,0,False,False)
                self.assertTrue(g.hero_death.active);self.assertTrue(g.hero_death.electrical)
                self.assertEqual(g.hero_death.kind,'scorpion');self.assertEqual(g.hero_death.index,enemy.index)
                self.assertEqual(g.hero_death.duration,1.2)
                self.assertEqual(g.hero_death.y,enemy.y-24)
                x=g.hero.x
                for _ in range(50):g.update(STEP,1,True,True,fire=True,down=True)
                self.assertEqual(g.hero.x,x);self.assertFalse(g.solar.active);self.assertFalse(g.hero.floating)
                with patch.object(g.beetle_death_sprites,'draw',wraps=g.beetle_death_sprites.draw) as shared:
                    g.draw(1,present=False);shared.assert_called_once()
                finish_respawn(g)
                self.assertEqual((g.lives,g.deaths,g.state,g.energy.value),(2,1,'play',60))
                self.assertTrue(g.scorpions[enemy.index].alive)

    def test_pause_save_roundtrip_preserves_source_and_remaining_vibration(self):
        g=self.g;self.stage();g.update(STEP,0,False,False)
        for _ in range(30):g.update(STEP,0,False,False)
        g.enter_menu('pause');data=copy.deepcopy(capture(g))
        for _ in range(10):g.update(STEP,1,True,True)
        self.assertEqual(capture(g),data)
        restore(g,data);self.assertEqual(capture(g),data)
        bad=copy.deepcopy(data);bad['scorpions'][0]['alive']=False
        with self.assertRaises(ValueError):validate(bad)
        bad=copy.deepcopy(data);bad['hero_death']['index']=99
        with self.assertRaises(ValueError):validate(bad)
        with patch.object(g.gamepads,'rumble') as rumble:
            g.resume_from_menu()
            rumble.assert_called_once_with('death',duration=950)
        finish_respawn(g);self.assertEqual((g.lives,g.deaths),(2,1))

    def test_last_life_waits_for_animation_and_keeps_electrical_corpse(self):
        g=self.g
        with patch.object(g.gamepads,'rumble') as rumble:
            self.stage(lives=1);g.update(STEP,0,False,False)
            rumble.assert_called_once_with('death',duration=1200)
            self.assertEqual(g.state,'play');self.assertEqual(g.lives,0)
            finish_respawn(g);self.assertEqual(g.state,'game_over')
            self.assertEqual(rumble.call_args.args,('game_over',))
        with patch.object(g.beetle_death_sprites,'draw',wraps=g.beetle_death_sprites.draw) as shared:
            g.draw(1,present=False);shared.assert_called_once()

    def test_invulnerability_dead_scorpions_and_laser_priority(self):
        g=self.g;self.stage();g.invuln=1;g.update(STEP,0,False,False)
        self.assertEqual((g.lives,g.deaths),(3,0))
        enemy=self.stage();enemy.ignite();g.update(STEP,0,False,False)
        self.assertEqual((g.lives,g.deaths),(3,0))
        self.stage();g.laser_bolts=[LaserBolt(g.hero.x,g.hero.y-27,660.,0.)]
        g.update(STEP,0,False,False)
        self.assertEqual(g.hero_death.kind,'laser');self.assertFalse(g.hero_death.electrical)
        self.assertEqual((g.lives,g.deaths),(2,1))
