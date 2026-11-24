"""Single solar checkpoint; fixed-step activation and cached native-HD light atlas."""
import math
import random
import pygame as pg

CHECKPOINT_X=4800.
GROUND_Y=620.
RESPAWN=(CHECKPOINT_X-60,GROUND_Y)
ACTIVATION_TIME=1.2
LOOP_TIME=2.4
ACTIVATION_FRAMES=72
LOOP_FRAMES=48


class Obelisk:
    def __init__(self):
        self.active=False
        self.clock=self.previous_clock=0.

    def update(self,dt,hero):
        self.previous_clock=self.clock
        if self.active:
            self.clock+=dt
            return False
        if hero.grounded and abs(hero.y-GROUND_Y)<2 and abs(hero.x-CHECKPOINT_X)<65:
            self.active=True
            return True
        return False

    def frame(self,alpha=1.):
        if not self.active:return None
        t=self.previous_clock+(self.clock-self.previous_clock)*max(0.,min(1.,alpha))
        if t<ACTIVATION_TIME:
            return min(ACTIVATION_FRAMES-1,int(t/ACTIVATION_TIME*ACTIVATION_FRAMES))
        return ACTIVATION_FRAMES+int(((t-ACTIVATION_TIME)%LOOP_TIME)/LOOP_TIME*LOOP_FRAMES)%LOOP_FRAMES


class ObeliskSprites:
    CELL=(160,256)

    def __init__(self,path):
        source=pg.image.load(str(path)).convert_alpha()
        # Keep the generated pyramidion, pedestal and their fixed common anchor.
        source=source.subsurface((150,65,724,1410))
        self.base=pg.Surface(self.CELL,pg.SRCALPHA).convert_alpha()
        image=pg.transform.smoothscale(source,(108,210))
        self.base.blit(image,(26,32))
        self.atlas=pg.Surface((self.CELL[0]*8,self.CELL[1]*15),pg.SRCALPHA).convert_alpha()
        for index in range(ACTIVATION_FRAMES+LOOP_FRAMES):
            frame=pg.Surface(self.CELL,pg.SRCALPHA)
            if index<ACTIVATION_FRAMES:
                progress=index/(ACTIVATION_FRAMES-1)
                phase=0.
            else:
                progress=1.;phase=(index-ACTIVATION_FRAMES)/LOOP_FRAMES
            self.paint_light(frame,progress,phase,index)
            self.atlas.blit(frame,((index%8)*160,(index//8)*256))
        self.images=[self.base,self.atlas]

    @staticmethod
    def paint_light(frame,progress,phase,seed):
        if progress<=0:return
        rng=random.Random(seed)
        pulse=.86+.14*math.sin(phase*math.tau*2)
        top=round(230-157*min(1.,progress/.86))
        bottom=230
        # Recessed gold column is revealed strictly from the pedestal upwards.
        for width,color in ((22,(255,156,30,18)),(14,(255,172,35,35)),
                            (8,(255,186,46,100)),(4,(255,208,78,225)),
                            (2,(255,249,204,255))):
            col=(*color[:3],round(color[3]*pulse))
            pg.draw.line(frame,col,(80,top),(80,bottom),width)
        # Light follows the bottom plinth and energizes the floating cap last.
        pg.draw.line(frame,(255,200,76,round(150*progress)),(57,231),(103,231),2)
        if progress<1:
            pg.draw.circle(frame,(255,224,126,200),(80,top),3)
        if progress>.86:
            strength=min(1.,(progress-.86)/.14)
            pg.draw.line(frame,(255,210,80,round(220*strength*pulse)),(80,73),(80,69),3)
            pg.draw.circle(frame,(255,190,48,round(40*strength)),(80,69),12)
            pg.draw.circle(frame,(255,240,170,round(245*strength)),(80,69),3)
            # Tiny electric branches flicker along the live channel forever.
            for _ in range(4):
                y=rng.randrange(78,218);side=rng.choice((-1,1))
                points=[(80,y),(80+side*4,y-3),(80+side*7,y+1),(80+side*10,y-5)]
                pg.draw.lines(frame,(255,213,93,round(210*strength)),False,points,1)
                pg.draw.circle(frame,(255,244,187,round(220*strength)),points[-1],1)

    def draw(self,canvas,obelisk,x,y,alpha=1.):
        anchor=canvas.point((x,y))
        destination=self.base.get_rect(midbottom=(anchor[0],anchor[1]+14))
        canvas.native.blit(self.base,destination)
        index=obelisk.frame(alpha)
        if index is not None:
            area=pg.Rect(index%8*160,index//8*256,160,256)
            canvas.native.blit(self.atlas,destination,area)
