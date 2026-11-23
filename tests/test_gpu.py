import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch, MagicMock
import pygame as pg
from gpu_render import NativeCanvas, DesignCanvas, draw, FULL_HD


class GpuCompositionTests(unittest.TestCase):
    def test_preload_warms_textures_without_presenting_or_reading_back(self):
        renderer=MagicMock();renderer.target=None
        with patch('pygame._sdl2.video.Renderer') as renderer_type, patch('pygame._sdl2.video.Texture') as texture_type:
            renderer_type.from_window.return_value=renderer
            canvas=NativeCanvas(window=object())
            images=[pg.Surface((24,24)),pg.Surface((48,24))]
            canvas.preload(images)
            self.assertEqual(texture_type.from_surface.call_count,2)
            self.assertEqual(texture_type.from_surface.return_value.draw.call_count,2)
            self.assertIsNone(renderer.target)
            renderer.present.assert_not_called();renderer.to_surface.assert_not_called()
            canvas.release()

    def test_static_texture_is_uploaded_once_and_frames_stay_on_gpu(self):
        renderer=MagicMock()
        with patch('pygame._sdl2.video.Renderer') as renderer_type, patch('pygame._sdl2.video.Texture') as texture_type:
            renderer_type.from_window.return_value=renderer
            canvas=NativeCanvas(window=object())
            image=pg.Surface((24,24),pg.SRCALPHA)
            with patch('pygame.display.flip',side_effect=AssertionError('CPU frame upload')):
                for _ in range(3):
                    canvas.begin()
                    canvas.blit(image,(10,20))
                    canvas.blit(image,(40,20))
                    canvas.present(None)
            texture_type.assert_called_once_with(renderer,FULL_HD,target=True)
            texture_type.from_surface.assert_called_once_with(renderer,image)
            self.assertEqual(renderer.present.call_count,3)
            renderer.to_surface.assert_not_called()
            texture_type.from_surface.return_value.update.assert_not_called()
            self.assertEqual(canvas.uploads,1)
            canvas.release()
            self.assertFalse(canvas.gpu)
            self.assertEqual(len(canvas.textures),0)

    def test_native_text_and_sprites_keep_native_sizes(self):
        native=MagicMock()
        canvas=DesignCanvas(native)
        image=pg.Surface((80,114))
        canvas.blit_native(image,(400,620),'midbottom')
        rect=native.blit.call_args.args[1]
        self.assertEqual(rect.size,(80,114))
        self.assertEqual(rect.midbottom,(600,930))

    def test_gpu_rectangles_use_native_integer_edges(self):
        native=MagicMock()
        canvas=DesignCanvas(native)
        draw.rect(canvas,(255,0,0),(2/3,4/3,128,32))
        rect=native.rect.call_args.args[1]
        self.assertEqual(tuple(rect),(1,2,192,48))

    def test_repeated_curved_shapes_reuse_their_raster(self):
        renderer=MagicMock()
        with patch('pygame._sdl2.video.Renderer') as renderer_type, patch('pygame._sdl2.video.Texture'):
            renderer_type.from_window.return_value=renderer
            native=NativeCanvas(window=object())
            canvas=DesignCanvas(native)
            for x in (10,11,12,13):draw.circle(canvas,(255,0,0),(x,30),7)
            self.assertEqual(len(native.primitives),1)
            self.assertEqual(native.uploads,1)
            native.release()


if __name__=='__main__':unittest.main()
