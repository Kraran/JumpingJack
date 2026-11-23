import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from main import Hero, Platform, STEP, ROOT, level
from hero_animation import HeroAnimator, AnimationBank, load_bank, LAND_DURATIONS
import pygame as pg


class LandingLevelsTests(unittest.TestCase):
    def fall(self,height,glide=False,ground=True):
        target=620 if ground else 492
        hero=Hero(500,target-height);animation=HeroAnimator()
        floor=[Platform(0,target,2000,100 if ground else 32,ground)]
        for _ in range(1200):
            was=hero.grounded
            hero.update(STEP,0,glide,False,floor)
            animation.update(STEP,hero,was)
            if hero.grounded:return hero,animation,floor
        self.fail('No contact within ten seconds')

    def test_thresholds_use_height_on_ground_and_platforms(self):
        for ground in (True,False):
            for height,expected in ((95,'land'),(159.9,'land'),(160,'land_medium'),
                                    (279.9,'land_medium'),(280,'land_heavy'),(320,'land_heavy')):
                with self.subTest(ground=ground,height=height):
                    hero,animation,_=self.fall(height,ground=ground)
                    self.assertAlmostEqual(hero.landed_height,height)
                    self.assertEqual(hero.landing_kind,expected)
                    self.assertEqual(animation.state,expected)

    def test_highest_level_platforms_trigger_heavy_landing(self):
        platforms,_=level()
        height=620-min(p.y for p in platforms)
        self.assertEqual(height,320)
        self.assertEqual(self.fall(height)[1].state,'land_heavy')

    def test_glide_from_all_heights_has_no_bend_or_recovery(self):
        for ground in (True,False):
            for height in (95,200,320,500):
                hero,animation,_=self.fall(height,True,ground)
                self.assertEqual(animation.state,'idle')
                self.assertEqual(hero.recovery,0)
                self.assertEqual(hero.landed_height,0)

    def test_height_is_measured_from_jump_apex(self):
        hero=Hero(500,620);hero.grounded=True
        floor=[Platform(0,620,2000,100,True)];animation=HeroAnimator();apex=620
        for tick in range(200):
            was=hero.grounded
            hero.update(STEP,0,False,tick==0,floor)
            animation.update(STEP,hero,was);apex=min(apex,hero.y)
            if tick and hero.grounded:break
        self.assertAlmostEqual(hero.landed_height,620-apex)
        self.assertEqual(animation.state,'land_medium')

    def test_glide_resets_drop_before_release(self):
        hero=Hero(500,200);floor=[Platform(0,620,2000,100,True)]
        while hero.y<550:hero.update(STEP,0,True,False,floor)
        released_at=hero.y
        # First released step must reset to the previous glide position.
        while not hero.grounded:hero.update(STEP,0,False,False,floor)
        self.assertAlmostEqual(hero.landed_height,620-released_at)
        self.assertEqual(hero.landing_kind,'land')
        self.assertEqual(hero.recovery,0)

    def test_heavy_landing_freezes_movement_facing_and_jump_for_recovery(self):
        hero,animation,floor=self.fall(320)
        x,face=hero.x,hero.face
        for _ in range(71):
            hero.update(STEP,-1,True,True,floor)
            animation.update(STEP,hero,True)
            self.assertEqual(hero.x,x)
            self.assertEqual(hero.face,face)
            self.assertTrue(hero.grounded)
            self.assertEqual(hero.vy,0)
            self.assertEqual(hero.buffer,0)
        self.assertGreater(hero.recovery,0)
        self.assertEqual(animation.state,'land_heavy')
        hero.update(STEP,-1,False,False,floor)
        animation.update(STEP,hero,True)
        self.assertEqual(hero.recovery,0)
        self.assertEqual(animation.state,'idle')
        hero.update(STEP,-1,True,True,floor)
        animation.update(STEP,hero,True)
        self.assertLess(hero.x,x)
        self.assertLess(hero.vy,0)
        self.assertEqual(animation.state,'rise')

    def test_medium_landing_does_not_lock_controls(self):
        hero,animation,floor=self.fall(200)
        x=hero.x
        hero.update(STEP,1,True,True,floor)
        animation.update(STEP,hero,True)
        self.assertEqual(hero.recovery,0)
        self.assertGreater(hero.x,x)
        self.assertEqual(animation.state,'rise')

    def test_each_landing_plays_every_pose_once_without_looping(self):
        clips={name:list(range(count)) for name,count in
               (('land',8),('land_medium',8),('land_heavy',12))}
        bank=AnimationBank(clips)
        for name,duration in LAND_DURATIONS.items():
            animation=HeroAnimator();animation.state=name
            seen=[]
            for tick in range(round(duration*120)):
                animation.previous_elapsed=animation.elapsed=tick/120
                seen.append(animation.sample(bank))
            self.assertEqual(sorted(set(seen)),clips[name])
            self.assertEqual(seen,sorted(seen))
            animation.previous_elapsed=animation.elapsed=duration+1
            self.assertEqual(animation.sample(bank),clips[name][-1])

    def test_respawn_starts_without_fall_or_recovery_history(self):
        hero,_,_=self.fall(320)
        self.assertGreater(hero.recovery,0)
        respawn=Hero(500,620)
        self.assertEqual(respawn.recovery,0)
        self.assertEqual(respawn.fall_origin_y,620)
        self.assertEqual(respawn.landed_height,0)


class LandingSpriteTests(unittest.TestCase):
    def test_all_three_landing_clips_keep_lowest_contact_on_root_pixel(self):
        pg.init();pg.display.set_mode((64,64))
        try:
            bank=load_bank(ROOT/'assets')
            for key in LAND_DURATIONS:
                for pose in bank.clips[key]:
                    for image in pose.images:
                        self.assertEqual(pose.pivot[1],image.get_bounding_rect(min_alpha=32).bottom-1)
                        self.assertEqual(image.get_at((0,0)).a,0)
        finally:pg.quit()


if __name__=='__main__':unittest.main()
