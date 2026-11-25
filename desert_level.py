"""Level 02 geometry and encounter data, in shared design coordinates."""
from terrain import DuneGround,sand_height
LENGTH=14400
GROUND=620
RIVER=(700,3140)
WATER_Y=640
CHECKPOINTS=(4800,9600)
MEDALLION=(12960.,185.)
# Temple extends beyond the final viewport; its right jamb hides the hero.
TEMPLE_X=13820
TEMPLE_WIDTH=640
TEMPLE_BASE=620
TEMPLE_DOOR_LEFT=14145
TEMPLE_DOOR_TOP=390
TEMPLE_FRONT=14340
TEMPLE_FINISH=14384
# Large solid outcrops replace the sand beneath them: no ground-level bypass.
ROCKS=((4050,440,240),(6050,380,300),(8300,340,360),
       (10650,370,300),(12250,410,240))
REMOVED_ROCK=(13700,360,300)
REMOVED_LEDGE=(14100,480,180)
BRIDGES=((800,545,300),(1250,500,300),(1700,455,360),
         (2200,490,300),(2670,545,300))
LEDGES=((3450,485,240),(3770,500,180),(4480,470,300),(4890,335,180),
        (5260,455,360),(5700,500,180),(6480,460,240),(6830,315,180),
        (7200,455,300),(7490,325,120),(8020,500,180),(8820,455,240),
        (9200,320,300),(9750,470,240),(10320,500,180),(11130,465,360),
        (11580,330,180),(11330,300,120),(11950,500,180),(12600,500,180),
        (12870,455,180),(13220,315,240),(13410,500,180))
# Preserve collectible identities in existing saves; the last pair now rests
# above the sand on the approach to the temple instead of a removed platform.
CRYSTAL_LEDGES=LEDGES+(REMOVED_LEDGE,)
BEETLES=((1350,375),(2670,420),(3900,430),(5350,380),(7150,390),
         (9000,390),(10150,440),(11450,410),(12750,350),(13900,400))
VULTURES=((1900,155),(3650,170),(5950,150),(8750,150),(11150,150),(13350,155))
# spawn, patrol limits, floor limits, altitude, facing; all in the river zone.
CROCODILES=((540,460,600,0,700,620,-1),
            (1880,1800,1900,1700,2060,455,-1),
            (3430,3300,3540,3140,3790,620,-1))


def build(platform_type,exit_margin=96,*,rocks=ROCKS,ledges=LEDGES):
    floors=[(0,RIVER[0])];start=RIVER[1]
    for x,y,width in rocks:
        floors.append((start,x));start=x+width
    floors.append((start,LENGTH+exit_margin+32))
    platforms=[DuneGround(a,b-a) for a,b in floors]
    platforms += [platform_type(x,y,w,760-y,True,kind='rock') for x,y,w in rocks]
    platforms += [platform_type(x,y,w,26,kind='bridge') for x,y,w in BRIDGES]
    adjusted=[]
    for x,y,w in ledges:
        floor=min(sand_height(px) for px in range(x,x+w+1,10))
        top=max(300,min(y,floor-110))
        covered=any(a<=x and x+w<=a+width and abs(top-height)<1 for a,height,width in adjusted)
        if floor-top>=90 and not covered:
            platforms.append(platform_type(x,top,w,32));adjusted.append((x,top,w))
    gems=[]
    heights={x:y for x,y,w in adjusted}
    for x,y,w in BRIDGES+CRYSTAL_LEDGES:
        for px in (x+w*.28,x+w*.70):
            py=y if (x,y,w) in BRIDGES else heights.get(x,sand_height(px)-8)
            gems.append((px,py-42))
    gems.extend((x,sand_height(x)-50) for x in (220,380,3200,3600,4650,5500,6700,7400,
                                 9000,9700,10000,11300,11800,13080,14200))
    return platforms,gems


def water_hits(hero):
    return hero.x+12>RIVER[0] and hero.x-12<RIVER[1] and hero.y>WATER_Y


def temple_entered(hero):
    return hero.x>=TEMPLE_FINISH and TEMPLE_DOOR_TOP+hero.body_height<=hero.y<=TEMPLE_BASE+2
