import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import tempfile
import unittest
from pathlib import Path
import pygame as pg
from main import Game,Hero,STEP,level,EXIT_MARGIN
from gamepad import PadSnapshot
from savegame import SaveSlots,capture,restore
import temple_level as temple
import desert_level as desert


class TempleLevelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        self.g.new_game();self.g.start_level(3);self.g.state='play';self.g.invuln=100
        self.g.pad=PadSnapshot()

    def test_geometry_length_enemy_roster_and_collectibles(self):
        g=self.g
        self.assertEqual(g.world_length,desert.LENGTH)
        self.assertEqual(len(g.gems),79);self.assertEqual(len(g.beetle_motions),12)
        self.assertEqual(g.crocodiles,[]);self.assertEqual(g.vultures,[])
        self.assertEqual([o.x for o in g.obelisks],[4800,9600])
        self.assertEqual(sum(p.spiked for p in g.platforms),3)
        self.assertEqual(sum(not p.ground for p in g.platforms),34)

    def test_desert_win_continues_to_temple_with_lives_and_medallions(self):
        g=self.g;g.start_level(2);g.lives=2;g.medallions.collect(1);g.medallions.collect(2)
        g.state='win';g.continue_or_restart()
        self.assertEqual((g.level_id,g.lives,g.medallions.count,g.state),(3,2,2,'play'))
        self.assertTrue(g.menu_gameplay_blocked)

    def test_pits_are_fatal_and_dead_enemies_do_not_respawn(self):
        g=self.g;g.dead_beetles.add(4);g.hero=Hero(1800,900)
        g.update(STEP,0,False,False)
        self.assertEqual(g.lives,2);self.assertIn(4,g.dead_beetles)
        self.assertEqual(g.level_id,3)

    def test_solid_ceiling_stops_a_jump_and_cancels_gliding(self):
        g=self.g;g.hero=Hero(2480,310);g.hero.grounded=True
        bumped=False
        for tick in range(120):
            g.hero.update(STEP,0,True,tick==0,g.platforms)
            if g.hero.head_bump:
                bumped=True;self.assertFalse(g.hero.floating);self.assertTrue(g.hero.glide_locked)
                self.assertGreaterEqual(g.hero.y-g.hero.body_height,120)
                break
        self.assertTrue(bumped)

    def test_two_checkpoints_update_respawn_and_survive_death(self):
        g=self.g
        for index,x in enumerate(temple.CHECKPOINTS,1):
            g.hero=Hero(x,620);g.hero.grounded=True;g.update(STEP,0,False,False)
            self.assertEqual(g.check_index,index);self.assertEqual(g.checkpoint,(x-60,620))
        g.hero.y=900;g.update(STEP,0,False,False)
        self.assertEqual((g.hero.x,g.hero.y),(9540,620))
        self.assertTrue(all(o.active for o in g.obelisks))

    def test_high_medallion_completes_three_fragments_and_awards_one_life(self):
        g=self.g;g.medallions.collect(1);g.medallions.collect(2)
        g.hero=Hero(12960,455);g.hero.grounded=True
        for tick in range(120):
            g.update(STEP,0,False,tick==0)
            if 3 in g.medallions.claimed_levels:break
        self.assertEqual(g.lives,4);self.assertEqual(g.medallions.count,0)
        self.assertEqual(g.medallions.claimed_levels,{1,2,3})

    def test_save_and_load_temple_preserves_progress_and_claimed_third_medallion(self):
        g=self.g;g.hero=Hero(9600,620);g.hero.grounded=True;g.dead_beetles={0,5}
        g.medallions.count=0;g.medallions.claimed_levels={1,2,3};g.taken={3,17,78};g.lives=4
        data=capture(g)
        with tempfile.TemporaryDirectory() as directory:
            slots=SaveSlots(Path(directory));slots.write(0,data);g.new_game()
            slot=slots.read(0);self.assertEqual(slot.status,'ready');restore(g,slot.data)
        self.assertEqual(json.loads(json.dumps(capture(g))),json.loads(json.dumps(data)))
        g.enter_menu('load');g.draw(1,present=False)

    def test_lv03_cheat_and_final_sanctuary_replay(self):
        g=self.g;g.new_game();g.enter_menu('title')
        for key in (pg.K_l,pg.K_v,pg.K_0,pg.K_3):g.menu_key(key)
        self.assertEqual((g.level_id,g.state),(3,'play'))
        g.hero=Hero(temple.LENGTH+EXIT_MARGIN-1,620);g.hero.grounded=True;g.hero.vx=340
        g.update(STEP,1,False,False);self.assertTrue(g.temple_exit.active)
        for _ in range(600):
            if g.state=='win':break
            g.update(STEP,1,False,False)
        self.assertEqual(g.state,'win')
        g.draw(1,present=False);g.continue_or_restart()
        self.assertEqual((g.level_id,g.lives,g.state),(4,3,'play'))
