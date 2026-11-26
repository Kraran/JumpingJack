"""River impact, submerged ambush and return to calm, all atlases preloaded."""
import math
from functools import lru_cache
import pygame as pg
from desert_level import RIVER,WATER_Y
from hero_death import FRAMES,smooth
from rendering import pixel

CELL=(288,224)
PIVOT=(192,206)


def water_position(death,hero,t):
    drift=hero.vx*.1*(1-math.exp(-t/.1))
    x=max(RIVER[0]+16,min(RIVER[1]-16,death.hero_x+drift))
    rate=max(5.,min(18.,5+abs(hero.vy)/100))
    y=death.hero_y+(WATER_Y+31-death.hero_y)*(1-math.exp(-rate*t))
    return x,y


class WaterDeathSprites:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        sheet=pg.image.load(str(assets/'hero-water-death-v1.png')).convert_alpha();poses=[]
        for i in range(16):
            x0,x1=round(i%4*sheet.get_width()/4),round((i%4+1)*sheet.get_width()/4)
            y0,y1=round(i//4*sheet.get_height()/4),round((i//4+1)*sheet.get_height()/4)
            cell=sheet.subsurface((x0,y0,x1-x0,y1-y0)).copy()
            mask=pg.mask.from_surface(cell,85);clean=pg.mask.Mask(cell.get_size())
            for component in mask.connected_components(12):clean.draw(component,(0,0))
            bounds=clean.get_bounding_rects();bounds=bounds[0].unionall(bounds)
            alpha=clean.to_surface(surface=pg.Surface(cell.get_size(),pg.SRCALPHA),
                setcolor=(255,255,255,255),unsetcolor=(255,255,255,0))
            cell.blit(alpha,(0,0),special_flags=pg.BLEND_RGBA_MULT)
            scale=.55
            image=pg.transform.smoothscale(cell,(pixel(cell.get_width()*scale),pixel(cell.get_height()*scale)))
            frame=pg.Surface(CELL,pg.SRCALPHA)
            frame.blit(image,(pixel(PIVOT[0]-cell.get_width()*.69*scale),pixel(PIVOT[1]-(bounds.bottom-1)*scale)))
            poses.append(frame)
        self.actors=[pg.Surface((CELL[0]*8,CELL[1]*8),pg.SRCALPHA).convert_alpha() for _ in range(2)]
        for i in range(FRAMES):
            p=i/(FRAMES-1)*15;lo=min(14,int(p));weight=p-lo
            image=poses[lo].copy();other=poses[lo+1].copy()
            image.fill((round(255*(1-weight)),)*4,special_flags=pg.BLEND_RGBA_MULT)
            other.fill((round(255*weight),)*4,special_flags=pg.BLEND_RGBA_MULT)
            image.blit(other,(0,0),special_flags=pg.BLEND_RGBA_ADD)
            area=(i%8*CELL[0],i//8*CELL[1])
            self.actors[0].blit(image,area);self.actors[1].blit(pg.transform.flip(image,True,False),area)
        self.splash=pg.Surface((288*8,128*6),pg.SRCALPHA).convert_alpha()
        self.ripples=pg.Surface((288*8,48*8),pg.SRCALPHA).convert_alpha()
        for i in range(48):
            t=i/47*.8;frame=pg.Surface((288,128),pg.SRCALPHA)
            for j in range(22):
                vx=(j-10.5)*9;vy=-65-(j*37%105)
                x=144+vx*t;y=100+vy*t+160*t*t
                if y<102:
                    fade=max(0.,1-t/.8);color=(188,232,235,round(230*fade))
                    pg.draw.line(frame,color,(pixel(x),pixel(y)),(pixel(x-vx*.018),pixel(y-vy*.018)),2)
            width=18+130*min(1,t/.5)
            pg.draw.ellipse(frame,(177,227,231,round(150*(1-t/.8))),(144-width/2,97,width,6),2)
            self.splash.blit(frame,(i%8*288,i//8*128))
        for i in range(64):
            t=i/63;frame=pg.Surface((288,48),pg.SRCALPHA)
            for j in range(3):
                age=(t+j*.23)%1.;width=22+age*210
                pg.draw.ellipse(frame,(170,220,220,round(120*(1-age)*(1-t))),
                    (144-width/2,24-3-age*8,width,6+age*16),1)
            self.ripples.blit(frame,(i%8*288,i//8*48))
        self.images=[*self.actors,self.splash,self.ripples]

    def draw(self,canvas,death,hero,x,y,alpha,bank):
        t=death.time(alpha)
        if t>=death.duration-1e-9:return
        world_x=hero.px+(hero.x-hero.px)*alpha
        cam=world_x-x;anchor=death.x-cam
        wx,water=canvas.point((anchor,WATER_Y))
        if t<.42:
            pose=bank.clips['fall'][0];image=pose.images[0 if death.hero_face>0 else 1]
            ox,oy=pose.pivot
            if death.hero_face<0:ox=image.get_width()-1-ox
            px,py=canvas.point((x,y));top=py-oy
            height=max(0,min(image.get_height(),water-top))
            if height:canvas.native.blit_faded(image,(px-ox,top),(0,0,image.get_width(),height),255*(1-smooth((t-.26)/.16)))
        if .26<=t<2.4:
            phase=max(0.,min(1.,(t-.35)/1.77));frame=min(FRAMES-1,int(phase*(FRAMES-1)))
            sink=pixel(30*smooth((t-2.05)/.35))
            face=death.hero_face;pivot=PIVOT[0] if face>0 else CELL[0]-1-PIVOT[0]
            height=max(0,min(CELL[1],PIVOT[1]-sink+2))
            opacity=255*smooth((t-.26)/.16)*(1-smooth((t-2.25)/.15))
            canvas.native.blit_faded(self.actors[0 if face>0 else 1],(wx-pivot,water-PIVOT[1]+sink),
                (frame%8*CELL[0],frame//8*CELL[1],CELL[0],height),opacity)
        for start in (0.,.65):
            age=t-start
            if 0<=age<.8:
                frame=min(47,int(age/.8*48))
                canvas.native.blit(self.splash,(wx-144,water-100),(frame%8*288,frame//8*128,288,128))
        ripple=min(63,int(t/death.duration*64))
        canvas.native.blit(self.ripples,(wx-144,water-24),(ripple%8*288,ripple//8*48,288,48))
