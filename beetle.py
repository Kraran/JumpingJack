"""Titanium scarab animation, shared GPU atlas and fixed-step flight clock."""
import math
from dataclasses import dataclass
import pygame as pg
from terrain import DuneGround,obstacle_boxes

SPAWNS=((1920,495),(3250,490),(4480,480),(5800,495),(7090,470),(8510,500))
FLIGHT_FPS=48.
TURN_TIME=.16
SHATTER_TIME=.34
DEATH_TIME=.60
CELL=(168,128)
TILTS=tuple(range(-12,13,3))
SIGHT_RANGE=460.
LOSE_RANGE=720.
CHASE_SPEED=300.
CHASE_ACCEL=850.
REARM_TIME=1.5


def position(index,t,spawns=SPAWNS):
    x,y=spawns[index]
    return x+math.sin(t*.75+index)*105,y+math.sin(t*1.9+index)*46


def velocity(index,t,spawns=SPAWNS):
    return math.cos(t*.75+index)*78.75,math.cos(t*1.9+index)*87.4


class BeetleMotion:
    def __init__(self,index,t=0.,spawns=SPAWNS):
        self.index=index
        self.spawns=spawns
        self.facing=1 if velocity(index,t,spawns)[0]>=0 else -1
        self.turn_to=self.facing
        self.turning=False
        self.timer=self.previous_timer=0.
        self.clock=self.previous_clock=index*.071
        self.angle=self.previous_angle=0.
        self.x,self.y=position(index,t,spawns)
        self.px,self.py=self.x,self.y
        self.vx,self.vy=velocity(index,t,spawns)
        self.state='patrol';self.rearm=0.

    def sees(self,hero,platforms=()):
        if self.turning:return False
        dx=hero.x-self.x;dy=hero.y-28-self.y
        if dx*self.facing<=0 or abs(dy)>abs(dx)*1.5 or math.hypot(dx,dy)>SIGHT_RANGE:return False
        start=(self.x,self.y);end=(hero.x,hero.y-28)
        return not any(box.clipline(start,end) for box in obstacle_boxes(platforms,start,end))

    def move(self,dt,platforms):
        # Slide along solid stone instead of flying through platforms or ground.
        for axis in ('x','y'):
            old=getattr(self,axis);delta=getattr(self,'v'+axis)*dt
            if not delta:continue
            start=(self.x,self.y)
            end=(self.x+delta,self.y) if axis=='x' else (self.x,self.y+delta)
            allowed=delta
            for wall in obstacle_boxes(platforms,start,end,(36,28)):
                if wall.collidepoint(start):continue
                if wall.clipline(start,end):
                    edge=(wall.left if delta>0 else wall.right) if axis=='x' else (wall.top if delta>0 else wall.bottom)
                    distance=edge-old-(.01 if delta>0 else -.01)
                    allowed=min(allowed,distance) if delta>0 else max(allowed,distance)
            setattr(self,axis,old+allowed)
            if allowed!=delta:setattr(self,'v'+axis,0.)

    def update(self,dt,t,hero=None,platforms=(),can_attack=True):
        self.px,self.py=self.x,self.y
        self.previous_clock=self.clock;self.clock+=dt
        self.previous_timer=self.timer
        self.previous_angle=self.angle
        self.rearm=max(0.,self.rearm-dt)
        if self.state=='chase':
            if (hero is None or not can_attack
                    or math.hypot(hero.x-self.x,hero.y-28-self.y)>LOSE_RANGE):
                self.state='return';self.rearm=REARM_TIME
        elif (hero is not None and can_attack and self.rearm<=0 and self.sees(hero,platforms)):
            self.state='chase'
        if self.state=='patrol':
            self.x,self.y=position(self.index,t,self.spawns)
            self.vx,self.vy=velocity(self.index,t,self.spawns)
            for platform in platforms:
                if isinstance(platform,DuneGround) and platform.x<=self.x<=platform.x+platform.w:
                    self.y=min(self.y,platform.height_at(self.x)-18)
        else:
            if self.state=='chase':
                dx,dy=hero.x-self.x,hero.y-28-self.y
                distance=math.hypot(dx,dy)
                speed=min(CHASE_SPEED,distance*4)
                desired=(dx/distance*speed,dy/distance*speed) if distance else (0.,0.)
            else:
                hx,hy=position(self.index,t,self.spawns);hvx,hvy=velocity(self.index,t,self.spawns)
                desired=(hvx+(hx-self.x)*2,hvy+(hy-self.y)*2)
                length=math.hypot(*desired)
                if length>230:desired=tuple(v*230/length for v in desired)
            ax,ay=desired[0]-self.vx,desired[1]-self.vy
            change=math.hypot(ax,ay);weight=min(1.,CHASE_ACCEL*dt/change) if change else 1.
            self.vx+=ax*weight;self.vy+=ay*weight
            self.move(dt,platforms)
            if self.state=='return':
                hx,hy=position(self.index,t,self.spawns)
                if math.hypot(self.x-hx,self.y-hy)<.25:
                    self.x,self.y=hx,hy;self.state='patrol'
        vx,vy=self.vx,self.vy
        target=1 if vx>=0 else -1
        if self.turning:
            self.timer+=dt
            if self.timer+1e-9>=TURN_TIME:
                self.facing=self.turn_to;self.turning=False
        elif target!=self.facing and abs(vx)>1:
            self.turn_to=target;self.timer=0.;self.previous_timer=0.;self.turning=True
        self.angle=max(-12.,min(12.,-vy*self.facing*.13))

    def position(self,alpha=1.):
        alpha=max(0.,min(1.,alpha))
        return self.px+(self.x-self.px)*alpha,self.py+(self.y-self.py)*alpha

    def sample(self,alpha=1.):
        alpha=max(0.,min(1.,alpha))
        if self.turning:
            t=self.previous_timer+(self.timer-self.previous_timer)*alpha
            index=min(7,int(t/TURN_TIME*8))
            return ('turn',0,0,index if self.facing<0 else 7-index)
        t=self.previous_clock+(self.clock-self.previous_clock)*alpha
        angle=self.previous_angle+(self.angle-self.previous_angle)*alpha
        tilt=min(TILTS,key=lambda value:abs(value-angle))
        return ('flight',self.facing,tilt,int(t*FLIGHT_FPS+1e-9)%16)


