"""Screen-space life emblem flight, GPU zoom and a flash masking respawn."""
from dataclasses import dataclass
import pygame as pg
from gpu_render import SCALE,FULL_HD
from lives import life_position
from rendering import pixel

FLASH_AT=.88
REAPPEAR=.94
DURATION=1.28


def smooth(t):
    t=max(0.,min(1.,t))
    return t*t*(3-2*t)


@dataclass
class Resurrection:
    active:bool=False
    elapsed:float=0.
    previous_elapsed:float=0.
    life_index:int=0
    spawned:bool=False

    def begin(self,remaining_lives):
        self.active=True;self.elapsed=self.previous_elapsed=0.
        self.life_index=min(5,max(0,remaining_lives));self.spawned=False

    def update(self,dt):
        self.previous_elapsed=self.elapsed
        self.elapsed=min(DURATION,self.elapsed+dt)
        spawn=not self.spawned and self.elapsed>=REAPPEAR-1e-9
        if spawn:self.spawned=True
        return spawn,self.elapsed>=DURATION-1e-9

    def time(self,alpha):return self.previous_elapsed+(self.elapsed-self.previous_elapsed)*max(0.,min(1.,alpha))


class ResurrectionSprites:
    def __init__(self,symbol,path):
        self.symbol_size=symbol.get_size()
        self.symbol=symbol
        emblem=pg.image.load(str(path)).convert_alpha()
        emblem=emblem.subsurface(emblem.get_bounding_rect(min_alpha=64))
        self.emblem=pg.transform.smoothscale(emblem,(1240,pixel(1240*self.symbol_size[1]/self.symbol_size[0])))
        self.halo=pg.Surface((256,256),pg.SRCALPHA).convert_alpha()
        for radius in range(128,0,-1):
            opacity=round(165*(1-radius/128)**2)
            pg.draw.circle(self.halo,(255,205,86,opacity),(128,128),radius)
        self.images=[self.emblem,self.halo]
        self.flash=pg.Surface(FULL_HD).convert();self.flash.fill((255,250,225))

    def geometry(self,sequence,alpha=1):
        t=sequence.time(alpha);p=smooth(t/FLASH_AT)
        x,y=life_position(sequence.life_index)
        start=(pixel(x*SCALE)+self.symbol_size[0]/2,pixel(y*SCALE)+self.symbol_size[1]/2)
        center=(start[0]+(FULL_HD[0]/2-start[0])*p,start[1]+(FULL_HD[1]/2-start[1])*p)
        width=self.symbol_size[0]*(1240/self.symbol_size[0])**p
        height=width*self.symbol_size[1]/self.symbol_size[0]
        return pg.Rect(pixel(center[0]-width/2),pixel(center[1]-height/2),max(1,pixel(width)),max(1,pixel(height)))

    def draw(self,canvas,sequence,alpha=1):
        if not sequence.active:return
        t=sequence.time(alpha)
        if t<REAPPEAR:
            rect=self.geometry(sequence,alpha)
            extent=pixel(rect.w*1.9)
            halo=pg.Rect(0,0,extent,extent);halo.center=rect.center
            canvas.native.blit(self.halo,halo)
            canvas.native.blit(self.symbol if rect.w<=72 else self.emblem,rect)
        opacity=(255*smooth((t-FLASH_AT)/(REAPPEAR-FLASH_AT)) if t<REAPPEAR else
                 255*(1-smooth((t-REAPPEAR)/(DURATION-REAPPEAR))))
        if opacity>0:
            if canvas.native.gpu:canvas.native.rect((255,250,225,round(opacity)),pg.Rect(0,0,*FULL_HD))
            else:
                self.flash.set_alpha(round(opacity));canvas.native.surface.blit(self.flash,(0,0))
