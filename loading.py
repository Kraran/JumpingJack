"""Immediate startup screen, independent of game assets and simulation."""
import math
import pygame as pg
from localization import translate


class LoadingCancelled(Exception):
    """The player closed the window or pressed Escape during startup."""


class LoadingScreen:
    def __init__(self,enabled=True,language='fr'):
        self.enabled=enabled;self.active=True;self.progress=0.;self.labels={}
        self.language=language
        if not enabled:return
        self.background=pg.Surface((1920,1080)).convert()
        for y in range(1080):
            t=y/1080
            pg.draw.line(self.background,(round(10+9*t),round(24+14*t),round(33+10*t)),(0,y),(1919,y))
        gold=(216,175,96);muted=(82,96,92)
        for radius in (155,172):pg.draw.circle(self.background,muted,(1450,410),radius,2)
        pg.draw.circle(self.background,gold,(1450,410),101,2)
        for ray in range(24):
            a=ray/24*math.tau
            pg.draw.line(self.background,gold,(round(1450+math.cos(a)*117),round(410+math.sin(a)*117)),
                         (round(1450+math.cos(a)*139),round(410+math.sin(a)*139)),2)
        pg.draw.polygon(self.background,(35,51,54),[(1050,835),(1390,540),(1730,835)])
        pg.draw.polygon(self.background,(27,42,47),[(1400,835),(1645,635),(1890,835)])
        pg.draw.line(self.background,muted,(158,836),(1762,836),1)
        self.title_font=pg.font.SysFont('Georgia',88)
        self.font=pg.font.SysFont('Segoe UI',27)
        self.small=pg.font.SysFont('Segoe UI',21)
        self.static=[(self.small.render(translate('LES SABLES D’HORUS',language),True,gold),(162,252)),
                     (self.title_font.render('JUMPING JACK',True,(247,235,205)),(152,306)),
                     (self.font.render(translate('Préparation de votre aventure',language),True,(170,187,185)),(162,438)),
                     (self.small.render(translate('Échap pour quitter',language),True,(131,151,151)),(162,895))]
        self.images=[self.background]+[image for image,pos in self.static]

    def show(self,canvas,screen,progress,label):
        self.progress=max(self.progress,min(1.,progress))
        if not self.enabled or not self.active:return
        for event in pg.event.get([pg.QUIT,pg.KEYDOWN]):
            if event.type==pg.QUIT or event.key==pg.K_ESCAPE:raise LoadingCancelled()
        key=(label,round(self.progress*100))
        if key not in self.labels:
            self.labels[key]=(self.font.render(translate(label,self.language),True,(231,206,153)),
                              self.small.render(f'{key[1]:02} %',True,(231,206,153)))
        caption,percent=self.labels[key]
        canvas.begin();canvas.blit(self.background,(0,0))
        for image,position in self.static:canvas.blit(image,position)
        canvas.blit(caption,(162,660));canvas.blit(percent,(978-percent.get_width(),668))
        canvas.rect((43,61,64),(162,724,816,10))
        canvas.rect((237,194,105),(162,724,round(816*self.progress),10))
        canvas.present(screen)

    def release(self,canvas):
        self.active=False
        images=getattr(self,'images',[])+[image for pair in self.labels.values() for image in pair]
        for image in images:canvas.textures.pop(id(image),None)
        self.labels.clear()
        if self.enabled:
            self.images.clear();self.static.clear();self.background=None
