"""Bronze Guardian: slow patrol, directional sight and a bounded fast pursuit."""
from dataclasses import dataclass
import statistics
from functools import lru_cache
import pygame as pg
from crocodile import segment_box
from terrain import obstacle_boxes

WALK_SPEED=36.
RUN_SPEED=460.
SIGHT=620.
SIGHT_HEIGHT=150.
ALERT_TIME=.22
TURN_TIME=.24
LOST_TIME=.65
ATTACK_TIME=.48
ATTACK_RANGE=76.
DEATH_TIME=1.
BODY_WIDTH=44.
BODY_HEIGHT=86.
WALK_STRIDE=76.
RUN_STRIDE=132.


@dataclass
class Hoplite:
    spawn_x: float
    patrol_left: float
    patrol_right: float
    floor_left: float
    floor_right: float
    y: float=620.
    initial_facing: int=-1

    def __post_init__(self):self.reset()

    def reset(self):
        self.alive=True
        self.x=self.px=float(self.spawn_x)
        self.facing=self.previous_facing=self.initial_facing
        self.state=self.previous_state='patrol'
        self.timer=self.previous_timer=0.
        self.distance=self.previous_distance=0.
        self.lost=0.
        self.turn_to=self.facing
        self.turn_next='patrol'
        self.death_timer=self.previous_death_timer=0.

    def sees(self,hero,platforms=(),facing=None):
        facing=self.facing if facing is None else facing
        dx=hero.x-self.x
        if dx*facing<0 or abs(dx)>SIGHT:return False
        eye=(self.x,self.y-74)
        target=(hero.x,hero.y-getattr(hero,'body_height',54)*.6)
        if abs(target[1]-eye[1])>SIGHT_HEIGHT:return False
        return not any(box.clipline(eye,target) for box in obstacle_boxes(platforms,eye,target))

    def change(self,state):self.state=state;self.timer=0.

    def turn(self,facing,next_state):
        self.turn_to=facing;self.turn_next=next_state;self.change('turn')

    def move(self,dt,speed,platforms):
        destination=max(self.floor_left+32,min(self.floor_right-32,self.x+self.facing*speed*dt))
        # The patrol's floor bounds handle pits; actual geometry handles walls.
        for p in platforms:
            if p.y>=self.y-1 or p.y+p.h<=self.y-BODY_HEIGHT:continue
            if self.facing>0 and self.x+BODY_WIDTH/2<=p.x<=destination+BODY_WIDTH/2:
                destination=min(destination,p.x-BODY_WIDTH/2)
            elif self.facing<0 and destination-BODY_WIDTH/2<=p.x+p.w<=self.x-BODY_WIDTH/2:
                destination=max(destination,p.x+p.w+BODY_WIDTH/2)
        self.x=destination
        self.distance+=abs(self.x-self.px)
        return abs(self.x-self.px)>1e-8

    def update(self,dt,hero,platforms=(),can_attack=True):
        self.px=self.x;self.previous_facing=self.facing
        self.previous_state=self.state;self.previous_timer=self.timer
        self.previous_distance=self.distance;self.previous_death_timer=self.death_timer
        if not self.alive:
            self.death_timer=min(DEATH_TIME,self.death_timer+dt)
            return None
        self.timer+=dt
        visible=can_attack and self.sees(hero,platforms)
        event=None
        if self.state=='turn':
            if self.timer>=TURN_TIME-1e-9:
                self.facing=self.turn_to
                self.change(self.turn_next)
            return None
        if self.state=='attack':
            if self.timer>=ATTACK_TIME:self.change('chase' if visible else 'return')
            return None
        if self.state=='alert':
            if not visible:self.change('return')
            elif self.timer>=ALERT_TIME:self.change('chase')
            return None
        if visible:
            self.lost=0.
            if self.state not in ('chase',):
                self.change('alert');return 'warning'
        elif self.state=='chase':
            self.lost+=dt
            if self.lost>=LOST_TIME:self.change('return')
        if self.state=='chase':
            direction=1 if hero.x>=self.x else -1
            if direction!=self.facing:self.turn(direction,'chase');return None
            if abs(hero.x-self.x)<=ATTACK_RANGE and abs(hero.y-self.y)<75:
                self.change('attack');return 'attack'
            self.move(dt,RUN_SPEED,platforms)
        elif self.state=='return':
            if self.patrol_left<=self.x<=self.patrol_right:self.change('patrol')
            else:
                direction=1 if self.x<self.patrol_left else -1
                if direction!=self.facing:self.turn(direction,'return')
                elif not self.move(dt,WALK_SPEED,platforms):self.change('patrol')
        elif self.state=='patrol':
            if (self.facing>0 and self.x>=self.patrol_right or self.facing<0 and self.x<=self.patrol_left):
                self.turn(-self.facing,'patrol')
            else:
                old=self.x;self.move(dt,WALK_SPEED,platforms)
                self.x=max(self.patrol_left,min(self.patrol_right,self.x))
                self.distance=self.previous_distance+abs(self.x-old)
                if self.x==old:self.turn(-self.facing,'patrol')
        return event

    def ignite(self):
        if not self.alive:return False
        self.alive=False;self.px=self.x;self.state=self.previous_state='dead'
        self.death_timer=self.previous_death_timer=0.
        return True

    @property
    def hurtbox(self):
        return pg.Rect(round(self.x-BODY_WIDTH/2),round(self.y-BODY_HEIGHT),round(BODY_WIDTH),round(BODY_HEIGHT))

    def hits(self,hero):
        if not self.alive:return False
        # Relative swept body contact stays reliable at high pursuit speed.
        height=max(getattr(hero,'body_height',54),54-22*getattr(hero,'previous_crouch',0))
        half=BODY_WIDTH/2
        bounds=(self.px-half-15,self.y-BODY_HEIGHT,self.px+half+15,self.y+height)
        start=(hero.px,hero.py)
        delta=((hero.x-hero.px)-(self.x-self.px),hero.y-hero.py)
        if segment_box(start,delta,bounds):return True
        if self.state=='attack' and .12<=self.timer<=.30:
            sword=pg.Rect(round(self.x if self.facing>0 else self.x-100),round(self.y-76),100,30)
            return sword.colliderect(hero.rect)
        return False


