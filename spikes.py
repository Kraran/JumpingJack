"""Downward bronze teeth: lethal only to an upward head crossing their edge."""
import pygame as pg
from gpu_render import SCALE

SPIKE_DEPTH=26.
SPIKE_PITCH=24.
SPIKED_PLATFORM_X=(5220,6040,6900,8190)


def tooth_spans(width):
    original_count=max(1,int(width/SPIKE_PITCH));pitch=width/original_count
    count=max(1,original_count-1)
    offset=(width-count*pitch)/2
    for index in range(count):
        yield offset+index*pitch+2,offset+(index+1)*pitch-2


def teeth(platform):
    for left,right in tooth_spans(platform.w):yield platform.x+left,platform.x+right


def upward_contact(platform,x,old_top,new_top):
    """Vertical sweep against actual triangular lower edges, not their box.

    Horizontal movement is handled first by the platform solver; entering from
    a side while already above an edge never counts as crossing it from below.
    """
    if new_top>=old_top:return None
    base=platform.y+platform.h;nearest=None
    for left,right in teeth(platform):
        lo,hi=max(left,x-15),min(right,x+15)
        if lo>=hi:continue
        center=(left+right)/2
        point=max(lo,min(hi,center))
        edge=base+SPIKE_DEPTH*(1-abs(point-center)/((right-left)/2))
        if old_top>=edge-.001 and new_top<=edge:
            if nearest is None or edge>nearest:nearest=edge
    return nearest


class SpikeSprites:
    def __init__(self,path,widths):
        source=pg.image.load(str(path)).convert_alpha()
        if source.get_at((0,0)).a>8:raise ValueError(f'{path.name}: fond non transparent')
        bounds=source.get_bounding_rect(min_alpha=32)
        if not bounds.w:raise ValueError(f'{path.name}: pic vide')
        tooth=source.subsurface(bounds);height=round(SPIKE_DEPTH*SCALE)
        self.atlas=pg.Surface((round(max(widths)*SCALE),height*len(widths)),pg.SRCALPHA).convert_alpha()
        self.areas={}
        for row,width in enumerate(widths):
            area=pg.Rect(0,row*height,round(width*SCALE),height)
            for begin,end in tooth_spans(width):
                left=round(begin*SCALE);right=round(end*SCALE)
                image=pg.transform.smoothscale(tooth,(right-left,height))
                self.atlas.blit(image,(left,row*height))
            self.areas[width]=area

    @property
    def images(self):return [self.atlas]

    def draw(self,canvas,platform,cam):
        destination=canvas.rect((platform.x-cam,platform.y+platform.h,platform.w,SPIKE_DEPTH))
        canvas.native.blit(self.atlas,destination,self.areas[platform.w])
