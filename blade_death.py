"""Preloaded sharp-blade recoil, limp collapse and a brief blood trace."""
from functools import lru_cache
import pygame as pg
from rendering import pixel
from hero_death import FRAMES,BLADE_DURATION

CELL=(224,192)
PIVOT=(112,178)
POSE_TIME=1.1


class BladeDeathSprites:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        sheet=pg.image.load(str(assets/'hero-blade-death-v1.png')).convert_alpha()
        rows=(0,313,665,1020,sheet.get_height())
        scale=134/(sheet.get_width()/4);poses=[]
        for i in range(16):
            left,right=round(i%4*sheet.get_width()/4),round((i%4+1)*sheet.get_width()/4)
            cell=sheet.subsurface((left,rows[i//4],right-left,rows[i//4+1]-rows[i//4])).copy()
            mask=pg.mask.from_surface(cell,96).connected_component()
            bounds=mask.get_bounding_rects()[0]
            alpha=mask.to_surface(surface=pg.Surface(cell.get_size(),pg.SRCALPHA),
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
        self.cut=pg.Surface((64*12,64),pg.SRCALPHA).convert_alpha()
        for i in range(12):
            t=i/11;opacity=round(235*(1-t))
            frame=pg.Surface((64,64),pg.SRCALPHA)
            if i<5:pg.draw.line(frame,(135,24,26,opacity),(25,29),(37,35),2)
            for j in range(4):
                x=32+(j-1.5)*13*t;y=32-12*t+34*t*t+j*2
                pg.draw.circle(frame,(145,28,30,opacity),(pixel(x),pixel(y)),1 if j%2 else 2)
            self.cut.blit(frame,(i*64,0))
        self.images.append(self.cut)

    def draw(self,canvas,death,hero,x,y,alpha):
        t=death.time(alpha);index=min(FRAMES-1,int(t/POSE_TIME*(FRAMES-1)))
        face=death.hero_face;px,py=canvas.point((x,y))
        pivot=PIVOT[0] if face>0 else CELL[0]-1-PIVOT[0]
        canvas.native.blit(self.images[0 if face>0 else 1],(px-pivot,py-PIVOT[1]),
                           (index%8*CELL[0],index//8*CELL[1],*CELL))
        if t>=.3:return
        world_x=hero.px+(hero.x-hero.px)*alpha;world_y=hero.py+(hero.y-hero.py)*alpha
        impact=canvas.point((death.x+x-world_x,death.y+y-world_y+5))
        canvas.native.blit(self.cut,(impact[0]-32,impact[1]-32),(min(11,int(t/.3*12))*64,0,64,64))