@dataclass(frozen=True)
class HoplitePose:
    atlas: pg.Surface
    areas: tuple
    pivot: tuple=(108,208)

    def draw(self,canvas,x,y,facing):
        px,py=canvas.point((x,y))
        root_x=self.pivot[0] if facing>0 else 255-self.pivot[0]
        canvas.native.blit(self.atlas,(px-root_x,py-self.pivot[1]),self.areas[0 if facing>0 else 1])


class HopliteSprites:
    """All sixty poses and their mirrors live in one preloaded GPU atlas."""
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,directory):return cls(directory)

    def __init__(self,directory):
        specifications=(('walk',4,4,156),('run',4,4,148),('turn',4,2,156),
                        ('attack',4,2,156),('death',4,3,156))
        self.atlas=pg.Surface((2048,3376),pg.SRCALPHA).convert_alpha()
        self.shadow=pg.Rect(0,3360,66,9)
        pg.draw.ellipse(self.atlas,(68,55,38,110),self.shadow)
        self.clips={};index=0
        for name,columns,rows,height in specifications:
            version=2 if name=='death' else 1
            source=pg.image.load(str(directory/f'hoplite-{name}-v{version}.png')).convert_alpha()
            if source.get_at((0,0)).a>8:raise ValueError(f'Hoplite {name}: transparent background required')
            cells=[];bounds=[]
            for i in range(columns*rows):
                x0,x1=round(i%columns*source.get_width()/columns),round((i%columns+1)*source.get_width()/columns)
                y0,y1=round(i//columns*source.get_height()/rows),round((i//columns+1)*source.get_height()/rows)
                cell=source.subsurface((x0,y0,x1-x0,y1-y0))
                bound=cell.get_bounding_rect(min_alpha=64)
                if not bound.w:raise ValueError(f'Hoplite {name}: empty pose {i}')
                cells.append(cell);bounds.append(bound)
            # One scale and one floor anchor per clip preserve actual gait bob.
            # Never independently crop/resize each frame of a moving character.
            reference=bounds[0].h if name=='death' else statistics.median(b.h for b in bounds)
            scale=height/reference
            baseline=sorted(b.bottom for b in bounds)[min(len(bounds)-1,round((len(bounds)-1)*.9))]
            poses=[]
            for pose_index,cell in enumerate(cells):
                image=pg.transform.smoothscale(cell,(max(1,round(cell.get_width()*scale)),max(1,round(cell.get_height()*scale))))
                frame=pg.Surface((256,224),pg.SRCALPHA).convert_alpha()
                floor=bounds[pose_index].bottom if name=='death' and pose_index>=8 else baseline
                frame.blit(image,(108-round(cell.get_width()*.45*scale),208-round(floor*scale)))
                areas=[]
                for oriented in (frame,pg.transform.flip(frame,True,False)):
                    area=pg.Rect(index%8*256,index//8*224,256,224)
                    self.atlas.blit(oriented,area);areas.append(area);index+=1
                poses.append(HoplitePose(self.atlas,tuple(areas)))
            self.clips[name]=poses

    @property
    def images(self):return [self.atlas]

    def sample(self,enemy,alpha=1):
        alpha=max(0.,min(1.,alpha))
        if not enemy.alive:
            time=enemy.previous_death_timer+(enemy.death_timer-enemy.previous_death_timer)*alpha
            return self.clips['death'][min(11,int(time/DEATH_TIME*12))]
        time=enemy.previous_timer+(enemy.timer-enemy.previous_timer)*alpha if enemy.state==enemy.previous_state else enemy.timer
        if enemy.state=='turn':return self.clips['turn'][min(7,int(time/TURN_TIME*8))]
        if enemy.state=='attack':return self.clips['attack'][min(7,int(time/ATTACK_TIME*8))]
        if enemy.state=='alert' or enemy.state=='chase' and abs(enemy.x-enemy.px)<1e-8:
            return self.clips['attack'][1]
        distance=enemy.previous_distance+(enemy.distance-enemy.previous_distance)*alpha
        running=enemy.state=='chase'
        return self.clips['run' if running else 'walk'][int(distance/(RUN_STRIDE if running else WALK_STRIDE)*16)%16]

    def draw(self,canvas,enemy,camera,alpha=1):
        x=enemy.px+(enemy.x-enemy.px)*alpha-camera
        if -160<x<1440:
            if enemy.alive:
                px,py=canvas.point((x,enemy.y))
                canvas.native.blit(self.atlas,(px-33,py-3),self.shadow)
            self.sample(enemy,alpha).draw(canvas,x,enemy.y,enemy.facing)
