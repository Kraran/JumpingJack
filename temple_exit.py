"""The sanctuary ending: turn away, plant each foot, climb into darkness."""
import math
from dataclasses import dataclass
from functools import lru_cache
import pygame as pg
from gpu_render import SCALE
from rendering import pixel

ENTRY_X=14092.
CENTER_X=13860+443/1.5
APPROACH=.45
TURN=.32
STEP_TIME=.55
CLIMB=6*STEP_TIME
DURATION=APPROACH+TURN+CLIMB+.25
FOOT_Y=(620.,607.,593.,580.,567.,555.,545.)
FPS=120


def smooth(value):
    t=max(0.,min(1.,value));return t*t*(3-2*t)


@dataclass
class TempleExit:
    active:bool=False
    elapsed:float=0.
    previous_elapsed:float=0.
    start_x:float=ENTRY_X
    start_y:float=620.

    def can_start(self,hero):
        return hero.x>=ENTRY_X and hero.grounded and abs(hero.y-620)<2

    def begin(self,hero):
        self.active=True;self.elapsed=self.previous_elapsed=0.
        self.start_x=min(hero.x,CENTER_X);self.start_y=hero.y
        hero.face=1;hero.vx=hero.vy=0.;hero.floating=False
        hero.crouch=hero.previous_crouch=0.

    def update(self,dt,hero):
        self.previous_elapsed=self.elapsed;self.elapsed=min(DURATION,self.elapsed+dt)
        hero.px,hero.py=hero.x,hero.y
        if self.elapsed<APPROACH:
            p=smooth(self.elapsed/APPROACH)
            hero.x=self.start_x+(CENTER_X-self.start_x)*p
            hero.y=self.start_y+(620-self.start_y)*p
        else:
            hero.x=CENTER_X
            step=max(0.,min(6.,(self.elapsed-APPROACH-TURN)/STEP_TIME))
            i=min(5,int(step));p=smooth((step-i-.18)/.72)
            hero.y=FOOT_Y[i]+(FOOT_Y[i+1]-FOOT_Y[i])*p
        hero.vx=(hero.x-hero.px)/dt if dt else 0.;hero.vy=0.;hero.grounded=True
        return self.elapsed>=DURATION


class TempleExitSprites:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        def load(name,columns,rows,turn=False):
            sheet=pg.image.load(str(assets/name)).convert_alpha();cells=[];bounds=None
            for i in range(columns*rows):
                x0,x1=round(i%columns*sheet.get_width()/columns),round((i%columns+1)*sheet.get_width()/columns)
                y0,y1=round(i//columns*sheet.get_height()/rows),round((i//columns+1)*sheet.get_height()/rows)
                cell=sheet.subsurface((x0,y0,x1-x0,y1-y0));cells.append(cell)
                rect=cell.get_bounding_rect(min_alpha=64);bounds=rect if bounds is None else bounds.union(rect)
            scale=106/bounds.h;frames=[]
            for i,cell in enumerate(cells):
                floor=cell.get_bounding_rect(min_alpha=64).bottom-1
                root_x=cell.get_width()*(.62-.06*i/(len(cells)-1) if turn else .56)
                image=pg.transform.smoothscale(cell,(round(cell.get_width()*scale),round(cell.get_height()*scale)))
                frame=pg.Surface((140,120),pg.SRCALPHA)
                frame.blit(image,(pixel(70-root_x*scale),pixel(116-floor*scale)))
                frames.append(frame)
            return frames
        turn=load('hero-stairs-turn-v1.png',4,2,True)
        climb=load('hero-stairs-climb-v1.png',6,4)
        self.areas=[];self.pivots=[];frames=[]
        count=math.ceil((TURN+CLIMB+.25)*FPS)+1
        for i in range(count):
            t=i/FPS
            if t<TURN:
                phase=smooth(t/TURN)*(len(turn)-1);index=int(phase)
                a=turn[index];b=turn[min(len(turn)-1,index+1)];weight=phase-index;depth=0.
            else:
                phase=((t-TURN)/(STEP_TIME*2)%1)*len(climb);index=int(phase)
                a=climb[index];b=climb[(index+1)%len(climb)];weight=phase-index
                depth=min(1.,(t-TURN)/CLIMB)
            image=a.copy();other=b.copy()
            image.fill((round(255*(1-weight)),)*4,special_flags=pg.BLEND_RGBA_MULT)
            other.fill((round(255*weight),)*4,special_flags=pg.BLEND_RGBA_MULT)
            image.blit(other,(0,0),special_flags=pg.BLEND_RGBA_ADD)
            scale=1-.30*depth;size=(round(140*scale),round(120*scale))
            image=pg.transform.smoothscale(image,size)
            shade=round(255*(1-.8*depth));opacity=round(255*(1-smooth((depth-.42)/.58)))
            image.fill((shade,shade,shade,opacity),special_flags=pg.BLEND_RGBA_MULT)
            frames.append(image);self.pivots.append((70*scale,116*scale))
        columns=14;self.atlas=pg.Surface((columns*140,math.ceil(len(frames)/columns)*120),pg.SRCALPHA).convert_alpha()
        for i,image in enumerate(frames):
            rect=pg.Rect(i%columns*140,i//columns*120,*image.get_size())
            self.atlas.blit(image,rect);self.areas.append(rect)
        self.images=[self.atlas]

    def draw(self,canvas,ending,hero,camera,alpha):
        elapsed=ending.previous_elapsed+(ending.elapsed-ending.previous_elapsed)*alpha
        index=max(0,min(len(self.areas)-1,round((elapsed-APPROACH)*FPS)))
        x=(hero.px+(hero.x-hero.px)*alpha-camera)*SCALE
        y=(hero.py+(hero.y-hero.py)*alpha)*SCALE;ox,oy=self.pivots[index]
        canvas.native.blit(self.atlas,(pixel(x-ox),pixel(y-oy)),self.areas[index])
