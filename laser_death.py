"""Laser scorch, recoil and ground-aware collapse, all poses preloaded."""
from functools import lru_cache
import math
import pygame as pg
from rendering import pixel
from hero_death import FRAMES,LASER_COLLAPSE

CELL=(224,192)
PIVOT=(112,178)
SMOKE_FRAMES=48


def pose_position(death,t):
    if t<.28:return max(0.,t/.28*7)
    if death.landed_at is None or t<death.landed_at:return 7.
    return 7+8*min(1.,max(0.,(t-death.landed_at)/LASER_COLLAPSE))


class LaserDeathSprites:
    ASSET='hero-laser-death-v1.png'
    ROWS=(0,337,675,1020)
    HEIGHT=115
    @classmethod
    @lru_cache(maxsize=6)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        sheet=pg.image.load(str(assets/self.ASSET)).convert_alpha()
        rows=(*self.ROWS,sheet.get_height());poses=[];scale=None
        for i in range(16):
            left,right=round(i%4*sheet.get_width()/4),round((i%4+1)*sheet.get_width()/4)
            cell=sheet.subsurface((left,rows[i//4],right-left,rows[i//4+1]-rows[i//4])).copy()
            mask=pg.mask.from_surface(cell,96).connected_component();bounds=mask.get_bounding_rects()[0]
            if scale is None:scale=self.HEIGHT/bounds.h
            alpha=mask.to_surface(surface=pg.Surface(cell.get_size(),pg.SRCALPHA),
                                  setcolor=(255,255,255,255),unsetcolor=(255,255,255,0))
            cell.blit(alpha,(0,0),special_flags=pg.BLEND_RGBA_MULT)
            image=pg.transform.smoothscale(cell,(round(cell.get_width()*scale),round(cell.get_height()*scale)))
            frame=pg.Surface(CELL,pg.SRCALPHA)
            frame.blit(image,(pixel(PIVOT[0]-cell.get_width()*.52*scale),pixel(PIVOT[1]-(bounds.bottom-1)*scale)))
            poses.append(frame)
        self.images=[pg.Surface((CELL[0]*8,CELL[1]*8),pg.SRCALPHA).convert_alpha() for _ in range(2)]
        for i in range(FRAMES):
            position=i/(FRAMES-1)*15;lo=min(14,int(position));weight=position-lo
            frame=poses[lo].copy();frame.fill((round(255*(1-weight)),)*4,special_flags=pg.BLEND_RGBA_MULT)
            other=poses[lo+1].copy();other.fill((round(255*weight),)*4,special_flags=pg.BLEND_RGBA_MULT)
            frame.blit(other,(0,0),special_flags=pg.BLEND_RGBA_ADD)
            area=pg.Rect(i%8*CELL[0],i//8*CELL[1],*CELL)
            self.images[0].blit(frame,area);self.images[1].blit(pg.transform.flip(frame,True,False),area)
        self.smoke=pg.Surface((96*8,96*6),pg.SRCALPHA).convert_alpha()
        for i in range(SMOKE_FRAMES):
            frame=pg.Surface((96,96),pg.SRCALPHA)
            for j in range(4):
                age=(i/SMOKE_FRAMES+j/4)%1.
                x=48+math.sin(age*5+j)*5;y=80-age*47
                pg.draw.circle(frame,(92,88,85,round(65*math.sin(age*math.pi))),
                               (pixel(x),pixel(y)),pixel(2+age*5))
            pg.draw.circle(frame,(190,63,18,110),(48,80),3)
            self.smoke.blit(frame,(i%8*96,i//8*96))
        self.flare=pg.Surface((32*16,32),pg.SRCALPHA).convert_alpha()
        for i in range(16):
            frame=pg.Surface((32,32),pg.SRCALPHA);fade=1-i/15
            pg.draw.circle(frame,(255,76,20,round(180*fade)),(16,16),6)
            pg.draw.circle(frame,(255,220,132,round(255*fade)),(16,16),2)
            self.flare.blit(frame,(i*32,0))
        self.images += [self.smoke,self.flare]

    def draw(self,canvas,death,hero,x,y,alpha):
        t=death.time(alpha);position=pose_position(death,t)
        index=min(FRAMES-1,int(position/15*(FRAMES-1)))
        face=death.hero_face;px,py=canvas.point((x,y))
        pivot=PIVOT[0] if face>0 else CELL[0]-1-PIVOT[0]
        canvas.native.blit(self.images[0 if face>0 else 1],(px-pivot,py-PIVOT[1]),
                           (index%8*CELL[0],index//8*CELL[1],*CELL))
        collapse=max(0.,(position-7)/8)
        offset_x=max(-10.,min(10.,death.x-death.hero_x))
        offset_y=max(-50.,min(-8.,death.y-death.hero_y))*(1-.7*collapse)
        burn=canvas.point((x+offset_x,y+offset_y))
        if t<.18:
            canvas.native.blit(self.flare,(burn[0]-16,burn[1]-16),(min(15,int(t/.18*16))*32,0,32,32))
        if t>=.12:
            smoke=int(t/1.6*SMOKE_FRAMES)%SMOKE_FRAMES
            canvas.native.blit(self.smoke,(burn[0]-48,burn[1]-80),(smoke%8*96,smoke//8*96,96,96))
