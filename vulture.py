"""Solar guardian: visible windup, committed dive, curved pull-up and patrol."""
import math
import json
from dataclasses import dataclass
import pygame as pg
from crocodile import segment_box

SPAWNS=((5950.,190.),(7520.,180.),(9000.,205.))
SIGHT=650.
WINDUP=.40
AIM_LOCK_TIME=.12
DIVE_SPEED=780.
DIVE_TIME=1.0
PULLUP_TIME=.65
REARM=3.
TURN_TIME=.20
DEATH_TIME=.8
CELL=(256,256)
DIVE_ANGLES=(15,30,45,60,75,90)


class Vulture:
    def __init__(self,index):
        self.index=index;self.home=SPAWNS[index]
        self.clock=self.previous_clock=index*.173
        self.x,self.y=self.patrol_position();self.px,self.py=self.x,self.y
        self.vx=math.cos(self.clock*.45)*99;self.vy=0.
        self.facing=1 if self.vx>=0 else -1
        self.state='patrol';self.alive=True
        self.timer=self.previous_timer=0.;self.cooldown=0.
        self.turning=False;self.turn_to=self.facing;self.turn=self.previous_turn=0.
        self.target=None;self.dive_angle=45

    def patrol_position(self):
        return self.home[0]+math.sin(self.clock*.45)*220,self.home[1]+math.sin(self.clock*.85)*18

    def sees(self,hero,platforms):
        if self.turning:return False
        dx=hero.x-self.x;dy=hero.y-hero.body_height/2-self.y
        if dx*self.facing<-20 or dy<35 or math.hypot(dx,dy)>SIGHT:return False
        return not any(p.rect.clipline((self.x,self.y),(hero.x,hero.y-hero.body_height/2)) for p in platforms)

    def change(self,state):
        self.state=state;self.timer=self.previous_timer=0.

    def move(self,dt,platforms):
        dx,dy=self.vx*dt,self.vy*dt;length=math.hypot(dx,dy)
        if not length:return False
        fraction=1.;hit=False
        for p in platforms:
            box=p.rect.inflate(52,36)
            if box.collidepoint(self.x,self.y):continue
            crossing=box.clipline((self.x,self.y),(self.x+dx,self.y+dy))
            if crossing:
                entry=crossing[0]
                candidate=max(0.,(math.hypot(entry[0]-self.x,entry[1]-self.y)-1)/length)
                if candidate<fraction:fraction=candidate;hit=True
        self.x+=dx*fraction;self.y+=dy*fraction
        return hit

    def steer(self,target,dt,speed=260.,accel=950.,feed=(0.,0.)):
        dx,dy=target[0]-self.x,target[1]-self.y;distance=math.hypot(dx,dy)
        pace=min(speed,distance*2.5)
        desired=(dx/distance*pace,dy/distance*pace) if distance else (0.,0.)
        desired=(desired[0]+feed[0],desired[1]+feed[1])
        magnitude=math.hypot(*desired)
        if magnitude>speed:desired=tuple(value*speed/magnitude for value in desired)
        ax,ay=desired[0]-self.vx,desired[1]-self.vy;length=math.hypot(ax,ay)
        weight=min(1.,accel*dt/length) if length else 1.
        self.vx+=ax*weight;self.vy+=ay*weight

    def return_target(self,platforms):
        home=self.patrol_position()
        for p in platforms:
            box=p.rect.inflate(52,36)
            if self.y>box.top and box.clipline((self.x,self.y),home):
                if box.left<=self.x<=box.right and self.y>=box.bottom:
                    edge=box.left-12 if abs(self.x-box.left)<abs(self.x-box.right) else box.right+12
                    return edge,self.y
                return self.x,box.top-12
        return home

    def update(self,dt,hero,platforms,can_attack=True):
        self.px,self.py=self.x,self.y
        self.previous_clock=self.clock;self.clock+=dt
        self.previous_timer=self.timer;self.timer+=dt
        self.previous_turn=self.turn
        self.cooldown=max(0.,self.cooldown-dt)
        if not self.alive:
            self.x+=self.vx*.15*dt;self.y+=(25+60*self.timer)*dt
            return
        if self.state=='patrol':
            self.x,self.y=self.patrol_position()
            self.vx=math.cos(self.clock*.45)*99
            self.vy=math.cos(self.clock*.85)*15.3
            if can_attack and self.cooldown<=0 and self.sees(hero,platforms):
                self.target=(hero.x,hero.y-hero.body_height/2)
                self.change('warning')
        elif self.state=='warning':
            self.vx*=math.exp(-10*dt);self.vy*=math.exp(-10*dt)
            self.move(dt,platforms)
            if can_attack and self.timer<WINDUP-AIM_LOCK_TIME and self.sees(hero,platforms):
                self.target=(hero.x,hero.y-hero.body_height/2)
            if not can_attack:
                self.change('return');self.cooldown=REARM
            elif self.timer>=WINDUP-1e-9:
                dx,dy=self.target[0]-self.x,max(40,self.target[1]-self.y)
                distance=math.hypot(dx,dy);self.vx=dx/distance*DIVE_SPEED;self.vy=dy/distance*DIVE_SPEED
                if abs(dx)>1:self.facing=1 if dx>0 else -1
                angle=math.degrees(math.atan2(dy,abs(dx)))
                self.dive_angle=min(DIVE_ANGLES,key=lambda value:abs(value-angle))
                self.change('dive')
        elif self.state=='dive':
            blocked=self.move(dt,platforms)
            passed=(self.target[0]-self.x)*self.vx+(self.target[1]-self.y)*self.vy<=0
            if blocked or passed or self.timer>=DIVE_TIME or not can_attack:
                if blocked:self.vy=min(self.vy,-80.)
                self.change('pullup');self.cooldown=REARM
        elif self.state=='pullup':
            self.steer((self.x+self.facing*160,self.y-240),dt,280,1800)
            if self.move(dt,platforms):self.vx*=.5;self.vy=-80.
            if self.timer>=PULLUP_TIME:self.change('return')
        elif self.state=='return':
            target=self.return_target(platforms)
            feed=(math.cos(self.clock*.45)*99,math.cos(self.clock*.85)*15.3) if target==self.patrol_position() else (0.,0.)
            self.steer(target,dt,feed=feed)
            if self.move(dt,platforms):self.vx*=.5;self.vy=0.
            home=self.patrol_position()
            if math.hypot(self.x-home[0],self.y-home[1])<1:
                self.x,self.y=home;self.change('patrol')
        if self.state in ('patrol','return'):
            facing=1 if self.vx>=0 else -1
            if self.turning:
                self.turn+=dt
                if self.turn>=TURN_TIME:self.facing=self.turn_to;self.turning=False
            elif facing!=self.facing and abs(self.vx)>5:
                self.turning=True;self.turn_to=facing;self.turn=self.previous_turn=0.

    def ignite(self):
        if not self.alive:return False
        self.alive=False;self.change('death');return True

    @property
    def hurtbox(self):return pg.Rect(round(self.x-28),round(self.y-18),56,36)

    def hits(self,hero):
        if not self.alive:return False
        height=max(hero.body_height,round(54-22*hero.previous_crouch))
        start=(hero.px-self.px,hero.py-height/2-self.py)
        end=(hero.x-self.x,hero.y-height/2-self.y)
        return segment_box(start,(end[0]-start[0],end[1]-start[1]),(-43,-18-height/2,43,18+height/2))

    def position(self,alpha=1.):
        alpha=max(0.,min(1.,alpha))
        return self.px+(self.x-self.px)*alpha,self.py+(self.y-self.py)*alpha

    def sample(self,alpha=1.):
        alpha=max(0.,min(1.,alpha));t=self.previous_timer+(self.timer-self.previous_timer)*alpha
        if not self.alive:return ('death',self.facing,0,min(15,int(t/DEATH_TIME*16)))
        if self.state=='warning':return ('warning',self.facing,0,min(7,int(t/WINDUP*8)))
        if self.state=='dive':return ('dive',self.facing,self.dive_angle,int(t*24)%8)
        if self.state=='pullup':return ('pullup',self.facing,0,min(7,int(t/PULLUP_TIME*8)))
        if self.turning:
            turn=self.previous_turn+(self.turn-self.previous_turn)*alpha
            index=min(7,int(turn/TURN_TIME*8))
            return ('turn',0,0,index if self.facing>0 else 7-index)
        clock=self.previous_clock+(self.clock-self.previous_clock)*alpha
        return ('flight',self.facing,0,int(clock*20)%24)


