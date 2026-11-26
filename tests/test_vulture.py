import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch,MagicMock
import pygame as pg
from main import Game,Hero,Platform,STEP,WORLD
from vulture import Vulture,SPAWNS,WINDUP,DIVE_SPEED,DEATH_TIME,CELL


class VultureMotionTests(unittest.TestCase):
    def start_dive(self):
        enemy=Vulture(0);hero=Hero(enemy.x+200,620)
        enemy.update(STEP,hero,[])
        self.assertEqual(enemy.state,'warning')
        for _ in range(48):enemy.update(STEP,hero,[])
        self.assertEqual(enemy.state,'dive')
        return enemy,hero

    def test_guardians_spawn_only_in_second_half_and_glide_phases_differ(self):
        self.assertTrue(all(x>WORLD/2 and y<250 for x,y in SPAWNS))
        self.assertEqual(len(set(Vulture(i).sample()[-1] for i in range(3))),3)

    def test_sight_requires_hero_below_in_front_and_unobstructed(self):
        enemy=Vulture(0);hero=Hero(enemy.x+200,620)
        self.assertTrue(enemy.sees(hero,[]))
        self.assertFalse(enemy.sees(hero,[Platform(enemy.x+80,220,50,300)]))
        hero.x=enemy.x-200;self.assertFalse(enemy.sees(hero,[]))
        hero.x=enemy.x+200;hero.y=100;self.assertFalse(enemy.sees(hero,[]))
        hero.y=620;hero.x=enemy.x+1000;self.assertFalse(enemy.sees(hero,[]))
        enemy.turning=True;hero.x=enemy.x+100;self.assertFalse(enemy.sees(hero,[]))

    def test_windup_precedes_dive_and_target_does_not_home(self):
        enemy,hero=self.start_dive();target=enemy.target;velocity=(enemy.vx,enemy.vy)
        self.assertAlmostEqual((enemy.vx**2+enemy.vy**2)**.5,DIVE_SPEED)
        hero.x-=400;enemy.update(STEP,hero,[])
        self.assertEqual(enemy.target,target);self.assertEqual((enemy.vx,enemy.vy),velocity)

    def test_aim_tracks_visible_hero_then_locks_before_launch(self):
        enemy=Vulture(0);hero=Hero(enemy.x+200,620)
        enemy.update(STEP,hero,[])
        hero.x+=60
        for _ in range(20):enemy.update(STEP,hero,[])
        self.assertEqual(enemy.target,(hero.x,hero.y-hero.body_height/2))
        visible_target=enemy.target;hero.x+=40
        wall=Platform(enemy.x+60,220,50,300)
        enemy.update(STEP,hero,[wall])
        self.assertEqual(enemy.target,visible_target)
        for _ in range(15):enemy.update(STEP,hero,[])
        locked=enemy.target;hero.x+=80
        for _ in range(12):enemy.update(STEP,hero,[])
        self.assertEqual(enemy.state,'dive');self.assertEqual(enemy.target,locked)

    def test_dive_pulls_up_and_returns_without_position_jump(self):
        enemy,hero=self.start_dive();seen=set()
        for _ in range(2400):
            before=enemy.position();enemy.update(STEP,hero,[],can_attack=False)
            seen.add(enemy.state)
            self.assertLess(abs(enemy.x-before[0]),7)
            self.assertLess(abs(enemy.y-before[1]),7)
            if enemy.state=='patrol':break
        self.assertTrue({'pullup','return','patrol'}<=seen)

    def test_platform_intercepts_dive_and_guardian_remains_alive(self):
        enemy,hero=self.start_dive();floor=Platform(0,450,9600,100,True)
        for _ in range(120):
            enemy.update(STEP,hero,[floor])
            self.assertLessEqual(enemy.y,432)
            if enemy.state=='pullup':break
        self.assertTrue(enemy.alive);self.assertEqual(enemy.state,'pullup')

    def test_respawn_grace_prevents_acquisition(self):
        enemy=Vulture(0);hero=Hero(enemy.x+150,620)
        for _ in range(100):enemy.update(STEP,hero,[],can_attack=False)
        self.assertEqual(enemy.state,'patrol')

    def test_fast_relative_contact_is_lethal_but_dead_robot_is_not(self):
        enemy=Vulture(0);enemy.px=enemy.x=100;enemy.py=100;enemy.y=450
        hero=Hero(100,350);hero.py=350
        self.assertTrue(enemy.hits(hero))
        enemy.ignite();self.assertFalse(enemy.hits(hero));self.assertFalse(enemy.ignite())

    def test_warning_dive_pullup_and_destruction_use_full_authored_ranges(self):
        enemy=Vulture(0)
        for state,count,duration in (('warning',8,WINDUP),('pullup',8,.65),('death',16,DEATH_TIME)):
            enemy.state=state;enemy.alive=state!='death';seen=set()
            for i in range(count):
                enemy.timer=enemy.previous_timer=(i+.2)/count*duration
                seen.add(enemy.sample()[-1])
            self.assertEqual(seen,set(range(count)))


class VultureGameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()
    def setUp(self):self.g.reset();self.g.state='play';self.g.invuln=100

    def test_solar_ray_destroys_guardian_and_removes_its_contact(self):
        g=self.g;g.hero=Hero(9000,620);g.hero.grounded=True
        enemy=g.vultures[2];enemy.x=enemy.px=9200;enemy.y=enemy.py=566
        g.solar.update(.2,g.hero,True,g.energy);g.solar_hits()
        self.assertFalse(enemy.alive);self.assertFalse(enemy.hits(g.hero))
        self.assertEqual(enemy.state,'death')

    def test_guardian_contact_uses_death_rumble_and_resets_all_guardians(self):
        from support import finish_respawn
        g=self.g;g.invuln=0;g.hero=Hero(9000,620);g.hero.grounded=True
        enemy=g.vultures[2];enemy.x=enemy.px=9000;enemy.y=enemy.py=593
        enemy.state='warning';enemy.target=(9000,593);enemy.vx=enemy.vy=0
        with patch.object(g.gamepads,'rumble') as rumble:g.update(STEP,0,False,False)
        self.assertEqual(g.deaths,1);rumble.assert_called_once_with('death',duration=1200)
        self.assertEqual(g.hero_death.kind,'vulture')
        finish_respawn(g)
        self.assertTrue(all(v.alive and v.state=='patrol' for v in g.vultures))

    def test_pause_and_drawing_do_not_advance_guardian_simulation(self):
        g=self.g;before=[(v.clock,v.x,v.y,v.state) for v in g.vultures]
        g.state='pause';g.cam=g.prev_cam=5500
        with patch.object(g,'close'),patch('main.pg.event.get',return_value=[]):g.run(frames=2)
        self.assertEqual(before,[(v.clock,v.x,v.y,v.state) for v in g.vultures])

    def test_all_mirrors_and_dive_angles_share_a_cached_atlas(self):
        bank=self.g.vulture_sprites
        self.assertEqual(len(bank.images),1);self.assertEqual(len(bank.areas),216)
        self.assertLessEqual(max(bank.atlas.get_size()),4096)
        canvas=MagicMock();canvas.point.return_value=(400,300)
        enemy=Vulture(0)
        with patch('pygame.transform.rotozoom',side_effect=AssertionError('runtime rotation')),patch('pygame.image.load',side_effect=AssertionError('runtime load')):
            for key,area in bank.areas.items():
                self.assertTrue(bank.atlas.get_rect().contains(area))
                bounds=bank.atlas.subsurface(area).get_bounding_rect(min_alpha=1)
                if key[0]=='death' and key[-1]==15:self.assertEqual(bounds.w,0)
                else:self.assertGreater(bounds.w,0)
                with patch.object(enemy,'sample',return_value=key):bank.draw(canvas,enemy,0,.5)
        self.assertEqual(canvas.native.blit.call_count,216)

    def test_flight_chest_anchor_has_no_outlier_pose_or_loop_seam(self):
        bank=self.g.vulture_sprites
        for face in (-1,1):
            bounds=[bank.atlas.subsurface(bank.areas[('flight',face,0,i)]).get_bounding_rect(min_alpha=64) for i in range(24)]
            for current,following in zip(bounds,bounds[1:]+bounds[:1]):
                self.assertLessEqual(abs(current.top-following.top),8)
                self.assertLessEqual(abs(current.centerx-following.centerx),8)
                self.assertGreater(current.left,0)
