"""Stable solar shard, pre-baked light pulse and embers in one native-HD atlas."""
import math
import pygame as pg

CELL=72
FRAMES=48
PERIOD=1.6
CORE_HEIGHT=40


def phase(time,index=0):return (time/PERIOD+index*.137)%1.


class SolarCrystals:
    def __init__(self,path):
        source=pg.image.load(str(path)).convert_alpha()
        if source.get_at((0,0)).a>8:raise ValueError(f'{path.name}: fond non transparent')
        bounds=source.get_bounding_rect(min_alpha=64)
        if not bounds.w:raise ValueError(f'{path.name}: cristal vide')
        core=pg.transform.smoothscale(source.subsurface(bounds),(max(1,round(bounds.w*CORE_HEIGHT/bounds.h)),CORE_HEIGHT))
        self.atlas=pg.Surface((CELL*8,CELL*6),pg.SRCALPHA).convert_alpha()
        self.areas=[]
        for index in range(FRAMES):
            t=index/FRAMES;pulse=.5+.5*math.sin(t*math.tau)
            frame=pg.Surface((CELL,CELL),pg.SRCALPHA)
            for radius in range(24,3,-1):
                intensity=round((1-radius/25)**2*(24+18*pulse))
                pg.draw.circle(frame,(255,167,36,intensity),(36,36),radius)
            image=core.copy();brightness=round(255*(.88+.12*pulse))
            image.fill((brightness,brightness,brightness,255),special_flags=pg.BLEND_RGBA_MULT)
            frame.blit(image,image.get_rect(center=(36,36)))
            for mote in range(3):
                age=(t+mote/3)%1.
                x=round(36+math.sin((age+mote*.27)*math.tau)*(16+3*mote))
                y=round(58-44*age);alpha=round(210*math.sin(math.pi*age))
                pg.draw.polygon(frame,(255,218,109,alpha),[(x,y-2),(x+1,y),(x,y+2),(x-1,y)])
            area=pg.Rect(index%8*CELL,index//8*CELL,CELL,CELL)
            self.atlas.blit(frame,area);self.areas.append(area)

    @property
    def images(self):return [self.atlas]

    def sample(self,time,index=0):return min(FRAMES-1,int(phase(time,index)*FRAMES))

    def draw(self,canvas,x,y,time,index=0,bob=True):
        if bob:y+=math.sin(time*2.4+index)*5
        px,py=canvas.point((x,y))
        canvas.native.blit(self.atlas,pg.Rect(px-CELL//2,py-CELL//2,CELL,CELL),
                           self.areas[self.sample(time,index)])
