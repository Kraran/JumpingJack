"""Exécuteur: articulated 0–90° laser turret and swept lethal projectiles."""
import math
import random
from dataclasses import dataclass
from functools import lru_cache
import pygame as pg
from gpu_render import SCALE
from rendering import pixel
from terrain import obstacle_boxes

WALK_SPEED=27.
SIGHT=650.
CHARGE=.72
AIM_LOCK=.14
RECOIL=.22
RELOAD=1.5
TURN_TIME=.48
TURN_SETTLE=.04
TURN_FRAMES=49
BOLT_SPEED=660.
BOLT_RADIUS=5.
DEATH_TIME=1.25
DEATH_FRAMES=64
EXPLOSION_SIZE=(432,288)
# Rear bearing centers measured on the 234-pixel body poses, before the
# individual foot pivots are applied. They follow the shell, not the legs.
BODY_SOCKETS=((35.66,19.13),(35.38,18.93),(35.41,19.16),(34.82,18.31),
              (34.88,17.71),(34.67,18.58),(36.16,18.09),(35.72,18.55),
              (35.61,19.07),(35.45,18.84),(35.51,18.89),(35.07,18.83),
              (35.88,19.20),(35.26,20.00),(34.93,19.82),(34.86,19.44),
              (35.53,19.90),(35.60,20.63),(34.99,20.53),(35.14,20.62),
              (35.26,20.76),(35.28,20.77),(35.01,20.69),(34.86,20.67))
SPAWNS=((1500,1320,1580,620,-1),(6400,6120,6800,620,-1),
        (8450,8200,8750,620,1),(10200,9950,10500,620,-1),(13660,13400,13840,620,-1))


def segment_fraction(start,end,rect):
    low,high=0.,1.
    for origin,delta,a,b in ((start[0],end[0]-start[0],rect.left,rect.right),
                             (start[1],end[1]-start[1],rect.top,rect.bottom)):
        if abs(delta)<1e-12:
            if not a<=origin<=b:return None
            continue
        enter,leave=(a-origin)/delta,(b-origin)/delta
        low=max(low,min(enter,leave));high=min(high,max(enter,leave))
        if low>high:return None
    return low


@dataclass
class LaserBolt:
    x:float
    y:float
    vx:float
    vy:float
    age:float=0.
    px:float|None=None
    py:float|None=None
    alive:bool=True

    def __post_init__(self):
        if self.px is None:self.px=self.x
        if self.py is None:self.py=self.y

    def update(self,dt,hero,platforms,can_hit=True):
        if not self.alive:return False
        self.px,self.py=self.x,self.y;self.age+=dt
        start=(self.x,self.y);end=(self.x+self.vx*dt,self.y+self.vy*dt)
        wall=1.1
        for rect in obstacle_boxes(platforms,start,end,(BOLT_RADIUS*2,BOLT_RADIUS*2)):
            fraction=segment_fraction(start,end,rect)
            if fraction is not None:wall=min(wall,fraction)
        hit=None
        if can_hit:
            height=max(hero.body_height,round(54-22*getattr(hero,'previous_crouch',0)))
            body=pg.Rect(round(hero.px-15-BOLT_RADIUS),round(hero.py-height-BOLT_RADIUS),
                         round(30+2*BOLT_RADIUS),round(height+2*BOLT_RADIUS))
            relative=(end[0]-(hero.x-hero.px),end[1]-(hero.y-hero.py))
            hit=segment_fraction(start,relative,body)
        killed=hit is not None and hit<wall
        fraction=hit if killed else min(1.,wall)
        self.x=start[0]+(end[0]-start[0])*fraction;self.y=start[1]+(end[1]-start[1])*fraction
        if killed or wall<=1 or self.age>=2.5:self.alive=False
        return killed


