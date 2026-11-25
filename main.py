"""Jumping Jack: Les sables d'Horus. Python 3.10+, pygame 2.6+."""
from __future__ import annotations
import argparse
import gc
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
from hero_animation import load_bank, HeroAnimator, landing_clip, LAND_DURATIONS, DROP_TIME, DROP_RELEASE,CROUCH_TIME
from crocodile import Crocodile,CrocodileSprites, create_crocodiles
from gamepad import Gamepads, PadSnapshot, merge_axis
from solar import SolarRay
from rest import RestPose
from energy import SolarEnergy,MAX_ENERGY,RAY_COST
from obelisk import Obelisk,ObeliskSprites,CHECKPOINT_X,GROUND_Y,RESPAWN
from plasma_fx import PlasmaEffect
from platform_sprites import SacredPlatforms
from spikes import SpikeSprites,SPIKED_PLATFORM_X,upward_contact
from vulture import Vulture,VultureSprites,SPAWNS as VULTURE_SPAWNS
from crystal import SolarCrystals
import desert_level
import temple_level
import tower_level
from tower_art import TowerArt,VerticalCanvas
from desert_art import DesertArt
from vase import Vase,VaseSprites,SPAWNS as VASE_SPAWNS
from temple_art import TempleArt
from temple_exit import TempleExit,TempleExitSprites,APPROACH
from scorpion import Scorpion,ScorpionSprites
from terrain import DuneGround,sand_height
from settings import Settings
from menu import StartMenu,PAGES as MENU_PAGES
from loading import LoadingScreen,LoadingCancelled
from localization import translate,CODES
from savegame import SaveSlots,capture as capture_save,restore as restore_save
from lives import STARTING_LIVES,load_life_symbol
from medallion import MedallionInventory,MedallionSprites,POSITION as FIRST_MEDALLION,position as medallion_position,touches as touches_medallion,tune as medallion_tune
from beetle import BeetleSprites, BeetleMotion, BeetleDeath, SPAWNS, DEATH_TIME
from rendering import DisplayStatus, FramePacer, ParallaxLayer, configure_display, pixel,integer_viewport

ROOT = Path(__file__).resolve().parent
W, H = 1920, 1080
VIEW_W, VIEW_H = DESIGN
STEP = 1 / 120
WORLD = 9600
EXIT_MARGIN = 96  # Let the entire hero and cape leave the fixed final viewport.
PLATFORM_WIDTHS=(120,180,240,300,360)  # Very small, small, medium, large, very large.
GOLD = (237, 194, 105)
INK = (23, 39, 46)


@dataclass
class Platform:
    x: float
    y: float
    w: float
    h: float
    ground: bool = False
    spiked: bool = False
    kind: str = 'stone'

    @property
    def rect(self):
        return pg.Rect(self.x, self.y, self.w, self.h)


def level(level_id=1):
    if level_id==2:return desert_level.build(Platform,EXIT_MARGIN)
    if level_id==3:return temple_level.build(Platform,EXIT_MARGIN)
    if level_id==4:return tower_level.build(Platform,EXIT_MARGIN)
    if level_id!=1:raise ValueError(f'Niveau inconnu : {level_id}')
    floors = [(0, 1220), (1400, 2350), (2550, 3570), (3800, 4850),
              (5070, 6190), (6400, 7540), (7780, WORLD+EXIT_MARGIN+32)]
    plats = [Platform(a, 620, b-a, 140, True) for a, b in floors]
    # Size indices refer to PLATFORM_WIDTHS; horizontal spacing follows the
    # new footprints while heights preserve the low/high platform progression.
    layout=[(390,492,2),(760,355,1),(1100,465,3),
            (1530,425,0),(1860,300,2),(2180,430,4),
            (2670,485,1),(2990,350,3),(3420,455,2),
            (3900,470,4),(4310,315,0),(4670,440,1),
            (5220,470,2),(5550,330,4),(6040,455,0),
            (6510,455,3),(6900,300,1),(7310,440,4),
            (7900,470,0),(8190,330,3),(8620,450,2)]
    ledges=[(x,y,PLATFORM_WIDTHS[size]) for x,y,size in layout]
    plats += [Platform(x,y,w,32,spiked=x in SPIKED_PLATFORM_X) for x,y,w in ledges]
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
        self.impact_vy = 0.
        self.landed_gliding = False
        self.fall_origin_y = self.y
        self.landed_height = 0.
        self.landing_kind = 'land'
        self.recovery = 0.
        self.drop_elapsed = None
        self.drop_support = None
        self.ignored_platform = None
        self.drop_jump_latched = False
        self.crouch=self.previous_crouch=0.
        self.glide_locked=False
        self.spike_hit=False
        self.bump=self.head_bump=False;self.bump_cooldown=0.;self.contacts=set()

    @property
    def body_height(self):return round(54-22*self.crouch)

    @property
    def rect(self):
        return pg.Rect(round(self.x-15), round(self.y-self.body_height), 30, self.body_height)

    def update(self, dt, axis, held, pressed, platforms, drop=False,allow_glide=True,down=False):
        terrain=tuple(p for p in platforms if isinstance(p,DuneGround))
        if terrain:platforms=tuple(p for p in platforms if not isinstance(p,DuneGround))
        old_contacts=self.contacts;self.contacts=set();self.bump=self.head_bump=False
        self.spike_hit=False
        self.bump_cooldown=max(0.,self.bump_cooldown-dt)
        def contact(platform,side):
            key=(id(platform),side);self.contacts.add(key)
            if key not in old_contacts:
                self.bump=True
                if side=='bottom' and self.bump_cooldown<=0:
                    self.head_bump=True;self.bump_cooldown=.12
        self.previous_crouch=self.crouch
        self.impact_vy = 0.
        self.landed_gliding = False
        self.landed_height = 0.
        if not held:self.drop_jump_latched=False
        if drop and pressed and self.grounded and self.recovery<=0 and self.drop_elapsed is None:
            pressed=False;self.buffer=0.
            support=next((p for p in platforms if not p.ground and abs(self.y-p.y)<=1
                          and self.x+13>p.x and self.x-13<p.x+p.w),None)
            if support is not None:
                self.drop_support=support;self.drop_elapsed=0.
                self.drop_jump_latched=True
        if self.drop_elapsed is not None:
            self.crouch=self.previous_crouch=0.
            self.drop_elapsed+=dt
            if self.drop_elapsed<DROP_RELEASE-1e-9:
                self.px,self.py=self.x,self.y
                self.vx=self.vy=0.;self.coyote=self.buffer=0.;self.floating=False
                return
            if self.drop_support is not None:
                self.ignored_platform=self.drop_support;self.drop_support=None
                self.grounded=False;self.vy=140.;self.fall_origin_y=self.y
                self.coyote=self.buffer=0.
            held=False;pressed=False
            if self.drop_elapsed>=DROP_TIME-1e-9:self.drop_elapsed=None
        if self.drop_jump_latched:
            held=False;pressed=False;self.buffer=0.
        if self.ignored_platform is not None:
            p=self.ignored_platform
            if (self.y-self.body_height>=p.y+p.h or self.x+15<=p.x or self.x-15>=p.x+p.w
                    or (self.drop_elapsed is None and self.y<=p.y)):
                self.ignored_platform=None
        was_grounded = self.grounded
        # Measure the uninterrupted descent from its apex, resetting after glide.
        if self.grounded or self.floating:self.fall_origin_y = self.y
        self.fall_origin_y = min(self.fall_origin_y,self.y)
        if self.recovery>0:
            self.recovery=max(0.,self.recovery-dt)
            if self.recovery<1e-9:self.recovery=0.
            axis=0;held=False;pressed=False
            self.vx=0.;self.buffer=0.;self.coyote=0.
        target_crouch=bool(down and self.grounded and self.recovery<=0 and self.drop_elapsed is None)
        if not self.grounded or self.recovery>0:
            self.crouch=self.previous_crouch=0.
        elif target_crouch:self.crouch=min(1.,self.crouch+dt/CROUCH_TIME)
        else:self.crouch=max(0.,self.crouch-dt/CROUCH_TIME)
        # Do not grow the body through a ceiling when standing from a crouch.
        old_height=round(54-22*self.previous_crouch)
        if self.body_height>old_height:
            for p in platforms:
                if (p is not self.ignored_platform and self.x+15>p.x and self.x-15<p.x+p.w
                        and self.y-old_height>=p.y+p.h-.001 and self.y-self.body_height<p.y+p.h):
                    self.crouch=max(self.crouch,(54-(self.y-p.y-p.h))/22)
        if self.crouch>0:
            if axis:self.face=1 if axis>0 else -1
            axis=0;self.vx=0.
        self.px, self.py = self.x, self.y
        self.coyote = .10 if self.grounded else max(0, self.coyote-dt)
        self.buffer = .12 if pressed else max(0, self.buffer-dt)
        target = axis*340
        accel = 2400 if self.grounded else 1750
        self.vx += max(-accel*dt, min(accel*dt, target-self.vx))
        if axis: self.face = 1 if axis>0 else -1
        can_stand=not any(p is not self.ignored_platform and self.x+15>p.x and self.x-15<p.x+p.w
                          and self.y-self.body_height>=p.y+p.h-.001 and self.y-54<p.y+p.h<=self.y
                          for p in platforms)
        if self.buffer and self.coyote and can_stand:
            self.crouch=self.previous_crouch=0.
            self.vy = -790
            self.grounded = False
            self.coyote = self.buffer = 0
        elif pressed and not self.grounded and not self.glide_locked:
            # A new press brakes ascent/descent, like the reference's aerial control.
            self.vy = max(0, self.vy*.12)
        self.floating = held and self.vy >= 0 and not self.grounded and allow_glide and not self.glide_locked
        gravity = 340 if self.floating else 1550
        self.vy = min(105 if self.floating else 950, self.vy+gravity*dt)
        old_x=self.x
        destination=max(16,self.x+self.vx*dt)
        side_hit=None
        for p in platforms:
            if p is self.ignored_platform or self.y<=p.y or self.y-self.body_height>=p.y+p.h:continue
            if self.vx>0 and old_x+15<=p.x+.001 and destination+15>=p.x:
                if side_hit is None or p.x-15<destination:destination=p.x-15;side_hit=p
            elif self.vx<0 and old_x-15>=p.x+p.w-.001 and destination-15<=p.x+p.w:
                if side_hit is None or p.x+p.w+15>destination:destination=p.x+p.w+15;side_hit=p
        self.x=destination
        if side_hit is not None:
            contact(side_hit,'left' if self.vx>0 else 'right');self.vx=0.
            if self.floating:
                self.glide_locked=True;self.floating=False;self.coyote=self.buffer=0.
                self.vy=min(950,self.vy+(1550-340)*dt)
        old_bottom = self.y
        old_top=self.y-self.body_height
        self.y += self.vy*dt
        self.grounded = False
        if self.vy<0:
            ceiling=None;spike_edge=None
            for p in platforms:
                if p is self.ignored_platform:continue
                if p.spiked:
                    edge=upward_contact(p,self.x,old_top,self.y-self.body_height)
                    if edge is not None and (spike_edge is None or edge>spike_edge):spike_edge=edge
                if (self.x+15>p.x and self.x-15<p.x+p.w and old_top>=p.y+p.h-.001
                        and self.y-self.body_height<=p.y+p.h):
                    if ceiling is None or p.y+p.h>ceiling.y+ceiling.h:ceiling=p
            if spike_edge is not None and (ceiling is None or spike_edge>=ceiling.y+ceiling.h):
                self.y=spike_edge+self.body_height;self.vy=0.;self.spike_hit=True
            elif ceiling is not None:
                self.y=ceiling.y+ceiling.h+self.body_height
                self.vy=0.;self.buffer=self.coyote=0.;self.floating=False;self.glide_locked=True
                contact(ceiling,'bottom')
        self.fall_origin_y = min(self.fall_origin_y,self.y)
        if self.vy >= 0:
            for p in sorted(platforms,key=lambda support:support.y):
                if p is self.ignored_platform:continue
                if self.x+15>p.x and self.x-15<p.x+p.w and old_bottom<=p.y+1 and self.y>=p.y:
                    self.y = p.y
                    self.impact_vy = self.vy
                    self.landed_gliding = self.floating
                    self.landed_height = 0. if self.floating else max(0.,p.y-self.fall_origin_y)
                    if not was_grounded:
                        self.landing_kind=landing_clip(self.landed_height)
                        if not self.floating and self.impact_vy>100 and self.landing_kind=='land_heavy':
                            self.recovery=LAND_DURATIONS['land_heavy']
                            self.vx=0.;self.buffer=0.;self.coyote=0.
                    self.vy = 0
                    self.grounded = True
                    self.floating = False
                    self.glide_locked=False
                    self.drop_elapsed=None;self.drop_support=None
                    break
        if terrain and self.vy>=0 and not self.grounded:
            for ground in terrain:
                if not ground.x-13<self.x<ground.x+ground.w+13:continue
                surface=ground.height_at(self.x)
                following=(was_grounded and ground.x-13<old_x<ground.x+ground.w+13
                           and abs(old_bottom-ground.height_at(old_x))<1)
                if not following and not (old_bottom<=surface+1 and self.y>=surface):continue
                body=pg.Rect(round(self.x-15),round(surface-self.body_height),30,self.body_height)
                if following and any(p is not self.ignored_platform and body.colliderect(p.rect) for p in platforms):
                    self.x=old_x;self.vx=0.;surface=ground.height_at(old_x)
                self.impact_vy=self.vy;self.landed_gliding=self.floating
                self.landed_height=0. if self.floating else max(0.,surface-self.fall_origin_y)
                if not was_grounded:
                    self.landing_kind=landing_clip(self.landed_height)
                    if not self.floating and self.impact_vy>100 and self.landing_kind=='land_heavy':
                        self.recovery=LAND_DURATIONS['land_heavy'];self.vx=0.;self.buffer=self.coyote=0.
                self.y=surface;self.vy=0.;self.grounded=True;self.floating=False
                self.glide_locked=False;self.drop_elapsed=None;self.drop_support=None
                break


