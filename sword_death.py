"""Dedicated sword-hit recoil and grounded collapse, prepared for native GPU draw."""
from functools import lru_cache
import pygame as pg
from hero_death import FRAMES,SWORD_LAND,SWORD_COLLAPSE
from rendering import pixel

CELL=(256,192)
PIVOT=(128,178)


def pose_index(death,alpha=1):
    t=death.time(alpha)
    if t<SWORD_LAND:
        pose=min(6.,t/SWORD_LAND*6)
    elif death.landed_at is None:
        pose=6.
    else:
        pose=6+9*min(1.,max(0.,(t-max(SWORD_LAND,death.landed_at))/SWORD_COLLAPSE))
    return min(FRAMES-1,round(pose/15*(FRAMES-1)))


class SwordDeathSprites:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        sheet=pg.image.load(str(assets/'hero-sword-death-v1.png')).convert_alpha()
        if sheet.get_at((0,0)).a>8:raise ValueError('Sword death: transparent background required')
        # Authored row gutters follow the shrinking silhouette, not equal quarters.
        rows=(0,370,716,1028,sheet.get_height())
        first=sheet.subsurface((0,0,round(sheet.get_width()/4),rows[1]))
        scale=110/first.get_bounding_rect(min_alpha=64).h
        originals=[]
        for i in range(16):
            left,right=round(i%4*sheet.get_width()/4),round((i%4+1)*sheet.get_width()/4)
            cell=sheet.subsurface((left,rows[i//4],right-left,rows[i//4+1]-rows[i//4]))
            bounds=cell.get_bounding_rect(min_alpha=64)
            if not bounds.w:raise ValueError(f'Sword death: empty pose {i}')
            image=pg.transform.smoothscale(cell,(round(cell.get_width()*scale),round(cell.get_height()*scale)))
            frame=pg.Surface(CELL,pg.SRCALPHA).convert_alpha()
            frame.blit(image,(pixel(PIVOT[0]-cell.get_width()*.5*scale),pixel(PIVOT[1]-bounds.bottom*scale)))
            originals.append(frame)
        self.atlas=pg.Surface((2048,3072),pg.SRCALPHA).convert_alpha()
        self.areas=[]
        for i in range(FRAMES):
            p=i/(FRAMES-1)*15;lo=min(14,int(p));weight=p-lo
            frame=originals[lo].copy();frame.fill((round(255*(1-weight)),)*4,special_flags=pg.BLEND_RGBA_MULT)
            following=originals[lo+1].copy();following.fill((round(255*weight),)*4,special_flags=pg.BLEND_RGBA_MULT)
            frame.blit(following,(0,0),special_flags=pg.BLEND_RGBA_ADD)
            areas=[]
            for face,image in enumerate((frame,pg.transform.flip(frame,True,False))):
                index=i*2+face;area=pg.Rect(index%8*CELL[0],index//8*CELL[1],*CELL)
                self.atlas.blit(image,area);areas.append(area)
            self.areas.append(tuple(areas))
        self.images=[self.atlas]

    def draw(self,canvas,death,hero,x,y,alpha):
        px,py=canvas.point((x,y));facing=death.hero_face
        pivot_x=PIVOT[0] if facing>0 else CELL[0]-1-PIVOT[0]
        area=self.areas[pose_index(death,alpha)][0 if facing>0 else 1]
        canvas.native.blit(self.atlas,(px-pivot_x,py-PIVOT[1]),area)
