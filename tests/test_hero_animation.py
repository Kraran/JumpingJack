import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import MagicMock
from types import SimpleNamespace
import pygame as pg
from hero_animation import AnimationBank, HeroAnimator, Pose, load_bank, CELL, STRIDE
from main import ROOT, Hero, Platform


def bank():
    return AnimationBank({name:list(range(n)) for name,n in
        [('run',24),('idle',4),('rise',4),('float',8),('fall',1),('land',1)]})


class AnimationTimingTests(unittest.TestCase):
    def hero(self):return SimpleNamespace(x=0.,px=0.,vx=340.,vy=0.,grounded=True,floating=False,face=1)

    def test_complete_run_uses_every_pose_at_60_hz(self):
        hero=self.hero();animation=HeroAnimator();seen=[]
        for _ in range(24):
            for _ in range(2):
                hero.px=hero.x;hero.x+=340/120
                animation.update(1/120,hero,True)
            seen.append(animation.sample(bank(),1))
        self.assertEqual(seen,list(range(1,24))+[0])
        self.assertAlmostEqual(hero.x,STRIDE)

    def test_same_distance_has_same_phase_at_different_update_rates(self):
        phases=[]
        for hz in (60,120,144):
            hero=self.hero();animation=HeroAnimator()
            for _ in range(hz):
                hero.px=hero.x;hero.x+=340/hz
                animation.update(1/hz,hero,True)
            phases.append(animation.phase)
        for phase in phases:self.assertAlmostEqual(phase,2.5)

    def test_render_interpolation_samples_between_simulation_steps(self):
        animation=HeroAnimator();animation.state='run'
        animation.previous_phase=0.;animation.phase=2/24
        self.assertEqual(animation.sample(bank(),0),0)
        self.assertEqual(animation.sample(bank(),.5),1)
        self.assertEqual(animation.sample(bank(),1),2)

    def test_stopping_does_not_advance_run_cycle(self):
        hero=self.hero();animation=HeroAnimator()
        hero.x=30;animation.update(1/120,hero,True)
        phase=animation.phase
        hero.px=hero.x;hero.vx=0
        for _ in range(120):animation.update(1/120,hero,True)
        self.assertEqual(animation.phase,phase)
        self.assertEqual(animation.state,'idle')

    def test_aerial_states_and_landing_do_not_block_next_jump(self):
        hero=self.hero();animation=HeroAnimator()
        hero.grounded=False;hero.vy=-700
        animation.update(1/120,hero,True);self.assertEqual(animation.state,'rise')
        hero.vy=-40;animation.update(1/120,hero,False);self.assertEqual(animation.state,'apex')
        hero.vy=100;hero.floating=True
        animation.update(1/120,hero,False);self.assertEqual(animation.state,'float')
        hero.vy=400;hero.floating=False
        animation.update(1/120,hero,False);self.assertEqual(animation.state,'fall')
        hero.grounded=True;hero.vy=0
        animation.update(1/120,hero,False);self.assertEqual(animation.state,'land')
        hero.grounded=False;hero.vy=-790
        animation.update(1/120,hero,True);self.assertEqual(animation.state,'rise')

    def test_reset_discards_previous_movement(self):
        animation=HeroAnimator();animation.phase=9.4;animation.state='float';animation.landing=.05
        animation.reset()
        self.assertEqual((animation.phase,animation.elapsed,animation.landing),(0.,0.,0.))
        self.assertEqual(animation.state,'idle')

    def test_coyote_jump_starts_at_first_pose_instead_of_old_fall_progress(self):
        hero=self.hero();hero.grounded=False;hero.vy=-780
        animation=HeroAnimator();animation.state='fall';animation.rise=1.
        animation.update(1/120,hero,False)
        self.assertEqual(animation.state,'rise')
        self.assertEqual(animation.sample(bank(),0),0)

    def test_turn_completes_without_stopping_locomotion_phase(self):
        hero=self.hero();hero.face=-1;animation=HeroAnimator()
        for _ in range(20):
            hero.px=hero.x;hero.x+=340/120
            animation.update(1/120,hero,True)
        self.assertEqual(animation.turn,1.)
        self.assertEqual(animation.render_facing(),-1)
        self.assertEqual(animation.state,'run')
        self.assertGreater(animation.phase,0)

    def test_reversing_mid_turn_retraces_angle_instead_of_snapping(self):
        hero=self.hero();hero.face=-1;animation=HeroAnimator()
        for _ in range(10):animation.update(1/120,hero,True)
        before=animation.turn
        hero.face=1;animation.update(1/120,hero,True)
        self.assertGreater(animation.turn,0)
        self.assertLess(animation.turn,before)
        self.assertEqual(animation.previous_turn,before)
        for _ in range(10):animation.update(1/120,hero,True)
        self.assertEqual(animation.turn,0)

    def test_jump_during_turn_selects_air_clip_and_keeps_turn_progress(self):
        b=bank();b.clips['turn_ground']=['g']*8;b.clips['turn_air']=['a']*8
        hero=self.hero();hero.face=-1;animation=HeroAnimator()
        for _ in range(5):animation.update(1/120,hero,True)
        self.assertEqual(animation.sample(b),'g')
        before=animation.turn
        hero.grounded=False;hero.vy=-790
        animation.update(1/120,hero,True)
        self.assertEqual(animation.state,'rise')
        self.assertGreater(animation.turn,before)
        self.assertEqual(animation.sample(b),'a')

    def test_mid_turn_uses_canonical_clip_direction_in_both_directions(self):
        animation=HeroAnimator();animation.previous_turn=.4;animation.turn=.6
        self.assertEqual(animation.render_facing(.5),1)
        animation.previous_turn=.6;animation.turn=.4
        self.assertEqual(animation.render_facing(.5),1)

    def test_physics_and_jump_keep_responding_during_turn(self):
        hero=Hero(500,620);hero.grounded=True;hero.vx=340
        animation=HeroAnimator();floor=[Platform(0,620,2000,100,True)]
        hero.update(1/120,-1,False,False,floor)
        animation.update(1/120,hero,True)
        self.assertNotEqual(hero.x,500)
        self.assertEqual(hero.face,-1)
        hero.update(1/120,-1,True,True,floor)
        animation.update(1/120,hero,True)
        self.assertLess(hero.vy,0)
        self.assertLess(hero.y,620)
        self.assertTrue(0<animation.turn<1)


class SpriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init();pg.display.set_mode((64,64));cls.bank=load_bank(ROOT/'assets')
    @classmethod
    def tearDownClass(cls):pg.quit()

    def test_all_58_active_poses_are_present_and_share_canvas_scale(self):
        self.assertEqual(self.bank.pose_count,58)
        self.assertEqual(len(self.bank.clips['run']),24)
        self.assertEqual(len(self.bank.clips['float']),8)
        self.assertEqual(len(self.bank.clips['turn_ground']),8)
        self.assertEqual(len(self.bank.clips['turn_air']),8)
        for clip in self.bank.clips.values():
            for pose in clip:
                for image in pose.images:
                    self.assertEqual(image.get_size(),(CELL,CELL))
                    self.assertGreater(image.get_bounding_rect(min_alpha=32).h,30)
                    self.assertLessEqual(image.get_at((0,0)).a,8)

    def test_running_head_height_does_not_pump_between_frames(self):
        tops=[p.images[0].get_bounding_rect(min_alpha=32).top for p in self.bank.clips['run']]
        self.assertLessEqual(max(tops)-min(tops),4)

    def test_mirroring_keeps_registered_root_on_same_native_pixel(self):
        image=pg.Surface((128,128),pg.SRCALPHA)
        pose=Pose((image,pg.transform.flip(image,True,False)),(68,123))
        canvas=MagicMock();canvas.point.return_value=(600,930)
        pose.draw(canvas,400,620,1)
        self.assertEqual(canvas.native.blit.call_args.args[1],(532,807))
        pose.draw(canvas,400,620,-1)
        self.assertEqual(canvas.native.blit.call_args.args[1],(541,807))


if __name__=='__main__':unittest.main()
