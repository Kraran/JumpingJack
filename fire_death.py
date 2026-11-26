"""Brazier ignition, ground-aware collapse, fire and soot; all atlases preloaded."""
import math
import pygame as pg
from laser_death import LaserDeathSprites,CELL,PIVOT,SMOKE_FRAMES
from hero_death import FRAMES,FIRE_REACTION,FIRE_COLLAPSE,FIRE_EXTINGUISH,smooth
from rendering import pixel

FADE_STEPS=16


def pose_position(death,t):
    if t<FIRE_REACTION:return max(0.,t/FIRE_REACTION*7)
    if death.landed_at is None or t<death.landed_at:return 7.
    return 7+8*min(1.,max(0.,(t-death.landed_at)/FIRE_COLLAPSE))


def extinction(death,t):
    if death.landed_at is None:return 0.
    return max(0.,min(1.,(t-death.landed_at-FIRE_COLLAPSE)/FIRE_EXTINGUISH))


class FireDeathSprites(LaserDeathSprites):
    ASSET='hero-fire-death-v1.png'
    ROWS=(0,330,655,980)

    def __init__(self,assets):
        super().__init__(assets)
        for i in range(SMOKE_FRAMES):
            for j in range(3):
                age=(i/SMOKE_FRAMES+j/3)%1.
                cx=i%8*96+pixel(48+math.sin(age*7+j)*12)
                cy=i//8*96+pixel(78-age*58)
                pg.draw.circle(self.smoke,(255,150,39,round(210*(1-age))),(cx,cy),1)
        self.fading_smoke=[]
        for strength in range(FADE_STEPS):
            smoke=self.smoke.copy()
            smoke.fill((255,255,255,round(255*(1-strength/FADE_STEPS))),special_flags=pg.BLEND_RGBA_MULT)
            self.fading_smoke.append(smoke)
        # One continuous volume, seeded by every part of each authored pose.
        # A coarse field is smoothed once at load time, never during rendering.
        self.envelopes=[pg.Surface((CELL[0]*8,CELL[1]*16),pg.SRCALPHA).convert_alpha() for _ in range(2)]
        for pose in range(16):
            key=round(pose/15*(FRAMES-1))
            cell=self.images[0].subsurface((key%8*CELL[0],key//8*CELL[1],*CELL))
            mask=pg.mask.from_surface(cell,70)
            seed=mask.to_surface(surface=pg.Surface(CELL,pg.SRCALPHA),
                                 setcolor=(255,255,255,255),unsetcolor=(255,255,255,0))
            field=pg.transform.smoothscale(seed,(56,48))
            density=[[field.get_at((x,y)).a/255 for y in range(48)] for x in range(56)]
            for phase in range(8):
                time=phase/8*math.tau;flame=pg.Surface((56,48),pg.SRCALPHA)
                for x in range(56):
                    for y in range(48):
                        heat=density[x][y]
                        # Rising turbulent tongues remain connected to the body.
                        for rise in range(1,15):
                            sx=x+round(math.sin(y*.5+time*2+rise*.4)*rise*.22)
                            sy=y+rise
                            if 0<=sx<56 and sy<48:
                                height=10+4*math.sin(x*.53+time*2)
                                heat=max(heat,density[sx][sy]*max(0.,1-rise/height))
                        if heat<.015:continue
                        noise=(math.sin(x*.67-y*.34+time*2)+math.sin(x*.27+y*.61-time*3)+
                               math.sin(x*1.13+y*.18+time))/3
                        core=max(0.,min(1.,.52+noise*.48))
                        color=(255,round(65+175*core),round(10+95*core**3),
                               round(smooth((heat-(.20+noise*.18))*2.5)*(115+80*core)))
                        flame.set_at((x,y),color)
                flame=pg.transform.smoothscale(flame,CELL)
                index=pose*8+phase;area=(index%8*CELL[0],index//8*CELL[1])
                self.envelopes[0].blit(flame,area)
                self.envelopes[1].blit(pg.transform.flip(flame,True,False),area)
        self.images+=self.envelopes+self.fading_smoke

    def draw(self,canvas,death,hero,x,y,alpha):
        t=death.time(alpha);position=pose_position(death,t)
        index=min(FRAMES-1,int(position/15*(FRAMES-1)));face=death.hero_face
        px,py=canvas.point((x,y));pivot=PIVOT[0] if face>0 else CELL[0]-1-PIVOT[0]
        canvas.native.blit(self.images[0 if face>0 else 1],(px-pivot,py-PIVOT[1]),
                           (index%8*CELL[0],index//8*CELL[1],*CELL))
        fade=extinction(death,t)
        if fade>=1 or t>=death.duration-1e-9:return
        strength=min(FADE_STEPS-1,int(fade*FADE_STEPS))
        ignition=smooth(t/.15);opacity=255*ignition*(1-fade)
        lo=min(14,int(position));blend=position-lo
        phase=t/.48*8;first=int(phase)%8;weight=phase-int(phase)
        atlas=self.envelopes[0 if face>0 else 1]
        for pose,pw in ((lo,1-blend),(lo+1,blend)):
            for frame,fw in ((first,1-weight),((first+1)%8,weight)):
                key=pose*8+frame
                canvas.native.blit_faded(atlas,(px-pivot,py-PIVOT[1]),
                    (key%8*CELL[0],key//8*CELL[1],*CELL),opacity*pw*fw)
        if t>=.25:
            collapse=smooth(max(0.,(position-7)/8))
            for offset in (-20,12):
                cx,cy=canvas.point((x+offset*face,y-30*(1-collapse)))
                smoke=(int(t/1.6*SMOKE_FRAMES)+offset)%SMOKE_FRAMES
                canvas.native.blit(self.fading_smoke[strength],(cx-48,cy-90),
                                   (smoke%8*96,smoke//8*96,96,96))
