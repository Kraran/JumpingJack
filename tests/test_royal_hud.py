import os
os.environ['SDL_VIDEODRIVER']='dummy'
os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
import pygame as pg
from main import Game,SCALE,ROOT
from rendering import pixel
from localization import CODES
import hud_layout


class RoyalHudTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.g=Game(True)
    @classmethod
    def tearDownClass(cls):cls.g.close()

    def text_rect(self,call):
        txt,pos,*args=call.args
        size=args[0] if args else 20
        color=args[1] if len(args)>1 else (246,236,210)
        serif=args[2] if len(args)>2 else False
        image=self.g.cache_text(txt,size,color,serif);w,h=image.get_size()
        maximum=call.kwargs.get('max_width')
        if maximum is not None and w>maximum*SCALE:
            width=pixel(maximum*SCALE);h=max(1,round(h*width/w));w=width
        x,y=self.g.canvas.point(pos)
        if call.kwargs.get('center',False):x-=w//2;y-=h//2
        return pg.Rect(x,y,w,h)

    def test_all_languages_and_levels_keep_hud_texts_separate(self):
        g=self.g
        for level in (1,2,3,4):
            g.new_game();g.start_level(level);g.state='play';g.hero.x=2000
            g.lives=99;g.score=10**12;g.taken=set(range(len(g.gems)));g.medallions.count=3
            g.energy.reset(0);g.energy.warning=.7;g.extra_life_notice=1.
            for language in CODES:
                with self.subTest(level=level,language=language):
                    g.settings.language=language
                    with patch.object(g,'text',wraps=g.text) as text:g.hud()
                    self.assertNotIn('ÉNERGIE SOLAIRE',[call.args[0] for call in text.call_args_list])
                    self.assertNotIn('ÉCHAP / START',[call.args[0] for call in text.call_args_list])
                    rectangles=[(call.args[0],self.text_rect(call)) for call in text.call_args_list]
                    for i,(label,rect) in enumerate(rectangles):
                        self.assertGreaterEqual(rect.h,13,(language,label,rect))
                        self.assertGreaterEqual(rect.top,8,(language,label,rect))
                        self.assertLessEqual(rect.bottom,pixel(hud_layout.HEIGHT*SCALE)-10,(language,label,rect))
                        for other,box in rectangles[i+1:]:
                            self.assertFalse(rect.colliderect(box),(language,label,other,rect,box))
                        if rect.left<pixel(hud_layout.COLUMN_EDGES[0]*SCALE):
                            self.assertLessEqual(rect.right,pixel(hud_layout.COLUMN_EDGES[0]*SCALE)-10,(language,label,rect))

    def test_header_is_transparent_and_the_life_flight_starts_at_its_new_slot(self):
        g=self.g;g.settings.language='fr';g.new_game()
        self.assertEqual(g.hud_panel.get_size(),(1920,pixel(hud_layout.HEIGHT*SCALE)))
        self.assertTrue(g.hud_panel.get_flags() & pg.SRCALPHA)
        self.assertEqual(g.hud_panel.get_at((1000,100)).a,0)
        self.assertEqual(pg.mask.from_surface(g.hud_panel).count(),0)
        for index in range(6):
            g.resurrection.begin(index)
            rect=g.resurrection_sprites.geometry(g.resurrection)
            self.assertEqual(rect.topleft,g.canvas.point(hud_layout.life_position(index)))
        g.resurrection.active=False

    def test_the_world_remains_visible_between_the_hud_elements(self):
        g=self.g;g.settings.language='fr';g.new_game();g.state='play';g.hero.x=2000
        color=(73,121,182);g.native_canvas.surface.fill(color)
        g.hud()
        for point in ((1000,180),(700,150),(500,160),(1700,155)):
            self.assertEqual(tuple(g.native_canvas.surface.get_at(point))[:3],color,point)
