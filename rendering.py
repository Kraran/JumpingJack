"""Pixel-aligned parallax and display pacing; no simulation state in the renderer."""
from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
import math
from pathlib import Path
import time

import pygame as pg


def pixel(value: float) -> int:
    return math.floor(value + .5)


def integer_viewport(output, logical):
    """Whole source pixels, centered. Small outputs clip rather than blur pixels."""
    scale=max(1,min(output[0]//logical[0],output[1]//logical[1]))
    size=(logical[0]*scale,logical[1]*scale)
    return size,((output[0]-size[0])//2,(output[1]-size[1])//2)


@dataclass(frozen=True)
class ParallaxLayer:
    name: str
    image: pg.Surface
    numerator: int
    denominator: int
    repeat: bool = True
    bounds: pg.Rect = field(init=False,compare=False)

    def __post_init__(self):
        object.__setattr__(self,'bounds',self.image.get_bounding_rect())

    def offset(self, camera: float) -> int:
        # Absolute camera position: no per-frame addition, lost fractions or drift.
        return pixel(camera*self.numerator/self.denominator)

    def draw(self, target: pg.Surface, camera: float):
        offset=self.offset(camera)
        width=self.image.get_width()
        if not self.repeat:
            target.blit(self.image,(-offset,0))
            return
        x=-(offset % width)
        while x<target.get_width():
            target.blit(self.image,(x+self.bounds.x,self.bounds.y),self.bounds)
            x+=width


class FramePacer:
    """Only pace in software when SDL has no synchronized presenter."""
    def __init__(self, clock=time.perf_counter, sleep=time.sleep):
        self.clock=clock
        self.sleep=sleep
        self.deadline=None

    def reset(self):
        self.deadline=None

    def wait(self, vsync: bool, refresh_hz: int):
        if vsync:
            self.reset()
            return
        period=1/max(1,refresh_hz)
        now=self.clock()
        if self.deadline is not None:
            remaining=self.deadline-now
            if remaining>0:
                self.sleep(remaining)
                now=self.clock()
            # A late frame starts a new cadence; never render catch-up bursts.
            following=self.deadline+period
            self.deadline=following if following>now else now+period
        else:
            self.deadline=now+period


@dataclass(frozen=True)
class DisplayStatus:
    refresh_hz: int = 60
    refresh_known: bool = False
    vsync: bool = False
    integer_scaling: bool = False
    renderer: str = 'logiciel'
    desktop_bounds: tuple[int,int,int,int] = (0,0,1280,720)
    accelerated: bool = False


class _DisplayMode(ctypes.Structure):
    _fields_=[('format',ctypes.c_uint32),('w',ctypes.c_int),('h',ctypes.c_int),
              ('refresh_rate',ctypes.c_int),('driverdata',ctypes.c_void_p)]


class _RendererInfo(ctypes.Structure):
    _fields_=[('name',ctypes.c_char_p),('flags',ctypes.c_uint32),
              ('num_texture_formats',ctypes.c_uint32),('texture_formats',ctypes.c_uint32*16),
              ('max_texture_width',ctypes.c_int),('max_texture_height',ctypes.c_int)]


class _Rect(ctypes.Structure):
    _fields_=[('x',ctypes.c_int),('y',ctypes.c_int),('w',ctypes.c_int),('h',ctypes.c_int)]


def configure_display(logical_size, window_id=None) -> DisplayStatus:
    """Inspect the *current window's* SDL renderer and monitor on Windows.

    Use the SDL library bundled with pygame, never a different system SDL.
    Missing native inspection leaves a conservative timed software fallback.
    """
    path=Path(pg.__file__).parent/'SDL2.dll'
    if not path.exists() or pg.display.get_driver()=='dummy' or window_id is None:
        return DisplayStatus()
    try:
        sdl=ctypes.CDLL(str(path))
        def bind(name, result, args):
            fn=getattr(sdl,name);fn.restype=result;fn.argtypes=args
            return fn
        ptr=ctypes.c_void_p
        window=bind('SDL_GetWindowFromID',ptr,[ctypes.c_uint32])(window_id)
        if not window:return DisplayStatus()
        bind('SDL_SetWindowMinimumSize',None,[ptr,ctypes.c_int,ctypes.c_int])(window,*logical_size)
        index=bind('SDL_GetWindowDisplayIndex',ctypes.c_int,[ptr])(window)
        mode=_DisplayMode()
        ok=bind('SDL_GetCurrentDisplayMode',ctypes.c_int,[ctypes.c_int,ctypes.POINTER(_DisplayMode)])(index,ctypes.byref(mode))==0
        known=ok and mode.refresh_rate>0
        refresh=mode.refresh_rate if known else 60
        bounds=_Rect()
        found=bind('SDL_GetDisplayBounds',ctypes.c_int,[ctypes.c_int,ctypes.POINTER(_Rect)])(index,ctypes.byref(bounds))==0
        desktop=(bounds.x,bounds.y,bounds.w,bounds.h) if found else (0,0,*logical_size)
        renderer=bind('SDL_GetRenderer',ptr,[ptr])(window)
        if not renderer:return DisplayStatus(refresh,known,desktop_bounds=desktop)
        bind('SDL_RenderSetVSync',ctypes.c_int,[ptr,ctypes.c_int])(renderer,1)
        integer=bind('SDL_RenderSetIntegerScale',ctypes.c_int,[ptr,ctypes.c_int])(renderer,1)==0
        info=_RendererInfo()
        result=bind('SDL_GetRendererInfo',ctypes.c_int,[ptr,ctypes.POINTER(_RendererInfo)])(renderer,ctypes.byref(info))
        if result!=0:return DisplayStatus(refresh,known,integer_scaling=integer,desktop_bounds=desktop)
        return DisplayStatus(refresh,known,bool(info.flags & 0x4),integer,
                             info.name.decode('utf-8','replace') if info.name else 'SDL',desktop,bool(info.flags & 0x2))
    except (OSError,AttributeError,pg.error,ImportError):
        return DisplayStatus()
