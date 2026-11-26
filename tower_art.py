"""Absolute vertical parallax and a translated gameplay canvas, all preloaded."""
from functools import lru_cache
import pygame as pg
from gpu_render import SCALE,DesignCanvas
from rendering import pixel
import tower_level as tower


class VerticalNative:
    def __init__(self,native,offset):self.native=native;self.offset=pixel(offset*SCALE)
    def blit(self,image,dest,area=None):
        if isinstance(dest,pg.Rect):dest=dest.move(0,-self.offset)
        else:dest=(dest[0],dest[1]-self.offset,*dest[2:])
        return self.native.blit(image,dest,area)
    def blit_faded(self,image,dest,area,opacity):
        return self.native.blit_faded(image,(dest[0],dest[1]-self.offset),area,opacity)
    def rect(self,color,rect,width=0):return self.native.rect(color,pg.Rect(rect).move(0,-self.offset),width)
    def raster(self,key,size,paint,position):
        return self.native.raster(key,size,paint,(position[0],position[1]-self.offset))
    def get_width(self):return self.native.get_width()
    def get_height(self):return self.native.get_height()


class VerticalCanvas(DesignCanvas):
    def __init__(self,native,offset):super().__init__(VerticalNative(native,offset))


class TowerArt:
    @classmethod
    @lru_cache(maxsize=2)
    def load(cls,assets):return cls(assets)
    def __init__(self,assets):
        source=pg.image.load(str(assets/'tower-interior-v1.png')).convert()
        far=pg.transform.smoothscale(source,(1920,1280))
        far.fill((144,146,153),special_flags=pg.BLEND_RGB_MULT)
        # Overlap the repeated ends so vertical tiling cannot expose a hard seam.
        band=96;period=far.get_height()-band
        self.far=pg.Surface((1920,period)).convert()
        self.far.blit(far,(0,0),(0,0,1920,period))
        for y in range(band):
            row=far.subsurface((0,period+y,1920,1)).copy()
            head=far.subsurface((0,y,1920,1)).copy()
            alpha=round(255*y/(band-1));row.fill((255-alpha,)*3,special_flags=pg.BLEND_RGB_MULT)
            head.fill((alpha,)*3,special_flags=pg.BLEND_RGB_MULT)
            row.blit(head,(0,0),special_flags=pg.BLEND_RGB_ADD);self.far.blit(row,(0,y))
        stone=pg.transform.smoothscale(pg.image.load(str(assets/'sandstone.png')).convert(),(256,256))
        stone.fill((136,125,108),special_flags=pg.BLEND_RGB_MULT);self.stone=stone
        self.middle=pg.Surface((1920,1536),pg.SRCALPHA).convert_alpha()
        for x in (105,1695):
            for y in range(0,1536,256):
                strip=pg.transform.smoothscale(stone,(120,256));strip.set_alpha(145)
                self.middle.blit(strip,(x,y))
                brace=pg.transform.smoothscale(stone.subsurface((0,30,128,20)),(136,20))
                brace.set_alpha(185);self.middle.blit(brace,(x-8,y+20))
        from temple_art import TempleArt
        gate=TempleArt.load(assets).gate
        self.exit=pg.transform.smoothscale(gate,(420,390))
        self.images=[self.far,self.middle,self.stone,self.exit]

    @staticmethod
    def vertical_tiles(native,image,camera,ratio):
        offset=pixel(camera*SCALE*ratio)%image.get_height()
        y=-offset
        while y<1080:native.blit(image,(0,y));y+=image.get_height()

    def background(self,canvas,camera):
        self.vertical_tiles(canvas.native,self.far,camera,.18)
        self.vertical_tiles(canvas.native,self.middle,camera,.42)
        if camera<720:
            canvas.native.blit(self.exit,(pixel(tower.SUMMIT[0]*SCALE)-210,
                                         pixel((tower.SUMMIT[1]-camera)*SCALE)-390))

    def structure(self,canvas,platform,camera):
        # Limit source and destination to the visible portion of this tall wall.
        left=pixel(platform.x*SCALE);right=pixel((platform.x+platform.w)*SCALE)
        top=max(pixel(platform.y*SCALE),pixel(camera*SCALE))
        bottom=min(pixel((platform.y+platform.h)*SCALE),pixel(camera*SCALE)+1080)
        if bottom<=top:return
        first=top//256*256
        for y in range(first,bottom,256):
            a=max(top,y);height=min(bottom,y+256)-a
            for x in range(left,right,256):
                width=min(256,right-x)
                canvas.native.blit(self.stone,(x,a),(0,a-y,width,height))
