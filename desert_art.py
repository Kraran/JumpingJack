"""Level 02: preloaded native-HD scenery, footbridges, rocks, reeds and river."""
import math
import random
from functools import lru_cache
import pygame as pg
from gpu_render import SCALE,draw
from rendering import ParallaxLayer,pixel
from desert_level import ROCKS,BRIDGES,RIVER,WATER_Y
from desert_level import TEMPLE_X,TEMPLE_WIDTH,TEMPLE_BASE,TEMPLE_DOOR_LEFT,TEMPLE_DOOR_TOP,TEMPLE_FRONT
from terrain import sand_height

# The walking plane crosses the middle of the deck's perspective (12 HD pixels).
BRIDGE_DECK_CENTER=8
WATER_CREST_MARGIN=4  # Native pixels above the nominal waterline.


class DesertArt:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        self.layers=[]
        for name,numerator,width in (('far',2,4080),('middle',6,3240),('near',12,3240)):
            image=pg.image.load(str(assets/f'desert-{name}-v1.png'))
            image=image.convert() if name=='far' else image.convert_alpha()
            image=pg.transform.smoothscale(image,(width,1080))
            self.layers.append(ParallaxLayer(name,image,numerator,25,name!='far'))
        sheet=pg.image.load(str(assets/'desert-props-v1.png')).convert_alpha()
        cw,ch=sheet.get_width()//2,sheet.get_height()//2
        sources=[]
        for index in range(4):
            cell=sheet.subsurface((index%2*cw,index//2*ch,cw,ch))
            sources.append(cell.subsurface(cell.get_bounding_rect(min_alpha=64)))
        images={}
        for x,y,w in ROCKS:
            key=('rock',w,620-y);source=sources[1 if w>=300 else 3]
            images[key]=pg.transform.smoothscale(source,(pixel(w*SCALE),pixel((620-y)*SCALE)))
        for _,_,w in BRIDGES:
            images[('bridge',w)]=pg.transform.smoothscale(sources[0],(pixel(w*SCALE),105))
        images['reeds']=pg.transform.smoothscale(sources[2],(150,210))
        self.reed_offsets={}
        for position in (70,335,650,3190,3530):
            image,offset=self.plant_reeds(images['reeds'],position)
            images[('reeds',position)]=image;self.reed_offsets[position]=offset
        placements={};x=y=row=0
        for key,image in images.items():
            if x+image.get_width()>2048:x=0;y+=row+2;row=0
            placements[key]=pg.Rect(x,y,*image.get_size());x+=image.get_width()+2
            row=max(row,image.get_height())
        self.props=pg.Surface((2048,y+row),pg.SRCALPHA).convert_alpha()
        for key,image in images.items():self.props.blit(image,placements[key])
        self.areas=placements
        sand=pg.image.load(str(assets/'desert-sand-v1.png')).convert()
        self.sand=pg.transform.smoothscale(sand,(1536,210))
        self.dunes=self.make_dunes()
        self.rock_sand={x:self.make_rock_sand(x,w) for x,_,w in ROCKS}
        self.water=self.make_water(assets/'desert-water-v1.png')
        self.shore=self.make_shore()
        source=pg.image.load(str(assets/'desert-temple-entrance-v1.png')).convert_alpha()
        size=(pixel(TEMPLE_WIDTH*SCALE),pixel(TEMPLE_WIDTH*SCALE*source.get_height()/source.get_width()))
        self.temple=pg.transform.smoothscale(source,size)
        # Authored floor baseline: y=968 in the 1536 x 1024 source.
        self.temple_top=pixel(TEMPLE_BASE*SCALE)-pixel(968/source.get_height()*size[1])
        self.temple_front_area=pg.Rect(pixel((TEMPLE_FRONT-TEMPLE_X)*SCALE),0,
                                      pixel((TEMPLE_X+TEMPLE_WIDTH-TEMPLE_FRONT)*SCALE),size[1])
        self.temple_shadow=pg.Surface((pixel((TEMPLE_FRONT-TEMPLE_DOOR_LEFT)*SCALE),
                                      pixel((TEMPLE_BASE-TEMPLE_DOOR_TOP)*SCALE)),pg.SRCALPHA).convert_alpha()
        for x in range(self.temple_shadow.get_width()):
            t=min(1.,x/(110*SCALE));alpha=round(240*t*t*(3-2*t))
            pg.draw.line(self.temple_shadow,(4,3,2,alpha),(x,0),(x,self.temple_shadow.get_height()-1))
        self.images=[layer.image for layer in self.layers]+[self.props,self.water,self.sand,self.shore,self.temple,self.temple_shadow]+[image for x,y,image in self.dunes]+[image for x,y,image in self.rock_sand.values()]

    def temple_background(self,canvas,camera):
        left=pixel((TEMPLE_X-camera)*SCALE)
        if left>=1920 or left+self.temple.get_width()<=0:return
        canvas.native.blit(self.temple,(left,self.temple_top))

    def temple_foreground(self,canvas,camera):
        if TEMPLE_X-camera>1280 or TEMPLE_X+TEMPLE_WIDTH-camera<0:return
        canvas.native.blit(self.temple_shadow,canvas.point((TEMPLE_DOOR_LEFT-camera,TEMPLE_DOOR_TOP)))
        canvas.native.blit(self.temple,(pixel((TEMPLE_FRONT-camera)*SCALE),self.temple_top),self.temple_front_area)

    def make_rock_sand(self,rock_x,rock_width):
        # A small textured drift buries the transparent foot of each rock.
        # World-space grain and smooth shoulders join the surrounding dunes.
        start=pixel((rock_x-40)*SCALE);width=pixel((rock_width+80)*SCALE)
        heights=[]
        for col in range(width):
            x=(start+col)/SCALE
            shoulder=max(0.,min(1.,(x-rock_x+40)/40,(rock_x+rock_width+40-x)/40))
            shoulder=shoulder*shoulder*(3-2*shoulder)
            rise=(12+1.6*math.sin(x*.023)+.7*math.sin(x*.051+1))*shoulder
            ground=620 if rock_x<=x<=rock_x+rock_width else sand_height(x)
            heights.append((ground-rise)*SCALE)
        top=math.floor(min(heights))-1;bottom=pixel(760*SCALE)
        image=pg.Surface((width,bottom-top),pg.SRCALPHA).convert_alpha()
        tw,th=self.sand.get_size()
        for y in range(-(top%th),image.get_height(),th):
            for x in range(-(start%tw),width,tw):image.blit(self.sand,(x,y))
        for col,height in enumerate(heights):
            surface=height-top;edge=math.floor(surface)
            pg.draw.line(image,(0,0,0,0),(col,0),(col,edge-1))
            color=image.get_at((col,edge));color.a=round((1-(surface-edge))*255)
            image.set_at((col,edge),color)
        return start,top,image

    @staticmethod
    def plant_reeds(source,position):
        width,height=source.get_size();center=pixel(position*SCALE)
        ground=pixel(sand_height(position)*SCALE)
        shifts=[pixel(sand_height((center-width//2+column)/SCALE)*SCALE)-ground
                for column in range(width)]
        # Root stock is buried, and each column is cut at the exact sand surface.
        buried=24;top=-height+buried+min(shifts)
        image=pg.Surface((width,height+max(shifts)-min(shifts)),pg.SRCALPHA).convert_alpha()
        for column,shift in enumerate(shifts):
            image.blit(source,(column,shift-min(shifts)),(column,0,1,height))
            surface=shift-top
            pg.draw.line(image,(0,0,0,0),(column,surface),(column,image.get_height()-1))
        return image,top

    def make_dunes(self):
        chunks=[];bottom=pixel(760*SCALE)
        for start in range(0,pixel(14600*SCALE),1536):
            width=min(1536,pixel(14600*SCALE)-start)
            heights=[pixel(sand_height((start+col)/SCALE)*SCALE) for col in range(width)]
            top=min(heights)-2;height=bottom-top
            image=pg.Surface((width,height),pg.SRCALPHA).convert_alpha()
            for y in range(-(top%210),height,210):image.blit(self.sand,(0,y))
            shade=pg.Surface(image.get_size(),pg.SRCALPHA)
            for col,surface in enumerate(heights):
                row=surface-top
                world_x=(start+col)/SCALE
                distance=RIVER[0]-world_x if world_x<=RIVER[0] else world_x-RIVER[1] if world_x>=RIVER[1] else 10000
                wet=max(0.,1-distance/120)
                pg.draw.line(image,(0,0,0,0),(col,0),(col,row-1))
                slope=(sand_height((start+col+3)/SCALE)-sand_height((start+col-3)/SCALE))/4
                for depth in range(0,48,4):
                    alpha=round(max(0.,slope)*(1-depth/48)*42+wet*100*(1-depth/48)**2)
                    if alpha:pg.draw.line(shade,(83,48,18,min(85,alpha)),(col,row+depth),(col,row+depth+3))
                pg.draw.line(image,(245,203,125,255),(col,row),(col,row+1))
            image.blit(shade,(0,0));chunks.append((start,top,image))
            # Sand below the waterline becomes a submerged shelf, not a cliff.
            for col in range(width):
                world_x=(start+col)/SCALE
                distance=RIVER[0]-world_x if world_x<=RIVER[0] else world_x-RIVER[1] if world_x>=RIVER[1] else 10000
                if distance>145:continue
                for row in range(max(0,pixel(WATER_Y*SCALE)-top),height):
                    depth=(top+row)/SCALE-WATER_Y
                    strength=max(0.,min(1.,1-distance/(50+depth*.9)))
                    strength=strength*strength*(3-2*strength)
                    color=image.get_at((col,row));color.a=round(color.a*(1-strength))
                    image.set_at((col,row),color)
        return chunks

    @staticmethod
    def make_shore():
        atlas=pg.Surface((2048,96*12),pg.SRCALPHA).convert_alpha()
        for index in range(48):
            frame=pg.Surface((256,96),pg.SRCALPHA)
            for ring in range(3):
                age=(index/48+ring/3)%1
                alpha=round(math.sin(math.pi*age)*72)
                x=126+round(age*44);y=21+ring*10+round(age*5)
                pg.draw.arc(frame,(215,231,212,alpha),(x,y,35+round(age*42),9),.15*math.pi,1.05*math.pi,1)
                pg.draw.line(frame,(133,192,187,alpha//2),(x+6,y+8),(x+20,y+8),1)
            atlas.blit(frame,(index%8*256,index//8*96))
            atlas.blit(pg.transform.flip(frame,True,False),(index%8*256,(index//8+6)*96))
        return atlas

    def shorelines(self,canvas,camera,time):
        frame=int((time/2.4%1)*48)
        for side,x in enumerate(RIVER):
            if -120<x-camera<1400:
                px,py=canvas.point((x-camera,WATER_Y))
                area=(frame%8*256,(frame//8+side*6)*96,256,96)
                canvas.native.blit(self.shore,(px-128,py-24),area)

    def dune_floor(self,canvas,ground,camera):
        camera=pixel(camera*SCALE)
        left=max(pixel(ground.x*SCALE),camera)
        right=min(pixel((ground.x+ground.w)*SCALE),camera+1920)
        for start,top,image in self.dunes:
            a=max(left,start);b=min(right,start+image.get_width())
            if b>a:canvas.native.blit(image,(a-camera,top),(a-start,0,b-a,image.get_height()))

    @staticmethod
    def make_water(path):
        # One continuous river: the photographic reflection must never tile.
        width=pixel((RIVER[1]-RIVER[0]+290)*SCALE)
        atlas=pg.Surface((width,128*48),pg.SRCALPHA).convert_alpha()
        padding=14
        vertical_padding=5
        source=pg.image.load(str(path)).convert()
        # Preserve the proportions of the waves instead of flattening the photo.
        band_height=max(1,round((128+vertical_padding*2)*source.get_width()/(width+padding*2)))
        band=source.subsurface((0,round(source.get_height()*.4),source.get_width(),band_height))
        base=pg.transform.smoothscale(band,(width+padding*2,128+vertical_padding*2))
        rng=random.Random(913)
        ripples=[(rng.randrange(width),rng.randrange(7,125),rng.randrange(9,35),rng.random()*math.tau) for _ in range(180)]
        for frame in range(48):
            image=pg.Surface((width,128),pg.SRCALPHA).convert_alpha();phase=frame/48*math.tau
            for y in range(128):
                # Travelling waves deform the reflection in both directions.
                # Overscan supplies every sample without wrapping any edge.
                shift=round(math.sin(phase+y*.15)*8+math.sin(phase*2-y*.07)*3)
                lift=round(math.sin(phase+y*.085)*3)
                image.blit(base,(0,y),(padding+shift,vertical_padding+y+lift,width,1))
            light=pg.Surface((width,128),pg.SRCALPHA)
            for x,y,ripple_width,a in ripples:
                ox=round(x+math.sin(phase+a)*15)
                oy=round(y+math.sin(phase+a*2)*3)
                strength=round(45+30*math.sin(phase+a))
                color=(213,224,194,strength)
                pg.draw.line(light,color,(ox,oy),(ox+ripple_width,oy),1)
            image.blit(light,(0,0))
            # A softly covered crest follows the same phase as the reflections.
            # Its world-space profile stays continuous while the camera scrolls.
            for x in range(width):
                top=WATER_CREST_MARGIN+2*math.sin(phase+x*.027)+.9*math.sin(phase*2-x*.051)
                edge=int(top)
                pg.draw.line(image,(0,0,0,0),(x,0),(x,edge-1))
                color=image.get_at((x,edge));color.a=round((1-(top-edge))*255)
                image.set_at((x,edge),color)
            atlas.blit(image,(0,frame*128))
        return atlas

    def background(self,canvas,camera):
        for layer in self.layers:layer.draw(canvas.native,camera*SCALE)

    def river(self,canvas,camera,time):
        left=pixel((RIVER[0]-145-camera)*SCALE);right=pixel((RIVER[1]+145-camera)*SCALE)
        if left>=1920 or right<=0:return
        frame=int((time/2.4%1)*48)
        visible_left=max(0,left);visible_right=min(1920,right)
        area=pg.Rect(visible_left-left,frame*128,visible_right-visible_left,128)
        canvas.native.blit(self.water,(visible_left,pixel(WATER_Y*SCALE)-WATER_CREST_MARGIN),area)

    def sand_floor(self,canvas,platform,camera):
        rect=canvas.rect((platform.x-camera,platform.y,platform.w,platform.h))
        left=max(0,rect.left);right=min(1920,rect.right)
        if right<=left:return
        origin=-pixel(camera*SCALE);tile=self.sand.get_width()
        first=(left-origin)//tile
        for index in range(first,math.ceil((right-origin)/tile)):
            x=origin+index*tile;clipped=max(left,x);width=min(right,x+tile)-clipped
            if width>0:
                canvas.native.blit(self.sand,(clipped,rect.top),
                                   (clipped-x,0,width,min(self.sand.get_height(),rect.h)))
        draw.rect(canvas,(234,191,110),(platform.x-camera,platform.y,platform.w,4))

    def platform(self,canvas,platform,camera):
        art_y=platform.y
        if platform.kind=='rock':
            # The rock is solid down into the soil; only its exposed face is art.
            from types import SimpleNamespace
            base=SimpleNamespace(x=platform.x,y=620,w=platform.w,h=140)
            self.sand_floor(canvas,base,camera)
            area=self.areas[('rock',platform.w,620-platform.y)]
        else:
            art_y-=BRIDGE_DECK_CENTER
            area=self.areas[('bridge',platform.w)]
            for fraction in (.08,.34,.65,.92):
                x=platform.x+platform.w*fraction-camera
                draw.rect(canvas,(81,57,32),(x-3,art_y+22,6,max(0,WATER_Y+25-art_y-22)))
        x,y=canvas.point((platform.x-camera,art_y))
        canvas.native.blit(self.props,(x,y),area)
        if platform.kind=='rock':
            left,top,image=self.rock_sand[platform.x]
            canvas.native.blit(image,(left-pixel(camera*SCALE),top))

    def reeds(self,canvas,camera):
        for x,offset in self.reed_offsets.items():
            if -120<x-camera<1400:
                area=self.areas[('reeds',x)]
                px,py=canvas.point((x-camera,sand_height(x)))
                canvas.native.blit(self.props,(px-area.w//2,py+offset),area)
