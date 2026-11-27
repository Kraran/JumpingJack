import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import unittest
from unittest.mock import patch

from main import Game, Hero, STEP
from greece_levels import LEVELS, HUD_LABELS
from savegame import capture, restore, validate
from localization import CODES, translate
from scorpion import LaserBolt


class GreeceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def setUp(self):self.g.new_game();self.g.settings.language='fr'

    def test_campaign_preserves_energy_lives_score_and_medals_through_world_boundary(self):
        g=self.g;g.start_level(4);g.lives=2;g.energy.value=17;g.score=1234
        g.medallions.collect(4)
        for target in range(5,9):
            g.state='win';g.continue_or_restart()
            self.assertEqual((g.level_id,g.state,g.lives,g.energy.value,g.score),(target,'play',2,17,1234))
            self.assertEqual(g.medallions.claimed_levels,{4})
        g.state='win';g.continue_or_restart()
        self.assertEqual((g.level_id,g.lives,g.score),(1,3,0))

    def test_all_greek_saves_round_trip_state_enemies_and_drop_references(self):
        g=self.g
        for level_id in LEVELS:
            with self.subTest(level=level_id):
                g.start_level(level_id);g.state='play';g.score=1230;g.level_score=20
                g.energy.value=41;g.taken={0,2};g.dead_beetles={0}
                g.medallions.claimed_levels=set(range(1,level_id+1));g.medallions.count=2
                g.obelisks[0].active=True;g.check_index=1
                g.checkpoint=(g.obelisks[0].x-60,g.obelisks[0].y)
                support=next(p for p in g.platforms if not p.ground)
                g.hero=Hero(support.x+support.w/2,support.y);g.hero.grounded=True
                g.hero.update(STEP,0,True,True,g.platforms,drop=True)
                if g.scorpions:
                    g.laser_bolts=[LaserBolt(1000.,500.,660.,-10.)]
                    g.scorpions[0].ignite()
                expected=json.loads(json.dumps(capture(g)))
                g.new_game();restore(g,expected)
                self.assertEqual(json.loads(json.dumps(capture(g))),expected)
                self.assertIsNot(g.hero.drop_support,support)
                self.assertIn(g.hero.drop_support,g.platforms)
                g.state='play';g.draw(.5,present=False)
                g.update(STEP,0,False,False)
                self.assertIn(0,g.dead_beetles)

    def test_codes_and_actual_greek_victory_bonus(self):
        g=self.g
        for level_id in LEVELS:
            g.enter_menu('title')
            self.assertTrue(g.menu.feed_code(f'LV{level_id:02}',g.time))
            self.assertEqual(g.menu.code_level,level_id)
            g.start_level(level_id);g.state='play'
            g.hero=Hero(g.world_length+96,LEVELS[level_id].FLOORS[-1][2]);g.hero.grounded=True
            g.update(STEP,0,False,False)
            self.assertEqual(g.state,'win')
            self.assertEqual(g.score,level_id*1000+300)
            g.complete_level();self.assertEqual(g.score,level_id*1000+300)
            with patch.object(g,'text',wraps=g.text) as text:g.draw(1,present=False)
            calls=[call.args[0] for call in text.call_args_list]
            self.assertIn('Entrée, Start ou A pour rejouer' if level_id==8 else 'Entrée, Start ou A pour continuer',calls)
            g.new_game()

    def test_new_titles_translate_and_keep_the_level_numbers(self):
        for language in CODES:
            for level_id,label in HUD_LABELS.items():
                result=translate(label,language)
                self.assertIn(f'{level_id:02}',result)
                if language!='fr':self.assertNotEqual(result,label)

    def test_last_terrace_checkpoint_respawn_and_invalid_inventory(self):
        g=self.g;g.start_level(8);g.state='play'
        point=g.obelisks[-1];g.hero=Hero(point.x,point.y);g.hero.grounded=True
        g.invuln=100;g.update(STEP,0,False,False)
        self.assertEqual(g.checkpoint,(point.x-60,point.y))
        g.respawn_hero();self.assertEqual((g.hero.x,g.hero.y),g.checkpoint)
        self.assertEqual(g.cam_y,point.y-620)
        snapshot=json.loads(json.dumps(capture(g)));restore(g,snapshot)
        self.assertEqual(json.loads(json.dumps(capture(g))),snapshot)
        g.state='play';g.draw(.5,present=False)
        data=capture(g);data['medallions']['claimed']=[9]
        with self.assertRaises(ValueError):validate(data)
        data=capture(g);data['level']=9
        with self.assertRaises(ValueError):validate(data)


if __name__=='__main__':unittest.main()
