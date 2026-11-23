import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
import pygame as pg
from rendering import FramePacer, ParallaxLayer, integer_viewport, pixel
from main import Game, W, H, WORLD
from main import VIEW_W
from gpu_render import NativeCanvas, DesignCanvas, FULL_HD, SCALE, draw


class ParallaxTests(unittest.TestCase):
    def test_ratios_and_absolute_positions(self):
        image=pg.Surface((16,8))
        layers=[ParallaxLayer(str(n),image,n,25) for n in (2,6,12)]
        self.assertEqual([p.offset(1000) for p in layers],[80,240,480])
        # Reversing the camera, jumping and rendering extra frames cannot change phase.
        for camera in [0,10.9,8200,4500,1000,10.9,0]:
            for p in layers:self.assertEqual(p.offset(camera),pixel(camera*p.numerator/25))

    def test_periodic_images_have_no_missing_columns(self):
        image=pg.Surface((7,3))
        for x in range(7):image.fill((20+x*20,0,0),(x,0,1,3))
        layer=ParallaxLayer('test',image,1,1)
        target=pg.Surface((24,3))
        for camera in (-15,-7,-1,0,1,6,7,8,10000):
            target.fill('magenta');layer.draw(target,camera)
            for x in range(24):
                self.assertEqual(target.get_at((x,1)),image.get_at(((x+camera)%7,1)))

    def test_transparent_margins_do_not_erase_far_layer(self):
        image=pg.Surface((8,8),pg.SRCALPHA)
        image.fill((255,0,0,255),(2,4,3,3))
        target=pg.Surface((20,8));target.fill('blue')
        layer=ParallaxLayer('cutout',image,1,1)
        layer.draw(target,1)
        self.assertEqual(target.get_at((1,4))[:3],(255,0,0))
        self.assertEqual(target.get_at((0,4))[:3],(0,0,255))
        self.assertEqual(target.get_at((9,4))[:3],(255,0,0))

    def test_rounding_is_consistent_at_half_pixels(self):
        self.assertEqual([pixel(x) for x in [0,.49,.5,1.49,1.5,2.5]],[0,0,1,1,2,3])

    def test_integer_output_has_no_fractional_stretch(self):
        self.assertEqual(integer_viewport((1920,1080),(1280,720)),((1280,720),(320,180)))
        self.assertEqual(integer_viewport((2560,1440),(1280,720)),((2560,1440),(0,0)))
        self.assertEqual(integer_viewport((3440,1440),(1280,720)),((2560,1440),(440,0)))


class FakeTime:
    def __init__(self):self.now=0.;self.sleeps=[]
    def clock(self):return self.now
    def sleep(self,dt):self.sleeps.append(dt);self.now+=dt


class PacingTests(unittest.TestCase):
    def test_vsync_does_not_add_a_second_limiter(self):
        t=FakeTime();p=FramePacer(t.clock,t.sleep)
        for _ in range(100):p.wait(True,360)
        self.assertEqual(t.sleeps,[])
        self.assertIsNone(p.deadline)

    def test_fallback_tracks_refresh_instead_of_240_cap(self):
        for hz in (60,75,120,144,165,240,360):
            t=FakeTime();p=FramePacer(t.clock,t.sleep)
            for _ in range(hz+1):p.wait(False,hz)
            self.assertAlmostEqual(t.now,1.,places=8)

    def test_small_sleep_overshoot_does_not_accumulate_drift(self):
        t=FakeTime()
        def late_sleep(dt):t.now+=dt+.0003
        p=FramePacer(t.clock,late_sleep)
        for _ in range(601):p.wait(False,60)
        self.assertAlmostEqual(t.now,10.0003,places=7)

    def test_stall_does_not_trigger_catchup_burst(self):
        t=FakeTime();p=FramePacer(t.clock,t.sleep)
        p.wait(False,60);t.now=2.
        p.wait(False,60);p.wait(False,60)
        self.assertAlmostEqual(t.sleeps[-1],1/60)


class RenderingIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):pg.quit()

    def test_three_real_assets_with_clear_upper_silhouettes(self):
        layers=self.g.background_layers
        self.assertEqual(len(layers),3)
        self.assertEqual([p.name for p in layers],['far','middle','near'])
        for layer in layers[1:]:
            self.assertGreater(layer.bounds.h,0)
            self.assertGreater(layer.bounds.y,100)
            self.assertEqual(layer.image.get_size(),(3240,1080))
            self.assertEqual(layer.image.get_at((0,0)).a,0)

    def test_entire_level_far_plane_covers_canvas(self):
        far=self.g.background_layers[0]
        for camera in (0,(WORLD-VIEW_W)/2,WORLD-VIEW_W):
            self.assertGreaterEqual(far.image.get_width()-far.offset(camera*SCALE),W)

    def test_all_planes_receive_same_interpolated_camera(self):
        self.g.state='play';self.g.prev_cam=1000;self.g.cam=1004
        seen=[]
        original=ParallaxLayer.draw
        def capture(layer,target,camera):
            seen.append((layer.name,camera));return original(layer,target,camera)
        with patch.object(ParallaxLayer,'draw',capture):self.g.draw(.375)
        self.assertEqual(seen,[('far',1502.25),('middle',1502.25),('near',1502.25)])

    def test_render_stable_after_camera_return(self):
        self.g.time=0
        self.g.background(1234.125)
        before=pg.image.tostring(self.g.capture(),'RGB')
        self.g.background(8000);self.g.background(0)
        self.g.background(1234.125)
        self.assertEqual(before,pg.image.tostring(self.g.capture(),'RGB'))

    def test_native_full_hd_frame_and_text(self):
        self.g.draw(1)
        self.assertEqual(self.g.capture().get_size(),FULL_HD)
        self.assertEqual((W,H),(1920,1080))
        self.assertGreater(self.g.font(20).get_height(),20)

    def test_layout_maps_to_single_native_pixels(self):
        self.assertEqual(self.g.canvas.point((2/3,2/3)),(1,1))
        self.assertEqual(self.g.canvas.point((1280,720)),FULL_HD)
        left=self.g.canvas.rect((10-2/3,0,128,32))
        right=self.g.canvas.rect((138-2/3,0,128,32))
        self.assertEqual(left.right,right.left)
        self.assertEqual(left.width,192)

    def test_display_inspection_reuses_retained_window_wrapper(self):
        # Creating temporary _sdl2 wrappers leaves SDL event data dangling after GC.
        wrapper=self.g.sdl_window
        with patch('pygame._sdl2.video.Window') as window_type:
            window_type.from_display_module.side_effect=AssertionError('temporary wrapper')
            for _ in range(3):self.g.refresh_display_status()
        self.assertIs(wrapper,self.g.sdl_window)
        pg.event.get()


if __name__=='__main__':unittest.main()
