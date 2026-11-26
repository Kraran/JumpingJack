"""Level 04: one-screen-wide, 14,400-unit temple tower ascent."""
WIDTH=LENGTH=1280
HEIGHT=14400
BASE_Y=HEIGHT-100
START=(400.,float(BASE_Y))
import random
LAYOUT_VERSION=3


def make_layout(seed=70421):
    rng=random.Random(seed);gaps=[rng.randint(112,180) for _ in range(95)]
    for i in range(1,len(gaps)):
        if gaps[i-1]+gaps[i]<280:gaps[i]=280-gaps[i-1]
    correction=13900-sum(gaps)
    while correction:
        i=rng.randrange(len(gaps));step=1 if correction>0 else -1;value=gaps[i]+step
        if (110<=value<=180 and (i==0 or gaps[i-1]+value>=280)
                and (i==len(gaps)-1 or gaps[i+1]+value>=280)):
            gaps[i]=value;correction-=step
    route=[];center=START[0];y=BASE_Y
    for i,gap in enumerate(gaps):
        choices=[]
        for direction in (-1,1):
            for distance in range(245,356,5):
                if i in (21,53,81) and distance>300:continue
                target=center+direction*distance
                if 170<=target<=1110:choices.append((target,distance))
        center,distance=rng.choice(choices)
        widths=((240,) if i in (21,53,81) else (360,) if distance>=325 else
                (300,) if distance>=285 else (180,240,300))
        width=rng.choice(widths);center=max(80+width/2,min(1200-width/2,center))
        y-=gap;route.append((round(center-width/2),y,width))
    # Author a safe irregular final approach to the central summit.
    def bridge(start,count):
        if not count:return [] if 245<=abs(start-640)<=300 else None
        for center in range(200,1101,5):
            if 245<=abs(center-start)<=355:
                tail=bridge(center,count-1)
                if tail is not None:return [center]+tail
        return None
    tail=bridge(route[-4][0]+route[-4][2]/2,3)
    if tail is None:raise ValueError('No summit bridge')
    for j,center in enumerate(tail):route[-3+j]=(center-180,route[-3+j][1],360)
    extras=[];rows=sorted(set(range(5,len(route),5))|{21,53,81})
    for i in rows:
        x,y,w=route[i];width=360 if i in (21,53,81) else rng.choice((120,180,240,300))
        options=((80,width),(1200-width,width))
        left,width=max(options,key=lambda item:max(x-(item[0]+item[1]),item[0]-(x+w)))
        if max(x-(left+width),left-(x+w))<65:width=180;left=80 if x>640 else 1020
        extras.append((left,y,width,i))
    return tuple(route),tuple(extras)


LEDGES,BRANCHES=make_layout()
SUMMIT=(640.,float(BASE_Y-139*101))
CHECKPOINTS=tuple((float(LEDGES[i][0]+LEDGES[i][2]/2),float(LEDGES[i][1])) for i in (31,63))
MEDALLION=(float(LEDGES[90][0]+LEDGES[90][2]/2),float(LEDGES[90][1]-186))
BEETLES=tuple((float(400 if n%2 else 900),float(LEDGES[i][1]-55)) for n,i in enumerate(range(9,96,8)))
SCORPIONS=tuple((float(x+w/2),float(x+100),float(x+w-100),float(y),-1 if x<600 else 1)
                for x,y,w,i in BRANCHES if i in (21,53,81))
VASES=((240.,float(BASE_Y)),(1000.,float(BASE_Y)))+tuple(
    (float(x+w-55 if x<600 else x+55),float(y)) for x,y,w,i in BRANCHES if i in (5,15,30,45,60,75,90))
TORCHES=tuple((float(x+35 if x<600 else x+w-35),float(y-35))
              for x,y,w,i in BRANCHES if i in (10,25,40,55,70,85,90))
SPIKED_ROWS={5,10,15,20,25,30,35,40,45,50,55,60,75,85,90}
GYROSPHERES=tuple(next((float(cx),float(LEDGES[i][1]-65)) for cx in (640,320,960,200,1080)
    if not any(x-18<cx<x+w+18 and y-18<LEDGES[i][1]-65<y+50
               for x,y,w in LEDGES+tuple((x,y,w) for x,y,w,row in BRANCHES))) for i in (14,46,78,30,62,90))


def collectible_sites():
    rng=random.Random(90274);sites=[]
    groups=[('route',i,x,y,w) for i,(x,y,w) in enumerate(LEDGES)]
    groups += [('base',0,64,BASE_Y,1152),('summit',0,SUMMIT[0]-120,SUMMIT[1],240)]
    groups += [('branch',i,x,y,w) for i,(x,y,w,row) in enumerate(BRANCHES)]
    for group,i,x,y,w in groups:
        count=rng.choices((0,1,2),weights=(.38,.42,.20))[0]
        for slot,f in enumerate((.5,) if count==1 else (.28,.72) if count==2 else ()):
            sites.append((group,i,slot,x+w*f,y-42))
    return tuple(sites)


GEM_SITES=collectible_sites()

def route_platforms(platforms):return list(platforms[4:5+len(LEDGES)])


VULTURES=CROCODILES=()


def camera_target(y):return max(0.,min(HEIGHT-720,y-720*.60))


def progress(y):return max(0,min(100,round((BASE_Y-y)/(BASE_Y-SUMMIT[1])*100)))


def completed(hero):
    return hero.grounded and abs(hero.y-SUMMIT[1])<2 and abs(hero.x-SUMMIT[0])<135


def build(platform_type,exit_margin=96):
    platforms=[platform_type(64,BASE_Y,WIDTH-128,140,True,kind='tower_floor'),
               platform_type(0,-120,64,HEIGHT+300,True,kind='tower_wall'),
               platform_type(WIDTH-64,-120,64,HEIGHT+300,True,kind='tower_wall'),
               platform_type(64,-120,WIDTH-128,120,True,kind='tower_ceiling')]
    platforms += [platform_type(x,y,w,32) for x,y,w in LEDGES]
    platforms.append(platform_type(SUMMIT[0]-120,SUMMIT[1],240,32))
    platforms += [platform_type(x,y,w,32,spiked=i in SPIKED_ROWS) for x,y,w,i in BRANCHES]
    gems=[(x,y) for group,row,slot,x,y in GEM_SITES]
    return platforms,gems
