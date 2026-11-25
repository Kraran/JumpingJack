import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
import pygame as pg
from main import Game,Hero,STEP
from terrain import DuneGround,sand_height,overlaps_rect
from hero_animation import HeroAnimator


class DunePhysicsTests(unittest.TestCase):
    def test_high_nonperiodic_profile_and_smooth_walk_in_both_directions(self):
        ground=DuneGround(4290,1760)
        self.assertGreaterEqual(620-sand_height(5480),250)
        for start,direction in ((4350,1),(5990,-1)):
            hero=Hero(start,sand_height(start));hero.grounded=True;hero.vx=direction*340
            animator=HeroAnimator()
            for _ in range(550):
                old_y=hero.y;hero.update(STEP,direction,False,False,[ground])
                animator.update(STEP,hero,True)
                self.assertTrue(hero.grounded)
                self.assertAlmostEqual(hero.y,sand_height(hero.x))
                self.assertLess(abs(hero.y-old_y),5)
                self.assertEqual(hero.vy,0);self.assertEqual(animator.state,'run')
                if hero.x>5990 or hero.x<4350:break
        self.assertNotAlmostEqual(sand_height(5000),sand_height(10000))

    def test_jump_and_glide_land_on_the_real_slope(self):
        ground=DuneGround(4290,1760)
        hero=Hero(4720,sand_height(4720));hero.grounded=True;hero.vx=340
        airborne=False
        for tick in range(300):
            hero.update(STEP,1,False,tick==0,[ground])
            airborne=airborne or not hero.grounded
            if tick>1 and hero.grounded:break
        self.assertTrue(airborne);self.assertTrue(hero.grounded)
        self.assertAlmostEqual(hero.y,sand_height(hero.x))
        hero=Hero(5480,200);hero.vy=500
        for _ in range(300):
            hero.update(STEP,0,True,False,[ground])
            if hero.grounded:break
        self.assertTrue(hero.grounded);self.assertTrue(hero.landed_gliding)
        self.assertAlmostEqual(hero.y,355);self.assertEqual(hero.recovery,0)

    def test_ray_hits_the_actual_crest_not_the_ground_bounding_box(self):
        ground=DuneGround(4290,1760)
        for start,direction in ((5000,1),(5800,-1)):
            distance=ground.ray_distance(start,520,direction,700)
            self.assertGreater(distance,0);self.assertLess(distance,300)
            self.assertAlmostEqual(sand_height(start+direction*distance),520,delta=.05)
        self.assertFalse(overlaps_rect(ground,pg.Rect(4990,450,30,50)))
        self.assertTrue(overlaps_rect(ground,pg.Rect(5470,340,30,80)))


class DuneAndCheatGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):
        g=self.g;g.new_game();g.enter_menu('title');g.quit_requested=False;g.time=0
        g.menu.selected['title']=0

    def type_code(self,text):
        for char in text:self.g.menu_key(pg.key.key_code(char.lower()),char)

    def test_lv02_starts_fresh_level_two_immediately_case_insensitively(self):
        g=self.g;g.lives=1;g.medallions.collect(1)
        self.type_code('Lv02')
        self.assertEqual((g.state,g.level_id,g.lives),('play',2,3))
        self.assertEqual(g.medallions.count,0)
        self.assertEqual(g.hero.y,sand_height(g.hero.x))
        self.assertFalse(g.pending_jump);self.assertFalse(g.pending_fire)
        g.lives=2;g.menu_key(pg.K_2,'2');self.assertEqual(g.lives,2)

    def test_wrong_code_settings_and_partial_code_do_not_start_a_game(self):
        g=self.g;self.type_code('LV01');self.assertEqual(g.state,'title')
        self.type_code('L');g.enter_menu('settings');self.type_code('LV02')
        self.assertEqual(g.state,'settings')
        g.enter_menu('title');self.type_code('V02');self.assertEqual(g.state,'title')
        self.type_code('LV');g.time=20;self.type_code('02');self.assertEqual(g.state,'title')

    def test_keypad_and_real_keydown_events_activate_the_code(self):
        g=self.g
        for key in (pg.K_l,pg.K_v,pg.K_KP0,pg.K_KP2):g.menu_key(key)
        self.assertEqual((g.state,g.level_id),('play',2))
        g.new_game();g.enter_menu('title')
        for key,text in ((pg.K_l,'l'),(pg.K_v,'v'),(pg.K_LSHIFT,''),(pg.K_0,'0'),(pg.K_2,'2')):
            g.menu_key(key,text)
        self.assertEqual((g.state,g.level_id),('play',2))
        g.new_game();g.enter_menu('title')
        events=[pg.event.Event(pg.KEYDOWN,key=pg.key.key_code(c.lower()),unicode=c) for c in 'LV02']
        with patch('main.pg.event.get',return_value=events),patch.object(g,'close'),patch.object(g.pacer,'wait'):
            g.run(frames=1)
        self.assertEqual((g.state,g.level_id,g.lives),('play',2,3))

    def test_dune_render_surface_matches_collision_heights_at_chunk_edges(self):
        g=self.g;g.start_level(2);g.state='play'
        for start,top,image in g.desert_art.dunes:
            for col in (0,image.get_width()//2,image.get_width()-1):
                expected=round(sand_height((start+col)/1.5)*1.5)
                row=next(y for y in range(image.get_height()) if image.get_at((col,y)).a>128)
                self.assertLessEqual(abs(top+row-expected),1)
        before=(g.elapsed,g.hero.x,g.hero.y)
        for x in (0,4400,5300,9000,11200,13000):
            g.cam=g.prev_cam=x;g.draw(1,present=False)
        self.assertEqual(before,(g.elapsed,g.hero.x,g.hero.y))

    def test_both_banks_slope_to_the_water_and_submerged_sand_fades_out(self):
        g=self.g
        self.assertEqual(sand_height(700),640);self.assertEqual(sand_height(3140),640)
        self.assertLess(sand_height(650),sand_height(680))
        self.assertGreater(sand_height(3160),sand_height(3220))
        def alpha_at(x,y):
            px=round(x*1.5);py=round(y*1.5)
            for start,top,image in g.desert_art.dunes:
                if start<=px<start+image.get_width():return image.get_at((px-start,py-top)).a
        self.assertEqual(alpha_at(520,700),255)
        self.assertGreater(alpha_at(610,700),alpha_at(680,700))
        self.assertLess(alpha_at(699,700),5)
        self.assertLess(alpha_at(3141,700),5)
        self.assertEqual(alpha_at(680,638),255)

    def test_shore_sand_is_safe_but_actual_water_still_kills(self):
        g=self.g
        for x in (695,3145):
            g.new_game();g.start_level(2);g.state='play';g.invuln=100
            g.hero=Hero(x,sand_height(x));g.hero.grounded=True
            g.update(STEP,0,False,False)
            self.assertEqual(g.lives,3);self.assertTrue(g.hero.grounded)
            g.hero=Hero(740,645);g.update(STEP,0,True,False)
            self.assertEqual(g.lives,2)


if __name__=='__main__':unittest.main()
