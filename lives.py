"""HUD emblem taken directly from the hero's golden chest insignia."""
import pygame as pg
from hud_layout import life_position

STARTING_LIVES=3


def game_over_tune(rate,channels):
    """A short descending motif, prepared once with the other effects."""
    import math
    from array import array
    data=array('h')
    for frequency,duration in ((220.,.20),(196.,.20),(164.81,.24),(110.,.65)):
        for frame in range(int(rate*duration)):
            t=frame/rate
            envelope=min(1.,t/.012)*(1-t/duration)**1.5
            wave=math.sin(math.tau*frequency*t)+.25*math.sin(math.tau*frequency*2*t)
            sample=round(4200*envelope*wave)
            data.extend([sample]*channels)
    return data


def load_life_symbol(path,size=(36,30)):
    # The frontal hovering pose exposes both wings of the original insignia.
    source=pg.image.load(str(path)).convert_alpha().subsurface((1093,477,54,39))
    mask=pg.mask.Mask(source.get_size())
    for y in range(source.get_height()):
        for x in range(source.get_width()):
            r,g,b,a=source.get_at((x,y))
            if a>128 and r>110 and g>70 and r>g*1.05 and b<g*.8:mask.set_at((x,y))
    mask=mask.connected_component()
    image=pg.Surface(source.get_size(),pg.SRCALPHA)
    for y in range(source.get_height()):
        for x in range(source.get_width()):
            if mask.get_at((x,y)):image.set_at((x,y),source.get_at((x,y)))
    bounds=image.get_bounding_rect()
    if not bounds.w:raise ValueError('Symbole de poitrine du héros introuvable')
    image=image.subsurface(bounds)
    scale=min(size[0]/image.get_width(),size[1]/image.get_height())
    return pg.transform.smoothscale(image,(round(image.get_width()*scale),round(image.get_height()*scale)))
