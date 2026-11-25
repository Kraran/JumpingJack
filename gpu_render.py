"""Full HD GPU scene composition, with a software backend for offline tests."""
from collections import OrderedDict
import pygame as pg
from rendering import integer_viewport, pixel

FULL_HD=(1920,1080)
DESIGN=(1280,720)
SCALE=1.5


class NativeCanvas:
    def __init__(self, window=None):
        self.size=FULL_HD
        self.renderer=None
        self.framebuffer=None
        self.surface=None
        self.textures=OrderedDict()
        self.primitives=OrderedDict()
        self.scaled_images=OrderedDict()
        self.uploads=0
        self.draw_calls=0
        if window is not None:
            from pygame._sdl2.video import Renderer, Texture
            self.renderer=Renderer.from_window(window)
            self.framebuffer=Texture(self.renderer,FULL_HD,target=True)
            self.framebuffer.blend_mode=pg.BLENDMODE_NONE
        else:
            self.surface=pg.Surface(FULL_HD).convert()

    @property
    def gpu(self):return self.renderer is not None
    def get_width(self):return self.size[0]
    def get_height(self):return self.size[1]
    def get_size(self):return self.size

    def begin(self):
        self.draw_calls=0
        if self.gpu:
            self.renderer.target=self.framebuffer
            self.renderer.logical_size=FULL_HD
            self.renderer.draw_color=(10,17,22,255)
            self.renderer.clear()
        else:self.surface.fill((10,17,22))

    def texture(self, image):
        key=id(image)
        entry=self.textures.pop(key,None)
        if entry is None:
            from pygame._sdl2.video import Texture
            entry=(image,Texture.from_surface(self.renderer,image))
            self.uploads+=1
        self.textures[key]=entry
        # Keep the hero/enemy poses and the prewarmed menu/HUD text resident.
        if len(self.textures)>2048:self.textures.popitem(last=False)
        return entry[1]

    def preload(self, images):
        if self.gpu:
            previous=self.renderer.target
            self.renderer.target=self.framebuffer
            try:
                for image in images:
                    # Exercise each texture offscreen before it appears in play.
                    # Restoring the target submits the queued warm-up draws.
                    self.texture(image).draw(dstrect=(0,0,1,1))
            finally:self.renderer.target=previous

    def blit(self,image,dest,area=None):
        source=pg.Rect(area) if area is not None else image.get_rect()
        if isinstance(dest,pg.Rect):rect=dest.copy()
        elif len(dest)==4:rect=pg.Rect(dest)
        else:rect=pg.Rect(pixel(dest[0]),pixel(dest[1]),source.w,source.h)
        if rect.w<=0 or rect.h<=0 or not rect.colliderect(pg.Rect(0,0,*FULL_HD)):return rect
        self.draw_calls+=1
        if self.gpu:
            self.texture(image).draw(source,rect)
        elif rect.size==source.size:
            self.surface.blit(image,rect,source)
        else:
            key=(id(image),tuple(source),rect.size)
            entry=self.scaled_images.pop(key,None)
            if entry is None:entry=(image,pg.transform.scale(image.subsurface(source),rect.size))
            self.scaled_images[key]=entry
            if len(self.scaled_images)>640:self.scaled_images.popitem(last=False)
            self.surface.blit(entry[1],rect)
        return rect

    def rect(self,color,rect,width=0):
        rect=pg.Rect(rect)
        if rect.w<=0 or rect.h<=0:return
        self.draw_calls+=1
        if self.gpu:
            self.renderer.draw_color=pg.Color(color)
            self.renderer.draw_blend_mode=pg.BLENDMODE_BLEND
            if not width:self.renderer.fill_rect(rect)
            else:
                for i in range(min(width,(min(rect.size)+1)//2)):
                    self.renderer.draw_rect(rect.inflate(-2*i,-2*i))
        else:pg.draw.rect(self.surface,color,rect,width)

    def blit_additive(self,image,dest,area=None):
        """Composite preloaded light without uploading or reading a frame."""
        source=pg.Rect(area) if area is not None else image.get_rect()
        rect=pg.Rect(dest) if isinstance(dest,pg.Rect) else pg.Rect(dest,source.size)
        if rect.w<=0 or rect.h<=0 or not rect.colliderect(pg.Rect(0,0,*FULL_HD)):return rect
        self.draw_calls+=1
        if self.gpu:
            texture=self.texture(image);previous=texture.blend_mode
            try:
                texture.blend_mode=pg.BLENDMODE_ADD
                texture.draw(source,rect)
            finally:texture.blend_mode=previous
        else:
            self.surface.blit(image,rect,source,special_flags=pg.BLEND_RGB_ADD)
        return rect

    def raster(self,key,size,paint,position):
        image=self.primitives.pop(key,None)
        if image is None:
            image=pg.Surface(size,pg.SRCALPHA)
            paint(image)
        self.primitives[key]=image
        if len(self.primitives)>256:self.primitives.popitem(last=False)
        self.blit(image,position)

    def present(self,screen):
        if self.gpu:
            self.renderer.target=None
            self.renderer.logical_size=FULL_HD
            self.renderer.draw_color=(10,17,22,255)
            self.renderer.clear()
            self.framebuffer.draw(dstrect=(0,0,*FULL_HD))
            self.renderer.present()
        else:
            size,pos=integer_viewport(screen.get_size(),FULL_HD)
            screen.fill((10,17,22))
            image=self.surface if size==FULL_HD else pg.transform.scale(self.surface,size)
            screen.blit(image,pos)
            pg.display.flip()

    def capture(self):
        """Readback is restricted to explicit screenshots, never the game loop."""
        if not self.gpu:return self.surface.copy()
        previous=self.renderer.target
        self.renderer.target=self.framebuffer
        image=self.renderer.to_surface()
        self.renderer.target=previous
        return image

    def release(self):
        # Texture destructors must run BEFORE pygame destroys their SDL renderer.
        if self.renderer is not None:self.renderer.target=None
        self.textures.clear()
        self.framebuffer=None
        self.renderer=None
        self.primitives.clear()
        self.scaled_images.clear()


class DesignCanvas:
    """Map world/layout units directly to native HD pixels, never upscale a frame."""
    def __init__(self,native):self.native=native
    def get_width(self):return DESIGN[0]
    def get_height(self):return DESIGN[1]
    def point(self,p):return (pixel(p[0]*SCALE),pixel(p[1]*SCALE))
    def rect(self,r):
        x,y,w,h=r
        a,b=self.point((x,y));c,d=self.point((x+w,y+h))
        return pg.Rect(a,b,c-a,d-b)

    def blit(self,image,dest,area=None):
        source=pg.Rect(area) if area is not None else image.get_rect()
        x,y=dest[:2]
        rect=self.rect((x,y,source.w,source.h))
        return self.native.blit(image,rect,source)

    def blit_native(self,image,pos,anchor='topleft'):
        rect=image.get_rect(**{anchor:self.point(pos)})
        return self.native.blit(image,rect)


class Draw:
    """Rasterize small curved shapes once; GPU rectangles stay native primitives."""
    def rect(self,target,color,rect,width=0,**kwargs):
        if not isinstance(target,DesignCanvas):return pg.draw.rect(target,color,rect,width,**kwargs)
        r=target.rect(rect);w=max(1,pixel(width*SCALE)) if width else 0
        radius=kwargs.get('border_radius',0)
        if not radius:return target.native.rect(color,r,w)
        radius=pixel(radius*SCALE)
        key=('rect',tuple(color),tuple(r.size),w,radius)
        target.native.raster(key,r.size,lambda s:pg.draw.rect(s,color,s.get_rect(),w,border_radius=radius),r.topleft)

    def ellipse(self,target,color,rect,width=0):
        if not isinstance(target,DesignCanvas):return pg.draw.ellipse(target,color,rect,width)
        r=target.rect(rect)
        if r.w<=0 or r.h<=0:return
        w=max(1,pixel(width*SCALE)) if width else 0
        key=('ellipse',tuple(color),r.size,w)
        target.native.raster(key,r.size,lambda s:pg.draw.ellipse(s,color,s.get_rect(),w),r.topleft)

    def circle(self,target,color,center,radius,width=0):
        if not isinstance(target,DesignCanvas):return pg.draw.circle(target,color,center,radius,width)
        x,y=target.point(center);r=max(1,pixel(radius*SCALE))
        w=max(1,pixel(width*SCALE)) if width else 0
        key=('circle',tuple(color),r,w)
        target.native.raster(key,(r*2+1,r*2+1),lambda s:pg.draw.circle(s,color,(r,r),r,w),(x-r,y-r))

    def polygon(self,target,color,points,width=0):
        if not isinstance(target,DesignCanvas):return pg.draw.polygon(target,color,points,width)
        points=[target.point(p) for p in points]
        x=min(p[0] for p in points);y=min(p[1] for p in points)
        rel=tuple((a-x,b-y) for a,b in points)
        size=(max(p[0] for p in rel)+1,max(p[1] for p in rel)+1)
        w=max(1,pixel(width*SCALE)) if width else 0
        key=('polygon',tuple(color),rel,w)
        target.native.raster(key,size,lambda s:pg.draw.polygon(s,color,rel,w),(x,y))

    def line(self,target,color,start,end,width=1):
        if not isinstance(target,DesignCanvas):return pg.draw.line(target,color,start,end,width)
        a=target.point(start);b=target.point(end);w=max(1,pixel(width*SCALE))
        if a[0]==b[0]:return target.native.rect(color,(a[0]-w//2,min(a[1],b[1]),w,abs(b[1]-a[1])+1))
        if a[1]==b[1]:return target.native.rect(color,(min(a[0],b[0]),a[1]-w//2,abs(b[0]-a[0])+1,w))
        x=min(a[0],b[0])-w;y=min(a[1],b[1])-w
        rel=((a[0]-x,a[1]-y),(b[0]-x,b[1]-y))
        size=(abs(b[0]-a[0])+2*w+1,abs(b[1]-a[1])+2*w+1)
        key=('line',tuple(color),rel,w)
        target.native.raster(key,size,lambda s:pg.draw.line(s,color,*rel,w),(x,y))

    def lines(self,target,color,closed,points,width=1):
        if not isinstance(target,DesignCanvas):return pg.draw.lines(target,color,closed,points,width)
        for a,b in zip(points,points[1:]):self.line(target,color,a,b,width)
        if closed:self.line(target,color,points[-1],points[0],width)

    def arc(self,target,color,rect,start,stop,width=1):
        if not isinstance(target,DesignCanvas):return pg.draw.arc(target,color,rect,start,stop,width)
        r=target.rect(rect);w=max(1,pixel(width*SCALE))
        key=('arc',tuple(color),r.size,start,stop,w)
        target.native.raster(key,r.size,lambda s:pg.draw.arc(s,color,s.get_rect(),start,stop,w),r.topleft)


draw=Draw()
