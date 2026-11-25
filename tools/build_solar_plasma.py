"""Rebuild the approved solar plasma atlas; optional developer dependencies only."""
import os
os.environ.setdefault('SDL_VIDEODRIVER','dummy')
os.environ.setdefault('SDL_AUDIODRIVER','dummy')
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import math
import random
import json
import argparse
import numpy as np
from PIL import Image, ImageFilter
import pygame as pg
from plasma_fx import FX_FPS, FX_FRAMES, FRAME_SIZE, ORIGIN, COLUMNS

def smooth(x):
    x=max(0.,min(1.,x));return x*x*(3-2*x)


def plasma(t,elapsed,duration,origin):
    # All turbulence is continuous and advected downstream; no random redraws.
    age=elapsed-.15
    if age<-.15 or age>duration+.32:return None
    charge=smooth((elapsed+.01)/.15) if age<0 else 1.
    power=smooth(age/.025) if age>=0 else 0.
    if age>duration:power=math.exp(-(age-duration)/.055)
    length=min(790.,max(0.,age*14000))
    margin=110;center=125;size=(1000,250)
    layer=pg.Surface(size);layer.fill((0,0,0))
    rng=random.Random(283)
    if power>.004 and length>1:
        u=np.linspace(0.,1.,260)
        x=u*length
        envelope=(1-np.exp(-x/45))*(.92-.48*u**6)
        for strand in range(25):
            phase=rng.random()*math.tau
            speed=1.8+rng.random()*1.8
            amplitude=9+rng.random()*20
            side=1 if strand%2 else -1
            advect=x*.013-t*speed*5
            wave=(np.sin(advect+phase)+.43*np.sin(x*.033-t*speed*10+phase*1.7)
                  +.19*np.sin(x*.067-t*speed*17+phase*.4))
            y=center+envelope*(side*amplitude*.45+amplitude*.68*wave)
            taper=(.72+.28*math.sin(t*5.2+phase)**2)
            end=int(len(u)*(.83+.17*rng.random()))
            points=[(round(margin+xx),round(yy)) for xx,yy in zip(x[:end],y[:end])]
            color=(round((125+95*taper)*power),round((58+92*taper)*power),round((8+27*taper)*power))
            pg.draw.lines(layer,color,False,points,2 if strand%4 else 3)
            pg.draw.aalines(layer,color,False,points)
        # A living hot channel, not a rigid solid rectangle.
        for strand in range(5):
            y=center+(1-np.exp(-x/28))*(2.8*np.sin(x*.024-t*25+strand*1.3)
                    +1.5*np.sin(x*.057-t*43+strand*.8))
            points=[(round(margin+xx),round(yy)) for xx,yy in zip(x,y)]
            color=(round(230*power),round((175+strand*12)*power),round((75+strand*26)*power))
            pg.draw.lines(layer,color,False,points,2)
            pg.draw.aalines(layer,color,False,points)
        for spark in range(42):
            phase=(t*(.43+(spark%7)*.045)+spark*.6180339)%1
            xx=phase*length
            yy=center+math.sin(xx*.018-t*12+spark*1.6)*(8+spark%25)*(1-math.exp(-xx/70))
            brightness=power*math.sin(math.pi*phase)**.6
            color=(round(210*brightness),round(140*brightness),round(35*brightness))
            pg.draw.line(layer,color,(round(margin+xx-4),round(yy)),(round(margin+xx),round(yy)),1)
    flare=(charge*.45 if age<0 else power)
    if flare>.004:
        for radius,intensity in ((19,.12),(12,.2),(7,.5),(3,1.)):
            pg.draw.circle(layer,(round(255*flare*intensity),round(210*flare*intensity),round(95*flare*intensity)),(margin,center),radius)
        for ray in range(14):
            angle=ray*math.tau/14+t*.7
            radius=(16+11*math.sin(ray*2.7+t*6)**2)*flare
            end=(round(margin+math.cos(angle)*radius),round(center+math.sin(angle)*radius))
            pg.draw.aaline(layer,(round(170*flare),round(110*flare),round(34*flare)),(margin,center),end)
    raw=Image.frombytes('RGB',size,pg.image.tobytes(layer,'RGB'))
    wide=raw.filter(ImageFilter.GaussianBlur(11))
    close=raw.filter(ImageFilter.GaussianBlur(2.4))
    result=pg.image.frombytes(wide.tobytes(),size,'RGB')
    result.blit(pg.image.frombytes(close.tobytes(),size,'RGB'),(0,0),special_flags=pg.BLEND_RGB_ADD)
    result.blit(layer,(0,0),special_flags=pg.BLEND_RGB_ADD)
    return result,(round(origin[0]-margin),round(origin[1]-center))


def build_color_atlas(directory):
    """Straight alpha keeps the golden plasma from bleaching a bright sky."""
    source=Image.open(directory/'solar-plasma.png').convert('RGB')
    target=Image.new('RGBA',source.size)
    for top in range(0,source.height,FRAME_SIZE[1]):
        bottom=min(source.height,top+FRAME_SIZE[1])
        rgb=np.asarray(source.crop((0,top,source.width,bottom)),dtype=np.uint16)
        alpha=rgb.max(axis=2);denominator=np.maximum(alpha,1)[...,None]
        color=(rgb*255+denominator//2)//denominator
        color[...,1]=(color[...,1]*94+50)//100
        color[...,2]=(color[...,2]*72+50)//100
        rgba=np.empty((*alpha.shape,4),dtype=np.uint8)
        rgba[...,:3]=color;rgba[...,3]=alpha
        target.paste(Image.fromarray(rgba),(0,top))
    path=directory/'solar-plasma-color-v2.png';target.save(path)
    print('Color-preserving plasma atlas built:',path.name,target.size)


def build(color_only=False):
    directory=Path(__file__).resolve().parents[1]/'assets'
    if color_only:
        build_color_atlas(directory);return
    pg.init();pg.display.set_mode((1,1))
    atlas=pg.Surface((COLUMNS*FRAME_SIZE[0],((FX_FRAMES+COLUMNS-1)//COLUMNS)*FRAME_SIZE[1]))
    atlas.fill((0,0,0))
    for i in range(FX_FRAMES):
        t=i/FX_FPS
        effect=plasma(.5+t,t,.15,(0,0))
        if effect is not None:
            frame=pg.transform.smoothscale(effect[0],FRAME_SIZE)
            atlas.blit(frame,(i%COLUMNS*FRAME_SIZE[0],i//COLUMNS*FRAME_SIZE[1]))
    pg.image.save(atlas,directory/'solar-plasma.png')
    data={'fps':FX_FPS,'frames':FX_FRAMES,'frame_size':list(FRAME_SIZE),'origin':list(ORIGIN),'columns':COLUMNS}
    (directory/'solar-plasma.json').write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
    pg.quit()
    print('Plasma atlas built:',atlas.get_size())
    build_color_atlas(directory)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--color-only',action='store_true')
    build(parser.parse_args().color_only)
