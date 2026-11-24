import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
import pygame as pg
from main import Hero, Platform, Game, STEP, level, WORLD,EXIT_MARGIN,VIEW_W,PLATFORM_WIDTHS


class PhysicsTests(unittest.TestCase):
    def test_five_platform_sizes_are_distributed_across_the_level(self):
        platforms,_=level();ledges=[p for p in platforms if not p.ground]
        self.assertEqual(len(ledges),21)
        self.assertEqual({p.w for p in ledges},set(PLATFORM_WIDTHS))
        self.assertEqual(PLATFORM_WIDTHS[2],240)
        for width in PLATFORM_WIDTHS:
            self.assertGreaterEqual(sum(p.w==width for p in ledges),4)
            self.assertTrue(any(p.w==width and p.x<WORLD/2 for p in ledges))
            self.assertTrue(any(p.w==width and p.x>WORLD/2 for p in ledges))
        self.assertTrue(all(p.h==32 and 0<=p.x<p.x+p.w<=WORLD for p in ledges))

    def test_shards_remain_above_resized_platforms_and_do_not_overlap_stone(self):
        platforms,gems=level();ledges=[p for p in platforms if not p.ground]
        self.assertEqual(len(gems),52)
        for p in ledges:
            above=[(x,y) for x,y in gems if y==p.y-42 and p.x+15<x<p.x+p.w-15]
            self.assertEqual(len(above),2)
        for x,y in gems:
            self.assertFalse(any(p.rect.collidepoint(x,y) for p in platforms))

    def ground_hero(self):
        h=Hero(160,620);h.grounded=True
        return h

    def test_jump_height_and_landing(self):
        h=self.ground_hero();floor=[Platform(0,620,2000,100,True)]
        ys=[]
        for i in range(180):
            h.update(STEP,0,False,i==0,floor);ys.append(h.y)
        self.assertGreater(620-min(ys),190)
        self.assertLess(620-min(ys),210)
        self.assertEqual(h.y,620)
        self.assertTrue(h.grounded)

    def test_float_and_aerial_brake(self):
        h=Hero(100,200);h.vy=600
        h.update(STEP,1,True,True,[])
        self.assertLess(h.vy,105)
        for _ in range(120):h.update(STEP,1,True,False,[])
        self.assertLessEqual(h.vy,105)
        self.assertGreater(h.x,400)

    def test_jump_is_not_repeated_by_holding(self):
        h=self.ground_hero();floor=[Platform(0,620,2000,100,True)]
        for i in range(900):h.update(STEP,0,True,i==0,floor)
        self.assertEqual(h.y,620)
        self.assertTrue(h.grounded)

    def test_all_pits_can_be_crossed(self):
        platforms,_=level();floors=[p for p in platforms if p.ground]
        for a,b in zip(floors,floors[1:]):
            h=Hero(a.x+a.w-40,620);h.grounded=True;h.vx=340
            for i in range(150):h.update(STEP,1,True,i==0,[a,b])
            self.assertGreater(h.x,b.x)
            self.assertLessEqual(h.y,620)

    def test_solid_platform_blocks_jump_from_below(self):
        h=Hero(100,610);h.grounded=True
        platform=Platform(0,500,220,30)
        bumped=False
        for i in range(30):
            h.update(STEP,0,False,i==0,[platform]);bumped|=h.bump
            self.assertGreaterEqual(h.y-h.body_height,530)
        self.assertTrue(bumped);self.assertFalse(h.grounded)

    def test_buffered_jump(self):
        h=Hero(100,619);h.vy=100
        floor=[Platform(0,620,400,100,True)]
        h.update(STEP,0,False,True,floor)
        jumped=False
        for _ in range(12):
            h.update(STEP,0,False,False,floor)
            if h.vy<0:jumped=True;break
        self.assertTrue(jumped)

    def test_world_bounds(self):
        h=Hero(20,200)
        for _ in range(120):h.update(STEP,-1,False,False,[])
        self.assertEqual(h.x,16)
        h.x=WORLD-20
        for _ in range(120):h.update(STEP,1,False,False,[])
        self.assertGreater(h.x,WORLD+EXIT_MARGIN)


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):pg.quit()
    def setUp(self):self.g.reset();self.g.state='play'

    def test_collect_once(self):
        x,y=self.g.gems[0];self.g.hero=Hero(x,y+28)
        self.g.update(STEP,0,False,False)
        self.assertIn(0,self.g.taken)
        n=len(self.g.taken);self.g.update(STEP,0,False,False)
        self.assertEqual(n,len(self.g.taken))

    def test_checkpoint_respawn(self):
        self.g.hero=Hero(4800,620);self.g.update(STEP,0,False,False)
        self.assertEqual(self.g.check_index,1)
        self.g.hero.y=900;self.g.update(STEP,0,False,False)
        self.assertEqual(self.g.hero.x,4740)
        self.assertEqual(self.g.deaths,1)

    def test_enemy_respawn_and_grace(self):
        x,y=self.g.enemy_positions()[0]
        self.g.hero=Hero(x,y+27);self.g.update(STEP,0,False,False)
        self.assertEqual(self.g.deaths,1)
        self.assertGreater(self.g.invuln,0)

    def test_victory(self):
        self.g.hero=Hero(9250,620);self.g.update(STEP,0,False,False)
        self.assertEqual(self.g.state,'play')
        self.g.hero=Hero(WORLD-80,620);self.g.hero.grounded=True;self.g.hero.vx=340
        self.g.cam=self.g.prev_cam=WORLD-VIEW_W
        for _ in range(120):
            before=self.g.hero.x
            self.g.update(STEP,1,False,False)
            self.assertAlmostEqual(self.g.hero.x-before,340*STEP)
            self.assertEqual(self.g.hero.y,620)
            self.assertEqual(self.g.cam,WORLD-VIEW_W)
            if self.g.hero.x<WORLD+EXIT_MARGIN:self.assertEqual(self.g.state,'play')
            else:break
        self.assertEqual(self.g.state,'win')
        self.assertGreaterEqual(self.g.hero.x-self.g.cam,VIEW_W+EXIT_MARGIN)
        self.assertEqual(self.g.deaths,0)

    def test_render_states_and_mid_level(self):
        for state in ('title','play','pause','win'):
            self.g.state=state;self.g.draw(.5)
        for x in (3000,6000,8500):
            self.g.cam=self.g.prev_cam=x;self.g.draw(.5)

    def test_fullscreen_keeps_existing_renderer(self):
        self.g.fullscreen=False
        with patch('main.pg.display.toggle_fullscreen',return_value=1), patch.object(self.g,'create_display') as rebuild:
            self.g.toggle_fullscreen()
            self.assertTrue(self.g.fullscreen)
            self.g.toggle_fullscreen()
            self.assertFalse(self.g.fullscreen)
            rebuild.assert_not_called()
        self.g.draw(1)

    def test_renderer_failure_uses_software_display(self):
        original=pg.display.set_mode
        def fail_scaled(size,flags=0,**kwargs):
            if flags & pg.SCALED:raise pg.error('failed to create renderer')
            return original(size,flags,**kwargs)
        self.g.display_flags=pg.RESIZABLE|pg.SCALED
        with patch('main.pg.display.toggle_fullscreen',side_effect=pg.error('unsupported')), patch('main.pg.display.set_mode',side_effect=fail_scaled):
            self.g.toggle_fullscreen()
            self.assertTrue(self.g.fullscreen)
            self.assertFalse(self.g.display_flags & pg.SCALED)
            self.g.draw(1)
            self.g.toggle_fullscreen()
            self.assertFalse(self.g.fullscreen)
            self.g.draw(1)

    def test_unsupported_fullscreen_restores_window(self):
        original=pg.display.set_mode
        def fail_fullscreen(size,flags=0,**kwargs):
            if flags & pg.FULLSCREEN:raise pg.error('unsupported fullscreen mode')
            return original(size,flags,**kwargs)
        self.g.fullscreen=False
        with patch('main.pg.display.toggle_fullscreen',return_value=0), patch('main.pg.display.set_mode',side_effect=fail_fullscreen):
            self.g.toggle_fullscreen()
        self.assertFalse(self.g.fullscreen)
        self.g.draw(1)


if __name__=='__main__':unittest.main()
