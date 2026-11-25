"""Nonperiodic, smooth sand heightfield shared by physics and native rendering."""
from bisect import bisect_right
import math
import pygame as pg

# Unequal spacing and asymmetric crests, with small safe pads at checkpoints.
PROFILE=((0,620),(105,606),(230,573),(360,611),(450,620),(600,620),(650,626),(700,640),
 (3140,640),(3200,626),(3260,620),(3700,620),(3810,587),(3900,575),(3980,602),(4050,620),
 (4290,620),(4410,605),(4630,525),(4740,500),(4860,500),(5060,570),
 (5270,470),(5480,355),(5700,480),(5880,590),(6050,620),
 (6350,620),(6480,600),(6730,495),(6960,430),(7130,500),(7450,390),
 (7680,455),(7900,550),(8100,610),(8300,620),
 (8660,620),(8790,590),(9010,470),(9230,405),(9440,435),(9540,440),
 (9660,440),(9870,530),(10100,590),(10300,620),(10650,620),
 (10950,620),(11110,595),(11350,470),(11580,365),(11830,455),
 (12000,570),(12110,610),(12250,620),
 (12490,620),(12580,575),(12700,555),(12800,620),(12860,620),(13080,620),
 (13280,485),(13480,540),(13620,610),(13700,620),
 (14000,620),(14065,598),(14135,582),(14220,600),(14310,620),(14600,620))
_X=tuple(x for x,y in PROFILE)


def sand_height(x):
    index=max(0,min(len(PROFILE)-2,bisect_right(_X,x)-1))
    a,ya=PROFILE[index];b,yb=PROFILE[index+1]
    t=max(0.,min(1.,(x-a)/(b-a)))
    return ya+(yb-ya)*t*t*(3-2*t)


class DuneGround:
    ground=True;spiked=False;kind='dune'
    def __init__(self,x,width):
        self.x=x;self.w=width
        heights=[sand_height(x),sand_height(x+width)]
        heights.extend(y for px,y in PROFILE if x<=px<=x+width)
        self.y=min(heights);self.h=760-self.y
        self._boxes=[]
        for left in range(round(x),math.ceil(x+width),32):
            right=min(x+width,left+32)
            top=math.floor(min(sand_height(left),sand_height((left+right)/2),sand_height(right)))
            self._boxes.append(pg.Rect(left,top,math.ceil(right-left),760-top))
        self._inflated={size:tuple(rect.inflate(*size) for rect in self._boxes)
                        for size in ((0,0),(36,28),(52,36))}

    @property
    def rect(self):return pg.Rect(self.x,self.y,self.w,self.h)
    def height_at(self,x):return sand_height(max(self.x,min(self.x+self.w,x)))
    def query(self,start,end,inflate=(0,0)):
        margin=inflate[0]/2
        first=max(0,math.floor((min(start[0],end[0])-margin-self.x)/32))
        last=min(len(self._boxes),math.floor((max(start[0],end[0])+margin-self.x)/32)+1)
        boxes=self._inflated[inflate]
        for index in range(first,last):yield boxes[index]

    def ray_distance(self,start,bottom,direction,maximum):
        low=max(0.,self.x-start if direction>0 else start-self.x-self.w)
        high=min(maximum,self.x+self.w-start if direction>0 else start-self.x)
        if high<low:return maximum
        previous=low;distance=low
        while distance<=high:
            if bottom>self.height_at(start+direction*distance):
                lo,hi=previous,distance
                for _ in range(8):
                    mid=(lo+hi)/2
                    if bottom>self.height_at(start+direction*mid):hi=mid
                    else:lo=mid
                return hi
            previous=distance;distance=min(high,distance+4.) if distance<high else high+1
        return maximum


def obstacle_boxes(platforms,start,end,inflate=(0,0)):
    for platform in platforms:
        if isinstance(platform,DuneGround):yield from platform.query(start,end,inflate)
        else:yield platform.rect.inflate(*inflate)


def surface_height(platform,x):
    return platform.height_at(x) if isinstance(platform,DuneGround) else platform.y


def overlaps_rect(platform,rect):
    if not isinstance(platform,DuneGround):return rect.colliderect(platform.rect)
    a=max(rect.left,platform.x);b=min(rect.right,platform.x+platform.w)
    if b<=a or rect.top>=760:return False
    heights=[platform.height_at(a),platform.height_at(b),platform.height_at((a+b)/2)]
    heights.extend(y for x,y in PROFILE[bisect_right(_X,a):bisect_right(_X,b)])
    return rect.bottom>min(heights)+1
