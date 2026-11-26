"""Prebaked electrocution poses and a cyan arc joining attacker to victim."""
from functools import lru_cache
import math
import random
import pygame as pg
from rendering import pixel
from hero_death import FRAMES

CELL=(224,192)
PIVOT=(112,178)
POSE_TIME=1.12


class BeetleDeathSprites:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        sheet=pg.image.load(str(assets/'hero-beetle-death-v1.png')).convert_alpha()
        # Authored row gutters follow the crouching/lying height, rather than
        # equal cells. Keep a common body scale and align only the floor.
        rows=(0,321,604,897,sheet.get_height());poses=[];scale=None
        for i in range(16):
            left,right=round(i%4*sheet.get_width()/4),round((i%4+1)*sheet.get_width()/4)
            cell=sheet.subsurface((left,rows[i//4],right-left,rows[i//4+1]-rows[i//4])).copy()
            visible=pg.mask.from_surface(cell,64).connected_component()
            actor=visible.copy()
            cyan=pg.mask.from_threshold(cell,(30,225,245,255),(100,100,100,100))
            actor.erase(cyan,(0,0));rects=actor.get_bounding_rects()
            if not rects:raise ValueError('Pose électrique vide')
            bounds=rects[0].unionall(rects[1:])
            if scale is None:scale=115/bounds.h
            alpha=visible.to_surface(surface=pg.Surface(cell.get_size(),pg.SRCALPHA),
                                     setcolor=(255,255,255,255),unsetcolor=(255,255,255,0))
            cell.blit(alpha,(0,0),special_flags=pg.BLEND_RGBA_MULT)
            image=pg.transform.smoothscale(cell,(round(cell.get_width()*scale),round(cell.get_height()*scale)))
            frame=pg.Surface(CELL,pg.SRCALPHA)
            frame.blit(image,(pixel(PIVOT[0]-cell.get_width()*.52*scale),pixel(PIVOT[1]-(bounds.bottom-1)*scale)))
            poses.append(frame)
        self.images=[pg.Surface((CELL[0]*8,CELL[1]*8),pg.SRCALPHA).convert_alpha() for _ in range(2)]
        for i in range(FRAMES):
            p=i/(FRAMES-1)*15;lo=min(14,int(p));weight=p-lo
            frame=poses[lo].copy();frame.fill((round(255*(1-weight)),)*4,special_flags=pg.BLEND_RGBA_MULT)
            other=poses[lo+1].copy();other.fill((round(255*weight),)*4,special_flags=pg.BLEND_RGBA_MULT)
            frame.blit(other,(0,0),special_flags=pg.BLEND_RGBA_ADD)
            area=pg.Rect(i%8*CELL[0],i//8*CELL[1],*CELL)
            self.images[0].blit(frame,area);self.images[1].blit(pg.transform.flip(frame,True,False),area)
        self.arcs=pg.Surface((1024,3072),pg.SRCALPHA).convert_alpha()
        rng=random.Random(9041)
        for variant in range(8):
            points=[(64,64)]+[(64+j*8,64+rng.randint(-7,7)) for j in range(1,6)]+[(112,64)]
            arc=pg.Surface((128,128),pg.SRCALPHA)
            for color,width in (((18,137,203,60),11),((41,220,255,140),5),((208,255,255,255),2)):
                pg.draw.lines(arc,color,False,points,width)
            for angle in range(24):
                image=pg.transform.rotate(arc,-angle*15)
                cell=pg.Surface((128,128),pg.SRCALPHA);cell.blit(image,((128-image.get_width())//2,(128-image.get_height())//2))
                key=angle*8+variant;self.arcs.blit(cell,(key%8*128,key//8*128))
        self.images.append(self.arcs)

    def draw(self,canvas,death,hero,x,y,alpha):
        t=death.time(alpha);index=min(FRAMES-1,int(t/POSE_TIME*(FRAMES-1)))
        face=death.hero_face;px,py=canvas.point((x,y))
        pivot=PIVOT[0] if face>0 else CELL[0]-1-PIVOT[0]
        canvas.native.blit(self.images[0 if face>0 else 1],(px-pivot,py-PIVOT[1]),
                           (index%8*CELL[0],index//8*CELL[1],*CELL))
        if not any(abs(t-center)<.065 for center in (.06,.22,.38)):return
        world_x=hero.px+(hero.x-hero.px)*alpha;world_y=hero.py+(hero.y-hero.py)*alpha
        start=canvas.point((death.x+x-world_x,death.y+y-world_y))
        end=canvas.point((x,y-42))
        dx,dy=end[0]-start[0],end[1]-start[1];length=math.hypot(dx,dy)
        if length<2:return
        angle=round(math.atan2(dy,dx)/math.tau*24)%24
        key=angle*8+int(t*60)%8;size=max(2,pixel(128*length/48))
        canvas.native.blit(self.arcs,pg.Rect(pixel(start[0]-size/2),pixel(start[1]-size/2),size,size),
                           (key%8*128,key//8*128,128,128))
