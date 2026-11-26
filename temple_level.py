"""Level 03: hypostyle halls, collapsed galleries and the inner sanctuary."""
from scorpion import SPAWNS as SCORPIONS
LENGTH=14400
GROUND=620
CHECKPOINTS=(4800,9600)
MEDALLION=(12960.,185.)
VULTURES=()
CROCODILES=()
GYROSPHERES=((5050.,250.),(9470.,245.))
BEETLES=((1000,440),(2350,410),(3250,380),(4300,430),(5850,380),
         (6650,420),(8050,380),(8700,440),(10150,400),(11450,390),(12750,350),(13700,420))
FLOORS=((0,1700),(1920,3500),(3740,5200),(5450,7100),
        (7350,9000),(9250,10800),(11050,12600),(12840,LENGTH+128))
LEDGES=((420,490,240),(800,350,180),(1220,450,300),(1660,470,180),
        (2070,450,240),(2480,310,180),(2880,450,360),(3320,480,180),
        (3700,470,120),(4080,440,300),(4480,305,180),(4930,455,240),
        (5270,475,180),(5650,450,300),(6050,310,180),(6460,445,360),
        (6900,475,180),(7260,475,180),(7650,450,240),(8040,310,120),
        (8450,450,360),(8860,475,180),(9180,475,180),(9530,445,240),
        (9940,300,180),(10340,450,300),(10740,475,180),(11120,460,240),
        (11520,320,180),(11920,455,360),(12380,475,180),(12870,455,180),
        (13220,315,240),(13550,470,180))
SPIKED={7650,10340,11920}


def build(platform_type,exit_margin=96):
    platforms=[platform_type(a,GROUND,b-a,140,True,kind='temple_floor') for a,b in FLOORS]
    platforms += [platform_type(x,y,w,32,spiked=x in SPIKED) for x,y,w in LEDGES]
    platforms.append(platform_type(0,-300,LENGTH+128,420,True,kind='temple_ceiling'))
    gems=[(x+w*f,y-42) for x,y,w in LEDGES for f in (.28,.70)]
    gems += [(x,570) for x in (220,1450,2250,3900,4800,6250,7800,9600,11200,13080,14000)]
    return platforms,gems