class Game:
    def __init__(self, headless=False, fullscreen=None,settings_path=None,saves_path=None):
        self.settings_path=Path(settings_path) if settings_path is not None else (None if headless else ROOT/'settings.json')
        self.settings=Settings.load(self.settings_path)
        initial_settings_saved=True
        if self.settings_path is not None and getattr(self.settings,'_language_detected',False):
            initial_settings_saved=self.settings.save(self.settings_path)
        self.saves=SaveSlots(saves_path if saves_path is not None else (None if headless else ROOT/'saves'))
        self.quit_requested=False
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
        initial_fullscreen=self.settings.fullscreen and not headless if fullscreen is None else fullscreen
        self.screen = self.create_display(False)
        self.install_canvas()
        pg.mouse.set_visible(False)
        self.loading=LoadingScreen(enabled=not headless,language=self.settings.language)
        self.loading_stage(0.,'Ouverture du temple…')
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
        self.loading_stage(.05,'Préparation des décors…')
        self.background_layers=self.load_background_layers()
        self.loading_stage(.12,'Création du Nil et des dunes…')
        self.desert_art=DesertArt.load(ROOT/'assets')
        self.loading_stage(.28,'Préparation de l’intérieur du temple…')
        self.temple_art=TempleArt.load(ROOT/'assets')
        self.tower_art=TowerArt.load(ROOT/'assets')
        self.vase_sprites=VaseSprites.load(ROOT/'assets')
        self.loading_stage(.35,'Assemblage du monde…')
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
        self.help_panel=pg.Surface((1040,36),pg.SRCALPHA)
        self.help_panel.fill((12,28,36,190))
        self.title_shade=pg.Surface((VIEW_W,VIEW_H),pg.SRCALPHA)
        self.title_shade.fill((7,22,30,110))
        self.overlay_shade=pg.Surface((VIEW_W,VIEW_H),pg.SRCALPHA)
        self.overlay_shade.fill((8,23,32,205))
        self.diagnostic_panel=pg.Surface((900,112),pg.SRCALPHA)
        self.diagnostic_panel.fill((12,28,36,215))
        self.hero_sprites = self.load_hero()
        self.loading_stage(.40,'Préparation des animations du héros…')
        self.animation_bank=load_bank(ROOT/'assets')
        self.hero_animation=HeroAnimator()
        self.temple_exit_sprites=TempleExitSprites.load(ROOT/'assets')
        self.energy=SolarEnergy()
        self.solar=SolarRay(PlasmaEffect.load(ROOT/'assets'))
        self.rest=RestPose()
        self.loading_stage(.52,'Préparation des crocodiles…')
        self.crocodile_sprites=CrocodileSprites.load(ROOT/'assets')
        self.loading_stage(.60,'Préparation des scarabées…')
        self.beetle_sprites=BeetleSprites.load(ROOT/'assets')
        self.scorpion_sprites=ScorpionSprites.load(ROOT/'assets')
        self.loading_stage(.65,'Préparation des plateformes et des pièges…')
        self.obelisk_sprites=ObeliskSprites(ROOT/'assets'/'solar-obelisk-v1.png')
        self.platform_sprites=SacredPlatforms(ROOT/'assets'/'sacred-platforms-v1.png',PLATFORM_WIDTHS)
        self.spike_sprites=SpikeSprites(ROOT/'assets'/'platform-spike-v1.png',PLATFORM_WIDTHS)
        self.loading_stage(.71,'Préparation des gardiens solaires…')
        self.vulture_sprites=VultureSprites.load(ROOT/'assets')
        self.loading_stage(.76,'Préparation des cristaux et des médaillons…')
        self.crystal_sprites=SolarCrystals(ROOT/'assets'/'solar-crystal-v1.png')
        self.medallion_sprites=MedallionSprites(ROOT/'assets'/'ra-medallion-v1.png')
        self.medallions=MedallionInventory()
        self.lives=STARTING_LIVES
        self.level_id=1
        self.life_symbol=load_life_symbol(ROOT/'assets'/'hero-atlas-v2.png')
        self.loading_stage(.81,'Préparation des menus et des sons…')
        self.menu=StartMenu(ROOT/'assets')
        self.menu.save_failed=not initial_settings_saved
        self.sound_on = self.settings.sound
        self.sounds = {}
        self.make_sounds()
        self.gamepads = Gamepads()
        self.gamepads.rumble_enabled=self.settings.rumble
        self.pad = PadSnapshot()
        self.state = 'title'
        self.controller_lost=False
        self.mouse_last_motion=None
        pg.mouse.set_visible(False)
        self.show_stats=False
        self.show_fps=self.settings.show_fps
        self.fps_count=0;self.fps_updated=-1.
        self.reset()
        self.loading_stage(.86,'Transfert des textures vers le rendu…')
        self.preload_textures()
        if initial_fullscreen:
            from pygame._sdl2.video import WINDOWPOS_CENTERED
            self.sdl_window.position=(WINDOWPOS_CENTERED,WINDOWPOS_CENTERED)
            self.toggle_fullscreen()
        self.loading_stage(.96,'Préchauffage du rendu et des animations…')
        self.prepare_rendering()
        gc.collect()  # Finish allocations from asset preparation before play.
        self.loading_stage(1.,'Prêt pour l’aventure')
        self.loading.release(self.native_canvas)

    def loading_stage(self,progress,label):
        try:self.loading.show(self.native_canvas,self.screen,progress,label)
        except LoadingCancelled:
            self.close()
            raise

    def install_canvas(self):
        try:
            self.native_canvas=NativeCanvas(self.sdl_window if self.presentation.accelerated else None)
        except pg.error:
            self.native_canvas=NativeCanvas()
        self.canvas=DesignCanvas(self.native_canvas)

    def preload_textures(self):
        if not hasattr(self,'background_layers'):return
        images=[p.image for p in self.background_layers]+self.tiles
        images += self.desert_art.images
        images += self.temple_art.images
        images += self.tower_art.images
        images += self.vase_sprites.images
        images += self.temple_exit_sprites.images
        images += [image for pair in self.hero_sprites for image in pair]
        if self.animation_bank:images += self.animation_bank.images
        if self.solar.effect:images += self.solar.effect.images
        if self.crocodile_sprites:images += self.crocodile_sprites.images
        if self.beetle_sprites:images += self.beetle_sprites.images
        images += self.scorpion_sprites.images
        images += self.platform_sprites.images
        images += self.spike_sprites.images
        images += self.vulture_sprites.images
        images += self.crystal_sprites.images
        images += self.medallion_sprites.images
        images += [self.life_symbol]
        images += self.obelisk_sprites.images
        images += self.menu.images
        images += [self.haze,self.hud_panel,self.help_panel,self.title_shade,
                   self.overlay_shade,self.diagnostic_panel]
        images += list(self.text_cache.values())
        if self.loading.active and self.loading.enabled:
            for start in range(0,len(images),40):
                self.native_canvas.preload(images[start:start+40])
                self.loading_stage(.86+.09*min(len(images),start+40)/len(images),'Transfert des textures vers le rendu…')
        else:self.native_canvas.preload(images)

    def prepare_rendering(self):
        """Warm the real scene, HUD and common effects without advancing play."""
        state=self.state
        try:
            for level_id in (1,2,3,4):
                gem_count=len(level(level_id)[1])
                for count in range(gem_count+1):self.cache_text(f'{count:02} / {gem_count}',23,GOLD)
            for label in ('NIVEAU 01  /  LE SEUIL DU DÉSERT','NIVEAU 02  /  LE DÉSERT','NIVEAU 03  /  LE TEMPLE','NIVEAU 04  /  LA TOUR'):
                self.cache_text(label,11,(198,209,199))
            self.cache_text('LA RIVIÈRE EST MORTELLE · EMPRUNTEZ LES PASSERELLES',16,GOLD)
            self.cache_text('LE SEUIL EST FRANCHI',44,GOLD,True)
            self.cache_text('NIVEAU 02 · LE DÉSERT',24)
            self.cache_text('Entrée, Start ou A pour continuer',18)
            self.cache_text('LE TEMPLE EST ATTEINT',44,GOLD,True)
            self.cache_text('NIVEAU 03 · LE TEMPLE',24)
            self.cache_text('LE SANCTUAIRE EST ATTEINT',44,GOLD,True)
            self.cache_text('LE SOMMET EST ATTEINT',44,GOLD,True)
            self.cache_text('NIVEAU 04 · LA TOUR',24)
            self.cache_text('L’ASCENSION EST TERMINÉE',24)
            for percent in range(101):self.cache_text(f'ASCENSION : {percent} %',16,GOLD)
            for label,color in (('ÉNERGIE SOLAIRE',GOLD),('ÉNERGIE SOLAIRE',(247,144,65)),
                                ('ÉNERGIE SOLAIRE ÉPUISÉE',(247,144,65)),
                                ('ÉNERGIE INSUFFISANTE',(255,160,91))):
                self.cache_text(label,10,color)
            self.cache_text('POINT DE REPRISE ACTIVÉ',19,GOLD)
            for count in range(4):self.cache_text(f'{count} / 3',20,GOLD)
            self.cache_text('VIE +1 OBTENUE',10,GOLD)
            self.cache_text('VIES',9,GOLD)
            self.cache_text('GAME OVER',44,GOLD,True)
            self.cache_text('Vous avez perdu toutes vos vies.',24)
            self.cache_text('Entrée, Start ou A pour une nouvelle partie',18)
            self.native_canvas.begin()
            self.menu.prepare(self)
            for digit in '0123456789':self.cache_text(digit,12)
            self.cache_text('FPS',10,GOLD)
            # Include half-pixel rounding variants before their first appearance.
            self.native_canvas.begin()
            for width in (47,48,49):
                for height in (7,8):
                    size=(width,height);color=(91,73,48)
                    self.native_canvas.raster(('ellipse',color,size,0),size,
                        lambda image,color=color:pg.draw.ellipse(image,color,image.get_rect()),(100,100))
            for width in (230,231,232):
                for height in (11,12,13):
                    size=(width,height);color=(81,69,44)
                    self.native_canvas.raster(('ellipse',color,size,0),size,
                        lambda image,color=color:pg.draw.ellipse(image,color,image.get_rect()),(100,100))
            for color in (GOLD,(130,224,227),(199,165,108)):
                for radius in (1,2,3):draw.circle(self.canvas,color,(100,100),radius)
            for name in ('title','settings','controls','play','pause','game_over'):
                self.state=name;self.draw(1,present=False)
            self.native_canvas.preload(list(self.text_cache.values()))
        finally:
            self.state=state
            # Submit the offscreen work; no screen swap or GPU readback.
            if self.native_canvas.gpu:self.native_canvas.renderer.target=None

    def capture(self):return self.native_canvas.capture()

    def close(self):
        self.native_canvas.release()
        if hasattr(self, 'gamepads'):
            self.gamepads.close()
        if pg.display.get_init():pg.mouse.set_visible(True)
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
                self.prepare_rendering()
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
        self.pending_drop=False
        if hasattr(self,'menu'):self.save_settings()

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

    def new_game(self):
        self.lives=STARTING_LIVES
        self.medallions=MedallionInventory()
        self.level_id=1
        self.reset()

    def start_level(self,level_id):
        if level_id not in (1,2,3,4):raise ValueError(f'Niveau inconnu : {level_id}')
        self.level_id=level_id
        self.reset()

    def continue_or_restart(self):
        if self.state=='win' and self.level_id in (1,2,3):
            self.start_level(self.level_id+1)
            self.resume_from_menu()
        else:self.resume_from_menu(new_game=True)

    def reset(self):
        self.gamepads.stop_rumble()
        self.energy.reset()
        self.solar.reset()
        self.rest.reset()
        self.wake_blocked=False
        self.dead_beetles=set()
        config={2:desert_level,3:temple_level,4:tower_level}.get(self.level_id)
        self.world_length=config.LENGTH if config else WORLD
        self.world_height=tower_level.HEIGHT if self.level_id==4 else VIEW_H
        self.beetle_spawns=config.BEETLES if config else SPAWNS
        self.vulture_spawns=config.VULTURES if config else VULTURE_SPAWNS
        self.medallion_anchor=config.MEDALLION if config else FIRST_MEDALLION
        self.beetle_motions=[BeetleMotion(i,spawns=self.beetle_spawns) for i in range(len(self.beetle_spawns))]
        self.vultures=[Vulture(i,self.vulture_spawns) for i in range(len(self.vulture_spawns))]
        self.scorpions=([Scorpion(i,tower_level.SCORPIONS) for i in range(3)] if self.level_id==4 else
                        [Scorpion(i) for i in range(len(temple_level.SCORPIONS))] if self.level_id==3 else [])
        self.laser_bolts=[]
        self.beetle_deaths=[]
        self.temple_exit=TempleExit()
        self.vases=([Vase(i,tower_level.VASES) for i in range(len(tower_level.VASES))] if self.level_id==4 else
                    [Vase(i) for i in range(len(VASE_SPAWNS))] if self.level_id==3 else [])
        self.platforms,self.gems=level(self.level_id)
        self.taken=set()
        self.hero=(Hero(*tower_level.START) if self.level_id==4 else
                   Hero(160,sand_height(160)) if self.level_id==2 else Hero())
        self.hero.grounded=True
        self.hero_animation.reset()
        self.crocodiles=[Crocodile(*spawn) for spawn in config.CROCODILES] if config else create_crocodiles()
        self.cam=self.prev_cam=0.
        self.cam_y=self.prev_cam_y=tower_level.HEIGHT-VIEW_H if self.level_id==4 else 0.
        self.checkpoint=(160,sand_height(160)-60) if self.level_id==2 else (160,560)
        if self.level_id==4:self.checkpoint=tower_level.START
        self.check_index=0
        points=config.CHECKPOINTS if config else (CHECKPOINT_X,)
        self.obelisks=([Obelisk(x,y) for x,y in points] if self.level_id==4 else
                       [Obelisk(x,sand_height(x) if self.level_id==2 else GROUND_Y) for x in points])
        self.obelisk=self.obelisks[0]
        self.deaths=0
        self.elapsed=0.
        self.previous_elapsed=0.
        self.invuln=0.
        self.particles=[]
        self.notice=0.
        self.extra_life_notice=0.
        self.acc=0.
        self.pending_jump=False
        self.pending_drop=False
        self.pending_fire=False
        self.pending_activity=False
        self.crouch_fire=False
        self.menu_gameplay_blocked=False

    def font(self,size,serif=False):
        key=(size,serif)
        if key not in self.fonts:
            self.fonts[key]=pg.font.SysFont('Georgia' if serif else 'Segoe UI',pixel(size*SCALE))
        return self.fonts[key]

    def cache_text(self,txt,size=20,color=(246,236,210),serif=False):
        txt=translate(txt,self.settings.language)
        key=(txt,size,color,serif)
        if key not in self.text_cache:
            if len(self.text_cache)>=1024:self.text_cache.pop(next(iter(self.text_cache)))
            self.text_cache[key]=self.font(size,serif).render(txt,True,color).convert_alpha()
        return self.text_cache[key]

    def text(self,txt,pos,size=20,color=(246,236,210),serif=False,center=False,max_width=None):
        s=self.cache_text(txt,size,color,serif)
        if max_width is not None and s.get_width()>max_width*SCALE:
            width=pixel(max_width*SCALE);height=max(1,round(s.get_height()*width/s.get_width()))
            x,y=self.canvas.point(pos)
            if center:x-=width//2;y-=height//2
            self.native_canvas.blit(s,(x,y,width,height))
            return
        self.canvas.blit_native(s,pos,'center' if center else 'topleft')

    def set_language(self,language):
        if language not in CODES:return
        if self.settings.language==language:return
        for image in self.text_cache.values():self.native_canvas.textures.pop(id(image),None)
        self.text_cache.clear();self.settings.language=language
        self.prepare_rendering();self.save_settings()

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
            for name,freq,duration in [('gem',880,.13),('jump',260,.13),('checkpoint',660,.3),('fall',140,.25),('win',520,.7),('crocodile',95,.18),('solar',1100,.20),('bong',185,.24)]:
                data=array('h')
                for i in range(int(rate*duration)):
                    t=i/rate; env=(1-t/duration)**2
                    f=freq*(1+t*2) if name!='fall' else freq*(1-t)
                    if name=='bong':
                        v=int(3600*math.exp(-19*t)*(math.sin(2*math.pi*freq*t)
                              +.48*math.sin(2*math.pi*freq*2.76*t)+.22*math.sin(2*math.pi*freq*5.4*t)))
                    else:v=int(1900*env*(math.sin(2*math.pi*f*t)+.3*math.sin(4*math.pi*f*t)))
                    for _ in range(channels): data.append(v)
                self.sounds[name]=pg.mixer.Sound(buffer=data)
            self.sounds['medallion']=pg.mixer.Sound(buffer=medallion_tune(rate,channels))
        except (pg.error,ImportError): pass

    def sound(self,name):
        if self.sound_on and name in self.sounds: self.sounds[name].play()

    def burst(self,x,y,color,n=16):
        for _ in range(n):
            a=self.rng.random()*math.tau; v=self.rng.uniform(35,170)
            self.particles.append([x,y,math.cos(a)*v,math.sin(a)*v,self.rng.uniform(.3,.7),color])

    def update(self,dt,axis,held,pressed,drop=False,fire=False,activity=False,down=False):
        if self.state=='game_over':return
        if self.temple_exit.active:
            if self.state!='play':return
            self.previous_elapsed=self.elapsed;self.elapsed+=dt
            finished=self.temple_exit.update(dt,self.hero)
            self.hero_animation.update(dt,self.hero,True,self.solar,self.rest)
            self.prev_cam=self.cam
            self.cam+=(self.world_length-VIEW_W-self.cam)*(1-math.exp(-5.8*dt))
            if finished:self.state='win';self.sound('win')
            return
        self.previous_elapsed=self.elapsed
        self.elapsed+=dt
        self.extra_life_notice=max(0.,self.extra_life_notice-dt)
        solids=self.collision_platforms()
        for vase in self.vases:vase.update(dt)
        for motion in self.beetle_motions:
            if motion.index not in self.dead_beetles:
                motion.update(dt,self.elapsed,self.hero,solids,can_attack=self.invuln<=0)
        for death in self.beetle_deaths:death.update(dt)
        self.beetle_deaths=[death for death in self.beetle_deaths if death.age<DEATH_TIME]
        was_resting=self.rest.active
        user_activity=bool(activity or axis or held or pressed or drop or fire or down)
        eligible=(self.hero.grounded and abs(self.hero.vx)<1 and self.hero.recovery<=0
                  and self.hero.drop_elapsed is None and not self.solar.active and self.hero_animation.landing<=0
                  and self.hero.crouch<=0)
        self.rest.update(dt,user_activity,eligible,self.hero.face)
        if was_resting and user_activity:self.wake_blocked=True
        if not self.rest.active and not was_resting and not user_activity:self.wake_blocked=False
        if self.rest.active or was_resting or self.wake_blocked:
            axis=0;held=False;pressed=False;drop=False;fire=False;down=False
            self.crouch_fire=False
            self.hero.vx=0.
        was_grounded=self.hero.grounded
        posture=self.solar.crouched if self.solar.active else down
        self.hero.update(dt,axis,held,pressed,solids,drop=drop,allow_glide=self.energy.can_glide,down=posture)
        for guardian in self.vultures:
            guardian.update(dt,self.hero,solids,can_attack=self.invuln<=0)
        for enemy in self.scorpions:
            bolt=enemy.update(dt,self.hero,solids,can_attack=self.invuln<=0)
            if bolt is not None:self.laser_bolts.append(bolt)
        if self.hero.head_bump:self.sound('bong')
        if self.hero.floating or self.hero.landed_gliding:self.energy.drain_glide(dt)
        for i,(x,y) in enumerate(self.gems):
            if i not in self.taken and abs(self.hero.x-x)<31 and abs(self.hero.y-28-y)<42:
                self.taken.add(i);self.energy.collect();self.burst(x,y,GOLD,12);self.sound('gem')
        if self.medallions.available(self.level_id) and touches_medallion(self.hero,self.elapsed,self.medallion_anchor):
            if self.medallions.collect(self.level_id):
                x,y=medallion_position(self.elapsed,self.medallion_anchor);self.burst(x,y,GOLD,24);self.sound('medallion')
                if self.medallions.redeem_extra_life():
                    self.lives+=1;self.extra_life_notice=3.
        if not down or not self.hero.grounded or self.hero.drop_elapsed is not None or self.hero.recovery>0:
            self.crouch_fire=False
        if (fire and down and self.hero.grounded and self.hero.crouch<1-1e-9
                and self.hero.drop_elapsed is None and self.hero.recovery<=0
                and not self.solar.active and self.solar.cooldown<=0):
            self.crouch_fire=True;fire=False
        if self.crouch_fire and self.hero.crouch>=1-1e-9:
            fire=True;self.crouch_fire=False
        if self.solar.update(dt,self.hero,fire,self.energy):self.sound('solar')
        if not self.hero.grounded:self.rest.reset()
        self.hero_animation.update(dt,self.hero,was_grounded,self.solar,self.rest)
        if was_grounded and not self.hero.grounded and self.hero.vy<0: self.sound('jump')
        self.prev_cam=self.cam
        if self.level_id==4:
            self.cam=self.prev_cam=0.
            self.prev_cam_y=self.cam_y
            self.cam_y+=(tower_level.camera_target(self.hero.y)-self.cam_y)*(1-math.exp(-5.8*dt))
        else:
            target=max(0,min(self.world_length-VIEW_W,self.hero.x-VIEW_W*.40+self.hero.vx*.24))
            self.cam+=(target-self.cam)*(1-math.exp(-5.8*dt))
        self.invuln=max(0,self.invuln-dt)
        self.notice=max(0,self.notice-dt)
        for enemy in self.crocodiles:
            event=enemy.update(dt,self.hero,can_attack=self.invuln<=0)
            if event=='warning':self.sound('crocodile')
            elif event=='lunge':self.burst(enemy.x+enemy.facing*35,enemy.y-4,(199,165,108),10)
        self.solar_hits()
        for index,obelisk in enumerate(self.obelisks,1):
            if obelisk.update(dt,self.hero) and index>self.check_index:
                self.checkpoint=(obelisk.x-60,obelisk.y);self.check_index=index;self.notice=3
                self.sound('checkpoint')
        hit=self.hero.y>(tower_level.HEIGHT+160 if self.level_id==4 else 850) or self.hero.spike_hit or (self.level_id==2 and desert_level.water_hits(self.hero))
        if self.level_id in (3,4) and self.temple_art.flame_hits(self.hero,self.elapsed,
                tower_level.TORCHES if self.level_id==4 else None):hit=True
        for bolt in self.laser_bolts:
            if bolt.update(dt,self.hero,solids,can_hit=self.invuln<=0):hit=True
        self.laser_bolts=[bolt for bolt in self.laser_bolts if bolt.alive]
        for x,y in self.enemy_positions():
            if self.invuln<=0 and abs(self.hero.x-x)<32 and abs(self.hero.y-self.hero.body_height/2-y)<self.hero.body_height/2+6:hit=True
        if self.invuln<=0 and any(enemy.hits(self.hero) for enemy in self.crocodiles):hit=True
        if self.invuln<=0 and any(enemy.hits(self.hero) for enemy in self.vultures):hit=True
        if self.invuln<=0 and any(enemy.hits(self.hero) for enemy in self.scorpions):hit=True
        if hit:
            self.laser_bolts.clear()
            self.gamepads.rumble('death')
            self.deaths+=1;self.lives=max(0,self.lives-1)
            if self.lives==0:
                self.state='game_over'
                self.hero_animation.reset()
                self.solar.reset();self.rest.reset();self.crouch_fire=False
                self.pending_jump=self.pending_drop=self.pending_fire=self.pending_activity=False
                return
            self.hero=Hero(*self.checkpoint)
            self.hero_animation.reset()
            self.solar.reset()
            self.energy.refill()
            self.beetle_motions=[BeetleMotion(i,self.elapsed,self.beetle_spawns) for i in range(len(self.beetle_spawns))]
            for enemy in self.scorpions:
                if enemy.alive:enemy.reset()
            self.vultures=[Vulture(enemy.index,self.vulture_spawns) if enemy.alive else enemy for enemy in self.vultures]
            self.rest.reset();self.wake_blocked=False
            self.crouch_fire=False
            for enemy in self.crocodiles:
                if enemy.alive:enemy.reset()
            self.cam=self.prev_cam=max(0,min(self.world_length-VIEW_W,self.hero.x-VIEW_W*.4))
            if self.level_id==4:self.cam_y=self.prev_cam_y=tower_level.camera_target(self.hero.y)
            self.invuln=2.;self.sound('fall');self.burst(self.hero.x,self.hero.y-25,(130,224,227),24)
        elif self.hero.head_bump:
            self.gamepads.rumble('head_bump')
        elif not was_grounded and self.hero.grounded and not self.hero.landed_gliding and self.hero.impact_vy>100 and self.hero.landing_kind=='land_heavy':
            self.gamepads.rumble('land_heavy')
        if self.level_id==3 and not hit and self.temple_exit.can_start(self.hero):
            self.temple_exit.begin(self.hero);self.solar.reset();self.rest.reset();self.crouch_fire=False
            self.laser_bolts.clear()
        finished=(desert_level.temple_entered(self.hero) if self.level_id==2 else
                  tower_level.completed(self.hero) if self.level_id==4 else
                  self.level_id==1 and self.hero.x>=self.world_length+EXIT_MARGIN)
        if self.state=='play' and finished:
            self.state='win';self.sound('win')
        for p in self.particles:
            p[0]+=p[2]*dt;p[1]+=p[3]*dt;p[3]+=100*dt;p[4]-=dt
        self.particles=[p for p in self.particles if p[4]>0]
        self.energy.update_display(dt)

    def collision_platforms(self):
        return self.platforms+[v for v in self.vases if not v.broken] if self.vases else self.platforms

    def enemy_positions(self):
        return [(x,y) for _,x,y in self.beetles()]

    def beetles(self,alpha=1.):
        return [(motion.index,*motion.position(alpha)) for motion in self.beetle_motions if motion.index not in self.dead_beetles]

    def solar_hits(self):
        if not self.solar.emitting:return
        beam=self.solar.bounds(self.hero,self.collision_platforms())
        contact=beam.inflate(2,2)
        for vase in self.vases:
            if not vase.broken and contact.colliderect(vase.rect):vase.shatter()
        for guardian in self.vultures:
            if guardian.alive and beam.colliderect(guardian.hurtbox):guardian.ignite()
        for enemy in self.crocodiles:
            if enemy.alive and beam.colliderect(enemy.hurtbox):
                enemy.ignite()
        for enemy in self.scorpions:
            if enemy.alive and beam.colliderect(enemy.hurtbox):enemy.ignite()
        for i,x,y in self.beetles():
            if beam.colliderect(pg.Rect(round(x-30),round(y-20),60,40)):
                self.dead_beetles.add(i);self.burst(x,y,GOLD,20)
                motion=self.beetle_motions[i]
                self.beetle_deaths.append(BeetleDeath(x,y,motion.facing,motion.vx,motion.vy))

    def background(self,cam):
        if self.level_id==3 and (self.state not in MENU_PAGES or self.state=='pause'):
            self.temple_art.background(self.canvas,cam,self.elapsed)
            return
        if self.level_id==2 and self.state not in ('title','settings','controls'):
            self.desert_art.background(self.canvas,cam)
            return
        for layer in self.background_layers:layer.draw(self.native_canvas,cam*SCALE)
        # Atmospheric haze is translucent, preserving the photographed stone.
        self.canvas.blit(self.haze,(0,500))

    def platform(self,p,cam):
        x=p.x-cam;y=int(p.y);w=int(p.w);h=int(p.h)
        if x>VIEW_W+60 or x+w<-60:return
        if self.level_id==3 and p.ground:
            self.temple_art.floor(self.canvas,p,cam);return
        if self.level_id==2:
            if p.kind=='dune':
                self.desert_art.dune_floor(self.canvas,p,cam);return
            if p.kind in ('rock','bridge'):
                self.desert_art.platform(self.canvas,p,cam);return
            if p.ground:
                self.desert_art.sand_floor(self.canvas,p,cam);return
        if not p.ground:
            self.platform_sprites.draw(self.canvas,p,cam)
            if p.spiked:self.spike_sprites.draw(self.canvas,p,cam)
            return
        draw.rect(self.canvas,(58,50,37),(x+5,y+10,w,h))
        for tx in range(max(0,math.floor(-x/128)),math.ceil(w/128)):
            tile=self.tiles[(int(p.x)//10+tx)%4]
            tw=min(128,w-tx*128)
            for ty in range(0,h,128):
                self.canvas.blit(tile,(x+tx*128,y+ty),(0,0,tw,min(128,h-ty)))
        draw.rect(self.canvas,(229,190,125),(x-4,y,w+8,7))
        draw.line(self.canvas,(103,73,41),(x,y+15),(x+w,y+15),3)

    def draw_hero(self,x,y,alpha=1):
        h=self.hero;t=self.time;f=h.face
        if self.temple_exit.active and self.temple_exit.elapsed>=APPROACH:
            self.temple_exit_sprites.draw(self.canvas,self.temple_exit,h,h.px+(h.x-h.px)*alpha-x,alpha)
            return
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
            if not enemy.alive and not (self.crocodile_sprites and self.crocodile_sprites.burn):continue
            x=enemy.px+(enemy.x-enemy.px)*alpha-cam
            if not -180<x<VIEW_W+180:continue
            if enemy.alive:draw.ellipse(self.canvas,(81,69,44),(x-77,enemy.y-5,154,8))
            if self.crocodile_sprites:
                self.crocodile_sprites.sample(enemy,alpha).draw(self.canvas,x,enemy.y,enemy.facing)
            else:
                # Visible fallback for development checkouts without the atlas.
                f=enemy.facing;y=enemy.y
                draw.polygon(self.canvas,(63,79,55),[(x-f*45,y-22),(x-f*145,y-44),(x-f*85,y-8),(x,y-5)])
                draw.ellipse(self.canvas,(68,85,58),(x-55,y-33,117,30))
                draw.rect(self.canvas,(83,99,65),(x+f*72-31,y-25,62,18),border_radius=5)
                draw.circle(self.canvas,(219,177,71),(x+f*64,y-28),3)

    def draw_tower(self,alpha,started,present):
        render_y=self.prev_cam_y+(self.cam_y-self.prev_cam_y)*alpha
        camera=pixel(render_y*SCALE)/SCALE
        original=self.canvas
        self.tower_art.background(original,render_y)
        animation_time=self.previous_elapsed+(self.elapsed-self.previous_elapsed)*alpha
        self.canvas=VerticalCanvas(self.native_canvas,camera)
        try:
            for x,y in tower_level.TORCHES:
                if camera-100<y<camera+VIEW_H+100:self.temple_art.draw_torch(self.canvas,x,y,animation_time)
            for platform in self.platforms:
                if platform.ground:
                    self.tower_art.structure(self.canvas,platform,camera)
                elif camera-40<platform.y<camera+VIEW_H+40:
                    self.platform_sprites.draw(self.canvas,platform,0)
                    if platform.spiked:self.spike_sprites.draw(self.canvas,platform,0)
            for i,(x,y) in enumerate(self.gems):
                if i not in self.taken and camera-70<y<camera+VIEW_H+70:
                    self.crystal_sprites.draw(self.canvas,x,y,animation_time,i)
            if self.medallions.available(4):
                x,y=medallion_position(animation_time,self.medallion_anchor)
                if camera-100<y<camera+VIEW_H+100:self.medallion_sprites.draw(self.canvas,x,y,animation_time)
            for obelisk in self.obelisks:
                if camera-50<obelisk.y<camera+VIEW_H+200:
                    self.obelisk_sprites.draw(self.canvas,obelisk,obelisk.x,obelisk.y,alpha)
            for i,x,y in self.beetles(alpha):
                if camera-100<y<camera+VIEW_H+100:
                    self.beetle_sprites.draw(self.canvas,self.beetle_motions[i].sample(alpha),x,y)
            for death in self.beetle_deaths:
                if camera-150<death.y<camera+VIEW_H+150:self.beetle_sprites.draw_death(self.canvas,death,alpha)
            for vase in self.vases:
                if camera-100<vase.floor<camera+VIEW_H+100:self.vase_sprites.draw(self.canvas,vase,0,alpha)
            for enemy in self.scorpions:
                if camera-200<enemy.y<camera+VIEW_H+200:self.scorpion_sprites.draw(self.canvas,enemy,0,alpha)
            for bolt in self.laser_bolts:
                if camera-100<bolt.y<camera+VIEW_H+100:self.scorpion_sprites.draw_bolt(self.canvas,bolt,0,alpha)
            hx=self.hero.px+(self.hero.x-self.hero.px)*alpha
            hy=self.hero.py+(self.hero.y-self.hero.py)*alpha
            if self.solar.active or self.invuln<=0 or int(self.time*12)%2==0:self.draw_hero(hx,hy,alpha)
            self.solar.draw(self.canvas,self.hero,self.collision_platforms(),0,alpha)
            for x,y,vx,vy,life,color in self.particles:
                if camera-30<y<camera+VIEW_H+30:draw.circle(self.canvas,color,(x,y),max(1,int(life*5)))
        finally:self.canvas=original
        self.hud(alpha)
        if self.state=='play':
            self.text(f'ASCENSION : {tower_level.progress(self.hero.y)} %',(VIEW_W/2,104),16,GOLD,center=True)
            if self.notice>0:self.text('POINT DE REPRISE ACTIVÉ',(VIEW_W/2,132),19,GOLD,center=True)
        elif self.state=='pause':self.menu.draw(self)
        elif self.state=='win':
            self.overlay('LE SOMMET EST ATTEINT','L’ASCENSION EST TERMINÉE','Entrée, Start ou A pour rejouer')
        elif self.state=='game_over':
            self.overlay('GAME OVER','Vous avez perdu toutes vos vies.','Entrée, Start ou A pour une nouvelle partie')
        if self.show_fps:self.draw_fps()
        if self.show_stats:self.draw_diagnostics()
        if present:self.present_frame(started)

    def draw(self,alpha=1,present=True):
        started=time.perf_counter()
        self.native_canvas.begin()
        alpha=max(0.,min(1.,alpha))
        if self.state in MENU_PAGES and self.state!='pause':
            self.background(0.)
            self.menu.draw(self)
            if present:self.present_frame(started)
            return
        if self.level_id==4:
            self.draw_tower(alpha,started,present);return
        render_cam=self.prev_cam+(self.cam-self.prev_cam)*alpha
        self.background(render_cam)
        # Snap once for the entire gameplay plane, independently of the layers.
        cam=pixel(render_cam*SCALE)/SCALE
        animation_time=self.previous_elapsed+(self.elapsed-self.previous_elapsed)*alpha
        if self.level_id==2:
            self.desert_art.river(self.canvas,cam,animation_time)
            self.desert_art.temple_background(self.canvas,cam)
        for p in self.platforms:self.platform(p,cam)
        if self.level_id==2:
            self.desert_art.shorelines(self.canvas,cam,animation_time)
            self.desert_art.reeds(self.canvas,cam)
        for i,(gx,gy) in enumerate(self.gems):
            if i in self.taken:continue
            x=gx-cam
            if not -30<x<VIEW_W+30:continue
            self.crystal_sprites.draw(self.canvas,x,gy,animation_time,i)
        if self.level_id not in self.medallions.claimed_levels:
            mx,my=medallion_position(animation_time,self.medallion_anchor)
            if -80<mx-cam<VIEW_W+80:self.medallion_sprites.draw(self.canvas,mx-cam,my,animation_time)
        for obelisk in self.obelisks:
            if -100<obelisk.x-cam<VIEW_W+100:
                self.obelisk_sprites.draw(self.canvas,obelisk,obelisk.x-cam,obelisk.y,alpha)
        for i,ex,ey in self.beetles(alpha):
            x=ex-cam
            if self.beetle_sprites:
                if -100<x<VIEW_W+100:self.beetle_sprites.draw(self.canvas,self.beetle_motions[i].sample(alpha),x,ey)
                continue
            if -70<x<VIEW_W+70:
                wing=math.sin(self.time*13)*12
                draw.ellipse(self.canvas,(58,68,57),(x-32,ey-8-wing,30,12+abs(wing)))
                draw.ellipse(self.canvas,(58,68,57),(x+2,ey-8-wing,30,12+abs(wing)))
                draw.ellipse(self.canvas,(31,67,64),(x-12,ey-13,24,29))
                draw.ellipse(self.canvas,(183,148,73),(x-8,ey-10,16,22),2)
                draw.circle(self.canvas,(234,168,69),(x,ey-14),4)
        for death in self.beetle_deaths:
            if self.beetle_sprites:
                self.beetle_sprites.draw_death(self.canvas,death,alpha,cam)
        for vase in self.vases:
            if -100<vase.center-cam<VIEW_W+100:self.vase_sprites.draw(self.canvas,vase,cam,alpha)
        self.draw_crocodiles(cam,alpha)
        for enemy in self.scorpions:
            if -200<enemy.x-cam<VIEW_W+200:self.scorpion_sprites.draw(self.canvas,enemy,cam,alpha)
        for bolt in self.laser_bolts:self.scorpion_sprites.draw_bolt(self.canvas,bolt,cam,alpha)
        for guardian in self.vultures:
            gx,gy=guardian.position(alpha)
            if -180<gx-cam<VIEW_W+180:self.vulture_sprites.draw(self.canvas,guardian,cam,alpha)
        hx=(self.hero.px+(self.hero.x-self.hero.px)*alpha)-cam
        hy=self.hero.py+(self.hero.y-self.hero.py)*alpha
        if self.temple_exit.active or self.solar.active or self.invuln<=0 or int(self.time*12)%2==0:self.draw_hero(hx,hy,alpha)
        self.solar.draw(self.canvas,self.hero,self.collision_platforms(),cam,alpha)
        if self.level_id==2:self.desert_art.temple_foreground(self.canvas,cam)
        elif self.level_id==3:self.temple_art.foreground(self.canvas,cam)
        for px,py,vx,vy,life,col in self.particles:
            draw.circle(self.canvas,col,(px-cam,py),max(1,int(life*5)))
        # Foreground sand motes, drifting continuously at a separate depth.
        for i in range(35):
            x=(i*173+self.time*(17+i%7)-cam*.65)%(VIEW_W+40)-20
            y=160+(i*97)%520+math.sin(self.time+i)*9
            draw.line(self.canvas,(231,202,146),(x,y),(x+3,y))
        self.hud(alpha)
        if self.state=='pause':self.menu.draw(self)
        elif self.state=='win':
            if self.level_id==1:self.overlay('LE SEUIL EST FRANCHI','NIVEAU 02 · LE DÉSERT','Entrée, Start ou A pour continuer')
            elif self.level_id==2:
                self.overlay('LE TEMPLE EST ATTEINT','NIVEAU 03 · LE TEMPLE','Entrée, Start ou A pour continuer')
                self.text(f'{len(self.taken)} / {len(self.gems)} éclats solaires   ·   {int(self.elapsed)//60:02}:{int(self.elapsed)%60:02}   ·   {self.deaths} morts',(VIEW_W/2,405),16,center=True)
            else:self.overlay('LE SANCTUAIRE EST ATTEINT','NIVEAU 04 · LA TOUR','Entrée, Start ou A pour continuer')
        elif self.state=='game_over':
            self.overlay('GAME OVER','Vous avez perdu toutes vos vies.','Entrée, Start ou A pour une nouvelle partie')
        if self.notice>0 and self.state=='play':self.text('POINT DE REPRISE ACTIVÉ',(VIEW_W/2,132),19,GOLD,center=True)
        elif self.level_id==2 and self.state=='play' and self.hero.x<3600:
            self.text('LA RIVIÈRE EST MORTELLE · EMPRUNTEZ LES PASSERELLES',(VIEW_W/2,112),16,GOLD,center=True)
        if self.show_fps:self.draw_fps()
        if self.show_stats:
            self.draw_diagnostics()
        if not present:return
        self.present_frame(started)

    def present_frame(self,started):
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

    def draw_fps(self):
        now=time.perf_counter()
        if now-self.fps_updated>=.25:
            total=sum(self.frame_intervals)
            self.fps_count=min(999,round(len(self.frame_intervals)/total)) if total>0 else 0
            self.fps_updated=now
        draw.rect(self.canvas,(15,34,42),(1167,99,90,28))
        digits=str(self.fps_count)
        for index,digit in enumerate(digits):self.text(digit,(1200-9*(len(digits)-index),104),12)
        self.text('FPS',(1213,106),10,GOLD)

    def hud(self,alpha=1.):
        self.canvas.blit(self.hud_panel,(0,0))
        self.text('VIES',(34,10),9,GOLD)
        for index in range(min(self.lives,6)):
            self.canvas.blit_native(self.life_symbol,(34+(index%3)*27,29+(index//3)*23))
        if self.lives>6:self.text(f'× {self.lives}',(34,62),10,GOLD)
        self.text('LES SABLES D’HORUS',(124,20),18)
        label={1:'NIVEAU 01  /  LE SEUIL DU DÉSERT',2:'NIVEAU 02  /  LE DÉSERT',3:'NIVEAU 03  /  LE TEMPLE',4:'NIVEAU 04  /  LA TOUR'}[self.level_id]
        self.text(label,(124,45),11,(198,209,199))
        animation_time=self.previous_elapsed+(self.elapsed-self.previous_elapsed)*max(0.,min(1.,alpha))
        self.crystal_sprites.draw(self.canvas,VIEW_W-331,41,animation_time,bob=False)
        self.text(f'{len(self.taken):02} / {len(self.gems)}',(VIEW_W-311,26),23,GOLD)
        self.text('ÉCHAP / START',(VIEW_W-188,34),14)
        self.medallion_sprites.draw(self.canvas,816,39,animation_time,hud=True)
        self.text(f'{self.medallions.count} / 3',(839,27),20,GOLD)
        if self.extra_life_notice>0:self.text('VIE +1 OBTENUE',(795,61),10,GOLD)
        self.draw_solar_gauge(alpha)
        if self.state=='play' and self.hero.x<1000 and (self.level_id!=4 or self.hero.y>tower_level.BASE_Y-180):
            self.canvas.blit(self.help_panel,((VIEW_W-self.help_panel.get_width())//2,665))
            self.text('Stick / ← →  Bouger    A / Espace  Saut    Bas / S  Accroupir    RT / B / F  Tir    Maintenir A  Planer',(VIEW_W/2,682),16,center=True,max_width=1040)

    def draw_solar_gauge(self,alpha=1.):
        x,y,width,height=515,30,250,13
        low=self.energy.value<RAY_COST
        color=(247,144,65) if low else GOLD
        label='ÉNERGIE SOLAIRE' if self.energy.value>0 else 'ÉNERGIE SOLAIRE ÉPUISÉE'
        self.text(label,(x,10),10,color)
        draw.rect(self.canvas,(15,28,33),(x-2,y-2,width+4,height+4))
        draw.rect(self.canvas,(123,110,72),(x-2,y-2,width+4,height+4),1)
        draw.rect(self.canvas,(46,58,57),(x,y,width,height))
        filled=width*self.energy.fraction(alpha)
        if filled>0:
            draw.rect(self.canvas,color,(x,y,filled,height))
            draw.rect(self.canvas,(255,235,165),(x,y,filled,3))
        for threshold in (RAY_COST,2*RAY_COST,3*RAY_COST):
            marker=x+width*threshold/MAX_ENERGY
            draw.line(self.canvas,(104,92,60),(marker,y+height-3),(marker,y+height),1)
        draw.circle(self.canvas,color,(x-15,y+height/2),5)
        for angle in range(0,360,60):
            a=math.radians(angle)
            draw.line(self.canvas,color,(x-15+math.cos(a)*8,y+height/2+math.sin(a)*8),
                      (x-15+math.cos(a)*10,y+height/2+math.sin(a)*10),1)
        if self.energy.warning>0:self.text('ÉNERGIE INSUFFISANTE',(x,y+height+5),10,(255,160,91))

    def title(self):
        self.menu.draw(self,'title')

    def save_settings(self):
        self.settings.fullscreen=self.fullscreen
        self.settings.sound=self.sound_on
        self.settings.rumble=self.gamepads.rumble_enabled
        self.settings.show_fps=self.show_fps
        self.menu.save_failed=not self.settings.save(self.settings_path)

    def toggle_sound(self):
        self.sound_on=not self.sound_on;self.save_settings()

    def enter_menu(self,page):
        self.gamepads.stop_rumble()
        self.state=page;self.acc=0.
        self.pending_jump=self.pending_drop=self.pending_fire=self.pending_activity=False
        self.menu.enter(page)
        self.controller_lost=False
        if page in ('save','load'):self.menu.refresh_slots(self)

    def update_cursor(self,now,moved=False):
        if self.state not in MENU_PAGES:self.mouse_last_motion=None
        elif moved:self.mouse_last_motion=now
        visible=self.mouse_last_motion is not None and now-self.mouse_last_motion<3.
        if pg.mouse.get_visible()!=visible:pg.mouse.set_visible(visible)

    def resume_from_menu(self,new_game=False):
        if new_game:self.new_game()
        self.state='play';self.acc=0.
        self.pending_jump=self.pending_drop=self.pending_fire=self.pending_activity=False
        self.menu_gameplay_blocked=True
        self.update_cursor(time.perf_counter())

    def menu_action(self,action):
        page=self.state
        if page not in MENU_PAGES:return
        if action in ('up','down'):
            self.menu.move(page,-1 if action=='up' else 1);return
        if action=='back':
            if page=='controls':self.enter_menu('settings')
            elif page=='settings':self.enter_menu(self.menu.origin)
            elif page=='save':self.enter_menu('pause')
            elif page=='load':self.enter_menu('title')
            elif page=='overwrite':self.enter_menu('save')
            elif page=='languages':self.enter_menu('settings')
            elif page=='pause':self.resume_from_menu()
            else:self.quit_requested=True
            return
        index=self.menu.selected[page]
        if page=='languages':
            if action in ('left','right') and index<len(CODES):self.menu.selected[page]=index^1
            elif action=='activate':
                if index==len(CODES):self.enter_menu('settings')
                else:self.set_language(CODES[index])
            return
        if page in ('save','load','overwrite'):
            if action!='activate':return
            if page=='overwrite':
                if index==0:self.save_slot(self.menu.slot_index)
                else:self.enter_menu('save')
            elif index==5:self.enter_menu('pause' if page=='save' else 'title')
            elif page=='save':
                self.menu.slot_index=index
                if self.menu.slots[index].status!='empty':
                    self.menu.selected['overwrite']=1;self.enter_menu('overwrite')
                else:self.save_slot(index)
            else:self.load_slot(index)
            return
        if page=='settings':
            if index==0:self.toggle_fullscreen()
            elif index==1:self.toggle_sound()
            elif index==2:
                self.gamepads.rumble_enabled=not self.gamepads.rumble_enabled
                if not self.gamepads.rumble_enabled:self.gamepads.stop_rumble()
                self.save_settings()
            elif index==3:
                self.show_fps=not self.show_fps;self.save_settings()
            elif action=='activate' and index==4:self.enter_menu('controls')
            elif action=='activate' and index==5:
                self.menu.selected['languages']=CODES.index(self.settings.language);self.enter_menu('languages')
            elif action in ('left','right') and index==5:
                offset=-1 if action=='left' else 1
                self.set_language(CODES[(CODES.index(self.settings.language)+offset)%len(CODES)])
            elif action=='activate' and index==6:self.enter_menu(self.menu.origin)
        elif action=='activate':
            if page=='controls':self.enter_menu('settings')
            elif index==0:self.resume_from_menu(new_game=page=='title')
            elif index==1:
                self.menu.origin=page;self.enter_menu('settings')
            elif index==2:self.enter_menu('save' if page=='pause' else 'load')
            elif page=='pause' and index==3:
                self.menu.selected['title']=0;self.enter_menu('title')
            else:self.quit_requested=True

    def save_slot(self,index):
        try:self.saves.write(index,capture_save(self))
        except (OSError,ValueError,TypeError):
            self.enter_menu('save');self.menu.message='Échec de la sauvegarde. La case précédente est conservée.'
        else:
            self.enter_menu('save');self.menu.message=f'Partie sauvegardée dans l’emplacement {index+1}.'

    def load_slot(self,index):
        slot=self.saves.read(index)
        if slot.status!='ready':
            self.menu.refresh_slots(self)
            self.menu.message='Cette case est vide ou ne peut pas être chargée.'
            return
        try:restore_save(self,slot.data)
        except (ValueError,TypeError,KeyError):
            self.menu.message='Impossible de charger cette sauvegarde.'
            return
        self.resume_from_menu()

    def menu_key(self,key,text=''):
        if self.state=='title':
            character=text or ({pg.K_KP0:'0',pg.K_KP2:'2'}.get(key,pg.key.name(key)))
            typed=len(character)==1 and character.isascii() and character.isalnum()
            if not typed and key not in (pg.K_LSHIFT,pg.K_RSHIFT,pg.K_LCTRL,pg.K_RCTRL,
                                         pg.K_LALT,pg.K_RALT,pg.K_CAPSLOCK,pg.K_NUMLOCK):self.menu.code=''
            if typed and self.menu.feed_code(character,self.time):
                self.new_game();self.start_level(self.menu.code_level);self.resume_from_menu()
                return
        if key in (pg.K_UP,pg.K_w,pg.K_z):self.menu_action('up')
        elif key in (pg.K_DOWN,pg.K_s):self.menu_action('down')
        elif key in (pg.K_LEFT,pg.K_q,pg.K_a):self.menu_action('left')
        elif key in (pg.K_RIGHT,pg.K_d):self.menu_action('right')
        elif key in (pg.K_RETURN,pg.K_SPACE):self.menu_action('activate')
        elif key==pg.K_ESCAPE:self.menu_action('back')
        elif key==pg.K_r and self.state=='pause':self.reset();self.state='play'

    def menu_pointer(self,position):
        if self.display_flags & pg.SCALED:return position[0]/SCALE,position[1]/SCALE
        size,offset=integer_viewport(self.screen.get_size(),(W,H))
        factor=size[0]/W*SCALE
        return (position[0]-offset[0])/factor,(position[1]-offset[1])/factor

    def overlay(self,title,sub,helptext):
        self.canvas.blit(self.overlay_shade,(0,0))
        self.text(title,(VIEW_W/2,280),44,GOLD,True,True,max_width=VIEW_W-100)
        self.text(sub,(VIEW_W/2,365),24,center=True,max_width=VIEW_W-100)
        self.text(helptext,(VIEW_W/2,442),18,center=True,max_width=VIEW_W-100)

    def handle_pad(self, pad):
        lost=pad.disconnected or (self.pad.connected and not pad.connected)
        reconnected=pad.connected and not self.pad.connected and self.controller_lost
        self.pad=pad
        if pad.connected:self.controller_lost=False
        # Reconnecting clears the warning, but a button held during reconnect
        # must not resume the paused game. The next deliberate press can resume.
        if reconnected and self.state=='pause':return
        if self.state=='play' and lost:
            self.menu.selected['pause']=0;self.enter_menu('pause')
            self.controller_lost=True
            return
        if pad.activity or pad.axis or pad.jump_held or pad.jump_pressed or pad.down_held or pad.fire_pressed or pad.sound_pressed or pad.start_pressed or pad.back_pressed:
            self.pending_activity=True
        if self.state=='play' and (self.rest.active or self.wake_blocked):return
        if self.state=='play' and pad.fire_pressed and not (pad.start_pressed or pad.back_pressed):
            self.pending_fire=True
        if pad.sound_pressed:self.toggle_sound()
        if pad.back_pressed and not pad.start_pressed and self.state in ('play','pause'):
            self.reset();self.state='play'
            return
        if self.state in MENU_PAGES:
            if pad.cancel_pressed or pad.back_pressed or (pad.start_pressed and self.state=='pause'):
                self.menu_action('back');return
            adjust=self.menu.pad_move(self.state,pad.menu_axis,pad.axis,self.time)
            if adjust:self.menu_action('right' if pad.axis>0 else 'left')
            if pad.confirm_pressed or pad.start_pressed or (pad.jump_pressed and not pad.menu_axis):
                self.menu_action('activate')
            return
        if self.state in ('win','game_over') and (pad.start_pressed or pad.jump_pressed):
            self.continue_or_restart()
        elif self.state=='play' and pad.start_pressed:
            self.menu.selected['pause']=0;self.enter_menu('pause')
        elif self.state=='play' and pad.jump_pressed:
            self.pending_jump=True
            self.pending_drop=pad.down_held

    def run(self,frames=0,screenshot=None):
        running=not self.quit_requested;count=0
        previous=time.perf_counter()
        while running:
            self.pacer.wait(self.presentation.vsync,self.presentation.refresh_hz)
            now=time.perf_counter()
            dt=min(now-previous,.1)
            previous=now
            self.time+=dt
            for e in pg.event.get():
                if e.type==pg.MOUSEMOTION and any(getattr(e,'rel',(0,0))):
                    self.update_cursor(time.perf_counter(),moved=True)
                if e.type==pg.QUIT:running=False
                elif e.type in (pg.JOYDEVICEADDED,pg.JOYDEVICEREMOVED,pg.CONTROLLERDEVICEADDED,pg.CONTROLLERDEVICEREMOVED,pg.CONTROLLERDEVICEREMAPPED):
                    self.gamepads.refresh()
                elif e.type in (pg.WINDOWMOVED,pg.WINDOWSIZECHANGED):self.refresh_display_status()
                elif e.type==pg.WINDOWFOCUSLOST:
                    self.gamepads.stop_rumble()
                    if self.state=='play':self.menu.selected['pause']=0;self.enter_menu('pause')
                elif e.type in (pg.MOUSEMOTION,pg.MOUSEBUTTONDOWN) and self.state in MENU_PAGES:
                    if self.menu.pointer(self.state,self.menu_pointer(e.pos)) and e.type==pg.MOUSEBUTTONDOWN and e.button==1:
                        self.menu_action('activate')
                elif e.type==pg.KEYDOWN:
                    self.pending_activity=True
                    if self.state=='play' and (self.rest.active or self.wake_blocked):continue
                    if e.key==pg.K_F11:
                        self.toggle_fullscreen()
                    elif e.key==pg.K_F3:self.show_stats=not self.show_stats
                    elif e.key==pg.K_m:self.toggle_sound()
                    elif self.state in MENU_PAGES:self.menu_key(e.key,getattr(e,'unicode',''))
                    elif e.key==pg.K_f and self.state=='play':self.pending_fire=True
                    elif e.key==pg.K_ESCAPE:
                        if self.state=='play':
                            self.menu.selected['pause']=0;self.enter_menu('pause')
                        elif self.state=='pause':self.state='play'
                        else:running=False
                        self.acc=0
                    elif e.key==pg.K_RETURN and self.state in ('win','game_over'):
                        self.continue_or_restart()
                    elif e.key==pg.K_r and self.state in ('play','pause'):
                        self.reset();self.state='play'
                    elif e.key in (pg.K_SPACE,pg.K_UP,pg.K_z,pg.K_w) and self.state=='play':
                        self.pending_jump=True
                        keys=pg.key.get_pressed()
                        self.pending_drop=bool(keys[pg.K_DOWN] or keys[pg.K_s])
            self.handle_pad(self.gamepads.poll())
            keys=pg.key.get_pressed()
            axis=merge_axis(int(keys[pg.K_RIGHT] or keys[pg.K_d])-int(keys[pg.K_LEFT] or keys[pg.K_q] or keys[pg.K_a]),self.pad.axis)
            held=keys[pg.K_SPACE] or keys[pg.K_UP] or keys[pg.K_z] or keys[pg.K_w] or self.pad.jump_held
            down=bool(keys[pg.K_DOWN] or keys[pg.K_s] or self.pad.down_held)
            if getattr(self,'menu_gameplay_blocked',False):
                if not (axis or held or down or any(keys) or self.pad.activity or self.pad.jump_held):
                    self.menu_gameplay_blocked=False
                axis=0;held=False;down=False
                self.pending_jump=self.pending_drop=self.pending_fire=self.pending_activity=False
            if self.quit_requested:running=False
            if self.state=='play':
                self.acc+=dt
                while self.acc>=STEP:
                    self.update(STEP,axis,held,self.pending_jump,self.pending_drop,self.pending_fire,
                                self.pending_activity or any(keys) or self.pad.activity,down=down)
                    self.pending_jump=False;self.pending_drop=False;self.pending_fire=False;self.pending_activity=False;self.acc-=STEP
                    if self.state!='play':break
            self.update_cursor(time.perf_counter())
            self.draw(self.acc/STEP if self.state=='play' else 1)
            count+=1
            if frames and count>=frames:running=False
        if screenshot:pg.image.save(self.capture(),str(screenshot))
        self.close()


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--headless',action='store_true');ap.add_argument('--frames',type=int,default=0);ap.add_argument('--screenshot');ap.add_argument('--play',action='store_true');ap.add_argument('--windowed',action='store_true')
    ap.add_argument('--level',type=int,choices=(1,2,3,4),default=1)
    args=ap.parse_args()
    try:game=Game(args.headless,fullscreen=False if args.windowed or args.headless else None)
    except LoadingCancelled:sys.exit(0)
    if args.level!=1:game.start_level(args.level)
    if args.play:game.state='play'
    try:game.run(args.frames,args.screenshot)
    finally:game.close()
