"""Five sacred sandstone platforms, pre-sized in a single native-HD GPU atlas."""
import pygame as pg
from gpu_render import SCALE


class SacredPlatforms:
    def __init__(self,path,widths):
        source=pg.image.load(str(path)).convert_alpha()
        if source.get_at((0,0)).a>8:raise ValueError(f'{path.name}: fond non transparent')
        height=round(32*SCALE)
        self.atlas=pg.Surface((round(max(widths)*SCALE),height*len(widths)),pg.SRCALPHA).convert_alpha()
        self.areas={}
        for index,width in enumerate(widths):
            top,bottom=round(index*source.get_height()/len(widths)),round((index+1)*source.get_height()/len(widths))
            cell=source.subsurface((0,top,source.get_width(),bottom-top))
            bounds=cell.get_bounding_rect(min_alpha=32)
            if not bounds.w:raise ValueError(f'{path.name}: plateforme vide {index}')
            image=pg.transform.smoothscale(cell.subsurface(bounds),(round(width*SCALE),height))
            area=pg.Rect(0,index*height,*image.get_size())
            self.atlas.blit(image,area);self.areas[width]=area

    @property
    def images(self):return [self.atlas]

    def draw(self,canvas,platform,cam):
        # No sprite overhang: the image fills exactly the physical slab.
        destination=canvas.rect((platform.x-cam,platform.y,platform.w,platform.h))
        canvas.native.blit(self.atlas,destination,self.areas[platform.w])
