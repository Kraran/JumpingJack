import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import copy
import math
import unittest
from unittest.mock import patch
import pygame as pg
from gyrosphere import Gyrosphere,SPEED,RADIUS,DEATH_TIME
from main import Game,Hero,Platform,STEP
from savegame import capture,restore,validate
from support import finish_respawn
import tower_level as tower


class GyrosphereMotionTests(unittest.TestCase):
    def test_horizontal_screen_and_navigation_use_the_world_camera_offset(self):
        orb=Gyrosphere(0,((10800.,300.),));hero=Hero(10500,327)
        self.assertFalse(orb.sees(hero,0));self.assertTrue(orb.sees(hero,0,10000))
        for _ in range(240):orb.update(STEP,hero,(),0,10000)
        self.assertEqual(orb.state,'chase');self.assertLess(orb.x,10700)
        obstacle=Platform(10450,380,420,32);hero=Hero(10400,500)
        route=orb.plan(hero,(obstacle,),0,10000)
        self.assertTrue(route);self.assertTrue(all(x>9900 for x,y in route))
        orb.update(STEP,hero,(),0,12000);self.assertEqual(orb.state,'idle')
        from main import level
        from terrain import sand_height
        import desert_level
        orb=Gyrosphere(0,desert_level.GYROSPHERES);hero=Hero(10590,sand_height(10590))
        platforms,_=level(2)
        for _ in range(1200):orb.update(STEP,hero,platforms,0,10078)
        self.assertLess(math.dist((orb.x,orb.y),(hero.x,hero.y-27)),40)

    def test_acquisition_and_loss_follow_the_actual_screen(self):
        orb=Gyrosphere(0,((300.,300.),));hero=Hero(600,327)
        for _ in range(240):orb.update(STEP,hero,(),0)
        self.assertEqual(orb.state,'chase');self.assertGreater(orb.x,350)
        self.assertLessEqual(math.hypot(orb.vx,orb.vy),SPEED+1e-6);self.assertGreater(orb.phase,0)
        x=orb.x
        for _ in range(240):orb.update(STEP,hero,(),800)
        self.assertEqual(orb.state,'idle');self.assertLess(orb.x-x,SPEED/4+.5)
        self.assertLess(math.hypot(orb.vx,orb.vy),SPEED*.001)
        self.assertEqual(orb.route,[])

    def test_rotation_reverses_with_motion_and_navigation_avoids_platforms(self):
        orb=Gyrosphere(0,((640.,600.),));hero=Hero(640,300)
        platform=Platform(420,450,440,32)
        for _ in range(2400):
            orb.update(1/60,hero,(platform,),0)
            self.assertFalse(platform.rect.inflate(round(RADIUS*2)-2,round(RADIUS*2)-2).collidepoint((orb.x,orb.y)))
        self.assertLess(orb.y,400)
        hero=Hero(100,orb.y+27)
        phase=orb.phase
        for _ in range(180):orb.update(1/60,hero,(),0)
        self.assertLess(orb.phase,phase)

    def test_swept_contact_and_three_clear_tower_spawns(self):
        orb=Gyrosphere(0,((150.,273.),));hero=Hero(300,300)
        orb.x=450;self.assertTrue(orb.hits(hero));orb.destroy();self.assertFalse(orb.hits(hero))
        from main import level
        platforms,_=level(4)
        self.assertEqual(len(tower.GYROSPHERES),6)
        for position in tower.GYROSPHERES:
            self.assertFalse(any(p.rect.inflate(32,32).collidepoint(position) for p in platforms))
        self.assertGreater(tower.GYROSPHERES[0][1]-tower.GYROSPHERES[1][1],3500)
        import desert_level,temple_level
        self.assertAlmostEqual(desert_level.GYROSPHERES[0][0]/desert_level.LENGTH,.75)
        for stage,config,count in ((2,desert_level,1),(3,temple_level,2),(4,tower,6)):
            platforms,_=level(stage);self.assertEqual(len(config.GYROSPHERES),count)
            for position in config.GYROSPHERES:
                self.assertFalse(any(p.rect.inflate(32,32).collidepoint(position) for p in platforms))


class GyrosphereGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def stage(self,lives=3):
        g=self.g;g.new_game();g.start_level(4);g.state='play';g.lives=lives;g.invuln=0
        g.hero=Hero(350,tower.BASE_Y);g.hero.grounded=True
        enemy=g.gyrospheres[0];enemy.x=enemy.px=350.;enemy.y=enemy.py=tower.BASE_Y-27.
        return enemy

    def test_contact_uses_classic_electrocution_and_last_life_waits(self):
        g=self.g
        for lives in (3,1):
            enemy=self.stage(lives)
            with patch.object(g.gamepads,'rumble') as rumble:
                g.update(STEP,0,False,False)
                self.assertTrue(g.hero_death.electrical);self.assertEqual(g.hero_death.kind,'gyrosphere')
                self.assertEqual(g.hero_death.duration,1.2);self.assertEqual(g.lives,lives-1)
                rumble.assert_called_once_with('death',duration=1200)
                with patch.object(g.beetle_death_sprites,'draw',wraps=g.beetle_death_sprites.draw) as draw:
                    g.draw(1,present=False);draw.assert_called_once()
                finish_respawn(g)
                self.assertEqual(g.state,'play' if lives>1 else 'game_over');self.assertEqual(g.deaths,1)
                self.assertTrue(enemy.alive)

    def test_solar_kill_scores_once_and_survives_respawn_and_save(self):
        g=self.g;enemy=self.stage();g.invuln=100
        g.solar.elapsed=.2;g.solar.powered=True
        with patch.object(g.solar,'bounds',return_value=enemy.rect.copy()):
            g.solar_hits();self.assertFalse(enemy.alive)
            score=g.score;g.solar_hits();self.assertEqual(g.score,score);self.assertGreaterEqual(score,200)
        g.solar.reset();g.kill_hero();finish_respawn(g)
        self.assertFalse(enemy.alive);self.assertEqual(enemy.death_timer,DEATH_TIME)
        data=capture(g);restore(g,data);self.assertFalse(g.gyrospheres[0].alive)
        g.restart_level();self.assertTrue(all(e.alive for e in g.gyrospheres))

    def test_pause_roundtrip_legacy_slots_and_source_validation(self):
        g=self.g;self.stage();g.update(STEP,0,False,False)
        for _ in range(30):g.update(STEP,0,False,False)
        g.enter_menu('pause');data=copy.deepcopy(capture(g))
        for _ in range(10):g.update(STEP,1,True,True)
        self.assertEqual(capture(g),data);restore(g,data);self.assertEqual(capture(g),data)
        bad=copy.deepcopy(data);bad['gyrospheres'][0]['alive']=False
        with self.assertRaises(ValueError):validate(bad)
        g.resume_from_menu();finish_respawn(g)
        old=capture(g);del old['gyrospheres'];restore(g,old)
        self.assertEqual(len(g.gyrospheres),6)
        for stage in (1,2,3):
            g.start_level(stage);self.assertEqual(len(g.gyrospheres),{1:0,2:1,3:2}[stage])

    def test_rendering_uses_only_the_preloaded_atlas_and_is_read_only(self):
        g=self.g;self.stage();enemy=g.gyrospheres[0]
        with patch.object(pg.image,'load',side_effect=AssertionError('runtime load')),\
             patch.object(pg.transform,'smoothscale',side_effect=AssertionError('runtime scale')):
            for i in range(120):
                enemy.phase=enemy.previous_phase=i/120
                before=copy.deepcopy(capture(g));g.draw(.5,present=False)
                self.assertEqual(capture(g),before)

    def test_previous_enemy_counts_upgrade_without_reviving_destroyed_robots(self):
        g=self.g
        for stage,old_count,new_count in ((2,0,1),(3,0,2),(4,3,6)):
            g.new_game();g.start_level(stage);g.state='play';g.dead_beetles.add(0);g.award_points(1400)
            if old_count:g.gyrospheres[0].destroy()
            old=copy.deepcopy(capture(g));old['gyrospheres']=old['gyrospheres'][:old_count]
            saved=copy.deepcopy(old['gyrospheres']);restore(g,old)
            self.assertEqual(len(g.gyrospheres),new_count);self.assertEqual(g.score,1400)
            self.assertIn(0,g.dead_beetles)
            self.assertEqual(capture(g)['gyrospheres'][:old_count],saved)
            self.assertTrue(all(orb.alive for orb in g.gyrospheres[old_count:]))
        bad=capture(g);bad['gyrospheres']=bad['gyrospheres'][:2]
        with self.assertRaises(ValueError):validate(bad)

    def test_contact_and_solar_score_in_horizontal_levels(self):
        from terrain import sand_height
        g=self.g
        for stage,x in ((2,10000.),(3,3000.)):
            g.new_game();g.start_level(stage);g.state='play';g.invuln=0
            y=sand_height(x) if stage==2 else 620
            g.hero=Hero(x,y);g.hero.grounded=True;g.cam=g.prev_cam=x-512
            orb=g.gyrospheres[0];orb.x=orb.px=x;orb.y=orb.py=y-27
            g.update(STEP,0,False,False)
            self.assertEqual(g.hero_death.kind,'gyrosphere');g.draw(1,present=False)
            finish_respawn(g);self.assertEqual((g.lives,g.deaths),(2,1))
            orb=g.gyrospheres[0];g.solar.elapsed=.2;g.solar.powered=True
            before=g.score
            with patch.object(g.solar,'bounds',return_value=orb.rect.copy()):
                g.solar_hits();self.assertEqual(g.score,before+200)
                g.solar_hits();self.assertEqual(g.score,before+200)
