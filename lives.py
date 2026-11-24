"""HUD emblem taken directly from the hero's golden chest insignia."""
import pygame as pg

STARTING_LIVES=3


def load_life_symbol(path):
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
    scale=min(36/image.get_width(),30/image.get_height())
    return pg.transform.smoothscale(image,(round(image.get_width()*scale),round(image.get_height()*scale)))
