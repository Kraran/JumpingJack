"""Preloaded three-plane temple interior and looping brazier flames."""
import math
from functools import lru_cache
import pygame as pg
from gpu_render import SCALE,draw
from rendering import ParallaxLayer,pixel
from temple_level import FLOORS

TORCH_X=tuple(range(650,14400,1050))
TORCH_Y=390
FLAME_SIZE=(144,160)
FLAME_ANCHOR=(72,145)
FLAME_FRAMES=48
FLAME_PERIOD=1.6


class TempleArt:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)

    def __init__(self,assets):
        far=pg.transform.smoothscale(pg.image.load(str(assets/'temple-interior-v1.png')).convert(),(3240,1080))
        far.fill((155,160,172),special_flags=pg.BLEND_RGB_MULT)
        self.ceiling=pg.transform.smoothscale(far.subsurface((1020,0,1024,90)),(1024,180))
        sheet=pg.image.load(str(assets/'temple-props-v1.png')).convert_alpha()
        cw,ch=sheet.get_width()//2,sheet.get_height()//2;sources=[]
        for index in range(4):
            cell=sheet.subsurface((index%2*cw,index//2*ch,cw,ch))
            bounds=cell.get_bounding_rect(min_alpha=64)
            if index==3:
                # The adjacent doorway spills two fragments into the left
                # edge of this cell. Keep the connected brazier, not the
                # aggregate bounds of everything in the atlas quadrant.
                components=pg.mask.from_surface(cell,63).get_bounding_rects()
                bounds=max(components,key=lambda rect:rect.w*rect.h)
            sources.append(cell.subsurface(bounds))
        middle=pg.Surface((2400,1080),pg.SRCALPHA).convert_alpha()
        near=pg.Surface((3000,1080),pg.SRCALPHA).convert_alpha()
        for surface,source,x,height,tint in ((middle,sources[0],400,850,(175,166,146)),
                (middle,sources[1],1740,470,(154,145,128)),(near,sources[0],2660,1030,(90,91,89))):
            image=pg.transform.smoothscale(source,(round(height*source.get_width()/source.get_height()),height))
            image.fill((*tint,255),special_flags=pg.BLEND_RGBA_MULT)
            surface.blit(image,(x,930-height))
        self.layers=[ParallaxLayer(name,image,n,25) for name,image,n in
                     (('temple-far',far,2),('temple-middle',middle,6),('temple-near',near,12))]
        self.brazier=pg.transform.smoothscale(sources[3],(86,94))
        self.gate=pg.transform.smoothscale(sources[2],(840,780))
        # Fill only the existing opening; keep the sculpted jambs intact.
        stairs=pg.transform.smoothscale(pg.image.load(str(assets/'temple-sanctuary-stairs-v1.png')).convert(),(266,508))
        self.gate.blit(stairs,(310,272))
        self.stone=pg.transform.smoothscale(pg.image.load(str(assets/'sandstone.png')).convert(),(256,256))
        self.stone.fill((165,151,126),special_flags=pg.BLEND_RGB_MULT)
        self.pit_walls={pixel((b-a)*SCALE):self.make_pit_wall(self.stone,pixel((b-a)*SCALE))
                       for (_,a),(b,_) in zip(FLOORS,FLOORS[1:])}
        sheet=pg.image.load(str(assets/'temple-flames-v2.png')).convert_alpha()
        authored=[]
        for i in range(24):
            x0,x1=round(i%6*sheet.get_width()/6),round((i%6+1)*sheet.get_width()/6)
            y0,y1=round(i//6*sheet.get_height()/4),round((i//6+1)*sheet.get_height()/4)
            authored.append(pg.transform.smoothscale(sheet.subsurface((x0,y0,x1-x0,y1-y0)),FLAME_SIZE))
        fw,fh=FLAME_SIZE
        self.flames=pg.Surface((fw*8,fh*6),pg.SRCALPHA).convert_alpha()
        self.flame_masks=[];self.flame_bounds=[]
        for i in range(FLAME_FRAMES):
            phase=i*24/FLAME_FRAMES;index=int(phase);weight=phase-index
            image=authored[index].copy();other=authored[(index+1)%24].copy()
            image.fill((round(255*(1-weight)),)*4,special_flags=pg.BLEND_RGBA_MULT)
            other.fill((round(255*weight),)*4,special_flags=pg.BLEND_RGBA_MULT)
            image.blit(other,(0,0),special_flags=pg.BLEND_RGBA_ADD)
            self.flames.blit(image,(i%8*fw,i//8*fh))
            # Warm, opaque fire burns; faint light and smoke do not.
            mask=pg.mask.Mask(FLAME_SIZE)
            for y in range(fh-9):
                for x in range(fw):
                    r,g,b,a=image.get_at((x,y))
                    if a>=120 and r>=160 and g>=65 and b<r*.87:mask.set_at((x,y))
            self.flame_masks.append(mask)
            bounds=mask.get_bounding_rects()
            self.flame_bounds.append(bounds[0].unionall(bounds) if bounds else pg.Rect(0,0,0,0))
        self.images=[far,middle,near,self.brazier,self.gate,self.flames,self.stone,self.ceiling,*self.pit_walls.values()]

    @staticmethod
    def make_pit_wall(stone,width):
        """Recessed masonry and converging side faces, using the floor stone."""
        height=pixel(100*SCALE)
        wall=pg.Surface((width,height),pg.SRCALPHA).convert_alpha();wall.fill((35,29,23))
        row=0;y=0
        while y<height:
            depth=y/height;bh=round(26-depth*8);bw=round(78-depth*22)
            for col,x in enumerate(range(-bw if row%2 else 0,width,bw)):
                sx=(row*43+col*61)%(stone.get_width()-96)
                sy=(row*37+col*19)%(stone.get_height()-48)
                brick=pg.transform.smoothscale(stone.subsurface((sx,sy,96,48)),(bw-2,bh-2))
                brick.fill((190,180,163),special_flags=pg.BLEND_RGB_MULT)
                wall.blit(brick,(x+1,y+1))
                pg.draw.line(wall,(85,69,47),(x+2,y+1),(x+bw-2,y+1))
            y+=bh;row+=1
        # Side walls widen into the opening with depth; these angled seams
        # separate the foreground cut from the smaller rear masonry courses.
        side=stone.copy();side.fill((133,129,118),special_flags=pg.BLEND_RGB_MULT)
        for y in range(height):
            inset=round(9+y*.17)
            for x in range(inset):
                color=side.get_at(((x*3+y//3)%256,(y*2)%256))
                wall.set_at((x,y),color);wall.set_at((width-1-x,y),color)
            if y%29<2:
                pg.draw.line(wall,(30,25,20),(0,y),(inset-1,y))
                pg.draw.line(wall,(30,25,20),(width-inset,y),(width-1,y))
        pg.draw.line(wall,(107,83,52),(9,0),(round(9+height*.17),height-1))
        pg.draw.line(wall,(74,57,37),(width-10,0),(width-round(10+height*.17),height-1))
        return wall

    def background(self,canvas,camera,time):
        for layer in self.layers:layer.draw(canvas.native,camera*SCALE)
        for (_,left),(right,_) in zip(FLOORS,FLOORS[1:]):
            image=self.pit_walls[pixel((right-left)*SCALE)]
            x=pixel((left-camera)*SCALE)
            if x<1920 and x+image.get_width()>0:
                canvas.native.blit(image,(x,pixel(620*SCALE)))
        frame=self.flame_frame(time)
        fw,fh=FLAME_SIZE
        for x in TORCH_X:
            if -120<x-camera<1400:
                px,py=canvas.point((x-camera,TORCH_Y))
                canvas.native.blit(self.brazier,(px-43,py))
                canvas.native.blit(self.flames,(px-FLAME_ANCHOR[0],py+6-FLAME_ANCHOR[1]),
                                   (frame%8*fw,frame//8*fh,fw,fh))
        if camera>12500:
            canvas.native.blit(self.gate,(pixel((13860-camera)*SCALE),pixel(620*SCALE)-780))

    def draw_torch(self,canvas,x,y,time):
        frame=self.flame_frame(time);fw,fh=FLAME_SIZE;px,py=canvas.point((x,y))
        canvas.native.blit(self.brazier,(px-43,py))
        canvas.native.blit(self.flames,(px-FLAME_ANCHOR[0],py+6-FLAME_ANCHOR[1]),
                           (frame%8*fw,frame//8*fh,fw,fh))

    @staticmethod
    def flame_frame(time):return int((time/FLAME_PERIOD%1)*FLAME_FRAMES)

    def flame_hits(self,hero,time,positions=None):
        return self.flame_source(hero,time,positions) is not None

    def flame_source(self,hero,time,positions=None):
        index=self.flame_frame(time);mask=self.flame_masks[index]
        height=max(hero.body_height,round(54-22*hero.previous_crouch))
        width=pixel(30*SCALE);height=pixel(height*SCALE)
        old=(hero.px*SCALE,hero.py*SCALE);end=(hero.x*SCALE,hero.y*SCALE)
        swept=pg.Rect(pixel(min(old[0],end[0])-15*SCALE),pixel(min(old[1],end[1])-height),
                      math.ceil(abs(end[0]-old[0])+width+2),math.ceil(abs(end[1]-old[1])+height+2))
        body=pg.mask.Mask((width,height),fill=True)
        steps=max(1,math.ceil(max(abs(end[0]-old[0]),abs(end[1]-old[1]))/2))
        for x,y in (positions if positions is not None else ((x,TORCH_Y) for x in TORCH_X)):
            top=pixel(y*SCALE)+6-FLAME_ANCHOR[1]
            left=pixel(x*SCALE)-FLAME_ANCHOR[0]
            if not swept.colliderect(self.flame_bounds[index].move(left,top)):continue
            for step in range(steps+1):
                t=step/steps
                hx=pixel(old[0]+(end[0]-old[0])*t-15*SCALE)
                hy=pixel(old[1]+(end[1]-old[1])*t-height)
                if mask.overlap(body,(hx-left,hy-top)) is not None:return (x,y)
        return None

    def floor(self,canvas,platform,camera):
        x=platform.x-camera
        if platform.kind=='temple_ceiling':
            origin=-pixel(camera*SCALE)%1024
            for left in range(origin-1024,1920,1024):canvas.native.blit(self.ceiling,(left,0))
            draw.rect(canvas,(38,34,26),(0,116,1280,4))
            return
        rect=canvas.rect((x,platform.y,platform.w,platform.h))
        left=max(0,rect.left);right=min(1920,rect.right);origin=-pixel(camera*SCALE)
        for tile in range((left-origin)//256,math.ceil((right-origin)/256)):
            start=origin+tile*256;visible=max(left,start);width=min(right,start+256)-visible
            if width>0:canvas.native.blit(self.stone,(visible,rect.top),(visible-start,0,width,min(256,rect.h)))
        draw.rect(canvas,(198,158,91),(x,platform.y,platform.w,6))

    def foreground(self,canvas,camera):
        if camera>12500:
            # Disappear behind the sanctuary jamb instead of walking over it.
            canvas.native.blit(self.gate,(pixel((14300-camera)*SCALE),pixel(620*SCALE)-780),
                               (660,0,180,780))
