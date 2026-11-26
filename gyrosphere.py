"""Screen-bound antigravity pursuit and a preloaded chrome rotation atlas."""
import heapq
import math
from functools import lru_cache
import pygame as pg
from scorpion import segment_fraction
from terrain import obstacle_boxes

DIAMETER=44
RADIUS=DIAMETER/3  # Native HD diameter converted to world radius.
SPEED=120.
POINTS=200
DEATH_TIME=.6
FRAMES=120
CELL=32


class Gyrosphere:
    def __init__(self,index,spawns):
        self.index=index;self.home=spawns[index];self.reset()

    def reset(self):
        self.x,self.y=self.home;self.px,self.py=self.x,self.y
        self.vx=self.vy=0.;self.phase=self.previous_phase=0.
        self.clock=self.previous_clock=0.;self.facing=1
        self.state='idle';self.alive=True
        self.death_timer=self.previous_death_timer=0.
        self.route=[];self.plan_timer=0.

    @property
    def rect(self):return pg.Rect(round(self.x-RADIUS),round(self.y-RADIUS),math.ceil(RADIUS*2),math.ceil(RADIUS*2))

    def sees(self,hero,camera,camera_x=0.):
        screen=pg.Rect(round(camera_x),round(camera),1280,720)
        return screen.colliderect(self.rect) and screen.colliderect(hero.rect)

    def plan(self,hero,platforms,camera,camera_x=0.):
        """A small local navigation grid keeps pursuit outside solid platforms."""
        y0=math.floor(camera/CELL)*CELL-CELL
        x0=math.floor(camera_x/CELL)*CELL-CELL
        cols,rows=42,25;target=(hero.x,hero.y-hero.body_height/2)
        region=pg.Rect(x0,y0,cols*CELL,rows*CELL)
        walls=[rect.inflate(math.ceil(RADIUS*2+4),math.ceil(RADIUS*2+4))
               for rect in obstacle_boxes(platforms,region.topleft,region.bottomright)
               if region.colliderect(rect)]
        clear=lambda a,b:not any(w.clipline(a,b) for w in walls)
        if clear((self.x,self.y),target):return [target]
        points={(x,y):(x0+(x+.5)*CELL,y0+(y+.5)*CELL) for y in range(rows) for x in range(cols)}
        free={key for key,point in points.items() if not any(w.collidepoint(point) for w in walls)}
        def nearest(point):
            candidates=sorted(free,key=lambda key:math.dist(points[key],point))
            return next((key for key in candidates if clear(point,points[key])),None)
        start=nearest((self.x,self.y));goal=nearest(target)
        if goal is None and free:goal=min(free,key=lambda key:math.dist(points[key],target))
        if start is None or goal is None:return []
        queue=[(0.,start)];cost={start:0.};parent={}
        while queue:
            _,node=heapq.heappop(queue)
            if node==goal:break
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                other=(node[0]+dx,node[1]+dy)
                if other not in free or not clear(points[node],points[other]):continue
                value=cost[node]+math.hypot(dx,dy)
                if value<cost.get(other,math.inf):
                    cost[other]=value;parent[other]=node
                    heapq.heappush(queue,(value+math.dist(other,goal),other))
        if goal not in cost:return []
        path=[goal]
        while path[-1]!=start:path.append(parent[path[-1]])
        route=[points[key] for key in reversed(path)]+[target]
        # Collapse visible segments for smooth steering instead of grid zigzags.
        result=[];origin=(self.x,self.y)
        while route:
            last=next((i for i in range(len(route)-1,-1,-1) if clear(origin,route[i])),0)
            origin=route[last];result.append(origin);route=route[last+1:]
        return result

    def update(self,dt,hero,platforms,camera,camera_x=0.):
        self.px,self.py=self.x,self.y
        self.previous_phase=self.phase;self.previous_clock=self.clock;self.clock+=dt
        self.previous_death_timer=self.death_timer
        if not self.alive:
            self.death_timer=min(DEATH_TIME,self.death_timer+dt);return
        visible=self.sees(hero,camera,camera_x)
        if not visible:
            self.state='idle';self.route=[];self.plan_timer=0.
        else:
            self.state='chase';self.plan_timer-=dt
            if self.plan_timer<=0:
                self.route=self.plan(hero,platforms,camera,camera_x);self.plan_timer=.35
        while self.route and math.dist((self.x,self.y),self.route[0])<7:self.route.pop(0)
        target=self.route[0] if visible and self.route else None
        dx,dy=(target[0]-self.x,target[1]-self.y) if target else (0.,0.)
        distance=math.hypot(dx,dy);speed=min(SPEED,distance*3)
        desired=(dx/distance*speed,dy/distance*speed) if distance else (0.,0.)
        weight=1-math.exp(-dt*4)
        self.vx+=(desired[0]-self.vx)*weight;self.vy+=(desired[1]-self.vy)*weight
        if not visible and math.hypot(self.vx,self.vy)<.005:self.vx=self.vy=0.
        for axis in ('x','y'):
            value=getattr(self,'v'+axis)*dt;start=(self.x,self.y)
            if abs(value)<1e-8:continue
            end=(self.x+value,self.y) if axis=='x' else (self.x,self.y+value)
            collision=False
            for rect in obstacle_boxes(platforms,start,end,(36,28)):
                wall=rect.inflate(0,2)
                if not wall.collidepoint(start) and wall.clipline(start,end):collision=True;break
            if collision:setattr(self,'v'+axis,0.)
            else:setattr(self,axis,getattr(self,axis)+value)
        travel=math.hypot(self.x-self.px,self.y-self.py)
        if travel>1e-7:
            self.facing=1 if (self.vx if abs(self.vx)>abs(self.vy)*.2 else self.vy)>=0 else -1
            self.phase+=travel/(RADIUS*2*math.pi)*self.facing

    def hits(self,hero):
        if not self.alive:return False
        body=hero.rect.inflate(math.ceil(RADIUS*2),math.ceil(RADIUS*2))
        body.x+=round(hero.px-hero.x);body.y+=round(hero.py-hero.y)
        end=(self.x-(hero.x-hero.px),self.y-(hero.y-hero.py))
        return segment_fraction((self.px,self.py),end,body) is not None

    def destroy(self):
        if not self.alive:return False
        self.alive=False;self.state='dead';self.vx=self.vy=0.
        self.death_timer=self.previous_death_timer=0.;self.route=[]
        return True


class GyrosphereSprites:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        self.atlas=pg.image.load(str(assets/'gyrosphere-rotation-v1.png')).convert_alpha()
        self.images=[self.atlas]

    def draw(self,canvas,enemy,alpha,explosions,camera_x=0.):
        x=enemy.px+(enemy.x-enemy.px)*alpha-camera_x;y=enemy.py+(enemy.y-enemy.py)*alpha
        if not enemy.alive:
            age=enemy.previous_death_timer+(enemy.death_timer-enemy.previous_death_timer)*alpha
            if age<DEATH_TIME:explosions.draw(canvas,('explosion',0,0,min(15,int(age/DEATH_TIME*16))),x,y)
            return
        phase=enemy.previous_phase+(enemy.phase-enemy.previous_phase)*alpha
        frame=int(phase%1*FRAMES)%FRAMES;px,py=canvas.point((x,y))
        canvas.native.blit(self.atlas,(px-DIAMETER//2,py-DIAMETER//2),
            (frame%16*DIAMETER,frame//16*DIAMETER,DIAMETER,DIAMETER))
