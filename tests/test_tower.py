import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import json
import unittest
from unittest.mock import patch
from main import Game,Hero,STEP,VIEW_W,VIEW_H
from savegame import capture,restore,validate
from tools.verify_tower import verify
from tower_art import VerticalNative
from localization import CODES,TOWER_ROWS,translate
import tower_level as tower


class TowerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        self.g.new_game();self.g.start_level(4);self.g.state='play';self.g.invuln=100

    def test_full_height_fixed_width_and_entire_route_reachable_without_glide(self):
        g=self.g;self.assertEqual((g.world_length,g.world_height),(VIEW_W,14400))
        self.assertEqual(len(g.gems),len(tower.GEM_SITES));self.assertEqual(len(g.obelisks),2)
        report=verify();self.assertEqual(report['platforms_reached'],len(tower.LEDGES)+1)
        self.assertFalse(report['glide_used']);self.assertFalse(report['teleports_used'])

    def test_deep_world_does_not_instantly_kill_and_side_walls_are_solid(self):
        g=self.g
        for _ in range(30):g.update(STEP,0,False,False)
        self.assertEqual(g.lives,3);self.assertGreater(g.hero.y,14000)
        for start,direction,expected in ((100,-1,79),(1180,1,1201)):
            hero=Hero(start,tower.BASE_Y);hero.grounded=True
            for _ in range(90):hero.update(STEP,direction,False,False,g.platforms)
            self.assertEqual(hero.x,expected)

    def test_vertical_camera_is_interpolated_and_never_moves_horizontally(self):
        g=self.g;g.hero=Hero(640,9500);g.cam_y=g.prev_cam_y=9400
        before=g.cam_y;g.update(STEP,1,False,False)
        self.assertEqual((g.cam,g.prev_cam),(0,0));self.assertEqual(g.prev_cam_y,before)
        self.assertLess(abs(g.cam_y-before),20)
        data=json.loads(json.dumps(capture(g)))
        for alpha in (0,.25,.5,.75,1):
            with patch.object(g.tower_art,'background',wraps=g.tower_art.background) as background:
                g.draw(alpha,present=False)
                self.assertAlmostEqual(background.call_args.args[1],g.prev_cam_y+(g.cam_y-g.prev_cam_y)*alpha)
        self.assertEqual(json.loads(json.dumps(capture(g))),data)

    def test_vertical_canvas_uses_one_identical_pixel_shift_for_every_world_draw(self):
        class Recorder:
            def blit(self,image,dest,area=None):self.dest=dest
        import pygame as pg
        native=Recorder();canvas=VerticalNative(native,100.2)
        canvas.blit(None,(120,300));self.assertEqual(native.dest,(120,150))
        canvas.blit(None,pg.Rect(120,300,20,10));self.assertEqual(native.dest,pg.Rect(120,150,20,10))

    def test_camera_simulation_is_independent_of_monitor_refresh(self):
        results=[];g=self.g
        for rate in (60,75,120,144,165,240,360):
            g.start_level(4);g.state='play';g.invuln=100;acc=0.;tick=0
            for frame in range(rate*2):
                acc+=1/rate
                while acc>=STEP-1e-10:
                    g.update(STEP,0,False,tick in (10,140));tick+=1;acc-=STEP
            self.assertEqual(tick,240)
            results.append((g.hero.y,g.cam_y))
        for position in results:self.assertEqual(position,results[0])

    def test_both_obelisks_and_death_restore_vertical_camera(self):
        from support import finish_respawn
        g=self.g
        for index,(x,y) in enumerate(tower.CHECKPOINTS,1):
            g.hero=Hero(x,y);g.hero.grounded=True;g.update(STEP,0,False,False)
            self.assertEqual(g.check_index,index);self.assertEqual(g.checkpoint,(x-60,y))
        g.hero.y=tower.HEIGHT+200;g.update(STEP,0,False,False)
        finish_respawn(g)
        self.assertEqual(g.lives,2);self.assertEqual(g.hero.y,tower.CHECKPOINTS[-1][1])
        self.assertEqual(g.cam_y,g.prev_cam_y);self.assertEqual(g.cam_y,tower.camera_target(g.hero.y))

    def test_high_medallion_is_reachable_with_real_jump(self):
        g=self.g;x,y,w=tower.LEDGES[90];g.hero=Hero(x+w/2,y);g.hero.grounded=True
        for tick in range(140):
            g.update(STEP,0,False,tick==0)
            if 4 in g.medallions.claimed_levels:break
        self.assertIn(4,g.medallions.claimed_levels);self.assertEqual(g.medallions.count,1)

    def test_save_roundtrip_preserves_altitude_camera_checkpoint_and_dead_enemy(self):
        g=self.g;g.hero=Hero(*tower.CHECKPOINTS[0]);g.hero.grounded=True
        g.update(STEP,0,False,False);g.dead_beetles.add(0)
        g.cam_y=g.prev_cam_y=tower.camera_target(g.hero.y)
        data=json.loads(json.dumps(capture(g)));restore(g,data)
        self.assertEqual(json.loads(json.dumps(capture(g))),data);g.draw(.5,present=False)
        bad=capture(g);bad['camera_y']=tower.HEIGHT
        with self.assertRaises(ValueError):validate(bad)
        bad=capture(g);bad['camera']=1
        with self.assertRaises(ValueError):validate(bad)

    def test_old_horizontal_saves_default_to_zero_vertical_camera(self):
        g=self.g;g.start_level(3);data=capture(g);del data['camera_y'];restore(g,data)
        self.assertEqual(g.cam_y,0);self.assertEqual(g.level_id,3)

    def test_sparse_crystals_and_irregular_platform_spacing_are_reproducible(self):
        from collections import Counter
        self.assertEqual(tower.make_layout(),(tower.LEDGES,tower.BRANCHES))
        self.assertEqual(tower.collectible_sites(),tower.GEM_SITES)
        counts=Counter((kind,row) for kind,row,slot,x,y in tower.GEM_SITES)
        groups=([('route',i) for i in range(len(tower.LEDGES))]+
                [('branch',i) for i in range(len(tower.BRANCHES))]+[('base',0),('summit',0)])
        self.assertEqual({counts[key] for key in groups},{0,1,2})
        self.assertLess(len(self.g.gems),110)
        heights=[tower.BASE_Y]+[y for x,y,w in tower.LEDGES]
        gaps=[a-b for a,b in zip(heights,heights[1:])]
        self.assertGreater(max(gaps)-min(gaps),50)
        centers=[tower.START[0]]+[x+w/2 for x,y,w in tower.LEDGES]
        self.assertGreater(sum(abs(a-b)>=275 for a,b in zip(centers,centers[1:])),len(gaps)//2)

    def test_tower_hazards_props_and_destroyed_actors_survive_save(self):
        g=self.g
        self.assertEqual((len(g.scorpions),len(g.vases),len(tower.TORCHES)),(3,9,7))
        self.assertEqual(sum(p.spiked for p in g.platforms),15)
        for x,y,w,row in tower.BRANCHES:self.assertEqual(y,tower.LEDGES[row][1])
        g.scorpions[0].ignite();g.vases[0].shatter()
        data=json.loads(json.dumps(capture(g)));restore(g,data)
        self.assertEqual(json.loads(json.dumps(capture(g))),data)
        self.assertFalse(g.scorpions[0].alive);self.assertTrue(g.vases[0].broken)

    def test_previous_tower_save_migrates_onto_a_support_without_reviving_enemies(self):
        g=self.g;g.hero=Hero(640,8000);g.lives=2;g.dead_beetles.add(0)
        old=capture(g);del old['tower_layout'];old['scorpions']=[];old['vases']=[];old['taken']=[0,1,200]
        restore(g,old)
        self.assertEqual((g.level_id,g.lives),(4,2));self.assertIn(0,g.dead_beetles)
        self.assertTrue(g.hero.grounded);self.assertGreaterEqual(g.hero.y,8000)
        self.assertTrue(any(abs(g.hero.y-p.y)<1 and p.x<=g.hero.x<=p.x+p.w for p in g.platforms))
        self.assertEqual(capture(g)['tower_layout'],tower.LAYOUT_VERSION)

    def test_campaign_cheat_and_summit_completion(self):
        g=self.g;g.start_level(3);g.state='win';g.lives=2;g.medallions.collect(3)
        g.continue_or_restart();self.assertEqual((g.level_id,g.lives,g.medallions.count),(4,2,1))
        g.new_game();g.enter_menu('title')
        import pygame as pg
        for key in (pg.K_l,pg.K_v,pg.K_0,pg.K_4):g.menu_key(key)
        self.assertEqual((g.level_id,g.state),(4,'play'))
        g.hero=Hero(*tower.SUMMIT);g.hero.grounded=True;g.invuln=100;g.update(STEP,0,False,False)
        self.assertEqual(g.state,'win');g.draw(1,present=False)
        g.continue_or_restart();self.assertEqual(g.level_id,5)

    def test_tower_ui_is_translated_in_all_supported_languages(self):
        self.assertEqual(set(TOWER_ROWS),set(CODES))
        for language in CODES:
            for source in ('NIVEAU 04  /  LA TOUR','LE SOMMET EST ATTEINT','L’ASCENSION EST TERMINÉE','ASCENSION : 50 %'):
                result=translate(source,language);self.assertTrue(result)
                if language!='fr':self.assertNotEqual(result,source,(language,source))
