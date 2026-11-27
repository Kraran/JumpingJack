"""Explicit full-output screenshots; PNG encoding runs outside the game loop."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
import time
import pygame as pg


def save_png(image,directory,stamp):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    for index in range(10000):
        suffix='' if index==0 else f'_{index:03}'
        path=directory/f'JumpingJack_{stamp}{suffix}.png'
        try:stream=path.open('xb')
        except FileExistsError:continue
        try:
            with stream:pg.image.save(image,stream,'.png')
        except Exception:
            path.unlink(missing_ok=True)
            raise
        return path
    raise OSError('Too many screenshots with the same timestamp')


class Screenshots:
    def __init__(self,directory,clock=time.monotonic):
        self.directory=Path(directory);self.clock=clock
        self.requested=False;self.jobs=[];self.worker=None
        self.last_path=None;self.error=None;self.notice_until=0.

    def request(self):
        # Bound memory if a key is spammed while the disk is slow.
        if len(self.jobs)<4:self.requested=True

    def submit(self,image):
        self.requested=False
        if self.worker is None:self.worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix='JumpingJack-capture')
        stamp=datetime.now().strftime('%Y-%m-%d_%H-%M-%S_%f')
        self.jobs.append(self.worker.submit(save_png,image,self.directory,stamp))

    def fail(self,error):
        self.requested=False;self.error=str(error);self.notice_until=self.clock()+3.

    def poll(self):
        pending=[]
        for job in self.jobs:
            if not job.done():pending.append(job);continue
            try:self.last_path=job.result();self.error=None
            except (OSError,pg.error) as error:self.error=str(error)
            self.notice_until=self.clock()+3.
        self.jobs=pending

    @property
    def notice(self):
        if self.clock()>=self.notice_until:return None
        return 'Échec de la capture d’écran.' if self.error else 'Capture enregistrée dans captures/.'

    def close(self):
        if self.worker is not None:self.worker.shutdown(wait=True);self.worker=None
        self.poll()