class Scorpion:
    def __init__(self,index,spawns=SPAWNS):
        self.index=index;self.spawn=spawns[index];self.reset()

    def reset(self):
        self.x,self.left,self.right,self.y,self.facing=self.spawn
        self.px=self.x;self.turn_from=self.turn_to=self.facing
        self.state=self.previous_state='patrol';self.alive=True
        self.timer=self.previous_timer=0.;self.clock=self.previous_clock=0.
        self.distance=self.previous_distance=0.;self.angle=self.previous_angle=0.
        self.cooldown=0.;self.death_timer=self.previous_death_timer=0.

    def pivot(self):return self.x+self.facing*16,self.y-52

    def muzzle(self):
        x,y=self.pivot();a=math.radians(self.angle)
        return x+self.facing*math.cos(a)*42,y-math.sin(a)*42

    @property
    def hurtbox(self):return pg.Rect(round(self.x-(62 if self.facing>0 else 88)),round(self.y-44),150,44)

    def sees(self,hero,platforms):
        dx=(hero.x-self.x)*self.facing
        if dx<0 or math.hypot(hero.x-self.x,hero.y-hero.body_height/2-(self.y-52))>SIGHT:return False
        start=self.pivot();end=(hero.x,hero.y-hero.body_height/2)
        return not any(rect.clipline(start,end) for rect in obstacle_boxes(platforms,start,end))

    def change(self,state):self.state=state;self.timer=self.previous_timer=0.

    def update(self,dt,hero,platforms,can_attack=True):
        self.px=self.x;self.previous_clock=self.clock;self.clock+=dt
        self.previous_timer=self.timer;self.timer+=dt;self.previous_state=self.state
        self.previous_angle=self.angle;self.previous_distance=self.distance
        self.previous_death_timer=self.death_timer
        self.cooldown=max(0.,self.cooldown-dt)
        if not self.alive:self.death_timer+=dt;return None
        visible=can_attack and self.sees(hero,platforms)
        if self.state!='turn' and (self.state!='charge' or self.timer<CHARGE-AIM_LOCK):
            x,y=self.pivot();target=max(0.,min(90.,math.degrees(math.atan2(y-(hero.y-hero.body_height/2),max(0.,(hero.x-x)*self.facing))))) if visible else 0.
            self.angle+=max(-240*dt,min(240*dt,target-self.angle))
        if self.state=='patrol':
            if visible and self.cooldown<=0:self.change('charge')
            else:
                self.x=max(self.left,min(self.right,self.x+self.facing*WALK_SPEED*dt))
                self.distance+=abs(self.x-self.px)
                if self.x in (self.left,self.right):
                    self.turn_from=self.facing;self.turn_to=-self.facing;self.change('turn')
        elif self.state=='turn':
            if self.timer>=TURN_TIME:
                self.facing=self.turn_to;self.distance=self.previous_distance=0.
                self.clock=self.previous_clock=0.
                self.angle=self.previous_angle=0.;self.change('patrol')
        elif self.state=='charge':
            if not can_attack or (not visible and self.timer<CHARGE-AIM_LOCK):
                self.cooldown=.4;self.change('patrol')
            elif self.timer>=CHARGE:
                x,y=self.muzzle();a=math.radians(self.angle)
                self.change('recoil');self.cooldown=RELOAD
                return LaserBolt(x,y,self.facing*math.cos(a)*BOLT_SPEED,-math.sin(a)*BOLT_SPEED)
        elif self.state=='recoil' and self.timer>=RECOIL:self.change('patrol')
        return None

    def hits(self,hero):
        if not self.alive:return False
        rect=self.hurtbox.copy();rect.x+=round(self.px-self.x)
        height=max(hero.body_height,round(54-22*getattr(hero,'previous_crouch',0)))
        rect=pg.Rect(rect.left-15,rect.top,rect.w+30,rect.h+height)
        return segment_fraction((hero.px,hero.py),
                                (hero.x-(self.x-self.px),hero.y),rect) is not None

    def ignite(self):
        if not self.alive:return False
        self.alive=False;self.change('dead');self.death_timer=self.previous_death_timer=0.
        return True


