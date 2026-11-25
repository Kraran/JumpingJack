"""Rare Fragment of Ra: session inventory, animated reward and four-note chime."""
import math
from array import array
from dataclasses import dataclass,field
import pygame as pg
from crystal import CORE_HEIGHT

POSITION=(6540.,185.)
LEVEL_ID=1
CAPACITY=3
FRAMES=48
PERIOD=2.4
CELL=128
HUD_CELL=48
CORE_SIZE=CORE_HEIGHT*2
NOTES=(523.25,659.25,783.99,1046.5)


@dataclass
class MedallionInventory:
    count:int=0
    claimed_levels:set=field(default_factory=set)

    @property
    def extra_life_ready(self):return self.count==CAPACITY

    def available(self,level_id=LEVEL_ID):return self.count<CAPACITY and level_id not in self.claimed_levels

    def collect(self,level_id=LEVEL_ID):
        if not self.available(level_id):return False
        self.claimed_levels.add(level_id);self.count+=1;return True

    def redeem_extra_life(self):
        if not self.extra_life_ready:return False
        self.count-=CAPACITY
        return True


def position(time,anchor=POSITION):return anchor[0],anchor[1]+math.sin(time*1.8)*2


def touches(hero,time,anchor=POSITION):
    x,y=position(time,anchor)
    return hero.rect.colliderect(pg.Rect(round(x-22),round(y-22),44,44))


def tune(rate,channels):
    duration=.76;data=array('h')
    for index in range(round(rate*duration)):
        t=index/rate;value=0.
        for note,freq in enumerate(NOTES):
            age=t-note*.12
            if 0<=age<.4:
                envelope=min(1.,age/.004)*math.exp(-12*age)
                value+=2100*envelope*(math.sin(math.tau*freq*age)+.25*math.sin(math.tau*freq*2.003*age))
        for _ in range(channels):data.append(max(-32767,min(32767,round(value))))
    return data


class MedallionSprites:
    def __init__(self,path):
        source=pg.image.load(str(path)).convert_alpha()
        if source.get_at((0,0)).a>8:raise ValueError(f'{path.name}: fond non transparent')
        bounds=source.get_bounding_rect(min_alpha=64)
        if not bounds.w:raise ValueError(f'{path.name}: médaillon vide')
        scale=CORE_SIZE/max(bounds.w,bounds.h)
        core=pg.transform.smoothscale(source.subsurface(bounds),(round(bounds.w*scale),round(bounds.h*scale)))
        self.atlas=pg.Surface((CELL*8,CELL*6+HUD_CELL*6),pg.SRCALPHA).convert_alpha()
        self.world=[];self.hud=[]
        for index in range(FRAMES):
            phase=index/FRAMES;pulse=.5+.5*math.sin(math.tau*phase)
            frame=pg.Surface((CELL,CELL),pg.SRCALPHA)
            for radius in range(59,8,-1):
                pg.draw.circle(frame,(255,191,62,round((1-radius/60)**2*(18+18*pulse))),(64,64),radius)
            image=core.copy();light=round(255*(.92+.08*pulse))
            image.fill((light,light,light,255),special_flags=pg.BLEND_RGBA_MULT)
            image=pg.transform.rotozoom(image,math.sin(math.tau*phase)*3,1.)
            frame.blit(image,image.get_rect(center=(64,64)))
            for mote in range(4):
                a=math.tau*(phase+mote/4);x=round(64+math.cos(a)*49);y=round(64+math.sin(a)*43)
                pg.draw.line(frame,(255,232,157,160),(x-2,y),(x+2,y),1)
                pg.draw.line(frame,(255,232,157,160),(x,y-2),(x,y+2),1)
            area=pg.Rect(index%8*CELL,index//8*CELL,CELL,CELL)
            self.atlas.blit(frame,area);self.world.append(area)
            small=pg.transform.smoothscale(frame,(HUD_CELL,HUD_CELL))
            hud=pg.Rect(index%8*HUD_CELL,CELL*6+index//8*HUD_CELL,HUD_CELL,HUD_CELL)
            self.atlas.blit(small,hud);self.hud.append(hud)

    @property
    def images(self):return [self.atlas]

    def draw(self,canvas,x,y,time,hud=False):
        index=min(FRAMES-1,int((time/PERIOD%1)*FRAMES))
        area=(self.hud if hud else self.world)[index];px,py=canvas.point((x,y))
        canvas.native.blit(self.atlas,pg.Rect(px-area.w//2,py-area.h//2,area.w,area.h),area)
