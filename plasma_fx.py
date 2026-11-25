"""Prebaked native-HD solar plasma, streamed from two persistent GPU textures."""
import json
import pygame as pg

FX_FPS=120
FX_FRAMES=76
FX_DURATION=FX_FRAMES/FX_FPS
FRAME_SIZE=(1330,84)
ORIGIN=(146,42)
COLUMNS=3


class PlasmaEffect:
    def __init__(self,sheet):
        self.images=(sheet,pg.transform.flip(sheet,True,False))
        self.alpha_blend=bool(sheet.get_flags() & pg.SRCALPHA)

    @classmethod
    def load(cls,directory):
        colored=directory/'solar-plasma-color-v2.png'
        path=colored if colored.exists() else directory/'solar-plasma.png'
        if not path.exists():return None
        info=json.loads((directory/'solar-plasma.json').read_text(encoding='utf-8'))
        expected={'fps':FX_FPS,'frames':FX_FRAMES,'frame_size':list(FRAME_SIZE),
                  'origin':list(ORIGIN),'columns':COLUMNS}
        if info!=expected:raise ValueError('solar-plasma.json: format incompatible')
        sheet=pg.image.load(str(path))
        sheet=sheet.convert_alpha() if path==colored else sheet.convert()
        rows=(FX_FRAMES+COLUMNS-1)//COLUMNS
        if sheet.get_size()!=(COLUMNS*FRAME_SIZE[0],rows*FRAME_SIZE[1]):
            raise ValueError('solar-plasma.png: dimensions incorrectes')
        return cls(sheet)

    def draw(self,canvas,start,center,end,elapsed,facing):
        frame=min(FX_FRAMES-1,max(0,int(elapsed*FX_FPS+1e-9)))
        width,height=FRAME_SIZE
        area=pg.Rect(frame%COLUMNS*width,frame//COLUMNS*height,width,height)
        muzzle,y=canvas.point((start,center))
        length=abs(canvas.point((end,center))[0]-muzzle)
        visible=min(width,ORIGIN[0]+length+1)
        if facing>0:
            area.w=visible;dest=(muzzle-ORIGIN[0],y-ORIGIN[1])
            image=self.images[0]
        else:
            image=self.images[1]
            area.x=image.get_width()-(area.x+width)
            area.x+=width-visible;area.w=visible
            dest=(muzzle-(visible-1-ORIGIN[0]),y-ORIGIN[1])
        if self.alpha_blend:canvas.native.blit(image,dest,area)
        else:canvas.native.blit_additive(image,dest,area)
