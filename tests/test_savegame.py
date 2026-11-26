import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import json
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
import pygame as pg
from main import Game,Hero,STEP
from savegame import SaveSlots,capture,restore,validate
from gamepad import PadSnapshot


def canonical(value):return json.loads(json.dumps(value))


class SaveGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.game=Game(True)
    @classmethod
    def tearDownClass(cls):cls.game.close()

    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.directory=Path(self.temporary.name)/'saves'
        self.g=self.game;self.g.new_game();self.g.saves=SaveSlots(self.directory)
        self.g.state='play';self.g.menu.message='';self.g.menu.selected.update(save=0,load=0)

    def test_five_persistent_slots_have_independent_dates_and_progress(self):
        for index in range(5):
            self.g.hero.x=300+index*70
            self.g.saves.write(index,capture(self.g))
        reopened=SaveSlots(self.directory)
        self.assertEqual(len(reopened.list()),5)
        for index,slot in enumerate(reopened.list()):
            self.assertEqual(slot.status,'ready')
            self.assertEqual(slot.data['hero']['x'],300+index*70)
            self.assertIsNotNone(datetime.fromisoformat(slot.timestamp).tzinfo)
        self.assertEqual(len(list(self.directory.glob('*.json'))),5)
        for index in (-1,5,True):
            with self.assertRaises(ValueError):reopened.read(index)

    def test_round_trip_preserves_both_levels_inventory_checkpoint_and_dead_enemies(self):
        for level in (1,2):
            with self.subTest(level=level):
                g=self.g;g.start_level(level);g.lives=2;g.deaths=1;g.elapsed=123.45;g.cam=440
                g.hero=Hero(900,300);g.hero.vy=160;g.hero.glide_locked=True
                g.energy.value=37;g.taken={0,2,5};g.medallions.count=1;g.medallions.claimed_levels={1}
                g.dead_beetles={0};g.crocodiles[0].ignite();g.vultures[0].ignite()
                g.obelisks[-1].active=True;g.obelisks[-1].clock=8
                g.check_index=len(g.obelisks);g.checkpoint=(g.obelisks[-1].x-60,g.obelisks[-1].y)
                g.hero_animation.update(STEP,g.hero,False,g.solar,g.rest)
                expected=canonical(capture(g));g.saves.write(2,expected)
                g.new_game();restore(g,g.saves.read(2).data)
                self.assertEqual(canonical(capture(g)),expected)
                g.resume_from_menu();g.draw(1,present=False)
                g.update(STEP,0,False,False)
                self.assertIn(0,g.dead_beetles);self.assertFalse(g.crocodiles[0].alive)
                self.assertFalse(g.vultures[0].alive)

    def test_platform_drop_references_are_rebound_to_loaded_geometry(self):
        g=self.g;support=next(p for p in g.platforms if not p.ground)
        g.hero=Hero(support.x+support.w/2,support.y);g.hero.grounded=True
        g.hero.update(STEP,0,True,True,g.platforms,drop=True)
        data=canonical(capture(g));restore(g,data)
        self.assertIsNot(g.hero.drop_support,support)
        self.assertTrue(any(g.hero.drop_support is p for p in g.platforms))
        for _ in range(60):g.hero.update(STEP,0,False,False,g.platforms)
        self.assertGreater(g.hero.y,support.y)

    def test_active_solar_seated_pose_and_enemy_dive_resume_without_animation_crashes(self):
        g=self.g;g.solar.update(STEP,g.hero,True,g.energy)
        g.hero_animation.update(STEP,g.hero,True,g.solar,g.rest)
        g.vultures[0].state='dive';g.vultures[0].target=(300,500)
        restore(g,canonical(capture(g)));g.draw(1,present=False)
        self.assertTrue(g.solar.active);self.assertEqual(g.energy.value,30)
        self.assertIs(g.hero_animation.solar,g.solar)
        g.solar.reset();g.rest.state='seated';g.rest.progress=1;g.rest.previous_progress=1
        g.hero_animation.update(STEP,g.hero,True,g.solar,g.rest)
        restore(g,canonical(capture(g)));g.draw(1,present=False)
        self.assertEqual(g.rest.state,'seated');self.assertIs(g.hero_animation.rest,g.rest)

    def test_legacy_platform_indices_survive_removal_of_the_final_rock_and_ledge(self):
        from main import Platform
        import desert_level as desert
        g=self.g;g.start_level(2)
        legacy=desert.build(Platform,rocks=desert.ROCKS+(desert.REMOVED_ROCK,),
                            ledges=desert.LEDGES+(desert.REMOVED_LEDGE,))[0]
        for x in (13220,14100):
            support=next(p for p in legacy if p.x==x and not p.ground)
            g.hero=Hero(support.x+support.w/2,support.y);g.hero.grounded=True;g.hero.drop_elapsed=.04
            data=canonical(capture(g));data['platform_refs']['drop_support']=legacy.index(support)
            data['taken']=[0,56,57,72]
            validate(data);restore(g,data)
            self.assertEqual(g.taken,{0,56,57,72});self.assertEqual(len(g.gems),73)
            if x==13220:
                self.assertIsNotNone(g.hero.drop_support);self.assertEqual(g.hero.drop_support.x,x)
            else:
                self.assertIsNone(g.hero.drop_support);self.assertIsNone(g.hero.drop_elapsed)
                self.assertFalse(g.hero.grounded)
                g.update(STEP,0,False,False);g.draw(1,present=False)

    def test_atomic_replace_failure_keeps_previous_save_and_cleans_temporary_file(self):
        g=self.g;g.saves.write(0,capture(g));path=g.saves.path(0);previous=path.read_bytes()
        g.lives=1
        with patch('savegame.Path.replace',side_effect=OSError('disk unavailable')):
            with self.assertRaises(OSError):g.saves.write(0,capture(g))
        self.assertEqual(path.read_bytes(),previous)
        self.assertFalse(list(self.directory.glob('*.tmp')))
        self.assertEqual(g.saves.read(0).data['lives'],3)

    def test_corrupt_incompatible_and_empty_files_do_not_change_the_current_run(self):
        g=self.g;g.saves.write(0,capture(g));document=json.loads(g.saves.path(0).read_text(encoding='utf-8'))
        invalids=['broken','[]','null',json.dumps({**document,'version':99})]
        for mutate in (lambda d:d['game'].update(lives=0),lambda d:d['game']['hero'].update(x=float('nan')),
                       lambda d:d['game']['animation'].update(state='unknown'),
                       lambda d:d['game']['vultures'][0].update(state='dive',target=None),
                       lambda d:d['game']['platform_refs'].update(ignored_platform=9999)):
            bad=copy.deepcopy(document);mutate(bad);invalids.append(json.dumps(bad))
        before=canonical(capture(g))
        for content in invalids:
            g.saves.path(0).write_text(content,encoding='utf-8');g.state='load';g.load_slot(0)
            self.assertEqual(g.state,'load');self.assertEqual(canonical(capture(g)),before)
            self.assertTrue(g.menu.message)
        self.assertEqual(g.saves.read(4).status,'empty')
        g.load_slot(4);self.assertEqual(g.state,'load')

    def test_pause_save_overwrite_cancel_and_load_from_title_with_controller(self):
        g=self.g;g.elapsed=87;g.enter_menu('pause');g.menu.selected['pause']=2
        g.handle_pad(PadSnapshot(confirm_pressed=True));self.assertEqual(g.state,'save')
        g.handle_pad(PadSnapshot(confirm_pressed=True));self.assertEqual(g.state,'save')
        self.assertEqual(g.saves.read(0).status,'ready');previous=g.saves.path(0).read_bytes()
        g.lives=1;g.menu_action('activate');self.assertEqual(g.state,'overwrite')
        self.assertEqual(g.menu.selected['overwrite'],1)
        g.menu_action('activate');self.assertEqual(g.state,'save')
        self.assertEqual(g.saves.path(0).read_bytes(),previous)
        g.menu_action('activate');g.menu.selected['overwrite']=0;g.menu_action('activate')
        self.assertEqual(g.saves.read(0).data['lives'],1)
        g.menu_action('back');self.assertEqual(g.state,'pause')
        g.enter_menu('title');g.menu.selected['title']=2;g.menu_action('activate')
        self.assertEqual(g.state,'load')
        header,detail,date=g.menu.slot_text(0)
        self.assertIn('Niveau 01',header);self.assertIn('01:27',detail);self.assertTrue(date)
        g.handle_pad(PadSnapshot(confirm_pressed=True,jump_pressed=True,jump_held=True))
        self.assertEqual(g.state,'play');self.assertTrue(g.menu_gameplay_blocked)
        self.assertFalse(g.pending_jump);self.assertEqual(g.lives,1)

    def test_failed_save_shows_error_and_keeps_run_paused(self):
        g=self.g;g.enter_menu('save')
        with patch.object(g.saves,'write',side_effect=OSError('disk full')):g.menu_action('activate')
        self.assertEqual(g.state,'save');self.assertIn('Échec',g.menu.message)
        self.assertEqual(g.saves.read(0).status,'empty')

    def test_slot_screens_freeze_the_simulation_and_support_mouse_and_back(self):
        g=self.g;g.enter_menu('pause');g.menu.selected['pause']=2;g.menu_action('activate')
        self.assertTrue(g.menu.pointer('save',g.menu.rectangles('save')[4].center))
        self.assertEqual(g.menu.selected['save'],4)
        before=canonical(capture(g))
        for page in ('save','load','overwrite'):
            g.enter_menu(page);g.draw(1,present=False)
            self.assertEqual(canonical(capture(g)),before)
            g.menu_key(pg.K_ESCAPE)
            self.assertEqual(g.state,{'save':'pause','load':'title','overwrite':'save'}[page])
