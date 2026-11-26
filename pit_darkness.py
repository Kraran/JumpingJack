"""Preloaded, depth-dependent pit lighting shared by horizontal levels."""
from functools import lru_cache
import pygame as pg
from gpu_render import SCALE,FULL_HD
from rendering import pixel


def pit_regions(platforms,level_id):
    if level_id==4:return ()
    excluded={'temple_ceiling','tower_ceiling','tower_wall'}
    spans=sorted((p.x,p.x+p.w) for p in platforms if p.ground and p.kind not in excluded)
    gaps=[];end=None
    for left,right in spans:
        if end is not None and left>end:gaps.append((end,left))
        end=max(right,end if end is not None else right)
    if level_id==2:
        from desert_level import RIVER
        # The river is water, rather than an empty shaft.
        gaps=[part for a,b in gaps for part in ((a,min(b,RIVER[0])),(max(a,RIVER[1]),b)) if part[1]>part[0]]
    return tuple(gaps)


class PitDarkness:
    @classmethod
    @lru_cache(maxsize=1)
    def load(cls):return cls()

    def __init__(self):
        self.images=[]
        for fade_depth in (95,85,75):
            image=pg.Surface((FULL_HD[0],pixel(100*SCALE)),pg.SRCALPHA).convert_alpha()
            for y in range(image.get_height()):
                depth=y/SCALE
                t=min(1.,depth/fade_depth)
                opacity=round(255*t*t*(3-2*t))
                pg.draw.line(image,(0,0,0,opacity),(0,y),(image.get_width()-1,y))
            self.images.append(image)

    def draw(self,canvas,regions,level_id,camera):
        if level_id not in (1,2,3):return
        image=self.images[level_id-1];top=pixel(620*SCALE)
        for left,right in regions:
            x=max(0,pixel((left-camera)*SCALE));end=min(FULL_HD[0],pixel((right-camera)*SCALE))
            if end>x:canvas.native.blit(image,(x,top),(0,0,end-x,image.get_height()))
