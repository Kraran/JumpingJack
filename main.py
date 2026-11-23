"""Jumping Jack: Les sables d'Horus. Python 3.10+, pygame 2.6+."""
from __future__ import annotations
import argparse
import math
import os
import random
import sys
import time
from collections import deque
from pathlib import Path
from dataclasses import dataclass
import pygame as pg
from gpu_render import NativeCanvas, DesignCanvas, DESIGN, SCALE, draw
from hero_animation import load_bank, HeroAnimator
from crocodile import CrocodileSprites, create_crocodiles
from rendering import DisplayStatus, FramePacer, ParallaxLayer, configure_display, pixel

ROOT = Path(__file__).resolve().parent
W, H = 1920, 1080
VIEW_W, VIEW_H = DESIGN
STEP = 1 / 120
WORLD = 9600
GOLD = (237, 194, 105)
INK = (23, 39, 46)


@dataclass
class Platform:
    x: float
    y: float
    w: float
    h: float
    ground: bool = False

    @property
    def rect(self):
        return pg.Rect(self.x, self.y, self.w, self.h)


def level():
    floors = [(0, 1220), (1400, 2350), (2550, 3570), (3800, 4850),
              (5070, 6190), (6400, 7540), (7780, 9600)]
    plats = [Platform(a, 620, b-a, 140, True) for a, b in floors]
    ledges = [(390, 492, 190), (740, 355, 180), (1100, 465, 220),
              (1530, 425, 220), (1880, 300, 190), (2200, 430, 250),
              (2670, 485, 240), (3020, 350, 230), (3420, 455, 270),
              (3930, 470, 210), (4260, 315, 240), (4670, 440, 290),
              (5220, 470, 240), (5550, 330, 230), (6010, 455, 300),
              (6550, 455, 200), (6880, 300, 240), (7350, 440, 330),
              (7900, 470, 220), (8240, 330, 240), (8620, 450, 260)]
    plats += [Platform(x,y,w,32) for x,y,w in ledges]
    gems = []
    for x,y,w in ledges:
        gems += [(x+w*.28,y-42), (x+w*.7,y-42)]
    gems += [(x,570) for x in (220,300,1600,2050,2800,4050,5300,6700,8030,8750)]
    return plats, gems


class Hero:
    def __init__(self, x=160, y=620):
        self.x, self.y = float(x), float(y)
        self.px, self.py = self.x, self.y
        self.vx = self.vy = 0.
        self.face = 1
        self.grounded = False
        self.coyote = self.buffer = 0.
        self.floating = False

    @property
    def rect(self):
        return pg.Rect(round(self.x-15), round(self.y-54), 30, 54)

    def update(self, dt, axis, held, pressed, platforms):
        self.px, self.py = self.x, self.y
        self.coyote = .10 if self.grounded else max(0, self.coyote-dt)
        self.buffer = .12 if pressed else max(0, self.buffer-dt)
        target = axis*340
        accel = 2400 if self.grounded else 1750
        self.vx += max(-accel*dt, min(accel*dt, target-self.vx))
        if axis: self.face = 1 if axis>0 else -1
        if self.buffer and self.coyote:
            self.vy = -790
            self.grounded = False
            self.coyote = self.buffer = 0
        elif pressed and not self.grounded:
            # A new press brakes ascent/descent, like the reference's aerial control.
            self.vy = max(0, self.vy*.12)
        self.floating = held and self.vy >= 0 and not self.grounded
        gravity = 340 if self.floating else 1550
        self.vy = min(105 if self.floating else 950, self.vy+gravity*dt)
        self.x = max(16, min(WORLD-16, self.x+self.vx*dt))
        for p in platforms:
            if p.ground and self.rect.colliderect(p.rect):
                if self.vx > 0: self.x = p.x-15
                elif self.vx < 0: self.x = p.x+p.w+15
                self.vx = 0
        old_bottom = self.y
        self.y += self.vy*dt
        self.grounded = False
        if self.vy >= 0:
            for p in platforms:
                if self.x+13>p.x and self.x-13<p.x+p.w and old_bottom<=p.y+1 and self.y>=p.y:
                    self.y = p.y
                    self.vy = 0
                    self.grounded = True
                    self.floating = False


