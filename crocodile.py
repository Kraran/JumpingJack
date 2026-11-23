"""Nile crocodile: ground patrol, short warning, lethal committed lunge."""
from dataclasses import dataclass
import math
from pathlib import Path
import pygame as pg
from hero_animation import Pose

WALK_SPEED=28.
LUNGE_SPEED=1050.
WARNING=.12
LUNGE_TIME=.24
RECOVERY=.85
TRIGGER_DISTANCE=250.
STRIDE=36.
TURN_TIME=.16


def segment_box(point,delta,bounds):
    """Swept point/AABB collision, including contact at either endpoint."""
    enter,leave=0.,1.
    for origin,speed,low,high in zip(point,delta,bounds[:2],bounds[2:]):
        if abs(speed)<1e-12:
            if origin<low or origin>high:return False
            continue
        a,b=(low-origin)/speed,(high-origin)/speed
        if a>b:a,b=b,a
        enter=max(enter,a);leave=min(leave,b)
        if enter>leave:return False
    return True


@dataclass
class Crocodile:
    spawn_x: float
    patrol_left: float
    patrol_right: float
    floor_left: float
    floor_right: float
    y: float = 620.
    initial_facing: int = -1

    def __post_init__(self):self.reset()

    def reset(self):
        self.x=self.px=float(self.spawn_x)
        self.facing=self.previous_facing=self.initial_facing
        self.state=self.previous_state='patrol'
        self.timer=self.previous_timer=0.
        self.distance=self.previous_distance=0.
        self.turn_to=self.facing
        self.turn_next='patrol'

    def start_turn(self,facing,next_state='patrol'):
        self.turn_to=facing
        self.turn_next=next_state
        self.state='turn';self.timer=0.

    def update(self,dt,hero,can_attack=True):
        self.px=self.x
        self.previous_state=self.state
        self.previous_facing=self.facing
        self.previous_timer=self.timer
        self.previous_distance=self.distance
        self.timer+=dt
        event=None
        if self.state=='patrol':
            near=abs(hero.x-self.x)<=TRIGGER_DISTANCE
            same_height=self.y-80<=hero.y and hero.y-54<=self.y+10
            if can_attack and near and same_height:
                target=1 if hero.x>=self.x else -1
                if target!=self.facing:self.start_turn(target,'warning')
                else:self.state='warning';self.timer=0.;event='warning'
            else:
                target=-1 if self.x>self.patrol_right else (1 if self.x<self.patrol_left else self.facing)
                if target!=self.facing:
                    self.start_turn(target)
                    return event
                self.x+=self.facing*WALK_SPEED*dt
                if self.facing>0 and self.px<=self.patrol_right<=self.x:
                    self.x=self.patrol_right;self.start_turn(-1)
                elif self.facing<0 and self.x<=self.patrol_left<=self.px:
                    self.x=self.patrol_left;self.start_turn(1)
                self.distance+=abs(self.x-self.px)
        elif self.state=='turn':
            if self.timer+1e-9>=TURN_TIME:
                self.facing=self.turn_to
                ready=can_attack and abs(hero.x-self.x)<=TRIGGER_DISTANCE and self.y-80<=hero.y and hero.y-54<=self.y+10
                self.state='warning' if self.turn_next=='warning' and ready else 'patrol'
                self.timer=0.
                if self.state=='warning':event='warning'
        elif self.state=='warning':
            if self.timer>=WARNING:
                self.state='lunge';self.timer=0.;event='lunge'
        elif self.state=='lunge':
            self.x+=self.facing*LUNGE_SPEED*dt
            self.x=max(self.floor_left+108,min(self.floor_right-108,self.x))
            if self.timer>=LUNGE_TIME or self.x==self.px:
                self.state='recover';self.timer=0.
        elif self.state=='recover' and self.timer>=RECOVERY:
            self.state='patrol';self.timer=0.
        return event

    def hits(self,hero):
        # Relative motion catches both a fast lunge and a player crossing the body.
        height=62 if 'lunge' in (self.state,self.previous_state) else 46
        left,right=(-56.,104.) if self.facing>0 else (-104.,56.)
        if self.state=='turn':
            orientation=self.facing*math.cos(math.pi*min(1,self.timer/TURN_TIME))
            left=-56.-48*max(0,-orientation)
            right=56.+48*max(0,orientation)
        bounds=(self.px+left-30,self.y-height-54,self.px+right,self.y)
        start=(hero.px-15,hero.py-54)
        delta=((hero.x-hero.px)-(self.x-self.px),hero.y-hero.py)
        return segment_box(start,delta,bounds)


def create_crocodiles():
    return [Crocodile(1000,820,1100,0,1220),
            Crocodile(3240,3000,3400,2550,3570),
            Crocodile(7050,6740,7340,6400,7540)]


class CrocodileSprites:
    def __init__(self,walk,attack,turn):self.walk,self.attack,self.turn=walk,attack,turn

    @property
    def images(self):return [image for pose in self.walk+self.attack+self.turn for image in pose.images]

    @classmethod
    def load(cls,directory: Path):
        paths=[directory/'crocodile-walk.png',directory/'crocodile-attack.png',directory/'crocodile-turn.png']
        if not all(path.exists() for path in paths):return None
        clips=[]
        for path,columns,rows in [(paths[0],4,4),(paths[1],2,4),(paths[2],2,4)]:
            sheet=pg.image.load(str(path)).convert_alpha()
            if sheet.get_at((0,0)).a>8:raise ValueError(f'{path.name}: fond non transparent')
            poses=[]
            for i in range(columns*rows):
                c,r=i%columns,i//columns
                x0,x1=round(c*sheet.get_width()/columns),round((c+1)*sheet.get_width()/columns)
                y0,y1=round(r*sheet.get_height()/rows),round((r+1)*sheet.get_height()/rows)
                cell=sheet.subsurface((x0,y0,x1-x0,y1-y0))
                bounds=cell.get_bounding_rect(min_alpha=32)
                if not bounds.w:raise ValueError(f'{path.name}: pose vide {i}')
                image=pg.transform.smoothscale(cell,(384,128))
                foot=round(bounds.bottom/cell.get_height()*128)
                pivot_x=round((.57,.563,.544,.516,.484,.456,.437,.43)[i]*384) if path==paths[2] else 219
                poses.append(Pose((image,pg.transform.flip(image,True,False)),(pivot_x,foot)))
            clips.append(poses)
        return cls(*clips)

    def sample(self,enemy,alpha):
        t=enemy.timer
        if enemy.state==enemy.previous_state:
            t=enemy.previous_timer+(enemy.timer-enemy.previous_timer)*alpha
        if enemy.state=='patrol':
            distance=enemy.previous_distance+(enemy.distance-enemy.previous_distance)*alpha
            return self.walk[int(distance/STRIDE*len(self.walk)+1e-9)%len(self.walk)]
        if enemy.state=='turn':return self.turn[min(len(self.turn)-1,int(t/TURN_TIME*len(self.turn)))]
        if enemy.state=='warning':return self.attack[min(1,int(t/WARNING*2))]
        if enemy.state=='lunge':return self.attack[2+min(3,int(t/LUNGE_TIME*4))]
        return self.attack[6 if t<.12 else 7]
