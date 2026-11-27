"""Greek world visual study: preloaded scenery, independent of campaign state."""
import pygame as pg

from gpu_render import SCALE
from platform_sprites import SacredPlatforms
from rendering import ParallaxLayer, pixel


class GreeceArt:
    def __init__(self, assets):
        self.layers = []
        soil = pg.image.load(str(assets / 'greece-ground-v1.png')).convert_alpha()
        for name, width, numerator, rise in (
            ('far', 2520, 2, 0), ('middle', 3240, 6, 175),
            ('near', 3240, 12, 40),
        ):
            source = pg.image.load(str(assets / f'greece-{name}-v1.png'))
            source = source.convert() if name == 'far' else source.convert_alpha()
            if name != 'far' and source.get_at((0, 0)).a > 8:
                raise ValueError(f'Greek {name}: transparent background required')
            image = pg.transform.smoothscale(source, (width, 950 if name == 'near' else 1080))
            if rise:
                plane = pg.Surface((width, 1080), pg.SRCALPHA).convert_alpha()
                plane.blit(image, (0, -rise))
                image = plane
            if name != 'far':
                # Each depth plane owns its ground. Compositing at load time
                # guarantees identical scrolling and pixel rounding for both.
                terrain_height, terrain_y = (360, 710) if name == 'middle' else (220, 825)
                landscape = pg.Surface((width, 1080), pg.SRCALPHA).convert_alpha()
                landscape.blit(pg.transform.smoothscale(soil, (width, terrain_height)), (0, terrain_y))
                landscape.blit(image, (0, 0))
                image = landscape
            self.layers.append(ParallaxLayer(name, image, numerator, 25, name != 'far'))
        self.platforms = SacredPlatforms(assets / 'greece-platforms-v1.png', (120, 180, 240, 300, 360))
        # A quiet masonry foundation below the richly carved playable lip.
        self.foundation = pg.Surface((540, 150)).convert()
        self.foundation.fill((194, 185, 163))
        for row in range(3):
            for column in range(-1, 4):
                x = column * 180 + (90 if row % 2 else 0)
                rectangle = pg.Rect(x, row * 50, 180, 50)
                shade = (row * 7 + column * 3) % 13
                pg.draw.rect(self.foundation, (218-shade, 211-shade, 190-shade), rectangle.inflate(-2, -2))
                pg.draw.line(self.foundation, (236, 229, 207), rectangle.topleft, rectangle.topright)

    @property
    def images(self):
        return [layer.image for layer in self.layers] + self.platforms.images + [self.foundation]

    def background(self, native, camera):
        # The opaque coastal panorama covers this 4,800-unit study without wrapping.
        # Raise the distant horizon so a band of sea remains beyond the dry land.
        native.blit(self.layers[0].image, (-150-self.layers[0].offset(camera*SCALE), -100))
        for layer in self.layers[1:]:
            layer.draw(native, camera*SCALE)

    def platform(self, canvas, platform, camera):
        left = pixel((platform.x-camera)*SCALE)
        right = pixel((platform.x+platform.w-camera)*SCALE)
        if right < 0 or left > 1920:
            return
        if not platform.ground:
            self.platforms.draw(canvas, platform, camera)
            return
        top = pixel(platform.y*SCALE)
        start = max(0, (-left)//540)
        end = min((right-left+539)//540, (1920-left+539)//540)
        for index in range(start, end):
            x = left+index*540
            width = min(540, right-x)
            bottom=min(1080,pixel((platform.y+platform.h)*SCALE))
            for y in range(max(0,top)//150*150,bottom,150):
                a=max(top,y,0);height=min(bottom,y+150)-a
                if height>0:canvas.native.blit(self.foundation,(x,a),(0,a-y,width,height))
            if platform.kind!='greek_ceiling':
                canvas.native.blit(self.platforms.atlas, (x, top, width, 48),
                                   self.platforms.areas[360])


class GreekWorldArt:
    """Campaign variants share platforms while keeping ground in each scenery plane."""
    def __init__(self, assets):
        self.coast=GreeceArt(assets)
        self.variants={}
        # Cover the complete camera range without a visible panorama wrap.
        far=pg.Surface((3840,1080)).convert()
        far.fill((187,177,149))
        far.blit(pg.transform.smoothscale(self.coast.layers[0].image,(3840,1080)),(0,-100))
        outside=[ParallaxLayer('greek-far',far,2,25,False)] + self.coast.layers[1:]
        self.variants[5]=outside
        self.variants[6]=outside
        gallery=pg.transform.smoothscale(pg.image.load(str(assets/'greece-gallery-v1.png')).convert(),(3840,1080))
        props=pg.image.load(str(assets/'greece-gallery-props-v1.png')).convert_alpha()
        middle=pg.Surface((3240,1080),pg.SRCALPHA).convert_alpha()
        middle.blit(pg.transform.smoothscale(props,(2000,670)),(300,260))
        near=pg.Surface((3240,1080),pg.SRCALPHA).convert_alpha()
        cell=props.subsurface((0,0,round(props.get_width()*.19),props.get_height()))
        column=cell.subsurface(cell.get_bounding_rect(min_alpha=64))
        near.blit(pg.transform.smoothscale(column,(180,850)),(2600,80))
        # Both architectural planes need their own continuous marble foundation.
        # Keep it in the same texture as the columns, including across gameplay
        # pits, so their feet cannot hang over a differently scrolling backdrop.
        stone=gallery.subsurface((0,1000,gallery.get_width(),80))
        coping=gallery.subsurface((0,980,gallery.get_width(),20))
        def supported_plane(plane):
            top=plane.get_bounding_rect(min_alpha=64).bottom-12
            grounded=pg.Surface(plane.get_size(),pg.SRCALPHA).convert_alpha()
            grounded.blit(pg.transform.smoothscale(stone,(plane.get_width(),1080-top)),(0,top))
            grounded.blit(pg.transform.smoothscale(coping,(plane.get_width(),16)),(0,top))
            grounded.blit(plane,(0,0))
            return grounded
        middle=supported_plane(middle)
        near=supported_plane(near)
        self.variants[7]=[ParallaxLayer(name,image,n,25,name!='gallery-far') for name,image,n in
                          (('gallery-far',gallery,2),('gallery-middle',middle,6),('gallery-near',near,12))]
        acropolis=pg.transform.smoothscale(pg.image.load(str(assets/'greece-acropolis-v1.png')).convert(),(3840,1080))
        self.variants[8]=[ParallaxLayer('acropolis-far',acropolis,2,25,False)] + self.coast.layers[1:]
        temple=pg.image.load(str(assets/'greece-parthenon-v1.png')).convert_alpha()
        bounds=temple.get_bounding_rect(min_alpha=32)
        self.parthenon=pg.transform.smoothscale(temple.subsurface(bounds),(1080,360))
        self.images=self.coast.images+[self.parthenon]
        self.images += [layer.image for layers in self.variants.values() for layer in layers]

    def background(self,canvas,camera,level_id,camera_y=0):
        phase=1400 if level_id==6 else 0
        for layer in self.variants[level_id]:layer.draw(canvas.native,(camera+phase)*SCALE)
        if level_id==8:
            from greece_levels import LEVELS
            config=LEVELS[8]
            canvas.native.blit(self.parthenon,(pixel((config.LENGTH-940-camera)*SCALE),
                                              pixel((config.FLOORS[-1][2]-camera_y)*SCALE)-360))

    def platform(self,canvas,platform,camera):
        if platform.kind=='greek_ceiling':
            # The panorama already contains the roof, in the same depth plane
            # as its walls. This support supplies collision only; a second
            # cropped roof at gameplay speed breaks the architecture in two.
            return
        self.coast.platform(canvas,platform,camera)
