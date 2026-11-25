"""Small preloaded flag icons; no dependency on emoji font support."""
import math
import pygame as pg
from localization import CODES


class LanguageFlags:
    def __init__(self):
        self.atlas=pg.Surface((200,math.ceil(len(CODES)/4)*32),pg.SRCALPHA).convert_alpha();self.areas={}
        patterns={'fr':('v',('#21468B','white','#ED2939')),'de':('h',('#161616','#D9232E','#FFCE00')),
                  'es':('h',('#AA151B','#F1BF00','#AA151B')),'it':('v',('#009246','white','#CE2B37')),
                  'nl':('h',('#AE1C28','white','#21468B')),'pl':('h',('white','#DC143C')),
                  'ro':('v',('#002B7F','#FCD116','#CE1126')),'hu':('h',('#CE2939','white','#477050')),
                  'ru':('h',('white','#0039A6','#D52B1E')),
                  'bg':('h',('white','#00966E','#D62612')),'sr':('h',('#C6363C','#0C4076','white'))}
        for index,code in enumerate(CODES):
            flag=pg.Surface((48,30),pg.SRCALPHA)
            if code in patterns:
                direction,colors=patterns[code]
                for i,color in enumerate(colors):
                    if direction=='v':pg.draw.rect(flag,color,(round(i*48/len(colors)),0,round((i+1)*48/len(colors))-round(i*48/len(colors)),30))
                    else:pg.draw.rect(flag,color,(0,round(i*30/len(colors)),48,round((i+1)*30/len(colors))-round(i*30/len(colors))))
                if code=='es':
                    pg.draw.rect(flag,'#F1BF00',(0,7,48,16));pg.draw.rect(flag,'#AD343A',(12,12,4,7))
                if code=='sr':pg.draw.rect(flag,'white',(14,9,5,13));pg.draw.rect(flag,'#C6363C',(15,13,3,7))
            elif code in ('sv','da','nb','fi','is'):
                background,cross={'sv':('#006AA7','#FECC00'),'da':('#C8102E','white'),
                                  'nb':('#BA0C2F','white'),'fi':('white','#003580'),'is':('#02529C','white')}[code]
                flag.fill(background)
                pg.draw.rect(flag,cross,(14,0,8,30));pg.draw.rect(flag,cross,(0,11,48,8))
                if code in ('nb','is'):
                    inner='#00205B' if code=='nb' else '#DC1E35'
                    pg.draw.rect(flag,inner,(16,0,4,30));pg.draw.rect(flag,inner,(0,13,48,4))
            elif code=='cs':
                flag.fill('white');pg.draw.rect(flag,'#D7141A',(0,15,48,15));pg.draw.polygon(flag,'#11457E',[(0,0),(24,15),(0,30)])
            elif code=='pt':
                flag.fill('#FF0000');pg.draw.rect(flag,'#006600',(0,0,19,30));pg.draw.circle(flag,'#FFCC00',(19,15),7)
                pg.draw.rect(flag,'white',(16,10,6,9));pg.draw.rect(flag,'#D62924',(17,12,4,6))
            elif code=='tr':
                flag.fill('#E30A17');pg.draw.circle(flag,'white',(19,15),9);pg.draw.circle(flag,'#E30A17',(22,14),7)
                star=[(round(32+math.cos(-math.pi/2+i*math.pi/5)*(5 if i%2==0 else 2)),
                       round(15+math.sin(-math.pi/2+i*math.pi/5)*(5 if i%2==0 else 2))) for i in range(10)]
                pg.draw.polygon(flag,'white',star)
            elif code=='en':
                flag.fill('#012169')
                for start,end in (((0,0),(48,30)),((0,30),(48,0))):
                    pg.draw.line(flag,'white',start,end,7);pg.draw.line(flag,'#C8102E',start,end,3)
                pg.draw.rect(flag,'white',(18,0,12,30));pg.draw.rect(flag,'white',(0,10,48,10))
                pg.draw.rect(flag,'#C8102E',(21,0,6,30));pg.draw.rect(flag,'#C8102E',(0,12,48,6))
            pg.draw.rect(flag,(206,191,150),flag.get_rect(),1)
            area=pg.Rect(index%4*50,index//4*32,48,30);self.atlas.blit(flag,area);self.areas[code]=area

    def draw(self,canvas,code,position):
        canvas.native.blit(self.atlas,canvas.point(position),self.areas[code])
