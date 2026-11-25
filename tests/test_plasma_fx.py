import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import MagicMock, patch
import pygame as pg
from main import ROOT, Hero, STEP
from plasma_fx import PlasmaEffect, FX_FPS, FX_FRAMES, FX_DURATION, FRAME_SIZE, COLUMNS
from gpu_render import DesignCanvas, NativeCanvas
from solar import SolarRay


class PlasmaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pg.init();pg.display.set_mode((32,32));cls.fx=PlasmaEffect.load(ROOT/'assets')
    @classmethod
    def tearDownClass(cls):pg.quit()

    def test_both_atlases_fit_standard_texture_limits(self):
        self.assertIsNotNone(self.fx)
        self.assertEqual(len(self.fx.images),2)
        for image in self.fx.images:
            self.assertLessEqual(max(image.get_size()),4096)

    def test_right_clipping_ends_at_wall_in_native_pixels(self):
        canvas=DesignCanvas(MagicMock())
        self.fx.draw(canvas,400,100,460,.2,1)
        image,dest,area=canvas.native.blit.call_args.args
        self.assertIs(image,self.fx.images[0])
        self.assertEqual(dest[0]+area.w-1,690)
        self.assertEqual(area.w,146+90+1)

    def test_left_clipping_ends_at_wall_in_native_pixels(self):
        canvas=DesignCanvas(MagicMock())
        self.fx.draw(canvas,400,100,340,.2,-1)
        image,dest,area=canvas.native.blit.call_args.args
        self.assertIs(image,self.fx.images[1])
        self.assertEqual(dest[0],510)
        self.assertEqual(area.w,146+90+1)

    def test_sampling_never_builds_or_mirrors_images_during_draw(self):
        canvas=DesignCanvas(MagicMock());seen=set()
        with patch('pygame.transform.flip',side_effect=AssertionError('runtime mirror')),patch('pygame.transform.smoothscale',side_effect=AssertionError('runtime scaling')):
            for frame in range(FX_FRAMES):
                self.fx.draw(canvas,400,100,1100,frame/FX_FPS,1)
                _,_,area=canvas.native.blit.call_args.args
                seen.add((area.x//FRAME_SIZE[0],area.y//FRAME_SIZE[1]))
        self.assertEqual(len(seen),FX_FRAMES)

    def test_afterglow_has_no_damage_and_stays_at_last_world_position(self):
        effect=MagicMock();ray=SolarRay(effect);hero=Hero(500,620)
        for tick in range(50):ray.update(STEP,hero,tick==0)
        self.assertFalse(ray.active);self.assertFalse(ray.emitting)
        self.assertIsNotNone(ray.visual_elapsed)
        hero.x=800;hero.y=400
        ray.draw(DesignCanvas(MagicMock()),hero,[],alpha=1)
        _,start,y,end,_,face=effect.draw.call_args.args
        self.assertEqual((start,y,face),(534,566,1))
        self.assertEqual(end,1234)
        ray.update(FX_DURATION,hero)
        self.assertIsNone(ray.visual_elapsed)

    def test_gliding_cancels_the_visual_tail(self):
        ray=SolarRay(self.fx);hero=Hero()
        ray.update(.35,hero,True);self.assertIsNotNone(ray.visual_elapsed)
        hero.floating=True;ray.update(STEP,hero)
        self.assertFalse(ray.active);self.assertIsNone(ray.visual_elapsed)

    def test_additive_software_fallback_preserves_black_and_saturates_light(self):
        canvas=NativeCanvas();canvas.surface.fill((20,30,40))
        image=pg.Surface((2,1));image.set_at((0,0),(0,0,0));image.set_at((1,0),(250,40,20))
        canvas.blit_additive(image,(10,10))
        self.assertEqual(tuple(canvas.surface.get_at((10,10)))[:3],(20,30,40))
        self.assertEqual(tuple(canvas.surface.get_at((11,10)))[:3],(255,70,60))
        canvas.release()

    def test_final_atlas_frame_is_completely_transparent(self):
        index=FX_FRAMES-1;w,h=FRAME_SIZE
        frame=self.fx.images[0].subsurface((index%COLUMNS*w,index//COLUMNS*h,w,h))
        self.assertEqual(pg.mask.from_surface(frame,threshold=0).count(),0)

    def test_colored_plasma_does_not_saturate_blue_sky_to_white(self):
        self.assertTrue(self.fx.alpha_blend)
        canvas=NativeCanvas();design=DesignCanvas(canvas)
        try:
            for sky in ((110,170,230),(180,205,235),(18,30,42)):
                canvas.surface.fill(sky)
                self.fx.draw(design,200,200,900,.22,1)
                golden=white=0
                for x in range(350,1300,2):
                    for y in range(275,325):
                        r,g,b,_=canvas.surface.get_at((x,y))
                        golden+=r>b+20 and r>g+5
                        white+=min(r,g,b)>248
                self.assertGreater(golden,100,sky)
                self.assertEqual(white,0,sky)
        finally:canvas.release()

    def test_alpha_draw_preserves_background_outside_the_effect(self):
        canvas=NativeCanvas();design=DesignCanvas(canvas);sky=(110,170,230)
        try:
            canvas.surface.fill(sky);self.fx.draw(design,200,200,900,.22,1)
            self.assertEqual(tuple(canvas.surface.get_at((160,259)))[:3],sky)
            mock=DesignCanvas(MagicMock());self.fx.draw(mock,200,200,900,.22,1)
            mock.native.blit.assert_called_once();mock.native.blit_additive.assert_not_called()
        finally:canvas.release()


if __name__=='__main__':unittest.main()
