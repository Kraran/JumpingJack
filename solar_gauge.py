"""Winged Horus HUD frame and preloaded, masked solar plasma textures."""
from functools import lru_cache
import math
import pygame as pg
from hud_layout import GAUGE as POSITION
from rendering import pixel

FRAMES=96
PERIOD=1.6


class SolarGauge:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        source=pg.image.load(str(assets/'solar-gauge-horus-v1.png')).convert_alpha()
        mask=pg.mask.from_surface(source,96).connected_component()
        bounds=mask.get_bounding_rects()[0]
        clean=mask.to_surface(surface=pg.Surface(source.get_size(),pg.SRCALPHA),
                              setcolor=(255,255,255,255),unsetcolor=(255,255,255,0))
        source.blit(clean,(0,0),special_flags=pg.BLEND_RGBA_MULT)
        self.frame=pg.transform.smoothscale(source.subsurface(bounds),(450,round(bounds.h*450/bounds.w)))
        self.empty_frame=self.frame.copy();self.empty_frame.fill((180,177,170),special_flags=pg.BLEND_RGB_MULT)
        inverse=pg.mask.from_surface(self.frame,96);inverse.invert()
        holes=[]
        for component in inverse.connected_components(100):
            rect=component.get_bounding_rects()[0]
            if rect.left>0 and rect.top>0 and rect.right<self.frame.get_width() and rect.bottom<self.frame.get_height():
                holes.append((rect,component))
        if not holes:raise ValueError('Fenêtre de la jauge solaire introuvable')
        self.window,inside=max(holes,key=lambda item:item[0].w*item[0].h)
        mask_image=inside.to_surface(surface=pg.Surface(self.frame.get_size(),pg.SRCALPHA),
                                    setcolor=(255,255,255,255),unsetcolor=(255,255,255,0)).subsurface(self.window)
        self.well=pg.Surface(self.window.size,pg.SRCALPHA).convert_alpha()
        w,h=self.window.size
        for y in range(h):
            light=round(7*math.sin(math.pi*y/max(1,h-1)))
            pg.draw.line(self.well,(8+light,19+light,29+light,255),(0,y),(w,y))
        self.well.blit(mask_image,(0,0),special_flags=pg.BLEND_RGBA_MULT)
        self.plasma=[];self.edges=[]
        for low in (False,True):
            atlas=pg.Surface((w*8,h*12),pg.SRCALPHA).convert_alpha()
            for frame in range(FRAMES):
                phase=math.tau*frame/FRAMES;image=pg.Surface((w,h),pg.SRCALPHA)
                for x in range(w):
                    nx=x/w
                    ribbons=[h*(.5+.25*math.sin(nx*math.tau*(1.5+j*.6)-phase*(j+1)+j*1.8)) for j in range(3)]
                    for y in range(h):
                        power=min(1.,.12+sum(.48*math.exp(-abs(y-center)/1.4) for center in ribbons))
                        color=((205+round(50*power),36+round(110*power),5+round(28*power)) if low else
                               (170+round(85*power),74+round(158*power),10+round(111*power)))
                        image.set_at((x,y),(*color,mask_image.get_at((x,y)).a))
                atlas.blit(image,(frame%8*w,frame//8*h))
            self.plasma.append(atlas)
            edge=pg.Surface((8,h),pg.SRCALPHA).convert_alpha()
            for x in range(8):
                strength=(x/7)**2
                color=(255,173,60) if low else (255,243,162)
                pg.draw.line(edge,(*color,round(230*strength)),(x,0),(x,h-1))
            self.edges.append(edge)
        self.images=[self.frame,self.empty_frame,self.well,*self.plasma,*self.edges]

    def draw(self,canvas,fraction,time,low=False):
        fraction=max(0.,min(1.,fraction));x,y=canvas.point(POSITION)
        rect=self.window.move(x,y)
        canvas.native.blit(self.well,rect)
        filled=max(0,min(rect.w,pixel(rect.w*fraction)))
        if filled:
            index=int((time%PERIOD)/PERIOD*FRAMES)%FRAMES
            source=pg.Rect(index%8*rect.w,index//8*rect.h,filled,rect.h)
            canvas.native.blit(self.plasma[int(low)],(rect.x,rect.y),source)
            width=min(8,filled)
            canvas.native.blit(self.edges[int(low)],(rect.x+filled-width,rect.y),(8-width,0,width,rect.h))
        # Mark the energy thresholds for one, two and three shots.
        for threshold in (.3,.6,.9):
            mark=rect.x+pixel(rect.w*threshold)
            canvas.native.rect((178,139,63),(mark,rect.bottom-4,1,4))
        canvas.native.blit(self.empty_frame if not filled else self.frame,(x,y))
