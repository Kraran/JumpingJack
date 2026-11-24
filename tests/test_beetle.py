import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import MagicMock,patch
import pygame as pg
from main import Game,Hero,Platform,STEP,ROOT
from beetle import BeetleMotion,BeetleSprites,BeetleDeath,TILTS,DEATH_TIME,position,SPAWNS,LOSE_RANGE


class BeetleMotionTests(unittest.TestCase):
    def test_only_visible_hero_in_front_triggers_chase(self):
        for dx,dy,expected in ((200,0,True),(-200,0,False),(600,0,False),(50,200,False)):
            motion=BeetleMotion(0);hero=Hero(motion.x+dx,motion.y+28+dy)
            motion.update(STEP,STEP,hero)
            self.assertEqual(motion.state=='chase',expected)
        motion=BeetleMotion(0);motion.facing=-1
        motion.update(STEP,STEP,Hero(motion.x-200,motion.y+28))
        self.assertEqual(motion.state,'chase')

    def test_stone_and_turning_block_initial_sight(self):
        motion=BeetleMotion(0);hero=Hero(motion.x+200,motion.y+28)
        wall=Platform(motion.x+90,motion.y-40,30,80)
        self.assertFalse(motion.sees(hero,[wall]))
        motion.turning=True;self.assertFalse(motion.sees(hero))
        motion.turning=False;self.assertTrue(motion.sees(hero))

    def test_pursuit_moves_toward_hero_and_can_follow_behind(self):
        motion=BeetleMotion(0);hero=Hero(motion.x+300,motion.y+100)
        x=motion.x
        for tick in range(90):motion.update(STEP,(tick+1)*STEP,hero)
        self.assertEqual(motion.state,'chase');self.assertGreater(motion.x,x+100)
        hero.x=motion.x-200
        for tick in range(120):motion.update(STEP,1+tick*STEP,hero)
        self.assertEqual(motion.state,'chase');self.assertLess(motion.vx,0)
        self.assertEqual(motion.facing,-1)

    def test_pursuit_has_no_time_limit_and_stops_only_at_excessive_distance(self):
        motion=BeetleMotion(0);hero=Hero(motion.x+200,motion.y+28)
        for tick in range(120*30):
            hero.x=motion.x+200;hero.y=motion.y+28
            motion.update(STEP,(tick+1)*STEP,hero)
            self.assertEqual(motion.state,'chase')
        hero.x=motion.x+LOSE_RANGE+10
        before=motion.position()
        motion.update(STEP,30+STEP,hero)
        self.assertEqual(motion.state,'return');self.assertGreater(motion.rearm,0)
        self.assertLess(abs(motion.x-before[0]),3)
        hero.x=motion.x+100
        motion.update(STEP,30+2*STEP,hero)
        self.assertNotEqual(motion.state,'chase')

    def test_return_rejoins_patrol_without_teleport(self):
        motion=BeetleMotion(0);motion.state='return';motion.x+=200;motion.y-=50
        for tick in range(2400):
            before=motion.position();motion.update(STEP,(tick+1)*STEP)
            self.assertLess(abs(motion.x-before[0]),3)
            self.assertLess(abs(motion.y-before[1]),3)
            if motion.state=='patrol':break
        self.assertEqual(motion.state,'patrol')

    def test_pursuit_cannot_cross_stone_or_acquire_during_respawn_grace(self):
        motion=BeetleMotion(0);hero=Hero(motion.x+300,motion.y+28)
        motion.update(STEP,STEP,hero,can_attack=False)
        self.assertEqual(motion.state,'patrol')
        motion.state='chase'
        wall=Platform(motion.x+80,motion.y-200,32,400)
        for tick in range(120):motion.update(STEP,(tick+2)*STEP,hero,[wall])
        self.assertLess(motion.x,wall.x-17)

    def test_complete_wing_cycle_samples_all_16_frames(self):
        motion=BeetleMotion(0);seen=set()
        for tick in range(120):
            motion.update(STEP,tick*STEP);seen.add(motion.sample()[-1])
        self.assertEqual(seen,set(range(16)))

    def test_each_enemy_starts_with_a_different_wing_phase(self):
        phases=[BeetleMotion(i).sample()[-1] for i in range(len(SPAWNS))]
        self.assertEqual(len(set(phases)),len(SPAWNS))

    def test_reversal_passes_through_front_before_changing_facing(self):
        motion=BeetleMotion(0);self.assertEqual(motion.facing,1)
        motion.update(STEP,2.2)
        self.assertTrue(motion.turning);self.assertEqual(motion.facing,1)
        motion.update(.08,2.28)
        self.assertEqual(motion.sample(),('turn',0,0,3))
        motion.update(.08,2.36)
        self.assertFalse(motion.turning);self.assertEqual(motion.facing,-1)

    def test_bank_angles_are_bounded_and_prebaked(self):
        motion=BeetleMotion(0)
        for tick in range(1000):
            motion.update(STEP,tick*STEP)
            key=motion.sample(.5)
            if key[0]=='flight':self.assertIn(key[2],TILTS)

    def test_destruction_plays_in_order_and_has_a_fixed_lifetime(self):
        death=BeetleDeath(10,20,-1,50,-20);seen=[]
        for _ in range(73):
            death.update(STEP);seen.append(death.sample()[-1])
        self.assertEqual(sorted(set(seen)),list(range(8)))
        self.assertEqual(seen,sorted(seen));self.assertGreater(death.age,DEATH_TIME)

    def test_explosion_plays_all_16_frames_after_the_metal_breakup(self):
        death=BeetleDeath(0,0,1);seen=[]
        for _ in range(73):
            death.update(STEP);seen.append(death.explosion_sample()[-1])
            if death.age>.34:self.assertEqual(death.sample()[-1],7)
        self.assertEqual(sorted(set(seen)),list(range(16)))
        self.assertEqual(seen,sorted(seen))


class BeetleSpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init();pg.display.set_mode((32,32));cls.bank=BeetleSprites.load(ROOT/'assets')
    @classmethod
    def tearDownClass(cls):pg.quit()

    def test_all_328_variants_share_one_gpu_atlas(self):
        self.assertEqual(len(self.bank.areas),328)
        self.assertEqual(len(self.bank.images),1)
        self.assertLessEqual(max(self.bank.atlas.get_size()),4096)
        for key,area in self.bank.areas.items():
            self.assertTrue(self.bank.atlas.get_rect().contains(area))
            if key[0]!='explosion' or key[-1]<14:
                self.assertGreater(self.bank.atlas.subsurface(area).get_bounding_rect(min_alpha=1 if key[0]=='explosion' else 32).w,0)

    def test_animation_does_not_rotate_mirror_or_load_during_render(self):
        canvas=MagicMock();canvas.point.return_value=(400,500)
        with patch('pygame.transform.rotozoom',side_effect=AssertionError('runtime rotation')),patch('pygame.transform.flip',side_effect=AssertionError('runtime mirror')),patch('pygame.image.load',side_effect=AssertionError('runtime load')):
            for key in self.bank.areas:self.bank.draw(canvas,key,0,0)
        self.assertEqual(canvas.native.blit.call_count,328)
        self.assertTrue(all(call.args[0] is self.bank.atlas for call in canvas.native.blit.call_args_list))

    def test_explosion_is_drawn_behind_the_metal_in_the_same_atlas(self):
        canvas=MagicMock();canvas.point.return_value=(400,500)
        death=BeetleDeath(10,20,-1);death.update(.15)
        self.bank.draw_death(canvas,death)
        calls=canvas.native.blit.call_args_list
        self.assertEqual(len(calls),2)
        self.assertEqual(calls[0].args[2],self.bank.areas[death.explosion_sample()])
        self.assertEqual(calls[1].args[2],self.bank.areas[death.sample()])


class BeetleGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.reset();self.g.state='play';self.g.invuln=10

    def test_world_positions_and_render_interpolation_use_simulation_clock(self):
        for motion in self.g.beetle_motions:
            motion.update(STEP,1.);motion.update(STEP,2.)
        self.g.time=999.
        for index,x,y in self.g.beetles(.5):
            a,b=position(index,1.),position(index,2.)
            expected=((a[0]+b[0])/2,(a[1]+b[1])/2)
            self.assertAlmostEqual(x,expected[0]);self.assertAlmostEqual(y,expected[1])

    def test_solar_kill_spawns_one_nondamaging_metal_destruction(self):
        self.g.hero=Hero(1600,550)
        for tick in range(24):
            self.g.hero.y=self.g.hero.py=550;self.g.hero.vy=0
            self.g.update(STEP,0,False,False,fire=tick==0)
        self.assertIn(0,self.g.dead_beetles)
        self.assertEqual(len(self.g.beetle_deaths),1)
        self.assertEqual(len(self.g.enemy_positions()),5)
        for _ in range(100):self.g.update(STEP,0,False,False)
        self.assertFalse(self.g.beetle_deaths)

    def test_death_preserves_kills_and_fragments_restart_restores_robots(self):
        self.g.dead_beetles.add(0);self.g.beetle_deaths.append(BeetleDeath(1920,495,-1))
        self.g.hero.y=900;self.g.update(STEP,0,False,False)
        self.assertEqual(len(self.g.beetles()),5);self.assertTrue(self.g.beetle_deaths)
        self.g.dead_beetles.add(1);self.g.reset()
        self.assertEqual(len(self.g.beetle_motions),6);self.assertEqual(len(self.g.beetles()),6)

    def test_pause_freezes_flight_direction_and_wing_phase(self):
        before=[motion.clock for motion in self.g.beetle_motions]
        self.g.state='pause'
        with patch.object(self.g,'close'),patch('main.pg.event.get',return_value=[]):
            self.g.run(frames=2)
        self.assertEqual(before,[motion.clock for motion in self.g.beetle_motions])

    def test_new_sprite_renderer_is_used_for_every_visible_robot(self):
        with patch.object(self.g.beetle_sprites,'draw') as draw:
            for x in (1600,3000,4200,5500,6800,8200):
                self.g.cam=self.g.prev_cam=x;self.g.draw(.5)
        self.assertGreaterEqual(draw.call_count,6)


if __name__=='__main__':unittest.main()