class ScorpionSprites:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        sheet=pg.image.load(str(assets/'scorpion-executor-walk-v2.png')).convert_alpha()
        cells=[];bounds=None
        for i in range(24):
            x0,x1=round(i%6*sheet.get_width()/6),round((i%6+1)*sheet.get_width()/6)
            y0,y1=round(i//6*sheet.get_height()/4),round((i//6+1)*sheet.get_height()/4)
            cell=sheet.subsurface((x0,y0,x1-x0,y1-y0));cells.append(cell)
            area=cell.get_bounding_rect(min_alpha=64);bounds=area if bounds is None else bounds.union(area)
        scale=234/bounds.w;size=(234,round(bounds.h*scale));body=[]
        for cell in cells:
            image=pg.transform.smoothscale(cell.subsurface(bounds),size)
            floor=image.get_bounding_rect(min_alpha=64).bottom-1
            body.append((image,(round(234*.43),floor)))
        self.tail_roots=tuple(((sx-pivot[0])/SCALE,(sy-pivot[1])/SCALE)
                              for (sx,sy),(_,pivot) in zip(BODY_SOCKETS,body))
        sheet=pg.image.load(str(assets/'scorpion-executor-parts-v1.png')).convert_alpha();sources=[]
        for i in range(4):
            x0,x1=round(i%2*sheet.get_width()/2),round((i%2+1)*sheet.get_width()/2)
            y0,y1=round(i//2*sheet.get_height()/2),round((i//2+1)*sheet.get_height()/2)
            cell=sheet.subsurface((x0,y0,x1-x0,y1-y0));sources.append(cell.subsurface(cell.get_bounding_rect(min_alpha=64)))
        link=pg.transform.smoothscale(sources[0],(39,15))
        gun=[]
        for source in sources[1:3]:gun.append(pg.transform.smoothscale(source,(78,round(source.get_height()*78/source.get_width()))))
        images={};self.offsets={}
        def add(key,image,pivot):
            if key[0] in ('turn','turn_entry','death') and image.get_bounding_rect(min_alpha=8).w:
                bounds=image.get_bounding_rect(min_alpha=8)
                image=image.subsurface(bounds).copy();pivot=(pivot[0]-bounds.x,pivot[1]-bounds.y)
            images[key]=image;self.offsets[key]=pivot
        for face in (-1,1):
            for i,(image,pivot) in enumerate(body):
                add(('body',face,i),image if face>0 else pg.transform.flip(image,True,False),
                    pivot if face>0 else (image.get_width()-pivot[0],pivot[1]))
        for angle in range(360):
            image=pg.transform.rotozoom(link,angle,1)
            add(('link',angle),image,(image.get_width()/2,image.get_height()/2))
        for angle in range(91):
            a=math.radians(angle)
            for powered,source in enumerate(gun):
                image=pg.transform.rotozoom(source,angle,1)
                offset=(source.get_width()/2-9)
                for face in (-1,1):
                    add(('gun',face,angle,powered),image if face>0 else pg.transform.flip(image,True,False),
                        (image.get_width()/2-face*math.cos(a)*offset,image.get_height()/2+math.sin(a)*offset))
            bolt=pg.Surface((66,28),pg.SRCALPHA)
            for radius in range(13,1,-1):pg.draw.circle(bolt,(255,30,35,round((1-radius/14)*28)),(48,14),radius)
            pg.draw.ellipse(bolt,(255,45,48,180),(4,9,49,10));pg.draw.ellipse(bolt,(255,168,120,255),(40,10,17,8))
            pg.draw.ellipse(bolt,(255,249,210,255),(45,12,12,4))
            image=pg.transform.rotozoom(bolt,angle,1)
            for face in (-1,1):
                add(('bolt',face,angle),image if face>0 else pg.transform.flip(image,True,False),
                    (image.get_width()/2+face*math.cos(a)*15,image.get_height()/2-math.sin(a)*15))
        # Build turn and destruction clips from the same registered rig.
        def stamp(target,key,x,y):
            image=images[key];ox,oy=self.offsets[key];target.blit(image,(pixel(x-ox),pixel(y-oy)))
        def rig(target,face,root,gait=0):
            x,y=root;points=self.tail_points(0,gait)
            for (ax,ay),(bx,by) in zip(points,points[1:]):
                angle=round(math.degrees(math.atan2(-(by-ay),face*(bx-ax))))%360
                stamp(target,('link',angle),x+face*(ax+bx)/2*SCALE,y+(ay+by)/2*SCALE)
            # The shell's rear bearing covers the root of the first link.
            stamp(target,('body',face,gait),x,y)
            stamp(target,('gun',face,0,0),x+face*16*SCALE,y-52*SCALE)
        # Only the coherent right-to-front views are used. Mirror their order
        # for the other half, so the barrel and chassis cannot disagree in yaw.
        sheet=pg.image.load(str(assets/'scorpion-executor-turn-v3.png')).convert_alpha()
        cells=[]
        for i in (0,1,2,3,5):
            x0,x1=round(i*sheet.get_width()/6),round((i+1)*sheet.get_width()/6)
            cell=sheet.subsurface((x0,0,x1-x0,sheet.get_height()//2))
            cells.append(cell.subsurface(cell.get_bounding_rect(min_alpha=64)))
        scale=234/cells[0].get_width();root=(192,235);size=(384,256)
        neutral={}
        for face in (-1,1):
            neutral[face]=pg.Surface(size,pg.SRCALPHA);rig(neutral[face],face,root)
        keys=[(0.,neutral[1])]
        angles=(0,15,30,45,90)
        for source,yaw,phase in zip(cells,angles,(.08,.17,.25,.33,.5)):
            image=pg.transform.smoothscale(source,(round(source.get_width()*scale),round(source.get_height()*scale)))
            pivot=(image.get_width()*(.5-.07*math.cos(math.radians(yaw))),image.get_height()-1)
            frame=pg.Surface(size,pg.SRCALPHA)
            frame.blit(image,(pixel(root[0]-pivot[0]),pixel(root[1]-pivot[1])))
            keys.append((phase,frame))
        # Reuse the exact same anchored poses rather than a separately drawn
        # left half with different proportions and cannon orientations.
        keys.extend((1-phase,pg.transform.flip(frame,True,False)) for phase,frame in reversed(keys[1:-1]))
        keys.append((1.,neutral[-1]))
        def blend(a,b,weight):
            first=a.copy();second=b.copy()
            first.fill((round(255*(1-weight)),)*4,special_flags=pg.BLEND_RGBA_MULT)
            second.fill((round(255*weight),)*4,special_flags=pg.BLEND_RGBA_MULT)
            first.blit(second,(0,0),special_flags=pg.BLEND_RGBA_ADD)
            return first
        for i in range(TURN_FRAMES):
            phase=i/(TURN_FRAMES-1)
            k=next((k for k in range(len(keys)-1) if keys[k+1][0]>=phase),len(keys)-2)
            lo,a=keys[k];hi,b=keys[k+1]
            image=blend(a,b,(phase-lo)/(hi-lo))
            for face in (-1,1):
                pose=image if face>0 else pg.transform.flip(image,True,False)
                if i==0:pose=neutral[face]
                elif i==TURN_FRAMES-1:pose=neutral[-face]
                add(('turn',face,i),pose,root)
        # Preserve each incoming gait as its feet settle into the common pivot.
        for face in (-1,1):
            for gait in range(24):
                entry=neutral[face].copy()
                # Rebuild the same rig with the actual incoming leg pose.
                entry.fill((0,0,0,0));rig(entry,face,root,gait)
                for i in range(5):
                    target=pg.Surface(size,pg.SRCALPHA)
                    stamp(target,('turn',face,4),*root)
                    add(('turn_entry',face,gait,i),blend(entry,target,i/4),root)
        # Use the scarab's authored fire/smoke, at 3.6 times its rendered size.
        # All interpolation, fragment rotation and compositing happen at load.
        from beetle import load_sheet
        fire=[pg.transform.smoothscale(frame,EXPLOSION_SIZE) for frame in
              load_sheet(assets/'robot-beetle-explosion-v1.png',4,4,1,True)]
        rng=random.Random(817)
        chunks=((70,165,55,55),(125,165,50,65),(175,165,55,65),
                (230,165,75,60),(100,205,65,38),(165,205,65,38),
                (115,110,42,34),(155,105,42,32),(210,145,78,30))
        fragments=[(rect,rng.uniform(-140,140),rng.uniform(-250,-110),rng.uniform(-290,290)) for rect in chunks]
        sparks=[(rng.uniform(-45,45),rng.uniform(-240,240),rng.uniform(-290,-90)) for _ in range(20)]
        for face in (-1,1):
            base=pg.Surface((384,256),pg.SRCALPHA);rig(base,face,(192,235))
            pieces=[(base.subsurface(rect).copy(),rect,vx,vy,spin) for rect,vx,vy,spin in fragments]
            for i in range(DEATH_FRAMES):
                t=i/(DEATH_FRAMES-1);seconds=t*DEATH_TIME
                image=pg.Surface((600,480),pg.SRCALPHA);pivot=(300,440)
                # Metal plates, legs, tail links and cannon are thrown outward.
                for piece,(sx,sy,w,h),vx,vy,spin in pieces:
                    rotated=pg.transform.rotozoom(piece,spin*seconds,1)
                    rotated.set_alpha(round(255*max(0.,1-t)**1.5))
                    cx=300+sx+w/2-192+face*vx*seconds
                    cy=440+sy+h/2-235+vy*seconds+180*seconds*seconds
                    image.blit(rotated,rotated.get_rect(center=(round(cx),round(cy))))
                # A short-lived intact shell makes the impact readable.
                if t<.16:
                    wreck=base.copy();wreck.set_alpha(round(255*(1-t/.16)))
                    image.blit(wreck,(108,205))
                phase=min(1.,t/.86)*15;index=min(14,int(phase))
                flame=blend(fire[index],fire[index+1],phase-index)
                root_a=(.76,.79,.81,.82)[index//4]
                root_b=(.76,.79,.81,.82)[(index+1)//4]
                root_y=root_a+(root_b-root_a)*(phase-index)
                flame.set_alpha(round(255*min(1.,(1-t)/.14)))
                image.blit(flame,(84,round(407-root_y*EXPLOSION_SIZE[1])))
                for dx,vx,vy in sparks:
                    px=300+dx+vx*seconds;py=411+vy*seconds+160*seconds*seconds
                    fade=max(0.,1-t/.8)
                    if fade:
                        pg.draw.line(image,(255,round(110+115*fade),60,round(255*fade)),
                                     (round(px),round(py)),(round(px-vx*.018),round(py-(vy+320*seconds)*.018)),2)
                if i==DEATH_FRAMES-1:image.fill((0,0,0,0))
                add(('death',face,i),image,pivot)
        atlas_width=2048;x=y=row=page=0;self.areas={};self.pages={};heights=[]
        for key,image in images.items():
            if x+image.get_width()+2>atlas_width:x=0;y+=row+2;row=0
            if y+image.get_height()>4096:
                heights.append(y+row);page+=1;x=y=row=0
            self.areas[key]=pg.Rect(x,y,*image.get_size());self.pages[key]=page
            x+=image.get_width()+2;row=max(row,image.get_height())
        heights.append(y+row)
        self.images=[pg.Surface((atlas_width,height),pg.SRCALPHA).convert_alpha() for height in heights]
        for key,image in images.items():self.images[self.pages[key]].blit(image,self.areas[key])
        self.atlas=self.images[0]

    def tail_points(self,clock,gait=0):
        wave=math.sin(clock*2)*1.2
        return (self.tail_roots[gait],(-58,-60),(-45,-75),(-24,-78+wave),(-3,-66+wave),(16,-52))

    def stamp(self,canvas,key,x,y):
        ox,oy=self.offsets[key];canvas.native.blit(self.images[self.pages[key]],(pixel(x-ox),pixel(y-oy)),self.areas[key])

    def draw(self,canvas,enemy,camera,alpha=1):
        x=pixel((enemy.px+(enemy.x-enemy.px)*alpha-camera)*SCALE);y=pixel(enemy.y*SCALE)
        t=enemy.previous_timer+(enemy.timer-enemy.previous_timer)*alpha
        face=enemy.facing
        if not enemy.alive:
            death=enemy.previous_death_timer+(enemy.death_timer-enemy.previous_death_timer)*alpha
            if death<DEATH_TIME:self.stamp(canvas,('death',face,min(DEATH_FRAMES-1,int(death/DEATH_TIME*DEATH_FRAMES))),x,y)
            return
        settling=enemy.state=='turn' and t<TURN_SETTLE
        if enemy.state=='turn' and not settling:
            phase=max(0.,min(1.,(t-TURN_SETTLE)/(TURN_TIME-TURN_SETTLE)))
            phase=phase*phase*(3-2*phase)
            index=round(phase*(TURN_FRAMES-1))
            gait=int(enemy.distance/42*24)%24
            key=('turn_entry',enemy.turn_from,gait,index) if index<5 else ('turn',enemy.turn_from,index)
            self.stamp(canvas,key,x,y);return
        distance=enemy.previous_distance+(enemy.distance-enemy.previous_distance)*alpha
        clock=enemy.previous_clock+(enemy.clock-enemy.previous_clock)*alpha
        gait=int(distance/42*24)%24 if enemy.state=='patrol' or settling else 0
        points=self.tail_points(clock,gait)
        if settling:
            weight=max(0.,1-t/TURN_SETTLE)
            points=tuple((ax,ay+(by-ay)*weight) for (ax,ay),(_,by) in zip(self.tail_points(0,gait),points))
        for (ax,ay),(bx,by) in zip(points,points[1:]):
            angle=round(math.degrees(math.atan2(-(by-ay),face*(bx-ax))))%360
            self.stamp(canvas,('link',angle),x+face*(ax+bx)/2*SCALE,y+(ay+by)/2*SCALE)
        self.stamp(canvas,('body',face,gait),x,y)
        angle=max(0,min(90,round(enemy.previous_angle+(enemy.angle-enemy.previous_angle)*alpha)))
        if settling:angle=round(angle*max(0.,1-t/TURN_SETTLE))
        recoil=math.sin(min(1,t/RECOIL)*math.pi)*3 if enemy.state=='recoil' else 0.
        a=math.radians(angle);gx=x+face*16*SCALE-face*math.cos(a)*recoil*SCALE;gy=y-52*SCALE+math.sin(a)*recoil*SCALE
        powered=int(enemy.state=='charge' and t>CHARGE*.25 or enemy.state=='recoil' and t<.1)
        self.stamp(canvas,('gun',face,angle,powered),gx,gy)
        if enemy.state=='recoil' and t<.09:
            self.stamp(canvas,('bolt',face,angle),gx+face*math.cos(a)*42*SCALE,gy-math.sin(a)*42*SCALE)

    def draw_bolt(self,canvas,bolt,camera,alpha=1):
        x=bolt.px+(bolt.x-bolt.px)*alpha;y=bolt.py+(bolt.y-bolt.py)*alpha
        face=1 if bolt.vx>=0 else -1
        angle=max(0,min(90,round(math.degrees(math.atan2(-bolt.vy,abs(bolt.vx))))))
        self.stamp(canvas,('bolt',face,angle),pixel((x-camera)*SCALE),pixel(y*SCALE))
