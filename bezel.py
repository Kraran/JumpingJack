"""Static, aspect-preserving bezel crops outside the unchanged game viewport."""
from collections import OrderedDict
import pygame as pg


def margins(output,game):
    width,height=output;bounds=pg.Rect(0,0,width,height)
    visible=pg.Rect(game).clip(bounds)
    candidates=(('left',pg.Rect(0,0,visible.left,height)),
                ('right',pg.Rect(visible.right,0,width-visible.right,height)),
                ('top',pg.Rect(visible.left,0,visible.w,visible.top)),
                ('bottom',pg.Rect(visible.left,visible.bottom,visible.w,height-visible.bottom)))
    return [(side,rect) for side,rect in candidates if rect.w>0 and rect.h>0]


def cover_crop(area,destination,side):
    """Cover proportionally, retaining the edge next to gameplay; never stretch art."""
    area=pg.Rect(area);dest=pg.Rect(destination)
    ratio=max(dest.w/area.w,dest.h/area.h)
    width=max(1,min(area.w,round(dest.w/ratio)))
    height=max(1,min(area.h,round(dest.h/ratio)))
    x=area.right-width if side=='left' else area.x if side=='right' else area.x+(area.w-width)//2
    y=area.y if side=='top' else area.bottom-height if side=='bottom' else area.y+(area.h-height)//2
    return pg.Rect(x,y,width,height)


class BezelArt:
    def __init__(self,assets):
        self.images={};self.scaled=OrderedDict()
        for theme in ('egypt','greece','solar'):
            try:self.images[theme]=pg.image.load(str(assets/f'{theme}-v1.png')).convert()
            except (pg.error,OSError):pass

    def pieces(self,theme,output,game):
        image=self.images.get(theme)
        if image is None:return
        half=image.get_width()//2
        for side,dest in margins(output,game):
            area=(pg.Rect(0,0,half,image.get_height()) if side=='left' else
                  pg.Rect(half,0,image.get_width()-half,image.get_height()) if side=='right' else image.get_rect())
            yield image,cover_crop(area,dest,side),dest

    def draw_software(self,surface,theme,game):
        for image,source,dest in self.pieces(theme,surface.get_size(),game):
            key=(theme,tuple(source),dest.size)
            cached=self.scaled.pop(key,None)
            if cached is None:cached=pg.transform.smoothscale(image.subsurface(source),dest.size)
            self.scaled[key]=cached
            if len(self.scaled)>32:self.scaled.popitem(last=False)
            surface.blit(cached,dest)