class Game:
    def __init__(self, headless=False, fullscreen=None):
        if headless:
            os.environ['SDL_VIDEODRIVER']='dummy'
            os.environ['SDL_AUDIODRIVER']='dummy'
        os.environ['SDL_RENDER_SCALE_QUALITY']='0'
        os.environ['SDL_RENDER_BATCHING']='1'
        pg.init()
        pg.display.set_caption("Jumping Jack — Les sables d'Horus")
        self.fullscreen = False
        self.display_flags=pg.RESIZABLE | (0 if headless else pg.SCALED)
        self.preferred_renderer='direct3d11' if os.name=='nt' and not headless and not os.environ.get('SDL_RENDER_DRIVER') else None
        self.desktop_size=pg.display.get_desktop_sizes()[0]
        self.presentation=DisplayStatus(desktop_bounds=(0,0,*self.desktop_size))
        initial_fullscreen=not headless if fullscreen is None else fullscreen
        self.screen = self.create_display(False)
        self.install_canvas()
        self.pacer=FramePacer()
        self.frame_intervals=deque(maxlen=240)
        self.submission_times=deque(maxlen=240)
        self.last_present=None
        self.diagnostic_time=-1.
        self.diagnostic_lines=()
        self.fonts = {}
        self.text_cache = {}
        self.rng = random.Random(17)
        self.time = 0.
        self.bg = None
        path = ROOT/'assets'/'egypt-panorama.png'
        if path.exists() and not (ROOT/'assets'/'parallax-far.png').exists():
            im = pg.image.load(str(path)).convert()
            self.bg = pg.transform.smoothscale(im,(2160,720))
        self.sky = pg.Surface((VIEW_W,VIEW_H)).convert()
        for y in range(VIEW_H):
            t=y/VIEW_H
            draw.line(self.sky,(int(74+159*t),int(136+73*t),int(159+6*t)),(0,y),(VIEW_W,y))
        self.background_layers=self.load_background_layers()
        self.tiles = [self.make_tile(128,128,i) for i in range(4)]
        stone = ROOT/'assets'/'sandstone.png'
        if stone.exists():
            texture = pg.transform.smoothscale(pg.image.load(str(stone)).convert(), (512,512))
            self.tiles = [texture.subsurface((i*128,0,128,128)).copy() for i in range(4)]
        self.haze=pg.Surface((VIEW_W,120),pg.SRCALPHA)
        for y in range(120):
            draw.line(self.haze,(234,198,139,int(28*y/120)),(0,y),(VIEW_W,y))
        self.hud_panel=pg.Surface((VIEW_W,90),pg.SRCALPHA)
        for y in range(90):draw.line(self.hud_panel,(12,28,36,int(185*(1-y/90))),(0,y),(VIEW_W,y))
        self.hud_panel=self.hud_panel.convert_alpha()
        self.help_panel=pg.Surface((820,36),pg.SRCALPHA)
        self.help_panel.fill((12,28,36,190))
        self.title_shade=pg.Surface((VIEW_W,VIEW_H),pg.SRCALPHA)
        self.title_shade.fill((7,22,30,110))
        self.overlay_shade=pg.Surface((VIEW_W,VIEW_H),pg.SRCALPHA)
        self.overlay_shade.fill((8,23,32,205))
        self.diagnostic_panel=pg.Surface((900,112),pg.SRCALPHA)
        self.diagnostic_panel.fill((12,28,36,215))
        self.hero_sprites = self.load_hero()
        self.animation_bank=load_bank(ROOT/'assets')
        self.hero_animation=HeroAnimator()
        self.crocodile_sprites=CrocodileSprites.load(ROOT/'assets')
        self.sound_on = True
        self.sounds = {}
        self.make_sounds()
        self.state = 'title'
        self.show_stats=False
        self.reset()
        self.preload_textures()
        if initial_fullscreen:
            from pygame._sdl2.video import WINDOWPOS_CENTERED
            self.sdl_window.position=(WINDOWPOS_CENTERED,WINDOWPOS_CENTERED)
            self.toggle_fullscreen()

    def install_canvas(self):
        try:
            self.native_canvas=NativeCanvas(self.sdl_window if self.presentation.accelerated else None)
        except pg.error:
            self.native_canvas=NativeCanvas()
        self.canvas=DesignCanvas(self.native_canvas)

    def preload_textures(self):
        if not hasattr(self,'background_layers'):return
        images=[p.image for p in self.background_layers]+self.tiles
        images += [image for pair in self.hero_sprites for image in pair]
        if self.animation_bank:images += self.animation_bank.images
        if self.crocodile_sprites:images += self.crocodile_sprites.images
        images += [self.haze,self.hud_panel,self.help_panel,self.title_shade,
                   self.overlay_shade,self.diagnostic_panel]
        images += list(self.text_cache.values())
        self.native_canvas.preload(images)

    def capture(self):return self.native_canvas.capture()

    def close(self):
        self.native_canvas.release()
        pg.quit()

    def create_display(self, fullscreen):
        """Rebuild the SDL window without retaining a previous SCALED renderer."""
        restore_canvas=hasattr(self,'native_canvas')
        if restore_canvas:self.native_canvas.release()
        modes=[]
        if self.display_flags & pg.SCALED:
            if self.preferred_renderer:modes.append((True,self.preferred_renderer))
            modes.append((True,None))
        modes.append((False,None))
        for scaled,driver in modes:
            # set_mode alone can retain the old SDL renderer on Windows.
            pg.display.quit()
            pg.display.init()
            pg.display.set_caption("Jumping Jack — Les sables d'Horus")
            previous_driver=os.environ.get('SDL_RENDER_DRIVER')
            flags=pg.FULLSCREEN if fullscreen else pg.RESIZABLE
            size=self.desktop_size if fullscreen and not scaled else (W,H)
            if scaled:flags |= pg.SCALED
            if driver:os.environ['SDL_RENDER_DRIVER']=driver
            try:
                screen=pg.display.set_mode(size,flags,vsync=1 if scaled else 0)
                from pygame._sdl2.video import Window
                # SDL events borrow this Python object: keep it alive for the window.
                self.sdl_window=Window.from_display_module()
            except pg.error:
                continue
            finally:
                if driver:
                    if previous_driver is None:os.environ.pop('SDL_RENDER_DRIVER',None)
                    else:os.environ['SDL_RENDER_DRIVER']=previous_driver
            self.display_flags=pg.RESIZABLE | (pg.SCALED if scaled else 0)
            self.fullscreen=fullscreen
            self.refresh_display_status()
            if restore_canvas:
                self.install_canvas()
                self.preload_textures()
            return screen
        raise pg.error('Impossible de créer la fenêtre du jeu')

    def toggle_fullscreen(self):
        target=not self.fullscreen
        try:
            # Keep the current accelerated renderer and its vsync settings.
            switched=pg.display.toggle_fullscreen()
        except pg.error:
            switched=False
        if switched:
            self.screen=pg.display.get_surface()
            self.fullscreen=target
            self.refresh_display_status()
        else:
            try:
                self.screen=self.create_display(target)
            except pg.error:
                # An unsupported fullscreen mode must leave a playable window.
                self.screen=self.create_display(False)
        self.acc=0.
        self.pending_jump=False

    def refresh_display_status(self):
        self.presentation=configure_display((W,H),self.sdl_window.id)
        if hasattr(self,'pacer'):self.pacer.reset()
        if hasattr(self,'frame_intervals'):self.frame_intervals.clear()
        self.last_present=None
        self.diagnostic_time=-1.

    def load_background_layers(self):
        layers=[]
        for name,num,repeat in [('far',2,False),('middle',6,True),('near',12,True)]:
            path=ROOT/'assets'/f'parallax-{name}.png'
            if path.exists():
                im=pg.image.load(str(path))
                im=im.convert_alpha() if repeat else im.convert()
                im=pg.transform.smoothscale(im,(3240,H))
                if repeat:im.set_alpha(255,pg.RLEACCEL)
            elif repeat:
                im=pg.Surface((3240,H),pg.SRCALPHA).convert_alpha()
            else:
                im=pg.transform.smoothscale(self.bg,(3240,H)) if self.bg else pg.transform.scale(self.sky,(3240,H))
            layers.append(ParallaxLayer(name,im,num,25,repeat))
        return tuple(layers)

    def reset(self):
        self.platforms,self.gems=level()
        self.taken=set()
        self.hero=Hero()
        self.hero.grounded=True
        self.hero_animation.reset()
        self.crocodiles=create_crocodiles()
        self.cam=self.prev_cam=0.
        self.checkpoint=(160,560)
        self.check_index=0
        self.deaths=0
        self.elapsed=0.
        self.invuln=0.
        self.particles=[]
        self.notice=0.
        self.acc=0.
        self.pending_jump=False

    def font(self,size,serif=False):
        key=(size,serif)
        if key not in self.fonts:
            self.fonts[key]=pg.font.SysFont('Georgia' if serif else 'Segoe UI',pixel(size*SCALE))
        return self.fonts[key]

    def text(self,txt,pos,size=20,color=(246,236,210),serif=False,center=False):
        key=(txt,size,color,serif)
        if key not in self.text_cache:
            if len(self.text_cache)>=192:self.text_cache.pop(next(iter(self.text_cache)))
            self.text_cache[key]=self.font(size,serif).render(txt,True,color).convert_alpha()
        s=self.text_cache[key]
        self.canvas.blit_native(s,pos,'center' if center else 'topleft')

    def make_tile(self,w,h,seed):
        r=random.Random(seed)
        s=pg.Surface((w,h)).convert()
        for y in range(h):
            c=1-y/h*.28
            draw.line(s,(int(157*c),int(115*c),int(66*c)),(0,y),(w,y))
        for _ in range(1500):
            x=r.randrange(w); y=r.randrange(h); shade=r.choice([(221,181,117),(117,84,50),(168,129,78)])
            s.set_at((x,y),shade)
        for y in (32,78,123):
            draw.line(s,(83,66,44),(0,y),(w,y),2)
            draw.line(s,(189,146,88),(0,y+2),(w,y+2))
            x=r.randrange(20,110);draw.line(s,(94,72,45),(x,y-44),(x,y),2)
        return s

    def load_hero(self):
        path=ROOT/'assets'/'hero-atlas-v2.png'
        if not path.exists():return []
        sheet=pg.image.load(str(path)).convert_alpha()
        if sheet.get_at((0,0)).a>32:return []
        cw=sheet.get_width()//4
        # The legacy atlas's second row starts above its mathematical midpoint.
        divider=round(sheet.get_height()*.465)
        cells=[]
        for i in range(8):
            y0,y1=(0,divider) if i<4 else (divider,sheet.get_height())
            cell=sheet.subsurface(((i%4)*cw,y0,cw,y1-y0))
            bounds=cell.get_bounding_rect(min_alpha=30)
            if not bounds.w or not bounds.h:return []
            cells.append(cell.subsurface(bounds))
        scale=min(114/max(im.get_height() for im in cells),132/max(im.get_width() for im in cells))
        sprites=[]
        for im in cells:
            bounds=im.get_rect()
            im=pg.transform.smoothscale(im,(max(1,int(bounds.w*scale)),max(1,int(bounds.h*scale))))
            sprites.append((im,pg.transform.flip(im,True,False)))
        return sprites

    def make_sounds(self):
        try:
            from array import array
            if not pg.mixer.get_init(): return
            rate,_,channels=pg.mixer.get_init()
            for name,freq,duration in [('gem',880,.13),('jump',260,.13),('checkpoint',660,.3),('fall',140,.25),('win',520,.7),('crocodile',95,.18)]:
                data=array('h')
                for i in range(int(rate*duration)):
                    t=i/rate; env=(1-t/duration)**2
                    f=freq*(1+t*2) if name!='fall' else freq*(1-t)
                    v=int(1900*env*(math.sin(2*math.pi*f*t)+.3*math.sin(4*math.pi*f*t)))
                    for _ in range(channels): data.append(v)
                self.sounds[name]=pg.mixer.Sound(buffer=data)
        except (pg.error,ImportError): pass

    def sound(self,name):
        if self.sound_on and name in self.sounds: self.sounds[name].play()

    def burst(self,x,y,color,n=16):
        for _ in range(n):
            a=self.rng.random()*math.tau; v=self.rng.uniform(35,170)
            self.particles.append([x,y,math.cos(a)*v,math.sin(a)*v,self.rng.uniform(.3,.7),color])

    def update(self,dt,axis,held,pressed):
        self.elapsed+=dt
        was_grounded=self.hero.grounded
        self.hero.update(dt,axis,held,pressed,self.platforms)
        self.hero_animation.update(dt,self.hero,was_grounded)
        if was_grounded and not self.hero.grounded and self.hero.vy<0: self.sound('jump')
        self.prev_cam=self.cam
        target=max(0,min(WORLD-VIEW_W,self.hero.x-VIEW_W*.40+self.hero.vx*.24))
        self.cam+=(target-self.cam)*(1-math.exp(-5.8*dt))
        self.invuln=max(0,self.invuln-dt)
        self.notice=max(0,self.notice-dt)
        for enemy in self.crocodiles:
            event=enemy.update(dt,self.hero,can_attack=self.invuln<=0)
            if event=='warning':self.sound('crocodile')
            elif event=='lunge':self.burst(enemy.x+enemy.facing*35,enemy.y-4,(199,165,108),10)
        for i,(x,y) in enumerate(self.gems):
            if i not in self.taken and abs(self.hero.x-x)<31 and abs(self.hero.y-28-y)<42:
                self.taken.add(i);self.burst(x,y,GOLD,12);self.sound('gem')
        for idx,x in enumerate((2800,5400,8050),1):
            if self.check_index<idx and abs(self.hero.x-x)<65 and self.hero.y>500:
                self.checkpoint=(x,615);self.check_index=idx;self.notice=3
                self.burst(x,570,(104,222,217),28);self.sound('checkpoint')
        hit=self.hero.y>850
        for x,y in self.enemy_positions():
            if self.invuln<=0 and abs(self.hero.x-x)<32 and abs(self.hero.y-27-y)<33:hit=True
        if self.invuln<=0 and any(enemy.hits(self.hero) for enemy in self.crocodiles):hit=True
        if hit:
            self.deaths+=1;self.hero=Hero(*self.checkpoint)
            self.hero_animation.reset()
            for enemy in self.crocodiles:enemy.reset()
            self.cam=self.prev_cam=max(0,min(WORLD-VIEW_W,self.hero.x-VIEW_W*.4))
            self.invuln=2.;self.sound('fall');self.burst(self.hero.x,self.hero.y-25,(130,224,227),24)
        if self.hero.x>9220:
            self.state='win';self.sound('win')
        for p in self.particles:
            p[0]+=p[2]*dt;p[1]+=p[3]*dt;p[3]+=100*dt;p[4]-=dt
        self.particles=[p for p in self.particles if p[4]>0]

    def enemy_positions(self):
        return [(x+math.sin(self.time*.75+i)*105, y+math.sin(self.time*1.9+i)*46)
                for i,(x,y) in enumerate([(1920,495),(3250,490),(4480,480),(5800,495),(7090,470),(8510,500)])]

    def background(self,cam):
        for layer in self.background_layers:layer.draw(self.native_canvas,cam*SCALE)
        # Atmospheric haze is translucent, preserving the photographed stone.
        self.canvas.blit(self.haze,(0,500))

    def platform(self,p,cam):
        x=p.x-cam;y=int(p.y);w=int(p.w);h=int(p.h)
        if x>VIEW_W+60 or x+w<-60:return
        draw.rect(self.canvas,(58,50,37),(x+5,y+10,w,h))
        for tx in range(max(0,math.floor(-x/128)),math.ceil(w/128)):
            tile=self.tiles[(int(p.x)//10+tx)%4]
            tw=min(128,w-tx*128)
            for ty in range(0,h,128):
                self.canvas.blit(tile,(x+tx*128,y+ty),(0,0,tw,min(128,h-ty)))
        draw.rect(self.canvas,(229,190,125),(x-4,y,w+8,7))
        draw.line(self.canvas,(103,73,41),(x,y+15),(x+w,y+15),3)
        if not p.ground:
            draw.rect(self.canvas,(176,135,79),(x+8,y+20,w-16,7))
            for k in range(18,w-12,30):
                draw.line(self.canvas,(92,79,56),(x+k,y+21),(x+k+6,y+26),2)
                draw.line(self.canvas,(226,177,103),(x+k+7,y+21),(x+k+3,y+27))

    def draw_hero(self,x,y,alpha=1):
        h=self.hero;t=self.time;f=h.face
        if self.animation_bank:
            if h.grounded:draw.ellipse(self.canvas,(91,73,48),(x-16,y-2,32,5))
            if 'turn_ground' in self.animation_bank.clips:f=self.hero_animation.render_facing(alpha)
            self.hero_animation.sample(self.animation_bank,alpha).draw(self.canvas,x,y,f)
            return
        if self.hero_sprites:
            if h.grounded:
                frame=int(t*12)%4 if abs(h.vx)>20 else 4
                draw.ellipse(self.canvas,(91,73,48),(x-16,y-2,32,5))
            else:frame=6 if h.floating else (5 if h.vy<0 else 7)
            image=self.hero_sprites[frame][0 if f>0 else 1]
            offset=0 if frame==6 else f*7
            self.canvas.blit_native(image,(x-offset,y+2),'midbottom')
            return
        # Cape is animated independently of the collision body.
        stride=math.sin(t*14)*min(abs(h.vx)/340,1)*8 if h.grounded else 5
        pts=[(x-f*9,y-43),(x-f*27,y-37),(x-f*(38+math.sin(t*9)*6),y-12),(x-f*17,y-17),(x-f*6,y-25)]
        draw.polygon(self.canvas,(103,29,39),pts)
        draw.lines(self.canvas,(224,83,65),False,pts[:3],3)
        for side in (-1,1):
            hip=(x+side*6,y-23);foot=(x+side*(9+stride),y-3)
            draw.line(self.canvas,(24,57,73),hip,foot,9)
            draw.line(self.canvas,GOLD,(foot[0]-3,foot[1]),(foot[0]+f*7,foot[1]),6)
        draw.polygon(self.canvas,(33,103,121),[(x-12,y-43),(x+12,y-43),(x+10,y-23),(x-9,y-23)])
        draw.line(self.canvas,GOLD,(x-10,y-24),(x+10,y-24),4)
        draw.polygon(self.canvas,GOLD,[(x,y-40),(x+6,y-34),(x,y-28),(x-6,y-34)])
        for side in (-1,1):
            raised=h.floating or not h.grounded
            hand=(x+side*22,y-44 if raised else y-27+side*stride*.4)
            draw.line(self.canvas,(36,104,121),(x+side*10,y-40),hand,7)
            draw.circle(self.canvas,(239,189,124),(int(hand[0]),int(hand[1])),4)
        draw.circle(self.canvas,(220,168,109),(int(x),int(y-51)),10)
        draw.arc(self.canvas,GOLD,(x-11,y-63,22,23),0,math.pi,5)
        draw.rect(self.canvas,(25,61,73),(x-9,y-55,18,6),border_radius=2)
        draw.line(self.canvas,(184,245,240),(x+f*2,y-52),(x+f*7,y-52),2)
        if h.floating:
            draw.arc(self.canvas,(169,231,223),(x-33,y-26,66,30),math.pi,math.tau,2)

    def draw_crocodiles(self,cam,alpha):
        for enemy in self.crocodiles:
            x=enemy.px+(enemy.x-enemy.px)*alpha-cam
            if not -180<x<VIEW_W+180:continue
            draw.ellipse(self.canvas,(81,69,44),(x-77,enemy.y-5,154,8))
            if self.crocodile_sprites:
                self.crocodile_sprites.sample(enemy,alpha).draw(self.canvas,x,enemy.y,enemy.facing)
            else:
                # Visible fallback for development checkouts without the atlas.
                f=enemy.facing;y=enemy.y
                draw.polygon(self.canvas,(63,79,55),[(x-f*45,y-22),(x-f*145,y-44),(x-f*85,y-8),(x,y-5)])
                draw.ellipse(self.canvas,(68,85,58),(x-55,y-33,117,30))
                draw.rect(self.canvas,(83,99,65),(x+f*72-31,y-25,62,18),border_radius=5)
                draw.circle(self.canvas,(219,177,71),(x+f*64,y-28),3)

    def draw(self,alpha=1):
        started=time.perf_counter()
        self.native_canvas.begin()
        alpha=max(0.,min(1.,alpha))
        render_cam=self.prev_cam+(self.cam-self.prev_cam)*alpha
        self.background(render_cam)
        # Snap once for the entire gameplay plane, independently of the layers.
        cam=pixel(render_cam*SCALE)/SCALE
        for p in self.platforms:self.platform(p,cam)
        for i,(gx,gy) in enumerate(self.gems):
            if i in self.taken:continue
            x=gx-cam;y=gy+math.sin(self.time*2.4+i)*5
            if not -30<x<VIEW_W+30:continue
            draw.circle(self.canvas,(166,130,62),(x,y),13,1)
            draw.polygon(self.canvas,(255,223,140),[(x,y-10),(x+7,y),(x,y+10),(x-7,y)])
            draw.line(self.canvas,(255,249,209),(x,y-7),(x,y+3),2)
        for idx,cx in enumerate((2800,5400,8050),1):
            x=cx-cam
            if -60<x<VIEW_W+60:
                draw.rect(self.canvas,(94,88,64),(x-15,555,30,65))
                draw.polygon(self.canvas,(182,157,104),[(x-15,555),(x,530),(x+15,555)])
                color=(119,235,223) if idx<=self.check_index else GOLD
                draw.circle(self.canvas,color,(x,565),7)
        for ex,ey in self.enemy_positions():
            x=ex-cam
            if -70<x<VIEW_W+70:
                wing=math.sin(self.time*13)*12
                draw.ellipse(self.canvas,(58,68,57),(x-32,ey-8-wing,30,12+abs(wing)))
                draw.ellipse(self.canvas,(58,68,57),(x+2,ey-8-wing,30,12+abs(wing)))
                draw.ellipse(self.canvas,(31,67,64),(x-12,ey-13,24,29))
                draw.ellipse(self.canvas,(183,148,73),(x-8,ey-10,16,22),2)
                draw.circle(self.canvas,(234,168,69),(x,ey-14),4)
        self.draw_crocodiles(cam,alpha)
        # Final sanctuary doorway.
        x=9250-cam
        if -250<x<VIEW_W+250:
            draw.rect(self.canvas,(67,64,52),(x-85,380,170,240))
            for dx in (-104,76):
                draw.rect(self.canvas,(173,137,84),(x+dx,350,30,270))
                draw.rect(self.canvas,GOLD,(x+dx-6,349,42,15))
            draw.rect(self.canvas,(202,164,100),(x-115,326,230,28))
            draw.circle(self.canvas,GOLD,(x,440),33,3)
            draw.line(self.canvas,GOLD,(x,406),(x,487),4)
            draw.line(self.canvas,GOLD,(x-22,463),(x+22,463),4)
        hx=(self.hero.px+(self.hero.x-self.hero.px)*alpha)-cam
        hy=self.hero.py+(self.hero.y-self.hero.py)*alpha
        if self.invuln<=0 or int(self.time*12)%2==0:self.draw_hero(hx,hy,alpha)
        for px,py,vx,vy,life,col in self.particles:
            draw.circle(self.canvas,col,(px-cam,py),max(1,int(life*5)))
        # Foreground sand motes, drifting continuously at a separate depth.
        for i in range(35):
            x=(i*173+self.time*(17+i%7)-cam*.65)%(VIEW_W+40)-20
            y=160+(i*97)%520+math.sin(self.time+i)*9
            draw.line(self.canvas,(231,202,146),(x,y),(x+3,y))
        self.hud()
        if self.state=='title':self.title()
        elif self.state=='pause':self.overlay('PAUSE', 'Échap pour reprendre', 'F11 · plein écran     M · son     R · recommencer')
        elif self.state=='win':
            self.overlay('LE SANCTUAIRE S’ÉVEILLE',f'{len(self.taken)} / {len(self.gems)} reliques   ·   {int(self.elapsed)//60:02}:{int(self.elapsed)%60:02}   ·   {self.deaths} morts','Entrée pour rejouer')
        if self.notice>0 and self.state=='play':self.text('POINT DE REPRISE ACTIVÉ',(VIEW_W/2,132),19,GOLD,center=True)
        if self.show_stats:
            self.draw_diagnostics()
        self.submission_times.append(time.perf_counter()-started)
        self.native_canvas.present(self.screen)
        presented=time.perf_counter()
        if self.last_present is not None:self.frame_intervals.append(presented-self.last_present)
        self.last_present=presented

    def draw_diagnostics(self):
        now=time.perf_counter()
        if now-self.diagnostic_time>=.25:
            status=self.presentation
            frames=sorted(self.frame_intervals)
            fps=len(frames)/sum(frames) if frames and sum(frames)>0 else 0
            p95=frames[min(len(frames)-1,int(len(frames)*.95))]*1000 if frames else 0
            hz=f'{status.refresh_hz} Hz' if status.refresh_known else '60 Hz (repli)'
            sync='VSync SDL active' if status.vsync else 'Cadence logicielle'
            self.diagnostic_lines=(f'{fps:.1f} FPS  |  P95 {p95:.2f} ms  |  Écran {hz}',
                f'{sync}  |  {status.renderer}  |  Full HD 1920 × 1080  |  Physique 120 Hz',
                f'{"Composition GPU" if self.native_canvas.gpu else "Repli CPU"}  |  {len(self.native_canvas.textures)} textures  |  Pixels Full HD entiers  |  Héros {self.animation_bank.pose_count if self.animation_bank else 8} poses',
                'Parallaxe : 0,08 / 0,24 / 0,48  |  Une caméra / une interpolation')
            self.diagnostic_time=now
        self.canvas.blit(self.diagnostic_panel,(20,88))
        for i,line in enumerate(self.diagnostic_lines):self.text(line,(30,94+i*25),16)

    def hud(self):
        self.canvas.blit(self.hud_panel,(0,0))
        self.text('J / J',(34,22),25,GOLD,True)
        self.text('LES SABLES D’HORUS',(124,20),18)
        self.text('NIVEAU 01  /  LE SEUIL DU DÉSERT',(124,45),11,(198,209,199))
        draw.polygon(self.canvas,GOLD,[(VIEW_W-331,32),(VIEW_W-324,41),(VIEW_W-331,50),(VIEW_W-338,41)],2)
        self.text(f'{len(self.taken):02} / {len(self.gems)}',(VIEW_W-311,26),23,GOLD)
        self.text('ÉCHAP  pause',(VIEW_W-156,34),14)
        draw.rect(self.canvas,(43,61,60),(VIEW_W//2-90,32,180,3))
        draw.rect(self.canvas,GOLD,(VIEW_W//2-90,32,int(180*min(self.hero.x/9250,1)),3))
        if self.state=='play' and self.hero.x<1000:
            self.canvas.blit(self.help_panel,(230,665))
            self.text('← → / Q D   Déplacement     ESPACE   Saut     Maintenir en descente   Planer',(VIEW_W/2,682),17,center=True)

    def title(self):
        self.canvas.blit(self.title_shade,(0,0))
        self.text('UNE AVENTURE DANS LES SABLES DU TEMPS',(VIEW_W/2,184),15,GOLD,center=True)
        self.text('JUMPING JACK',(VIEW_W/2,263),76,serif=True,center=True)
        self.text('LES SABLES D’HORUS',(VIEW_W/2,329),26,GOLD,serif=True,center=True)
        draw.line(self.canvas,GOLD,(VIEW_W/2-70,373),(VIEW_W/2+70,373))
        self.text('Un saut vers les dieux. Une cape contre le vent.',(VIEW_W/2,411),21,center=True)
        self.text('ENTRÉE  ·  EXPLORER LE DÉSERT',(VIEW_W/2,488),22,GOLD,center=True)
        self.text('← → / Q D  Bouger    ·    Espace  Sauter    ·    Espace en l’air  Freiner / planer',(VIEW_W/2,558),17,center=True)
        self.text('Rassemblez les reliques et rejoignez le sanctuaire à l’est.',(VIEW_W/2,593),17,center=True)
        self.text('F11  Plein écran     •     M  Son',(VIEW_W/2,654),14,(205,207,190),center=True)

    def overlay(self,title,sub,helptext):
        self.canvas.blit(self.overlay_shade,(0,0))
        self.text(title,(VIEW_W/2,280),44,GOLD,True,True)
        self.text(sub,(VIEW_W/2,365),24,center=True)
        self.text(helptext,(VIEW_W/2,442),18,center=True)

    def run(self,frames=0,screenshot=None):
        running=True;count=0
        previous=time.perf_counter()
        while running:
            self.pacer.wait(self.presentation.vsync,self.presentation.refresh_hz)
            now=time.perf_counter()
            dt=min(now-previous,.1)
            previous=now
            self.time+=dt
            for e in pg.event.get():
                if e.type==pg.QUIT:running=False
                elif e.type in (pg.WINDOWMOVED,pg.WINDOWSIZECHANGED):self.refresh_display_status()
                elif e.type==pg.WINDOWFOCUSLOST and self.state=='play':self.state='pause';self.acc=0
                elif e.type==pg.KEYDOWN:
                    if e.key==pg.K_F11:
                        self.toggle_fullscreen()
                    elif e.key==pg.K_F3:self.show_stats=not self.show_stats
                    elif e.key==pg.K_m:self.sound_on=not self.sound_on
                    elif e.key==pg.K_ESCAPE:
                        if self.state=='play':self.state='pause'
                        elif self.state=='pause':self.state='play'
                        else:running=False
                        self.acc=0
                    elif e.key==pg.K_RETURN and self.state in ('title','win'):
                        self.reset();self.state='play'
                    elif e.key==pg.K_r and self.state in ('play','pause'):
                        self.reset();self.state='play'
                    elif e.key in (pg.K_SPACE,pg.K_UP,pg.K_z,pg.K_w) and self.state=='play':self.pending_jump=True
            keys=pg.key.get_pressed()
            axis=int(keys[pg.K_RIGHT] or keys[pg.K_d])-int(keys[pg.K_LEFT] or keys[pg.K_q] or keys[pg.K_a])
            held=keys[pg.K_SPACE] or keys[pg.K_UP] or keys[pg.K_z] or keys[pg.K_w]
            if self.state=='play':
                self.acc+=dt
                while self.acc>=STEP:
                    self.update(STEP,axis,held,self.pending_jump)
                    self.pending_jump=False;self.acc-=STEP
                    if self.state!='play':break
            self.draw(self.acc/STEP if self.state=='play' else 1)
            count+=1
            if frames and count>=frames:running=False
        if screenshot:pg.image.save(self.capture(),str(screenshot))
        self.close()


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--headless',action='store_true');ap.add_argument('--frames',type=int,default=0);ap.add_argument('--screenshot');ap.add_argument('--play',action='store_true');ap.add_argument('--windowed',action='store_true')
    args=ap.parse_args();game=Game(args.headless,fullscreen=False if args.windowed or args.headless else True)
    if args.play:game.state='play'
    try:game.run(args.frames,args.screenshot)
    finally:game.close()