@dataclass
class BeetleDeath:
    x: float
    y: float
    facing: int
    vx: float=0.
    vy: float=0.
    age: float=0.
    previous_age: float=0.

    def update(self,dt):
        self.previous_age=self.age;self.age+=dt
        self.x+=self.vx*.2*dt;self.y+=(self.vy*.2+30*self.age)*dt

    def sample(self,alpha=1.):
        age=self.previous_age+(self.age-self.previous_age)*max(0.,min(1.,alpha))
        return ('death',self.facing,0,min(7,int(age/SHATTER_TIME*8)))

    def explosion_sample(self,alpha=1.):
        age=self.previous_age+(self.age-self.previous_age)*max(0.,min(1.,alpha))
        return ('explosion',0,0,min(15,int(age/DEATH_TIME*16)))


def load_sheet(path,columns,rows,cutoff=8,fading=False):
    sheet=pg.image.load(str(path)).convert_alpha();frames=[]
    if sheet.get_at((0,0)).a>8:raise ValueError(f'{path.name}: fond non transparent')
    for i in range(columns*rows):
        x0,x1=round(i%columns*sheet.get_width()/columns),round((i%columns+1)*sheet.get_width()/columns)
        y0,y1=round(i//columns*sheet.get_height()/rows),round((i//columns+1)*sheet.get_height()/rows)
        frame=pg.transform.smoothscale(sheet.subsurface((x0,y0,x1-x0,y1-y0)),(144,96))
        mask=pg.mask.from_surface(frame,cutoff).to_surface(
            surface=pg.Surface(frame.get_size(),pg.SRCALPHA),
            setcolor=(255,255,255,255),unsetcolor=(255,255,255,0))
        frame.blit(mask,(0,0),special_flags=pg.BLEND_RGBA_MULT)
        if not frame.get_bounding_rect(min_alpha=1 if fading else 32).w and not (fading and i>=columns*rows-2):
            raise ValueError(f'{path.name}: pose vide {i}')
        frames.append(frame)
    return frames


class BeetleSprites:
    def __init__(self,atlas,areas):self.atlas,self.areas=atlas,areas

    @property
    def images(self):return [self.atlas]

    @classmethod
    def load(cls,directory):
        paths=[directory/f'robot-beetle-{name}-v1.png' for name in ('flight','turn','death','explosion')]
        if not all(path.exists() for path in paths):return None
        flight=load_sheet(paths[0],4,4,48);turn=load_sheet(paths[1],2,4,48);death=load_sheet(paths[2],4,2)
        explosion=load_sheet(paths[3],4,4,1,True)
        count=16*2*len(TILTS)+8+8*2+16;columns=12
        atlas=pg.Surface((columns*CELL[0],math.ceil(count/columns)*CELL[1]),pg.SRCALPHA)
        areas={}
        def add(key,image,origin=None):
            index=len(areas);area=pg.Rect(index%columns*CELL[0],index//columns*CELL[1],*CELL)
            cell=pg.Surface(CELL,pg.SRCALPHA)
            center=(CELL[0]//2,CELL[1]//2)
            dest=image.get_rect(center=center) if origin is None else (center[0]-origin[0],center[1]-origin[1])
            cell.blit(image,dest);atlas.blit(cell,area);areas[key]=area
        for facing in (-1,1):
            for angle in TILTS:
                for i,image in enumerate(flight):
                    oriented=image if facing<0 else pg.transform.flip(image,True,False)
                    add(('flight',facing,angle,i),pg.transform.rotozoom(oriented,angle,1.))
        for i,image in enumerate(turn):add(('turn',0,0,i),image)
        for facing in (-1,1):
            for i,image in enumerate(death):
                add(('death',facing,0,i),image if facing<0 else pg.transform.flip(image,True,False))
        for i,image in enumerate(explosion):
            # The authored emission point stays low in each source cell.
            root_y=(.76,.79,.81,.82)[i//4]
            image=pg.transform.smoothscale(image,(120,80))
            add(('explosion',0,0,i),image,(60,round(root_y*80)))
        return cls(atlas,areas)

    def draw(self,canvas,key,x,y):
        root=canvas.point((x,y))
        canvas.native.blit(self.atlas,(root[0]-CELL[0]//2,root[1]-CELL[1]//2),self.areas[key])

    def frame(self,key):return self.atlas.subsurface(self.areas[key])

    def draw_death(self,canvas,death,alpha=1.,cam=0.):
        self.draw(canvas,death.explosion_sample(alpha),death.x-cam,death.y)
        self.draw(canvas,death.sample(alpha),death.x-cam,death.y)

    def death_frame(self,death,alpha=1.):
        """Composite an enlarged preview only; gameplay draws the atlas directly."""
        frame=self.frame(death.explosion_sample(alpha)).copy()
        frame.blit(self.frame(death.sample(alpha)),(0,0))
        return frame
