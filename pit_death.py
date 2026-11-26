"""Brief transition to a looping, preloaded arm-flailing fall."""
import math
from hero_death import FRAMES,smooth
from laser_death import LaserDeathSprites,CELL,PIVOT


def pit_position(death,hero,t):
    return (death.hero_x+hero.vx*.12*(1-math.exp(-t/.12)),
            death.hero_y+hero.vy*t+450*t*t)


class PitDeathSprites(LaserDeathSprites):
    ASSET='hero-pit-death-v1.png'
    ROWS=(0,314,627,941)
    HEIGHT=128

    def draw(self,canvas,death,hero,x,y,alpha,entry):
        t=death.time(alpha)
        if t>=death.duration-1e-9:return
        face=death.hero_face;px,py=canvas.point((x,y))
        opacity=smooth(t/.10)
        if opacity<1:
            image=entry.images[0 if face>0 else 1];ox,oy=entry.pivot
            if face<0:ox=image.get_width()-1-ox
            canvas.native.blit_faded(image,(px-ox,py-oy),image.get_rect(),255*(1-opacity))
        position=t/.14*4 if t<.14 else 4+((t-.14)/.30%1)*12
        if position>15:
            samples=((FRAMES-1,16-position),(round(4/15*(FRAMES-1)),position-15))
        else:
            frame=position/15*(FRAMES-1);lo=int(frame);weight=frame-lo
            samples=((lo,1-weight),(min(FRAMES-1,lo+1),weight))
        pivot=PIVOT[0] if face>0 else CELL[0]-1-PIVOT[0]
        for index,weight in samples:
            canvas.native.blit_faded(self.images[0 if face>0 else 1],(px-pivot,py-PIVOT[1]),
                (index%8*CELL[0],index//8*CELL[1],*CELL),255*opacity*weight)
