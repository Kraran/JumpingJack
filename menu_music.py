"""Preloaded streaming menu music with nonblocking fades and position-preserving pause."""
import time
from pathlib import Path
import pygame as pg

VOLUME=.65
FADE_IN=.8
FADE_OUT=2.
LOADING_FADE=1.2


class MenuMusic:
    def __init__(self,path,enabled=True,music=None,clock=time.monotonic):
        self.clock=clock;self.music=pg.mixer.music if music is None else music
        self.available=False;self.error=None
        self.started=False;self.paused=False;self.active=False;self.starts=0
        self.volume=0.;self.target=0.;self.fade_from=0.;self.fade_start=0.;self.fade_duration=FADE_IN
        if not enabled:return
        if music is None and not pg.mixer.get_init():return
        try:
            if not Path(path).is_file():return
            self.music.load(str(path));self.music.set_volume(0.)
            self.available=True
        except (pg.error,OSError) as error:self.error=str(error)

    def _advance(self,now):
        progress=max(0.,min(1.,(now-self.fade_start)/self.fade_duration))
        volume=self.fade_from+(self.target-self.fade_from)*progress
        if abs(volume-self.volume)>1e-7:
            self.volume=volume;self.music.set_volume(volume)
        if not self.active and self.started and not self.paused and progress>=1:
            self.music.pause();self.paused=True

    def start_loading(self,volume=1.):
        """SDL mixes this fade itself, even while assets block the main thread."""
        if not self.available:return
        try:
            self.volume=self.target=self.fade_from=VOLUME*max(0.,min(1.,volume))
            self.music.set_volume(self.volume)
            self.music.play(loops=-1,fade_ms=round(LOADING_FADE*1000))
            self.started=self.active=True;self.starts+=1
        except (pg.error,OSError) as error:
            self.error=str(error);self.available=False

    def update(self,active,now=None,volume=1.):
        if not self.available:return
        now=self.clock() if now is None else now
        try:
            self._advance(now)
            target=VOLUME*max(0.,min(1.,volume)) if active else 0.
            if bool(active)==self.active and abs(target-self.target)<1e-7:return
            self.active=bool(active)
            if self.active:
                if not self.started:
                    self.music.play(loops=-1);self.started=True;self.starts+=1
                elif self.paused:self.music.unpause()
                self.paused=False
            self.fade_from=self.volume;self.fade_start=now
            self.target=target
            self.fade_duration=FADE_IN if self.active else FADE_OUT
            self._advance(now)
        except (pg.error,OSError) as error:
            self.error=str(error);self.available=False
            try:self.music.stop()
            except (pg.error,OSError):pass

    def close(self):
        if not self.available:return
        try:
            self.music.stop();self.music.unload()
        except (pg.error,OSError):pass
        self.available=False;self.started=False