def load_sheet(path,columns,rows,anchor=(.55,.57),flip=False,death=False,pivots=None):
    source=pg.image.load(str(path)).convert_alpha()
    if source.get_at((0,0)).a>8:raise ValueError(f'{path.name}: fond non transparent')
    frames=[]
    for index in range(columns*rows):
        x0,x1=round(index%columns*source.get_width()/columns),round((index%columns+1)*source.get_width()/columns)
        y0,y1=round(index//columns*source.get_height()/rows),round((index//columns+1)*source.get_height()/rows)
        cell=source.subsurface((x0,y0,x1-x0,y1-y0))
        image=pg.transform.smoothscale(cell,(216,144))
        if not image.get_bounding_rect(min_alpha=8).w and index<columns*rows-2:raise ValueError(f'{path.name}: pose vide {index}')
        px,py=round(anchor[0]*216),round(anchor[1]*144)
        # Asset-specific chest pivots avoid confusing cyan eyes with the reactor.
        if pivots is not None:px,py=pivots[index]
        frame=pg.Surface(CELL,pg.SRCALPHA)
        frame.blit(image,(CELL[0]//2-px,CELL[1]//2-py))
        if flip:frame=pg.transform.flip(frame,True,False)
        if death and index>=12:frame.set_alpha(round(255*max(0.,(15-index)/3)))
        frames.append(frame)
    return frames


class VultureSprites:
    def __init__(self,atlas,areas):self.atlas,self.areas=atlas,areas
    @property
    def images(self):return [self.atlas]

    @classmethod
    def load(cls,directory):
        metadata=json.loads((directory/'vulture-animation.json').read_text(encoding='utf-8'))
        flight=load_sheet(directory/'vulture-flight-v2.png',6,4,pivots=metadata['flight_pivots'])
        attack=load_sheet(directory/'vulture-attack-v1.png',6,4,pivots=metadata['attack_pivots'])
        turn=load_sheet(directory/'vulture-turn-v1.png',4,2,pivots=metadata['turn_pivots'])
        death=load_sheet(directory/'vulture-death-v1.png',4,4,anchor=(.5,.55),flip=True,death=True)
        count=(24+8+8+16)*2+8+8*len(DIVE_ANGLES)*2
        columns=16;atlas=pg.Surface((columns*CELL[0],math.ceil(count/columns)*CELL[1]),pg.SRCALPHA).convert_alpha();areas={}
        def add(key,image):
            index=len(areas);area=pg.Rect(index%columns*CELL[0],index//columns*CELL[1],*CELL)
            cell=pg.Surface(CELL,pg.SRCALPHA)
            cell.blit(image,image.get_rect(center=(CELL[0]//2,CELL[1]//2)))
            atlas.blit(cell,area);areas[key]=area
        for face in (-1,1):
            for name,frames in (('flight',flight),('warning',attack[:8]),('pullup',attack[16:]),('death',death)):
                for index,image in enumerate(frames):add((name,face,0,index),image if face>0 else pg.transform.flip(image,True,False))
            for angle in DIVE_ANGLES:
                for index,image in enumerate(attack[8:16]):
                    oriented=pg.transform.rotozoom(image,45-angle,1.)
                    add(('dive',face,angle,index),oriented if face>0 else pg.transform.flip(oriented,True,False))
        for index,image in enumerate(turn):add(('turn',0,0,index),image)
        return cls(atlas,areas)

    def draw(self,canvas,enemy,cam,alpha=1.):
        if not enemy.alive and enemy.timer>=DEATH_TIME:return
        x,y=enemy.position(alpha);point=canvas.point((x-cam,y))
        area=self.areas[enemy.sample(alpha)]
        canvas.native.blit(self.atlas,pg.Rect(0,0,*CELL).move(point[0]-CELL[0]//2,point[1]-CELL[1]//2),area)
