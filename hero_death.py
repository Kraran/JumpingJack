"""Hero defeat timelines and preloaded mirrored crocodile animation."""
from dataclasses import dataclass
from functools import lru_cache
import math
import pygame as pg
from rendering import pixel

CAPTURE=.22
DURATION=1.75
FRAMES=64
BEETLE_DURATION=1.2
BEETLE_STUN=.16
BLADE_DURATION=1.2
SWORD_DURATION=1.65
SWORD_IMPACT=.10
SWORD_LAND=.28
SWORD_COLLAPSE=.85
LASER_DURATION=1.4
LASER_IMPACT=.18
LASER_COLLAPSE=.5
LASER_LIMIT=25.
FIRE_DURATION=1.6
FIRE_REACTION=.6
FIRE_COLLAPSE=.6
FIRE_EXTINGUISH=.4
WATER_DURATION=2.6
PIT_DURATION=.75


def smooth(t):
    t=max(0.,min(1.,t))
    return t*t*(3-2*t)


@dataclass
class HeroDeath:
    active:bool=False
    elapsed:float=0.
    previous_elapsed:float=0.
    index:int=0
    x:float=0.
    y:float=620.
    facing:int=1
    source_face:int=1
    hero_x:float=0.
    hero_y:float=620.
    hero_face:int=1
    kind:str='crocodile'
    landed_at:float|None=None

    @property
    def electrical(self):return self.kind in ('beetle','vulture','scorpion','gyrosphere')

    @property
    def duration(self):
        if self.kind=='pit':return PIT_DURATION
        if self.kind=='water':return WATER_DURATION
        if self.kind=='sword':
            return min(LASER_LIMIT,max(SWORD_DURATION,(self.landed_at or 0)+SWORD_COLLAPSE,
                                      self.elapsed+.2 if self.landed_at is None and self.elapsed>=1.5 else 0))
        if self.kind=='fire':
            return min(LASER_LIMIT,max(FIRE_DURATION,(self.landed_at or 0)+FIRE_COLLAPSE+FIRE_EXTINGUISH,
                                      self.elapsed+1. if self.landed_at is None and self.elapsed>=.6 else 0))
        if self.kind=='laser':
            return min(LASER_LIMIT,max(LASER_DURATION,(self.landed_at or 0)+LASER_COLLAPSE,
                                      self.elapsed+.25 if self.landed_at is None and self.elapsed>=1.2 else 0))
        return BLADE_DURATION if self.kind=='blade' else BEETLE_DURATION if self.electrical else DURATION

    def begin(self,index,enemy,hero):
        self.landed_at=None
        self.kind='crocodile'
        self.active=True;self.elapsed=self.previous_elapsed=0.
        self.index=index;self.x=enemy.x;self.y=enemy.y
        self.source_face=enemy.facing
        self.facing=1 if hero.x>=enemy.x else -1
        self.hero_x=hero.x;self.hero_y=hero.y;self.hero_face=hero.face

    def begin_beetle(self,enemy,hero):
        self.begin(enemy.index,enemy,hero)
        self.kind='beetle';self.facing=hero.face

    def begin_vulture(self,enemy,hero):
        self.begin(enemy.index,enemy,hero)
        self.kind='vulture';self.facing=hero.face

    def begin_scorpion(self,enemy,hero):
        self.begin(enemy.index,enemy,hero)
        self.kind='scorpion';self.facing=hero.face
        # The discharge leaves the shell/pincers, rather than the floor pivot.
        self.x=enemy.x+max(-50.,min(50.,hero.x-enemy.x));self.y=enemy.y-24

    def begin_gyrosphere(self,enemy,hero):
        self.begin(enemy.index,enemy,hero)
        self.kind='gyrosphere';self.facing=hero.face

    def begin_blade(self,hero):
        self.landed_at=None
        self.active=True;self.elapsed=self.previous_elapsed=0.
        self.kind='blade';self.index=0
        self.x=hero.x;self.y=hero.y-hero.body_height
        self.hero_x=hero.x;self.hero_y=hero.y
        self.facing=self.source_face=self.hero_face=hero.face

    def begin_sword(self,index,enemy,hero):
        self.begin(index,enemy,hero)
        self.kind='sword'
        self.facing=1 if hero.x>enemy.x else -1 if hero.x<enemy.x else enemy.facing
        self.hero_face=-self.facing
        self.x=hero.x-self.facing*12;self.y=hero.y-min(40,hero.body_height*.65)
        hero.face=self.hero_face
        hero.vx=self.facing*160.;hero.vy=min(60.,max(-90.,hero.vy))
        hero.grounded=False;hero.recovery=0.

    def begin_laser(self,bolt,hero):
        self.active=True;self.elapsed=self.previous_elapsed=0.;self.landed_at=None
        self.kind='laser';self.index=0;self.x=bolt.x;self.y=bolt.y
        self.hero_x=hero.x;self.hero_y=hero.y;self.hero_face=hero.face
        self.facing=self.source_face=1 if bolt.vx>=0 else -1
        length=max(1.,math.hypot(bolt.vx,bolt.vy))
        hero.vx=bolt.vx/length*280.;hero.vy=min(-60.,bolt.vy/length*220.)
        hero.grounded=False;hero.recovery=0.

    def begin_fire(self,source,hero):
        self.active=True;self.elapsed=self.previous_elapsed=0.;self.landed_at=None
        self.kind='fire';self.index=0;self.x,self.y=source
        self.hero_x=hero.x;self.hero_y=hero.y;self.hero_face=hero.face
        self.facing=self.source_face=-1 if hero.x<self.x else 1 if hero.x>self.x else -hero.face
        hero.vx=self.facing*100.;hero.vy=max(0.,hero.vy);hero.recovery=0.

    def begin_water(self,hero):
        from desert_level import RIVER,WATER_Y
        self.active=True;self.elapsed=self.previous_elapsed=0.;self.landed_at=None
        self.kind='water';self.index=0;self.y=float(WATER_Y)
        self.hero_x=hero.x;self.hero_y=max(WATER_Y,min(WATER_Y+35,hero.y))
        self.x=max(RIVER[0]+16,min(RIVER[1]-16,hero.x+hero.vx*.1))
        self.facing=self.source_face=self.hero_face=hero.face

    def begin_pit(self,hero):
        self.active=True;self.elapsed=self.previous_elapsed=0.;self.landed_at=None
        self.kind='pit';self.index=0;self.x=self.hero_x=hero.x;self.y=self.hero_y=hero.y
        self.facing=self.source_face=self.hero_face=hero.face
        hero.vy=max(100.,hero.vy);hero.grounded=False;hero.recovery=0.

    def update(self,dt):
        self.previous_elapsed=self.elapsed
        if self.kind in ('laser','fire','sword'):
            self.elapsed=min(LASER_LIMIT,self.elapsed+dt)
            return False  # Completion follows the corpse's actual landing.
        self.elapsed=min(self.duration,self.elapsed+dt)
        return self.elapsed>=self.duration-1e-9

    def time(self,alpha):
        return self.previous_elapsed+(self.elapsed-self.previous_elapsed)*max(0.,min(1.,alpha))


