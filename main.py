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
from hoplite import Hoplite,HopliteSprites,DEATH_TIME as HOPLITE_DEATH_TIME,ATTACK_TIME as HOPLITE_ATTACK_TIME
from gamepad import Gamepads, PadSnapshot, merge_axis
from solar import SolarRay
from rest import RestPose
from energy import SolarEnergy,RAY_COST
from solar_gauge import SolarGauge
from obelisk import Obelisk,ObeliskSprites,CHECKPOINT_X,GROUND_Y,RESPAWN
from plasma_fx import PlasmaEffect
from platform_sprites import SacredPlatforms
from spikes import SpikeSprites,SPIKED_PLATFORM_X,upward_contact
from vulture import Vulture,VultureSprites,SPAWNS as VULTURE_SPAWNS
from crystal import SolarCrystals
import desert_level
import temple_level
import tower_level
import greece_levels
from greece_art import GreekWorldArt
from tower_art import TowerArt,VerticalCanvas
from desert_art import DesertArt
from vase import Vase,VaseSprites,SPAWNS as VASE_SPAWNS
from temple_art import TempleArt
from temple_exit import TempleExit,TempleExitSprites,APPROACH
from hero_death import HeroDeath,CrocodileDeathSprites,CAPTURE as DEATH_CAPTURE,BEETLE_STUN,LASER_IMPACT,LASER_DURATION,LASER_LIMIT,smooth as death_smooth
from beetle_death import BeetleDeathSprites
from blade_death import BladeDeathSprites
from sword_death import SwordDeathSprites
from hero_death import SWORD_DURATION,SWORD_IMPACT,SWORD_LAND
from laser_death import LaserDeathSprites
from fire_death import FireDeathSprites
from water_death import WaterDeathSprites,water_position
from pit_death import PitDeathSprites,pit_position
from pit_darkness import PitDarkness,pit_regions
from hero_death import FIRE_REACTION,FIRE_DURATION
from scorpion import Scorpion,ScorpionSprites
from gyrosphere import Gyrosphere,GyrosphereSprites,DEATH_TIME as GYRO_DEATH_TIME,POINTS as GYRO_POINTS
from terrain import DuneGround,sand_height
from settings import Settings
from menu import StartMenu,PAGES as MENU_PAGES
from menu_music import MenuMusic
from bezel import BezelArt
from bezel_catalog import MODES as BEZEL_MODES,theme_for
from screenshots import Screenshots
from loading import LoadingScreen,LoadingCancelled
from localization import translate,CODES
from savegame import SaveSlots,capture as capture_save,restore as restore_save
from lives import STARTING_LIVES,load_life_symbol,game_over_tune,life_position
from resurrection import Resurrection,ResurrectionSprites,REAPPEAR
from level_bonus import sample as sample_life_bonus
import hud_layout as hud_layout
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
    if level_id in greece_levels.LEVELS:return greece_levels.LEVELS[level_id].build(Platform,EXIT_MARGIN)
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
            landing=None
            for p in platforms:
                if p is self.ignored_platform:continue
                if self.x+15>p.x and self.x-15<p.x+p.w and old_bottom<=p.y+1 and self.y>=p.y:
                    # Choose the first crossed surface without sorting or
                    # changing the level's drawing order. Keep stable ties.
                    if landing is None or p.y<landing.y:landing=p
            if landing is not None:
                self.y = landing.y
                self.impact_vy = self.vy
                self.landed_gliding = self.floating
                self.landed_height = 0. if self.floating else max(0.,landing.y-self.fall_origin_y)
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
        self.screenshots=Screenshots(ROOT/'captures')
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
        self.music_ready=False
        self.menu_music=MenuMusic(ROOT/'assets'/'audio'/'menu-the-lone-flyer.ogg',enabled=not headless)
        if self.settings.music:self.menu_music.start_loading(self.settings.music_volume/100)
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
        self.greece_art=GreekWorldArt(ROOT/'assets')
        self.vase_sprites=VaseSprites.load(ROOT/'assets')
        self.loading_stage(.35,'Assemblage du monde…')
        self.tiles = [self.make_tile(128,128,i) for i in range(4)]
        self.desert_sign=pg.transform.smoothscale(
            pg.image.load(str(ROOT/'assets'/'desert-direction-sign-v1.png')).convert_alpha(),
            (pixel(111*SCALE),pixel(74*SCALE)))
        stone = ROOT/'assets'/'sandstone.png'
        if stone.exists():
            texture = pg.transform.smoothscale(pg.image.load(str(stone)).convert(), (512,512))
            self.tiles = [texture.subsurface((i*128,0,128,128)).copy() for i in range(4)]
        self.haze=pg.Surface((VIEW_W,120),pg.SRCALPHA)
        for y in range(120):
            draw.line(self.haze,(234,198,139,int(28*y/120)),(0,y),(VIEW_W,y))
        self.hud_panel=pg.Surface((W,pixel(hud_layout.HEIGHT*SCALE)),pg.SRCALPHA).convert_alpha()
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
        self.solar_gauge=SolarGauge.load(ROOT/'assets')
        self.solar=SolarRay(PlasmaEffect.load(ROOT/'assets'))
        self.rest=RestPose()
        self.loading_stage(.52,'Préparation des crocodiles…')
        self.crocodile_sprites=CrocodileSprites.load(ROOT/'assets')
        self.hoplite_sprites=HopliteSprites.load(ROOT/'assets')
        self.hero_death_sprites=CrocodileDeathSprites.load(ROOT/'assets')
        self.beetle_death_sprites=BeetleDeathSprites.load(ROOT/'assets')
        self.blade_death_sprites=BladeDeathSprites.load(ROOT/'assets')
        self.sword_death_sprites=SwordDeathSprites.load(ROOT/'assets')
        self.laser_death_sprites=LaserDeathSprites.load(ROOT/'assets')
        self.fire_death_sprites=FireDeathSprites.load(ROOT/'assets')
        self.water_death_sprites=WaterDeathSprites.load(ROOT/'assets')
        self.pit_death_sprites=PitDeathSprites.load(ROOT/'assets')
        self.pit_darkness=PitDarkness.load()
        self.loading_stage(.60,'Préparation des scarabées…')
        self.beetle_sprites=BeetleSprites.load(ROOT/'assets')
        self.scorpion_sprites=ScorpionSprites.load(ROOT/'assets')
        self.gyrosphere_sprites=GyrosphereSprites.load(ROOT/'assets')
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
        self.life_symbol_empty=self.life_symbol.copy()
        self.life_symbol_empty.fill((85,102,120,130),special_flags=pg.BLEND_RGBA_MULT)
        self.resurrection_sprites=ResurrectionSprites(self.life_symbol,ROOT/'assets'/'life-symbol-hd-v1.png')
        self.loading_stage(.81,'Préparation des menus et des sons…')
        self.menu=StartMenu(ROOT/'assets')
        self.menu.save_failed=not initial_settings_saved
        self.sound_on = self.settings.sound
        self.sounds = {}
        self.make_sounds()
        self.apply_sound_volume()
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
        self.score=0
        self.run_totals=dict(shards=0,elapsed=0.,deaths=0)
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
        self.music_ready=True
        self.sync_menu_music()

    def loading_stage(self,progress,label):
        try:self.loading.show(self.native_canvas,self.screen,progress,label)
        except LoadingCancelled:
            self.close()
            raise

    def install_canvas(self):
        if not hasattr(self,'bezel_art'):self.bezel_art=BezelArt(ROOT/'assets'/'bezels')
        try:
            self.native_canvas=NativeCanvas(self.sdl_window if self.presentation.accelerated else None)
        except pg.error:
            self.native_canvas=NativeCanvas()
        self.canvas=DesignCanvas(self.native_canvas)
        self.native_canvas.bezel_art=self.bezel_art
        self.native_canvas.preload(self.bezel_art.images.values())
        self.sync_bezel()

    def sync_bezel(self):
        self.native_canvas.bezel_theme=theme_for(self.settings.bezel,getattr(self,'level_id',1))

    def set_bezel(self,mode):
        if mode not in BEZEL_MODES:return
        self.settings.bezel=mode
        self.sync_bezel();self.save_settings()

    def preload_textures(self):
        if not hasattr(self,'background_layers'):return
        images=[p.image for p in self.background_layers]+self.tiles
        images += self.desert_art.images
        images += self.temple_art.images
        images += self.tower_art.images
        images += self.greece_art.images
        images += self.vase_sprites.images
        images += [self.desert_sign]
        images += self.temple_exit_sprites.images
        images += self.hero_death_sprites.images
        images += self.beetle_death_sprites.images
        images += self.blade_death_sprites.images
        images += self.sword_death_sprites.images
        images += self.laser_death_sprites.images
        images += [image for pair in self.hero_sprites for image in pair]
        if self.animation_bank:images += self.animation_bank.images
        if self.solar.effect:images += self.solar.effect.images
        if self.crocodile_sprites:images += self.crocodile_sprites.images
        images += self.hoplite_sprites.images
        if self.beetle_sprites:images += self.beetle_sprites.images
        images += self.scorpion_sprites.images
        images += self.gyrosphere_sprites.images
        images += self.fire_death_sprites.images
        images += self.water_death_sprites.images
        images += self.pit_death_sprites.images
        images += self.pit_darkness.images
        images += self.platform_sprites.images
        images += self.spike_sprites.images
        images += self.vulture_sprites.images
        images += self.crystal_sprites.images
        images += self.medallion_sprites.images
        images += [self.life_symbol,self.life_symbol_empty]
        images += self.resurrection_sprites.images
        images += self.solar_gauge.images
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
        music_ready=self.music_ready
        self.music_ready=False
        try:
            for level_id in range(1,9):
                gem_count=len(level(level_id)[1])
                for count in range(gem_count+1):self.cache_text(f'{count:02} / {gem_count}',23,GOLD,outlined=True)
            for label in ('NIVEAU 01  /  LE SEUIL DU DÉSERT','NIVEAU 02  /  LE DÉSERT','NIVEAU 03  /  LE TEMPLE','NIVEAU 04  /  LA TOUR'):
                self.cache_text(label,11,(198,209,199),outlined=True)
            self.cache_text('LES HAUTEURS D’HÉLIOS',18,outlined=True)
            for label in greece_levels.HUD_LABELS.values():
                self.cache_text(label,11,(198,209,199),outlined=True)
            self.cache_text('LE SEUIL EST FRANCHI',44,GOLD,True)
            self.cache_text('NIVEAU 02 · LE DÉSERT',24)
            self.cache_text('Entrée, Start ou A pour continuer',18)
            self.cache_text('LE TEMPLE EST ATTEINT',44,GOLD,True)
            self.cache_text('NIVEAU 03 · LE TEMPLE',24)
            self.cache_text('LE SANCTUAIRE EST ATTEINT',44,GOLD,True)
            self.cache_text('LE SOMMET EST ATTEINT',44,GOLD,True)
            self.cache_text('NIVEAU 04 · LA TOUR',24)
            self.cache_text('L’ASCENSION EST TERMINÉE',24)
            for percent in range(101):self.cache_text(f'ASCENSION : {percent} %',16,GOLD,outlined=True)
            for label,color in (('ÉNERGIE SOLAIRE',GOLD),('ÉNERGIE SOLAIRE',(247,144,65)),
                                ('ÉNERGIE SOLAIRE ÉPUISÉE',(247,144,65)),
                                ('ÉNERGIE INSUFFISANTE',(255,160,91))):
                self.cache_text(label,10,color,outlined=True)
            self.cache_text('POINT DE REPRISE ACTIVÉ',19,GOLD,outlined=True)
            for count in range(4):self.cache_text(f'{count} / 3',20,GOLD,outlined=True)
            self.cache_text('VIE +1 OBTENUE',10,GOLD,outlined=True)
            self.cache_text('ÉPUISÉE',10,(247,144,65),outlined=True)
            self.cache_text('VIES',9,GOLD)
            self.cache_text('GAME OVER',44,GOLD,True)
            for label in ('Capture enregistrée dans captures/.','Échec de la capture d’écran.'):
                self.cache_text(label,14,GOLD,outlined=True)
            self.cache_text('Vous avez perdu toutes vos vies.',24)
            self.cache_text('Entrée, Start ou A pour une nouvelle partie',18)
            self.native_canvas.begin()
            self.menu.prepare(self)
            self.draw_solar_gauge(low=True)
            for digit in '0123456789':self.cache_text(digit,12,outlined=True)
            for digit in '0123456789':self.cache_text(digit,20,GOLD,outlined=True)
            self.cache_text('FPS',10,GOLD,outlined=True)
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
            self.music_ready=music_ready
            # Submit the offscreen work; no screen swap or GPU readback.
            if self.native_canvas.gpu:self.native_canvas.renderer.target=None

    def capture(self):return self.native_canvas.capture()

    def close(self):
        self.screenshots.close()
        if hasattr(self,'menu'):self.menu.end_volume_drag(self)
        if hasattr(self,'menu_music'):self.menu_music.close()
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
        self.score=0
        self.run_totals=dict(shards=0,elapsed=0.,deaths=0)
        self.lives=STARTING_LIVES
        self.medallions=MedallionInventory()
        self.level_id=1
        self.reset()

    def start_level(self,level_id,preserve_energy=False):
        if level_id not in range(1,9):raise ValueError(f'Niveau inconnu : {level_id}')
        self.level_id=level_id
        self.reset(preserve_energy=preserve_energy)

    def continue_or_restart(self):
        if self.state=='win' and self.level_id in range(1,8):
            self.bank_run_stats()
            self.start_level(self.level_id+1,preserve_energy=True)
            self.resume_from_menu()
        else:self.resume_from_menu(new_game=True)

    def bank_run_stats(self):
        self.run_totals['shards']+=len(self.taken)
        self.run_totals['elapsed']+=self.elapsed
        self.run_totals['deaths']+=self.deaths

    def restart_level(self):
        self.bank_run_stats()
        self.reset()

    def reset(self,preserve_energy=False):
        self.victory_started=None
        self.victory_lives=0
        self.level_score=0
        self.level_bonus_awarded=False
        self.gamepads.stop_rumble()
        if not preserve_energy:self.energy.reset()
        self.solar.reset()
        self.rest.reset()
        self.wake_blocked=False
        self.dead_beetles=set()
        config={2:desert_level,3:temple_level,4:tower_level,**greece_levels.LEVELS}.get(self.level_id)
        self.world_length=config.LENGTH if config else WORLD
        self.world_height=tower_level.HEIGHT if self.level_id==4 else VIEW_H
        self.beetle_spawns=config.BEETLES if config else SPAWNS
        self.vulture_spawns=config.VULTURES if config else VULTURE_SPAWNS
        self.medallion_anchor=config.MEDALLION if config else FIRST_MEDALLION
        self.beetle_motions=[BeetleMotion(i,spawns=self.beetle_spawns) for i in range(len(self.beetle_spawns))]
        self.vultures=[Vulture(i,self.vulture_spawns) for i in range(len(self.vulture_spawns))]
        self.scorpions=([Scorpion(i,tower_level.SCORPIONS) for i in range(3)] if self.level_id==4 else
                        [Scorpion(i) for i in range(len(temple_level.SCORPIONS))] if self.level_id==3 else
                        [Scorpion(i,config.SCORPIONS) for i in range(len(config.SCORPIONS))] if self.level_id>=5 else [])
        self.laser_bolts=[]
        gyro_spawns=getattr(config,'GYROSPHERES',())
        self.gyrospheres=[Gyrosphere(i,gyro_spawns) for i in range(len(gyro_spawns))]
        self.beetle_deaths=[]
        self.temple_exit=TempleExit()
        self.hero_death=HeroDeath()
        self.resurrection=Resurrection()
        self.vases=([Vase(i,tower_level.VASES) for i in range(len(tower_level.VASES))] if self.level_id==4 else
                    [Vase(i) for i in range(len(VASE_SPAWNS))] if self.level_id==3 else [])
        self.platforms,self.gems=level(self.level_id)
        self.pit_regions=pit_regions(self.platforms,self.level_id)
        self.taken=set()
        self.hero=(Hero(*tower_level.START) if self.level_id==4 else
                   Hero(*config.START) if self.level_id>=5 else
                   Hero(160,sand_height(160)) if self.level_id==2 else Hero())
        self.hero.grounded=True
        self.hero_animation.reset()
        self.crocodiles=[Crocodile(*spawn) for spawn in config.CROCODILES] if config else create_crocodiles()
        self.hoplites=[Hoplite(*spawn) for spawn in getattr(config,'HOPLITES',())]
        self.cam=self.prev_cam=0.
        self.cam_y=self.prev_cam_y=tower_level.HEIGHT-VIEW_H if self.level_id==4 else 0.
        # Every level entrance is the initial checkpoint, before any obelisk.
        self.checkpoint=(self.hero.x,self.hero.y)
        self.check_index=0
        points=config.CHECKPOINTS if config else (CHECKPOINT_X,)
        self.obelisks=([Obelisk(x,y) for x,y in points] if self.level_id>=4 else
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

    def cache_text(self,txt,size=20,color=(246,236,210),serif=False,outlined=False):
        txt=translate(txt,self.settings.language)
        key=(txt,size,color,serif)+(('outlined',) if outlined else ())
        if key not in self.text_cache:
            if len(self.text_cache)>=2048:self.text_cache.pop(next(iter(self.text_cache)))
            if outlined:
                base=self.cache_text(txt,size,color,serif)
                image=pg.Surface((base.get_width()+6,base.get_height()+6),pg.SRCALPHA).convert_alpha()
                shade=base.copy();shade.fill((6,12,18,200),special_flags=pg.BLEND_RGBA_MULT)
                image.blit(shade,(5,6))
                for dx,dy in ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1)):
                    image.blit(shade,(3+dx,3+dy))
                image.blit(base,(3,3));self.text_cache[key]=image
            else:self.text_cache[key]=self.font(size,serif).render(txt,True,color).convert_alpha()
        return self.text_cache[key]

    def text(self,txt,pos,size=20,color=(246,236,210),serif=False,center=False,max_width=None,outlined=False):
        s=self.cache_text(txt,size,color,serif,outlined=outlined)
        if outlined:
            w,h=s.get_width()-6,s.get_height()-6
            factor=min(1.,max_width*SCALE/w) if max_width is not None and w else 1.
            width,height=max(1,pixel(w*factor)),max(1,pixel(h*factor));pad=pixel(3*factor)
            x,y=self.canvas.point(pos)
            if center:x-=width//2;y-=height//2
            self.native_canvas.blit(s,(x-pad,y-pad,width+pad*2,height+pad*2))
            return
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
            self.sounds['game_over']=pg.mixer.Sound(buffer=game_over_tune(rate,channels))
        except (pg.error,ImportError): pass

    def sound(self,name):
        if self.sound_on and name in self.sounds: self.sounds[name].play()

    def apply_sound_volume(self):
        for sound in self.sounds.values():sound.set_volume(self.settings.sound_volume/100)

    def burst(self,x,y,color,n=16):
        for _ in range(n):
            a=self.rng.random()*math.tau; v=self.rng.uniform(35,170)
            self.particles.append([x,y,math.cos(a)*v,math.sin(a)*v,self.rng.uniform(.3,.7),color])

    def update(self,dt,axis,held,pressed,drop=False,fire=False,activity=False,down=False):
        if self.state in ('game_over','win'):return
        if self.resurrection.active:
            if self.state!='play':return
            self.prev_cam=self.cam;self.prev_cam_y=self.cam_y
            self.previous_elapsed=self.elapsed;self.elapsed+=dt
            spawn,finished=self.resurrection.update(dt)
            if spawn:self.respawn_hero()
            if self.resurrection.spawned:self.update_particles(dt)
            self.energy.update_display(dt)
            if finished:
                self.resurrection.active=False;self.menu_gameplay_blocked=True
            return
        if self.hero_death.active:
            if self.state!='play':return
            self.previous_elapsed=self.elapsed;self.elapsed+=dt
            finished=self.hero_death.update(dt)
            if self.hero_death.kind=='pit':
                self.hero.px,self.hero.py=self.hero.x,self.hero.y
                self.hero.x,self.hero.y=pit_position(self.hero_death,self.hero,self.hero_death.elapsed)
                self.prev_cam_y=self.cam_y
            if self.hero_death.kind=='water':
                self.hero.px,self.hero.py=self.hero.x,self.hero.y
                self.hero.x,self.hero.y=water_position(self.hero_death,self.hero,self.hero_death.elapsed)
                for boundary in (.55,1.35):
                    if self.hero_death.previous_elapsed<boundary<=self.hero_death.elapsed:self.rumble_death_animation()
            if self.hero_death.electrical or self.hero_death.kind in ('blade','laser','fire','sword'):
                if self.hero_death.electrical:
                    enemy={'beetle':self.beetle_motions,'vulture':self.vultures,
                           'scorpion':self.scorpions,'gyrosphere':self.gyrospheres}[self.hero_death.kind][self.hero_death.index]
                    enemy.previous_clock=enemy.clock;enemy.clock+=dt
                    if self.hero_death.kind=='vulture':enemy.previous_timer=enemy.timer;enemy.timer+=dt
                sword=self.hero_death.kind=='sword'
                if sword:
                    attacker=self.hoplites[self.hero_death.index]
                    attacker.previous_state=attacker.state;attacker.previous_timer=attacker.timer
                    if attacker.state=='attack':
                        attacker.timer=min(HOPLITE_ATTACK_TIME,attacker.timer+dt)
                        if attacker.timer>=HOPLITE_ATTACK_TIME:attacker.change('alert')
                fall_dt=dt if self.hero_death.kind in ('laser','fire') else max(0.,min(dt,self.hero_death.elapsed-(SWORD_IMPACT if sword else BEETLE_STUN)))
                if fall_dt:
                    if sword and self.hero_death.elapsed<.38:
                        self.hero.vx=self.hero_death.facing*160*max(0.,1-(self.hero_death.elapsed-SWORD_IMPACT)/.28)
                    self.hero.update(fall_dt,0,False,False,self.collision_platforms(),allow_glide=False)
                else:self.hero.px,self.hero.py=self.hero.x,self.hero.y
                if self.hero_death.kind in ('laser','fire','sword'):
                    death=self.hero_death
                    fire=death.kind=='fire';reaction=FIRE_REACTION if fire else SWORD_LAND if sword else .28
                    if self.hero.grounded and death.elapsed>=reaction and death.landed_at is None:death.landed_at=death.elapsed
                    lost=self.hero.y>(tower_level.HEIGHT+160 if self.level_id==4 else 850)
                    finished=(death.elapsed>=LASER_LIMIT or
                              death.elapsed>=(FIRE_DURATION if fire else SWORD_DURATION if sword else LASER_DURATION)-1e-9 and
                              (lost or death.landed_at is not None and death.elapsed>=death.duration-1e-9))
                    if fire and finished and death.landed_at is None:
                        death.landed_at=max(FIRE_REACTION,death.elapsed-1.)
                    refresh=(int(death.elapsed/.12+1e-9)!=int(death.previous_elapsed/.12+1e-9) if fire else
                             death.previous_elapsed<LASER_IMPACT<=death.elapsed or
                             death.elapsed>=1.2 and int(death.elapsed*5+1e-9)!=int(death.previous_elapsed*5+1e-9))
                    if not finished and refresh:
                        self.rumble_death_animation()
                self.prev_cam=self.cam
                if self.level_id==4:
                    self.cam=self.prev_cam=0.;self.prev_cam_y=self.cam_y
                    self.cam_y+=(tower_level.camera_target(self.hero.y)-self.cam_y)*(1-math.exp(-5.8*dt))
                else:
                    target=max(0,min(self.world_length-VIEW_W,self.hero.x-VIEW_W*.4))
                    self.cam+=(target-self.cam)*(1-math.exp(-5.8*dt))
            else:
                self.prev_cam=self.cam
                if self.hero_death.kind!='pit':
                    target=max(0,min(self.world_length-VIEW_W,self.hero_death.x-VIEW_W*.5))
                    self.cam+=(target-self.cam)*(1-math.exp(-5.8*dt))
            if finished:
                final=self.lives==0
                self.hero_death.active=False
                self.gamepads.stop_rumble()
                if final:self.gamepads.rumble('game_over')
                self.finish_death()
                self.menu_gameplay_blocked=True
            return
        if self.temple_exit.active:
            if self.state!='play':return
            self.previous_elapsed=self.elapsed;self.elapsed+=dt
            finished=self.temple_exit.update(dt,self.hero)
            self.hero_animation.update(dt,self.hero,True,self.solar,self.rest)
            self.prev_cam=self.cam
            self.cam+=(self.world_length-VIEW_W-self.cam)*(1-math.exp(-5.8*dt))
            if finished:self.complete_level()
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
                self.taken.add(i);self.award_points(10);self.energy.collect();self.burst(x,y,GOLD,12);self.sound('gem')
        if self.medallions.available(self.level_id) and touches_medallion(self.hero,self.elapsed,self.medallion_anchor):
            if self.medallions.collect(self.level_id):
                self.award_points(500)
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
            if self.level_id==8:
                self.prev_cam_y=self.cam_y
                target_y=greece_levels.LEVELS[8].floor_height(self.hero.x)-GROUND_Y
                self.cam_y+=(target_y-self.cam_y)*(1-math.exp(-5.8*dt))
        self.invuln=max(0,self.invuln-dt)
        for enemy in self.gyrospheres:enemy.update(dt,self.hero,solids,self.cam_y,self.cam)
        self.notice=max(0,self.notice-dt)
        for enemy in self.crocodiles:
            event=enemy.update(dt,self.hero,can_attack=self.invuln<=0)
            if event=='warning':self.sound('crocodile')
            elif event=='lunge':self.burst(enemy.x+enemy.facing*35,enemy.y-4,(199,165,108),10)
        for enemy in self.hoplites:enemy.update(dt,self.hero,solids,can_attack=self.invuln<=0)
        self.solar_hits()
        for index,obelisk in enumerate(self.obelisks,1):
            if obelisk.update(dt,self.hero) and index>self.check_index:
                self.checkpoint=(obelisk.x-60,obelisk.y);self.check_index=index;self.notice=3
                self.sound('checkpoint')
        water_hit=self.level_id==2 and desert_level.water_hits(self.hero)
        pit_limit=tower_level.BASE_Y+2 if self.level_id==4 else desert_level.WATER_Y+2 if self.level_id==2 else GROUND_Y+2
        pit_hit=self.hero.y>pit_limit and not self.hero.grounded and not water_hit
        hit=pit_hit or self.hero.spike_hit or water_hit
        fire_killer=None
        if self.level_id in (3,4):
            fire_source=self.temple_art.flame_source(self.hero,self.elapsed,
                tower_level.TORCHES if self.level_id==4 else None)
            if fire_source is not None:
                if not hit:fire_killer=fire_source
                hit=True
        laser_killer=None
        for bolt in self.laser_bolts:
            if bolt.update(dt,self.hero,solids,can_hit=self.invuln<=0):
                if not hit:laser_killer=bolt
                hit=True
        self.laser_bolts=[bolt for bolt in self.laser_bolts if bolt.alive]
        environmental_hit=hit;beetle_hit=None
        for x,y in self.enemy_positions():
            if self.invuln<=0 and abs(self.hero.x-x)<32 and abs(self.hero.y-self.hero.body_height/2-y)<self.hero.body_height/2+6:
                hit=True
                if not environmental_hit:
                    beetle_hit=next((m for m in self.beetle_motions if m.index not in self.dead_beetles
                                     and abs(m.x-x)<.01 and abs(m.y-y)<.01),None)
                break
        crocodile_hit=next((enemy for enemy in self.crocodiles if enemy.hits(self.hero)),None) if self.invuln<=0 else None
        killer=crocodile_hit if not hit else None
        if crocodile_hit is not None:hit=True
        vulture_hit=next((enemy for enemy in self.vultures if enemy.hits(self.hero)),None) if self.invuln<=0 else None
        vulture_killer=vulture_hit if not hit else None
        if vulture_hit is not None:hit=True
        scorpion_hit=next((enemy for enemy in self.scorpions if enemy.hits(self.hero)),None) if self.invuln<=0 else None
        scorpion_killer=scorpion_hit if not hit else None
        if scorpion_hit is not None:hit=True
        gyro_hit=next((enemy for enemy in self.gyrospheres if enemy.hits(self.hero)),None) if self.invuln<=0 else None
        gyro_killer=gyro_hit if not hit else None
        if gyro_hit is not None:hit=True
        hoplite_hit=next((enemy for enemy in self.hoplites if enemy.hits(self.hero)),None) if self.invuln<=0 else None
        hoplite_killer=hoplite_hit if not hit else None
        if hoplite_hit is not None:hit=True
        if hit:
            self.kill_hero(killer,beetle_hit,vulture_killer,laser_killer,scorpion_killer,fire_killer,water_hit,pit_hit,gyro_killer,hoplite_killer)
            if self.hero_death.active or self.resurrection.active or self.state=='game_over':return
        elif self.hero.head_bump:
            self.gamepads.rumble('head_bump')
        elif not was_grounded and self.hero.grounded and not self.hero.landed_gliding and self.hero.impact_vy>100 and self.hero.landing_kind=='land_heavy':
            self.gamepads.rumble('land_heavy')
        if self.level_id==3 and not hit and self.temple_exit.can_start(self.hero):
            self.temple_exit.begin(self.hero);self.solar.reset();self.rest.reset();self.crouch_fire=False
            self.laser_bolts.clear()
        finished=(desert_level.temple_entered(self.hero) if self.level_id==2 else
                  tower_level.completed(self.hero) if self.level_id==4 else
                  self.level_id in (1,5,6,7,8) and self.hero.x>=self.world_length+EXIT_MARGIN)
        if self.state=='play' and finished:
            self.complete_level()
        self.update_particles(dt)
        self.energy.update_display(dt)

    def award_points(self,points):
        self.score+=points
        self.level_score+=points

    def complete_level(self):
        if not self.level_bonus_awarded:
            self.victory_started=self.time
            self.victory_lives=self.lives
            self.award_points(self.level_id*1000+self.lives*100)
            self.level_bonus_awarded=True
        self.state='win';self.sound('win')

    def update_particles(self,dt):
        for p in self.particles:
            p[0]+=p[2]*dt;p[1]+=p[3]*dt;p[3]+=100*dt;p[4]-=dt
        self.particles=[p for p in self.particles if p[4]>0]

    def kill_hero(self,crocodile=None,beetle=None,vulture=None,laser=None,scorpion=None,fire=None,water=False,pit=False,gyrosphere=None,hoplite=None):
        self.laser_bolts.clear();self.beetle_deaths.clear();self.particles.clear()
        self.hero_death=HeroDeath()
        self.deaths+=1;self.lives=max(0,self.lives-1)
        if self.hero.spike_hit or hoplite is not None or pit or water or fire is not None or laser is not None or (crocodile is not None and self.crocodile_sprites) or beetle is not None or vulture is not None or scorpion is not None or gyrosphere is not None:
            if self.hero.spike_hit:
                self.hero_death.begin_blade(self.hero)
                self.hero.coyote=self.hero.buffer=0.;self.hero.floating=False
                self.hero.drop_elapsed=None;self.hero.drop_support=self.hero.ignored_platform=None
            elif hoplite is not None:
                self.hero_death.begin_sword(self.hoplites.index(hoplite),hoplite,self.hero)
                hoplite.state=hoplite.previous_state='attack'
                hoplite.timer=hoplite.previous_timer=.24;hoplite.px=hoplite.x
                self.hero.coyote=self.hero.buffer=0.;self.hero.floating=False
                self.hero.drop_elapsed=None;self.hero.drop_support=self.hero.ignored_platform=None
            elif pit:
                self.hero_death.begin_pit(self.hero)
                self.hero.coyote=self.hero.buffer=0.;self.hero.floating=False
                self.hero.drop_elapsed=None;self.hero.drop_support=self.hero.ignored_platform=None
            elif water:
                self.hero_death.begin_water(self.hero)
                self.hero.x,self.hero.y=self.hero_death.hero_x,self.hero_death.hero_y
                self.hero.coyote=self.hero.buffer=0.;self.hero.floating=False
                self.hero.drop_elapsed=None;self.hero.drop_support=self.hero.ignored_platform=None
            elif fire is not None:
                self.hero_death.begin_fire(fire,self.hero)
                self.hero.coyote=self.hero.buffer=0.;self.hero.floating=False
                self.hero.drop_elapsed=None;self.hero.drop_support=self.hero.ignored_platform=None
            elif laser is not None:
                self.hero_death.begin_laser(laser,self.hero)
                self.hero.coyote=self.hero.buffer=0.;self.hero.floating=False
                self.hero.drop_elapsed=None;self.hero.drop_support=self.hero.ignored_platform=None
            elif beetle is not None or vulture is not None or scorpion is not None or gyrosphere is not None:
                if beetle is not None:self.hero_death.begin_beetle(beetle,self.hero)
                elif vulture is not None:self.hero_death.begin_vulture(vulture,self.hero)
                elif scorpion is not None:self.hero_death.begin_scorpion(scorpion,self.hero)
                else:self.hero_death.begin_gyrosphere(gyrosphere,self.hero)
                attacker=beetle if beetle is not None else vulture if vulture is not None else scorpion if scorpion is not None else gyrosphere
                attacker.px=attacker.x
                if self.hero_death.kind!='scorpion':attacker.py=attacker.y
                self.hero.coyote=self.hero.buffer=0.;self.hero.floating=False
                self.hero.drop_elapsed=None;self.hero.drop_support=self.hero.ignored_platform=None
            else:self.hero_death.begin(self.crocodiles.index(crocodile),crocodile,self.hero)
            self.rumble_death_animation()
            if laser is None and fire is None and not water and not pit and hoplite is None:self.hero.vx=self.hero.vy=0.
            self.hero.px=self.hero.x;self.hero.py=self.hero.y
            self.solar.reset();self.rest.reset();self.crouch_fire=False
            self.pending_jump=self.pending_drop=self.pending_fire=self.pending_activity=False
            return
        self.gamepads.rumble('death' if self.lives else 'game_over')
        self.finish_death()

    def rumble_death_animation(self):
        if self.hero_death.active and self.hero_death.elapsed<self.hero_death.duration:
            if self.hero_death.kind=='water':
                elapsed=self.hero_death.elapsed
                event,end=('water_entry',.55) if elapsed<.55 else ('death',1.35) if elapsed<1.35 else ('laser_fall',self.hero_death.duration)
                self.gamepads.rumble(event,duration=max(1,math.ceil((end-elapsed)*1000-1e-7)))
                return
            if self.hero_death.kind=='fire':
                from fire_death import extinction
                death=self.hero_death
                event=('death' if death.elapsed<.12 else 'fire_embers' if extinction(death,death.elapsed)>0 else
                       'fire_burn' if int(death.elapsed/.12)%3 else 'fire_flicker')
                self.gamepads.rumble(event,duration=max(1,min(120,math.ceil((death.duration-death.elapsed)*1000-1e-7))))
                return
            if self.hero_death.kind=='laser':
                elapsed=self.hero_death.elapsed
                remaining=(LASER_IMPACT-elapsed if elapsed<LASER_IMPACT else self.hero_death.duration-elapsed)
                event='death' if elapsed<LASER_IMPACT else 'laser_fall'
                self.gamepads.rumble(event,duration=max(1,math.ceil(remaining*1000-1e-7)))
                return
            remaining=math.ceil((self.hero_death.duration-self.hero_death.elapsed)*1000-1e-7)
            self.gamepads.rumble('death',duration=max(1,remaining))

    def finish_death(self):
        if self.lives==0:
            self.state='game_over'
            self.cache_text(self.game_over_results(),22)
            self.cache_text(f'{translate("Niveau",self.settings.language)} {self.level_id:02}',18,GOLD)
            self.sound('game_over')
            self.hero_animation.reset()
            self.solar.reset();self.rest.reset();self.crouch_fire=False
            self.pending_jump=self.pending_drop=self.pending_fire=self.pending_activity=False
            return
        self.solar.reset();self.rest.reset();self.hero_animation.reset();self.crouch_fire=False
        self.pending_jump=self.pending_drop=self.pending_fire=self.pending_activity=False
        self.resurrection.begin(self.lives)
        self.prev_cam=self.cam;self.prev_cam_y=self.cam_y

    def respawn_hero(self):
        self.hero=Hero(*self.checkpoint)
        self.hero_animation.reset();self.solar.reset();self.energy.refill()
        self.beetle_motions=[BeetleMotion(i,self.elapsed,self.beetle_spawns) for i in range(len(self.beetle_spawns))]
        for enemy in self.scorpions:
            if enemy.alive:enemy.reset()
        for enemy in self.gyrospheres:
            if enemy.alive:enemy.reset()
            else:enemy.previous_death_timer=enemy.death_timer=GYRO_DEATH_TIME
        self.vultures=[Vulture(enemy.index,self.vulture_spawns) if enemy.alive else enemy for enemy in self.vultures]
        self.rest.reset();self.wake_blocked=False;self.crouch_fire=False
        for enemy in self.crocodiles:
            if enemy.alive:enemy.reset()
        for enemy in self.hoplites:
            if enemy.alive:enemy.reset()
            else:enemy.previous_death_timer=enemy.death_timer=HOPLITE_DEATH_TIME
        self.cam=self.prev_cam=max(0,min(self.world_length-VIEW_W,self.hero.x-VIEW_W*.4))
        if self.level_id==4:self.cam_y=self.prev_cam_y=tower_level.camera_target(self.hero.y)
        if self.level_id==8:self.cam_y=self.prev_cam_y=greece_levels.LEVELS[8].floor_height(self.hero.x)-GROUND_Y
        self.invuln=2.;self.sound('fall');self.burst(self.hero.x,self.hero.y-25,(130,224,227),24)

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
            if not vase.broken and contact.colliderect(vase.rect):
                vase.shatter();self.award_points(10)
        for guardian in self.vultures:
            if guardian.alive and beam.colliderect(guardian.hurtbox):
                guardian.ignite();self.award_points(200)
        for enemy in self.crocodiles:
            if enemy.alive and beam.colliderect(enemy.hurtbox):
                enemy.ignite()
                self.award_points(100)
        for enemy in self.hoplites:
            if enemy.alive and beam.colliderect(enemy.hurtbox):
                enemy.ignite();self.award_points(100)
        for enemy in self.scorpions:
            if enemy.alive and beam.colliderect(enemy.hurtbox):
                enemy.ignite();self.award_points(300)
        for enemy in self.gyrospheres:
            if enemy.alive and beam.colliderect(enemy.rect):
                enemy.destroy();self.award_points(GYRO_POINTS)
                self.burst(enemy.x,enemy.y,(130,224,227),14)
        for i,x,y in self.beetles():
            if beam.colliderect(pg.Rect(round(x-30),round(y-20),60,40)):
                self.dead_beetles.add(i);self.burst(x,y,GOLD,20)
                self.award_points(100)
                motion=self.beetle_motions[i]
                self.beetle_deaths.append(BeetleDeath(x,y,motion.facing,motion.vx,motion.vy))

    def background(self,cam):
        if self.level_id>=5 and (self.state not in MENU_PAGES or self.state=='pause'):
            self.greece_art.background(self.canvas,cam,self.level_id,self.prev_cam_y+(self.cam_y-self.prev_cam_y)*getattr(self,'render_alpha',1.))
            return
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
        if self.level_id>=5:
            self.greece_art.platform(self.canvas,p,cam)
            if p.spiked:self.spike_sprites.draw(self.canvas,p,cam)
            return
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
        if self.resurrection.active and (not self.resurrection.spawned or self.resurrection.time(alpha)<REAPPEAR):return
        if self.hero_death.active or (self.state=='game_over' and self.hero_death.elapsed>0):
            if self.hero_death.kind=='pit':
                clip='float' if self.hero_animation.state=='float' else 'fall'
                self.pit_death_sprites.draw(self.canvas,self.hero_death,h,x,y,alpha,self.animation_bank.clips[clip][0])
                return
            if self.hero_death.kind=='water':
                self.water_death_sprites.draw(self.canvas,self.hero_death,h,x,y,alpha,self.animation_bank)
                return
            if self.hero_death.kind in ('laser','fire'):
                sprites=self.fire_death_sprites if self.hero_death.kind=='fire' else self.laser_death_sprites
                sprites.draw(self.canvas,self.hero_death,h,x,y,alpha)
                return
            if self.hero_death.kind=='blade':
                self.blade_death_sprites.draw(self.canvas,self.hero_death,h,x,y,alpha)
                return
            if self.hero_death.kind=='sword':
                self.sword_death_sprites.draw(self.canvas,self.hero_death,h,x,y,alpha)
                return
            if self.hero_death.electrical:
                self.beetle_death_sprites.draw(self.canvas,self.hero_death,h,x,y,alpha)
                return
            elapsed=self.hero_death.time(alpha)
            if elapsed>=DEATH_CAPTURE:return
            p=death_smooth(elapsed/DEATH_CAPTURE)
            x+=(self.hero_death.x+self.hero_death.facing*85-self.hero_death.hero_x)*p
            y+=(self.hero_death.y-self.hero_death.hero_y)*p-math.sin(p*math.pi)*10
            self.animation_bank.clips['fall'][0].draw(self.canvas,x,y,self.hero_death.hero_face)
            return
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
        holding_death=(self.resurrection.active and not self.resurrection.spawned
                       and self.hero_death.elapsed>0)
        # The world is frozen during resurrection; don't replay the last lunge
        # interval as the renderer's interpolation fraction cycles each frame.
        crocodile_alpha=1. if self.resurrection.active else alpha
        for index,enemy in enumerate(self.crocodiles):
            if (self.hero_death.active or holding_death or (self.state=='game_over' and self.hero_death.elapsed>0)) and self.hero_death.kind=='crocodile' and index==self.hero_death.index:
                self.hero_death_sprites.draw(self.canvas,self.hero_death,cam,crocodile_alpha,self.crocodile_sprites)
                continue
            if not enemy.alive and not (self.crocodile_sprites and self.crocodile_sprites.burn):continue
            x=enemy.px+(enemy.x-enemy.px)*crocodile_alpha-cam
            if not -180<x<VIEW_W+180:continue
            if enemy.alive:draw.ellipse(self.canvas,(81,69,44),(x-77,enemy.y-5,154,8))
            if self.crocodile_sprites:
                self.crocodile_sprites.sample(enemy,crocodile_alpha).draw(self.canvas,x,enemy.y,enemy.facing)
            else:
                # Visible fallback for development checkouts without the atlas.
                f=enemy.facing;y=enemy.y
                draw.polygon(self.canvas,(63,79,55),[(x-f*45,y-22),(x-f*145,y-44),(x-f*85,y-8),(x,y-5)])
                draw.ellipse(self.canvas,(68,85,58),(x-55,y-33,117,30))
                draw.rect(self.canvas,(83,99,65),(x+f*72-31,y-25,62,18),border_radius=5)
                draw.circle(self.canvas,(219,177,71),(x+f*64,y-28),3)

    def draw_desert_sign(self,cam):
        if self.level_id!=1:return
        x=WORLD-300-cam
        if -55.5<x<VIEW_W+55.5:
            # Bury the sandy foot slightly in the ground; this is scenery only.
            self.canvas.blit_native(self.desert_sign,(x-55.5,GROUND_Y-72))

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
            for enemy in self.gyrospheres:
                if camera-100<enemy.y<camera+VIEW_H+100:self.gyrosphere_sprites.draw(self.canvas,enemy,alpha,self.beetle_sprites)
            for bolt in self.laser_bolts:
                if camera-100<bolt.y<camera+VIEW_H+100:self.scorpion_sprites.draw_bolt(self.canvas,bolt,0,alpha)
            hx=self.hero.px+(self.hero.x-self.hero.px)*alpha
            hy=self.hero.py+(self.hero.y-self.hero.py)*alpha
            if self.state=='game_over' or self.hero_death.active or self.resurrection.active or self.solar.active or self.invuln<=0 or int(self.time*12)%2==0:self.draw_hero(hx,hy,alpha)
            self.solar.draw(self.canvas,self.hero,self.collision_platforms(),0,alpha)
            for x,y,vx,vy,life,color in self.particles:
                if camera-30<y<camera+VIEW_H+30:draw.circle(self.canvas,color,(x,y),max(1,int(life*5)))
        finally:self.canvas=original
        self.hud(alpha)
        self.resurrection_sprites.draw(self.canvas,self.resurrection,alpha)
        if self.state=='play':
            self.hud_notice(f'ASCENSION : {tower_level.progress(self.hero.y)} %',152,16)
            if self.notice>0:self.hud_notice('POINT DE REPRISE ACTIVÉ',198,19)
        elif self.state=='pause':self.menu.draw(self)
        elif self.state=='win':
            self.draw_victory()
        elif self.state=='game_over':
            self.draw_game_over()
        if self.show_fps:self.draw_fps()
        if self.show_stats:self.draw_diagnostics()
        if present:self.present_frame(started)

    def draw(self,alpha=1,present=True):
        started=time.perf_counter()
        self.sync_bezel()
        self.sync_menu_music()
        self.native_canvas.begin()
        alpha=max(0.,min(1.,alpha))
        if self.state in MENU_PAGES and self.state!='pause':
            self.background(0.)
            self.menu.draw(self)
            if present:self.present_frame(started)
            return
        if self.level_id==4:
            self.draw_tower(alpha,started,present);return
        original=self.canvas
        try:self.draw_horizontal(alpha,started,present)
        finally:self.canvas=original

    def draw_horizontal(self,alpha,started,present):
        render_cam=self.prev_cam+(self.cam-self.prev_cam)*alpha
        self.render_alpha=alpha
        self.background(render_cam)
        original=self.canvas
        if self.level_id==8:
            render_y=self.prev_cam_y+(self.cam_y-self.prev_cam_y)*alpha
            self.canvas=VerticalCanvas(self.native_canvas,render_y)
        # Snap once for the entire gameplay plane, independently of the layers.
        cam=pixel(render_cam*SCALE)/SCALE
        animation_time=self.previous_elapsed+(self.elapsed-self.previous_elapsed)*alpha
        if self.level_id==2:
            self.desert_art.river(self.canvas,cam,animation_time)
            self.desert_art.temple_background(self.canvas,cam)
        for p in self.platforms:self.platform(p,cam)
        self.draw_desert_sign(cam)
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
        hoplite_alpha=1. if self.hero_death.active or self.resurrection.active else alpha
        for enemy in self.hoplites:self.hoplite_sprites.draw(self.canvas,enemy,cam,hoplite_alpha)
        for enemy in self.scorpions:
            if -200<enemy.x-cam<VIEW_W+200:self.scorpion_sprites.draw(self.canvas,enemy,cam,alpha)
        for enemy in self.gyrospheres:
            if -100<enemy.x-cam<VIEW_W+100:self.gyrosphere_sprites.draw(self.canvas,enemy,alpha,self.beetle_sprites,cam)
        for bolt in self.laser_bolts:self.scorpion_sprites.draw_bolt(self.canvas,bolt,cam,alpha)
        for guardian in self.vultures:
            gx,gy=guardian.position(alpha)
            if -180<gx-cam<VIEW_W+180:self.vulture_sprites.draw(self.canvas,guardian,cam,alpha)
        hx=(self.hero.px+(self.hero.x-self.hero.px)*alpha)-cam
        hy=self.hero.py+(self.hero.y-self.hero.py)*alpha
        if self.state=='game_over' or self.hero_death.active or self.resurrection.active or self.temple_exit.active or self.solar.active or self.invuln<=0 or int(self.time*12)%2==0:self.draw_hero(hx,hy,alpha)
        self.solar.draw(self.canvas,self.hero,self.collision_platforms(),cam,alpha)
        if self.level_id==2:
            self.desert_art.bridge_foreground(self.canvas,self.platforms,cam)
            self.desert_art.temple_foreground(self.canvas,cam)
        elif self.level_id==3:self.temple_art.foreground(self.canvas,cam)
        for px,py,vx,vy,life,col in self.particles:
            draw.circle(self.canvas,col,(px-cam,py),max(1,int(life*5)))
        # Foreground sand follows the interpolated simulation clock, including pause.
        for i in range(0 if self.level_id>=5 else 35):
            x=(i*173+animation_time*(17+i%7)-cam*.65)%(VIEW_W+40)-20
            y=160+(i*97)%520+math.sin(animation_time+i)*9
            draw.line(self.canvas,(231,202,146),(x,y),(x+3,y))
        self.pit_darkness.draw(self.canvas,self.pit_regions,self.level_id,cam)
        self.canvas=original
        self.hud(alpha)
        self.resurrection_sprites.draw(self.canvas,self.resurrection,alpha)
        if self.state=='pause':self.menu.draw(self)
        elif self.state=='win':
            self.draw_victory()
        elif self.state=='game_over':
            self.draw_game_over()
        if self.notice>0 and self.state=='play':self.hud_notice('POINT DE REPRISE ACTIVÉ',152,19)
        if self.show_fps:self.draw_fps()
        if self.show_stats:
            self.draw_diagnostics()
        if not present:return
        self.present_frame(started)

    def present_frame(self,started):
        self.screenshots.poll()
        capture=self.screenshots.requested
        if self.screenshots.notice and not capture:
            self.text(self.screenshots.notice,(VIEW_W/2,82),14,GOLD,center=True,outlined=True)
        self.submission_times.append(time.perf_counter()-started)
        if capture:
            try:
                image=self.native_canvas.present(self.screen,capture=True)
                self.screenshots.submit(image)
            except (pg.error,OSError) as error:
                self.screenshots.fail(error)
                self.native_canvas.present(self.screen)
        else:self.native_canvas.present(self.screen)
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
        self.canvas.blit(self.diagnostic_panel,(20,140))
        for i,line in enumerate(self.diagnostic_lines):self.text(line,(30,146+i*25),16)

    def draw_fps(self):
        now=time.perf_counter()
        if now-self.fps_updated>=.25:
            total=sum(self.frame_intervals)
            self.fps_count=min(999,round(len(self.frame_intervals)/total)) if total>0 else 0
            self.fps_updated=now
        digits=str(self.fps_count)
        for index,digit in enumerate(digits):self.text(digit,(1200-9*(len(digits)-index),141),12,outlined=True)
        self.text('FPS',(1213,143),10,GOLD,outlined=True)

    def hud_notice(self,message,y,size):
        self.text(message,(VIEW_W/2,y),size,GOLD,center=True,max_width=1000,outlined=True)

    def hud(self,alpha=1.):
        self.canvas.blit_native(self.hud_panel,(0,0))
        self.text('VIES',hud_layout.LIVES_LABEL,11,GOLD,max_width=45,outlined=True)
        visible=self.lives+(1 if self.hero_death.active and self.lives else 0)
        for index in range(6):
            self.canvas.blit_native(self.life_symbol if index<visible else self.life_symbol_empty,life_position(index))
        if self.lives>6:self.text(f'× {self.lives}',(302,20),10,GOLD,max_width=36,outlined=True)
        self.text('LES HAUTEURS D’HÉLIOS' if self.level_id>=5 else 'LES SABLES D’HORUS',hud_layout.TITLE,18,center=True,max_width=432,outlined=True)
        label={1:'NIVEAU 01  /  LE SEUIL DU DÉSERT',2:'NIVEAU 02  /  LE DÉSERT',3:'NIVEAU 03  /  LE TEMPLE',4:'NIVEAU 04  /  LA TOUR',**greece_levels.HUD_LABELS}[self.level_id]
        self.text(label,hud_layout.LEVEL,11,(198,209,199),center=True,max_width=432,outlined=True)
        shown_score=self.score
        if self.state=='win' and self.victory_started is not None:
            shown_score-=self.victory_lives*100-sample_life_bonus(self.time-self.victory_started,self.victory_lives).points
        digits=f'{shown_score:,}'.replace(',',' ')
        label_width=min(100,self.cache_text('SCORE  ',20,GOLD).get_width()/SCALE)
        score_x=hud_layout.SCORE[0]-(label_width+sum(6 if digit==' ' else 12 for digit in digits))/2
        self.text('SCORE  ',(score_x,hud_layout.SCORE[1]),20,GOLD,max_width=100,outlined=True)
        score_x+=label_width
        for digit in digits:
            if digit==' ':score_x+=6;continue
            self.text(digit,(score_x,hud_layout.SCORE[1]),20,GOLD,outlined=True)
            score_x+=12
        animation_time=self.previous_elapsed+(self.elapsed-self.previous_elapsed)*max(0.,min(1.,alpha))
        self.crystal_sprites.draw(self.canvas,*hud_layout.CRYSTAL,animation_time,bob=False)
        self.text(f'{len(self.taken):02} / {len(self.gems)}',hud_layout.CRYSTAL_COUNT,23,GOLD,max_width=76,outlined=True)
        self.medallion_sprites.draw(self.canvas,*hud_layout.MEDALLION,animation_time,hud=True)
        self.text(f'{self.medallions.count} / 3',hud_layout.MEDALLION_COUNT,20,GOLD,max_width=62,outlined=True)
        if self.extra_life_notice>0:self.text('VIE +1 OBTENUE',hud_layout.EXTRA_LIFE,10,GOLD,center=True,max_width=290,outlined=True)
        self.draw_solar_gauge(alpha)
        if self.state=='play' and self.hero.x<1000 and (self.level_id!=4 or self.hero.y>tower_level.BASE_Y-180):
            self.canvas.blit(self.help_panel,((VIEW_W-self.help_panel.get_width())//2,665))
            self.text('Stick / ← →  Bouger    A / Espace  Saut    Bas / S  Accroupir    RT / B / F  Tir    Maintenir A  Planer',(VIEW_W/2,682),16,center=True,max_width=1040)

    def draw_solar_gauge(self,alpha=1.,low=None):
        if low is None:low=self.energy.value<RAY_COST
        color=(247,144,65) if low else GOLD
        animation_time=self.previous_elapsed+(self.elapsed-self.previous_elapsed)*max(0.,min(1.,alpha))
        self.solar_gauge.draw(self.canvas,self.energy.fraction(alpha),animation_time,low)
        if self.energy.value<=0:self.text('ÉPUISÉE',hud_layout.ENERGY_WARNING,10,color,center=True,max_width=200,outlined=True)
        elif self.energy.warning>0:self.text('ÉNERGIE INSUFFISANTE',hud_layout.ENERGY_WARNING,10,(255,160,91),center=True,max_width=200,outlined=True)

    def title(self):
        self.menu.draw(self,'title')

    def save_settings(self):
        self.settings.fullscreen=self.fullscreen
        self.settings.sound=self.sound_on
        self.settings.rumble=self.gamepads.rumble_enabled
        self.settings.show_fps=self.show_fps
        self.menu.save_failed=not self.settings.save(self.settings_path)

    def toggle_sound(self):
        self.sound_on=not self.sound_on
        if self.sound_on and self.settings.sound_volume==0:
            self.settings.sound_volume=100;self.apply_sound_volume()
        self.save_settings()

    def sync_menu_music(self):
        paused_menu=(self.state in ('pause','save','overwrite') or
                     self.state in ('settings','controls','languages','bezels') and self.menu.origin=='pause')
        if self.music_ready:self.menu_music.update(self.settings.music and self.state in MENU_PAGES,
                                                  volume=self.settings.music_volume/100*(.7 if paused_menu else 1.))

    def adjust_volume(self,kind,direction):
        self.set_volume(kind,getattr(self.settings,kind+'_volume')+direction*10)

    def set_volume(self,kind,value,persist=True):
        key=kind+'_volume'
        value=max(0,min(100,round(value)))
        setattr(self.settings,key,value)
        if kind=='sound':
            self.sound_on=value>0;self.apply_sound_volume()
        else:self.settings.music=value>0;self.sync_menu_music()
        if persist:self.save_settings()

    def toggle_music(self):
        self.settings.music=not self.settings.music
        if self.settings.music and self.settings.music_volume==0:self.settings.music_volume=100
        self.save_settings();self.sync_menu_music()

    def enter_menu(self,page):
        self.menu.end_volume_drag(self)
        self.gamepads.stop_rumble()
        self.state=page;self.acc=0.
        self.sync_menu_music()
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
        self.sync_menu_music()
        self.pending_jump=self.pending_drop=self.pending_fire=self.pending_activity=False
        self.menu_gameplay_blocked=True
        self.rumble_death_animation()
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
            elif page=='bezels':self.enter_menu('settings')
            elif page=='pause':self.resume_from_menu()
            else:self.quit_requested=True
            return
        index=self.menu.selected[page]
        if page=='bezels':
            if action=='activate':
                if index==len(BEZEL_MODES):self.enter_menu('settings')
                else:self.set_bezel(BEZEL_MODES[index])
            elif action in ('left','right'):
                offset=-1 if action=='left' else 1
                self.set_bezel(BEZEL_MODES[(BEZEL_MODES.index(self.settings.bezel)+offset)%len(BEZEL_MODES)])
                self.menu.selected['bezels']=BEZEL_MODES.index(self.settings.bezel)
            return
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
            elif index==1:
                if action=='activate':self.toggle_sound()
                else:self.adjust_volume('sound',-1 if action=='left' else 1)
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
            elif index==6:
                if action=='activate':self.toggle_music()
                else:self.adjust_volume('music',-1 if action=='left' else 1)
            elif action=='activate' and index==7:
                self.menu.selected['bezels']=BEZEL_MODES.index(self.settings.bezel);self.enter_menu('bezels')
            elif action in ('left','right') and index==7:
                offset=-1 if action=='left' else 1
                self.set_bezel(BEZEL_MODES[(BEZEL_MODES.index(self.settings.bezel)+offset)%len(BEZEL_MODES)])
            elif action=='activate' and index==8:self.enter_menu(self.menu.origin)
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
        elif key==pg.K_r and self.state=='pause' and not (self.hero_death.active or self.resurrection.active):self.restart_level();self.state='play'

    def menu_pointer(self,position):
        if self.display_flags & pg.SCALED:return position[0]/SCALE,position[1]/SCALE
        size,offset=integer_viewport(self.screen.get_size(),(W,H))
        factor=size[0]/W*SCALE
        return (position[0]-offset[0])/factor,(position[1]-offset[1])/factor

    def draw_victory(self):
        title,subtitle=(('LE SEUIL EST FRANCHI','NIVEAU 02 · LE DÉSERT'),
                        ('LE TEMPLE EST ATTEINT','NIVEAU 03 · LE TEMPLE'),
                        ('LE SANCTUAIRE EST ATTEINT','NIVEAU 04 · LA TOUR'),
                        ('LE SOMMET EST ATTEINT','NIVEAU 05 · LES RIVAGES D’HÉLIOS'),
                        ('LE RIVAGE EST FRANCHI','NIVEAU 06 · LA VOIE DES STATUES'),
                        ('LA VOIE EST FRANCHIE','NIVEAU 07 · LES GALERIES DU MARBRE'),
                        ('LES GALERIES SONT FRANCHIES','NIVEAU 08 · L’ACROPOLE DU SOLEIL'),
                        ('L’ACROPOLE EST ATTEINTE','L’ASCENSION EST TERMINÉE'))[self.level_id-1]
        helptext='Entrée, Start ou A pour rejouer' if self.level_id==8 else 'Entrée, Start ou A pour continuer'
        self.overlay(title,subtitle,helptext)
        self.text(f'{len(self.taken)} / {len(self.gems)} éclats solaires   ·   {int(self.elapsed)//60:02}:{int(self.elapsed)%60:02}   ·   {self.deaths} morts',
                  (VIEW_W/2,405),16,center=True,max_width=VIEW_W-100)
        bonus=sample_life_bonus(self.time-self.victory_started,self.victory_lives) if self.victory_started is not None else None
        pending=self.victory_lives*100-bonus.points if bonus else 0
        self.text(f'Score total : {self.score-pending:,}'.replace(',',' '),
                  (VIEW_W/2,445),22,GOLD,center=True,max_width=VIEW_W-100)
        self.text(f'Points du niveau : {self.level_score-pending:,}'.replace(',',' '),
                  (VIEW_W/2,480),18,center=True,max_width=VIEW_W-100)
        if bonus:
            self.text('VIES',(VIEW_W/2-170,520),14,GOLD)
            self.text(str(bonus.remaining),(VIEW_W/2-125,520),14,GOLD)
            icons=min(6,bonus.remaining-int(bonus.flying))
            for index in range(icons):
                self.canvas.blit_native(self.life_symbol,(VIEW_W/2-95+index*34,520))
            if bonus.flying:
                p=min(1.,bonus.progress/.8);p=p*p*(3-2*p)
                x=VIEW_W/2-95+min(5,bonus.remaining-1)*34
                x+=(VIEW_W/2-210-x)*p
                y=520-75*p-math.sin(p*math.pi)*24
                width,height=self.life_symbol.get_size();zoom=1+.55*math.sin(p*math.pi)
                self.native_canvas.blit(self.life_symbol,(pixel(x*SCALE),pixel(y*SCALE),pixel(width*zoom),pixel(height*zoom)))
            self.text(f'× 100    +{bonus.points}',(VIEW_W/2,565),18,GOLD,center=True)

    def game_over_results(self):
        shards=self.run_totals['shards']+len(self.taken)
        elapsed=int(self.run_totals['elapsed']+self.elapsed)
        deaths=self.run_totals['deaths']+self.deaths
        return f'{shards} éclats solaires   ·   {elapsed//60:02}:{elapsed%60:02}   ·   {deaths} morts'

    def draw_game_over(self):
        self.canvas.blit(self.overlay_shade,(0,0))
        self.text('GAME OVER',(VIEW_W/2+3,243),88,(25,13,12),True,True,max_width=VIEW_W-100)
        self.text('GAME OVER',(VIEW_W/2,240),88,(247,154,70),True,True,max_width=VIEW_W-100)
        self.text('Vous avez perdu toutes vos vies.',(VIEW_W/2,330),24,center=True)
        self.text(f'{translate("Niveau",self.settings.language)} {self.level_id:02}',(VIEW_W/2,379),18,GOLD,center=True)
        self.text(self.game_over_results(),
                  (VIEW_W/2,420),22,center=True,max_width=VIEW_W-100)
        self.text(f'SCORE  {self.score:,}'.replace(',',' '),(VIEW_W/2,461),24,GOLD,center=True,max_width=VIEW_W-100)
        self.text('Entrée, Start ou A pour une nouvelle partie',(VIEW_W/2,505),18,center=True,max_width=VIEW_W-100)

    def overlay(self,title,sub,helptext):
        self.canvas.blit(self.overlay_shade,(0,0))
        self.text(title,(VIEW_W/2,280),44,GOLD,True,True,max_width=VIEW_W-100)
        self.text(sub,(VIEW_W/2,365),24,center=True,max_width=VIEW_W-100)
        self.text(helptext,(VIEW_W/2,605),18,center=True,max_width=VIEW_W-100)

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
        if pad.back_pressed and not pad.start_pressed and self.state in ('play','pause') and not (self.hero_death.active or self.resurrection.active):
            self.restart_level();self.state='play'
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
                    self.menu.end_volume_drag(self)
                    self.gamepads.stop_rumble()
                    if self.state=='play':self.menu.selected['pause']=0;self.enter_menu('pause')
                elif e.type==pg.MOUSEBUTTONUP and e.button==1:
                    self.menu.drag_volume(self,self.menu_pointer(e.pos))
                    self.menu.end_volume_drag(self)
                elif e.type==pg.MOUSEMOTION and self.menu.drag_volume(self,self.menu_pointer(e.pos)):
                    pass
                elif e.type in (pg.MOUSEMOTION,pg.MOUSEBUTTONDOWN) and self.state in MENU_PAGES:
                    if self.menu.pointer(self.state,self.menu_pointer(e.pos)) and e.type==pg.MOUSEBUTTONDOWN and e.button==1:
                        if not self.menu.click_volume(self,self.menu_pointer(e.pos)):
                            self.menu_action('activate')
                elif e.type==pg.KEYDOWN:
                    if e.key==pg.K_F12:
                        if not getattr(e,'repeat',False):self.screenshots.request()
                        continue
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
                        elif self.state=='pause':self.resume_from_menu()
                        else:running=False
                        self.acc=0
                    elif e.key==pg.K_RETURN and self.state in ('win','game_over'):
                        self.continue_or_restart()
                    elif e.key==pg.K_r and self.state in ('play','pause') and not (self.hero_death.active or self.resurrection.active):
                        self.restart_level();self.state='play'
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
                    was_dying=self.hero_death.active or self.resurrection.active
                    self.update(STEP,axis,held,self.pending_jump,self.pending_drop,self.pending_fire,
                                self.pending_activity or any(keys) or self.pad.activity,down=down)
                    self.pending_jump=False;self.pending_drop=False;self.pending_fire=False;self.pending_activity=False;self.acc-=STEP
                    if was_dying and not (self.hero_death.active or self.resurrection.active):self.acc=0.;break
                    if self.state!='play':break
            self.update_cursor(time.perf_counter())
            self.draw(self.acc/STEP if self.state=='play' else 1)
            count+=1
            if frames and count>=frames:running=False
        if screenshot:pg.image.save(self.capture(),str(screenshot))
        self.close()


if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--headless',action='store_true');ap.add_argument('--frames',type=int,default=0);ap.add_argument('--screenshot');ap.add_argument('--play',action='store_true');ap.add_argument('--windowed',action='store_true')
    ap.add_argument('--level',type=int,choices=range(1,9),default=1)
    args=ap.parse_args()
    try:game=Game(args.headless,fullscreen=False if args.windowed or args.headless else None)
    except LoadingCancelled:sys.exit(0)
    if args.level!=1:game.start_level(args.level)
    if args.play:game.state='play'
    try:game.run(args.frames,args.screenshot)
    finally:game.close()
