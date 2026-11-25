"""Solar ray timing, world geometry and cached GPU-friendly light primitives."""
import math
import pygame as pg
from gpu_render import draw
from plasma_fx import FX_DURATION

SHOT_TIME=.40
WINDUP=.15
BEAM_END=.30
FIRE_INTERVAL=.64
BEAM_RANGE=700.
BEAM_HEIGHT=24.
MUZZLE_X=34.
MUZZLE_Y=54.
CROUCH_MUZZLE_Y=28.
CROUCH_MUZZLE_X=29.


class SolarRay:
    def __init__(self,effect=None):
        self.effect=effect
        self.reset()

    def reset(self):
        self.elapsed=None
        self.previous_elapsed=0.
        self.cooldown=0.
        self.facing=1
        self.visual_elapsed=None
        self.previous_visual_elapsed=0.
        self.tail_root=None
        self.powered=False
        self.crouched=False

    @property
    def active(self):return self.elapsed is not None

    @property
    def emitting(self):
        return self.powered and self.active and WINDUP<=self.elapsed<BEAM_END

    def update(self,dt,hero,pressed=False,energy=None):
        if self.visual_elapsed is not None:
            self.previous_visual_elapsed=self.visual_elapsed
            self.visual_elapsed+=dt
            if self.visual_elapsed>=FX_DURATION:self.visual_elapsed=None
        self.cooldown=max(0.,self.cooldown-dt)
        if self.cooldown<1e-9:self.cooldown=0.
        blocked=(hero.floating or hero.recovery>0 or hero.drop_elapsed is not None
                 or (self.active and self.crouched and not hero.grounded))
        if blocked:
            self.elapsed=None
            self.visual_elapsed=None;self.tail_root=None
            return False
        if pressed and not self.active and not self.cooldown:
            self.crouched=hero.grounded and getattr(hero,'crouch',0)>=1-1e-9
            self.powered=energy is None or energy.spend_ray()
            self.elapsed=0.;self.facing=hero.face;self.cooldown=FIRE_INTERVAL
            self.visual_elapsed=dt if self.powered else None
            self.previous_visual_elapsed=0.;self.tail_root=None
        if not self.active:return False
        self.previous_elapsed=self.elapsed
        self.elapsed+=dt
        fired=self.powered and self.previous_elapsed<WINDUP<=self.elapsed
        if self.powered and self.previous_elapsed<BEAM_END<=self.elapsed:self.tail_root=(hero.x,hero.y)
        if self.elapsed>=SHOT_TIME-1e-9:self.elapsed=None
        return fired

    def geometry(self,hero,platforms,x=None,y=None):
        x=hero.x if x is None else x
        y=hero.y if y is None else y
        start=x+self.facing*(CROUCH_MUZZLE_X if self.crouched else MUZZLE_X)
        center=y-(CROUCH_MUZZLE_Y if self.crouched else MUZZLE_Y)
        length=BEAM_RANGE
        for p in platforms:
            if hasattr(p,'ray_distance'):
                length=min(length,p.ray_distance(start,center+BEAM_HEIGHT/2,self.facing,length))
                continue
            if p.y>=center+BEAM_HEIGHT/2 or p.y+p.h<=center-BEAM_HEIGHT/2:continue
            if self.facing>0 and p.x+p.w>start:
                length=min(length,max(0.,p.x-start))
            elif self.facing<0 and p.x<start:
                length=min(length,max(0.,start-(p.x+p.w)))
        return start,center,start+self.facing*length

    def bounds(self,hero,platforms):
        start,y,end=self.geometry(hero,platforms)
        if start==end:return pg.Rect(round(start),round(y),0,0)
        return pg.Rect(math.floor(min(start,end)),math.floor(y-BEAM_HEIGHT/2),
                       math.ceil(abs(end-start)),math.ceil(BEAM_HEIGHT))

    def draw(self,canvas,hero,platforms,cam=0.,alpha=1.):
        if not self.powered:return
        alpha=max(0.,min(1.,alpha))
        if self.effect is not None:
            if self.visual_elapsed is None:return
            t=self.previous_visual_elapsed+(self.visual_elapsed-self.previous_visual_elapsed)*alpha
            if self.tail_root is not None:x,y=self.tail_root
            else:
                x=hero.px+(hero.x-hero.px)*alpha
                y=hero.py+(hero.y-hero.py)*alpha
            start,center,end=self.geometry(hero,platforms,x,y)
            self.effect.draw(canvas,start-cam,center,end-cam,t,self.facing)
            return
        if not self.active:return
        t=self.previous_elapsed+(self.elapsed-self.previous_elapsed)*max(0.,min(1.,alpha))
        x=hero.px+(hero.x-hero.px)*alpha
        y=hero.py+(hero.y-hero.py)*alpha
        start,center,end=self.geometry(hero,platforms,x,y)
        start-=cam;end-=cam
        if WINDUP<=t<BEAM_END and start!=end:
            # Horizontal lines map directly to integer native GPU rectangles.
            for color,width in (((192,108,24),24),((255,183,43),14),
                                ((255,231,132),8),((255,255,235),3)):
                draw.line(canvas,color,(start,center),(end,center),width)
            draw.circle(canvas,(255,230,130),(end,center),5)
        if t<BEAM_END:
            radius=4 if t<WINDUP*.65 else (7 if t<WINDUP else 10)
            # Charge follows the approaching hands; full beam starts when joined.
            charge_x=start-self.facing*max(0.,1-t/WINDUP)*18
            draw.circle(canvas,(255,188,48),(charge_x,center),radius)
            draw.circle(canvas,(255,253,210),(charge_x,center),max(2,radius//2))