CrocodileDeath=HeroDeath  # Compatibility with the first crocodile-only revision.


class CrocodileDeathSprites:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        sheet=pg.image.load(str(assets/'hero-crocodile-death-v2.png')).convert_alpha()
        self.size=(480,200);self.pivot=(250,190);frames=[]
        for i in range(16):
            x0,x1=round(i%4*sheet.get_width()/4),round((i%4+1)*sheet.get_width()/4)
            y0,y1=round(i//4*sheet.get_height()/4),round((i//4+1)*sheet.get_height()/4)
            cell=sheet.subsurface((x0,y0,x1-x0,y1-y0)).copy()
            # Extract the connected actors, excluding stray alpha specks in gutters.
            mask=pg.mask.from_surface(cell,96).connected_component()
            bounds=mask.get_bounding_rects()[0]
            alpha=mask.to_surface(surface=pg.Surface(cell.get_size(),pg.SRCALPHA),
                                  setcolor=(255,255,255,255),unsetcolor=(255,255,255,0))
            cell.blit(alpha,(0,0),special_flags=pg.BLEND_RGBA_MULT)
            scale=1.15
            image=pg.transform.smoothscale(cell,(round(cell.get_width()*scale),round(cell.get_height()*scale)))
            frame=pg.Surface(self.size,pg.SRCALPHA)
            frame.blit(image,(pixel(250-cell.get_width()*.57*scale),pixel(190-(bounds.bottom-1)*scale)))
            frames.append(frame)
        self.images=[pg.Surface((3840,1600),pg.SRCALPHA).convert_alpha() for _ in range(2)]
        for i in range(FRAMES):
            position=i/(FRAMES-1)*15;lo=min(14,int(position));weight=position-lo
            image=frames[lo].copy();image.fill((round(255*(1-weight)),)*4,special_flags=pg.BLEND_RGBA_MULT)
            other=frames[lo+1].copy();other.fill((round(255*weight),)*4,special_flags=pg.BLEND_RGBA_MULT)
            image.blit(other,(0,0),special_flags=pg.BLEND_RGBA_ADD)
            rect=pg.Rect(i%8*480,i//8*200,480,200)
            self.images[0].blit(image,rect)
            self.images[1].blit(pg.transform.flip(image,True,False),rect)

    def draw(self,canvas,death,cam,alpha,crocodiles):
        t=death.time(alpha);x=death.x-cam
        if t<CAPTURE:
            if death.facing!=death.source_face:
                pose=crocodiles.turn[min(7,int(t/CAPTURE*8))];face=death.source_face
            else:pose=crocodiles.attack[min(1,int(t/CAPTURE*2))];face=death.facing
            pose.draw(canvas,x,death.y,face)
            return
        frame=min(FRAMES-1,int((t-CAPTURE)/(DURATION-CAPTURE)*FRAMES))
        px,py=canvas.point((x,death.y))
        pivot=self.pivot[0] if death.facing>0 else self.size[0]-1-self.pivot[0]
        canvas.native.blit(self.images[0 if death.facing>0 else 1],(px-pivot,py-self.pivot[1]),
                           (frame%8*480,frame//8*200,480,200))
