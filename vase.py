"""Solid Egyptian pottery, shattered by the solar ray and kept across lives."""
import math
import random
from functools import lru_cache
import pygame as pg
from gpu_render import SCALE
from rendering import pixel

SPAWNS=((820,620),(4060,620),(7840,620),(11400,620),
        (1370,450),(5800,450),(11240,460))
WIDTH=38
HEIGHT=64
BREAK_TIME=.8
BREAK_FRAMES=40


class Vase:
    ground=True;spiked=False;kind='vase';w=WIDTH;h=HEIGHT
    def __init__(self,index,spawns=SPAWNS):
        self.index=index;self.center,self.floor=spawns[index]
        self.broken=False;self.age=self.previous_age=0.
    @property
    def x(self):return self.center-WIDTH/2
    @property
    def y(self):return self.floor-HEIGHT
    @property
    def rect(self):return pg.Rect(round(self.x),round(self.y),WIDTH,HEIGHT)
    def shatter(self):
        if self.broken:return False
        self.broken=True;self.age=self.previous_age=0.;return True
    def update(self,dt):
        self.previous_age=self.age
        if self.broken:self.age=min(BREAK_TIME,self.age+dt)


class VaseSprites:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)
    def __init__(self,assets):
        image=pg.image.load(str(assets/'egyptian-vase-v1.png')).convert_alpha()
        image=image.subsurface(image.get_bounding_rect(min_alpha=64))
        height=pixel(HEIGHT*SCALE);width=round(image.get_width()*height/image.get_height())
        self.intact=pg.transform.smoothscale(image,(width,height))
        rng=random.Random(924);pieces=[]
        for row in range(3):
            for col in range(3):
                x0,x1=round(col*width/3),round((col+1)*width/3)
                y0,y1=round(row*height/3),round((row+1)*height/3)
                part=self.intact.subsurface((x0,y0,x1-x0,y1-y0)).copy()
                mask=pg.Surface(part.get_size(),pg.SRCALPHA)
                w,h=part.get_size()
                pg.draw.polygon(mask,'white',((2,1),(w-1,3),(w-3,h-2),(1,h-1)))
                part.blit(mask,(0,0),special_flags=pg.BLEND_RGBA_MULT)
                pieces.append((part,(x0+x1)/2-width/2,(y0+y1)/2-height,
                               rng.uniform(-100,100),rng.uniform(-150,-45),rng.uniform(-240,240)))
        dust=[(rng.uniform(-30,30),rng.uniform(-14,0),rng.uniform(-30,30),rng.uniform(7,15)) for _ in range(8)]
        self.atlas=pg.Surface((240*8,180*5),pg.SRCALPHA).convert_alpha()
        for i in range(BREAK_FRAMES):
            phase=i/(BREAK_FRAMES-1);t=phase*BREAK_TIME
            frame=pg.Surface((240,180),pg.SRCALPHA)
            for dx,dy,vx,r in dust:
                pg.draw.circle(frame,(180,145,98,round(75*(1-phase)**2)),
                               (round(120+dx+vx*t),round(157+dy-35*t)),round(r*(1+t)))
            if i==0:frame.blit(self.intact,(120-width//2,168-height))
            else:
                for part,dx,dy,vx,vy,spin in pieces:
                    fragment=pg.transform.rotozoom(part,spin*t,1)
                    bounds=fragment.get_bounding_rect(min_alpha=16)
                    if not bounds.w:continue
                    fragment=fragment.subsurface(bounds)
                    cx=120+dx+vx*t
                    cy=min(168-fragment.get_height()/2,168+dy+vy*t+500*t*t)
                    frame.blit(fragment,fragment.get_rect(center=(round(cx),round(cy))))
            self.atlas.blit(frame,(i%8*240,i//8*180))
        self.images=[self.intact,self.atlas]
    def draw(self,canvas,vase,camera,alpha=1):
        x=pixel((vase.center-camera)*SCALE);y=pixel(vase.floor*SCALE)
        if not vase.broken:
            canvas.native.blit(self.intact,(x-self.intact.get_width()//2,y-self.intact.get_height()))
        else:
            t=vase.previous_age+(vase.age-vase.previous_age)*alpha
            i=min(BREAK_FRAMES-1,round(t/BREAK_TIME*(BREAK_FRAMES-1)))
            canvas.native.blit(self.atlas,(x-120,y-168),(i%8*240,i//8*180,240,180))
