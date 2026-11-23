"""Optional native-window presentation check: python verify_display.py."""
import argparse
from dataclasses import asdict
import gc
import json
from pathlib import Path
import statistics
import time

import pygame as pg
from main import Game, WORLD, VIEW_W, W, H


def verify(frames, output,fullscreen_only=False):
    game=Game(fullscreen=fullscreen_only)
    game.state='play'
    results={}
    initial_fullscreen=game.fullscreen
    toggles=0
    try:
        phases=('fullscreen',) if fullscreen_only else ('window','fullscreen','returned_window')
        for phase,name in enumerate(phases):
            if phase:game.toggle_fullscreen();toggles+=1
            gc.collect()
            start=time.perf_counter()
            samples=[]
            last=None
            tick=start
            game.hero.x=game.hero.px=phase*1500+400
            game.hero.vx=340;game.hero.vy=0;game.hero.grounded=True;game.hero.floating=False
            for i in range(frames+30):
                game.pacer.wait(game.presentation.vsync,game.presentation.refresh_hz)
                if any(e.type==pg.QUIT or (e.type==pg.KEYDOWN and e.key==pg.K_ESCAPE) for e in pg.event.get()):
                    raise KeyboardInterrupt
                now=time.perf_counter()
                dt=now-tick;tick=now
                game.time=now-start
                game.cam=game.prev_cam=min(WORLD-VIEW_W,phase*1500+game.time*340)
                game.hero.px=game.hero.x;game.hero.x=game.cam+400
                game.hero_animation.update(dt,game.hero,True)
                game.draw(1)
                now=time.perf_counter()
                if i>=30 and last is not None:samples.append(now-last)
                last=now
            ordered=sorted(samples)
            results[name]={
                'display':asdict(game.presentation),'fullscreen':game.fullscreen,
                'render_size':[W,H],'gpu_composition':game.native_canvas.gpu,
                'texture_uploads':game.native_canvas.uploads,
                'hero_pose_count':game.animation_bank.pose_count if game.animation_bank else 8,
                'hero_animation_state':game.hero_animation.state,
                'hero_textures_cached':all(id(im) in game.native_canvas.textures for im in game.animation_bank.images) if game.native_canvas.gpu and game.animation_bank else False,
                'cpu_submission_median_ms':round(statistics.median(game.submission_times)*1000,3),
                'frames_measured':len(samples),'fps':round(len(samples)/sum(samples),2),
                'median_frame_ms':round(statistics.median(samples)*1000,2),
                'p95_frame_ms':round(ordered[int(len(ordered)*.95)]*1000,2),
                'max_frame_ms':round(max(samples)*1000,2),
                'late_frames':sum(t>1.5/game.presentation.refresh_hz for t in samples),
            }
            print(name,json.dumps(results[name],ensure_ascii=False),flush=True)
        for _ in range(10-toggles):
            game.toggle_fullscreen()
            gc.collect()
            for _ in range(3):pg.event.get();game.draw(1)
        assert game.fullscreen==initial_fullscreen
        results['fullscreen_toggles_passed']=10
        results['note']='SDL status and measured CPU presentation intervals; no physical scanout measurement.'
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(results,indent=2,ensure_ascii=False),encoding='utf-8')
    finally:
        game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frames',type=int,default=180)
    parser.add_argument('--fullscreen-only',action='store_true')
    parser.add_argument('--output',type=Path,default=Path(__file__).parent/'output'/'fullhd-gpu-timing.json')
    args=parser.parse_args()
    if args.frames<2:parser.error('--frames doit être au moins égal à 2')
    verify(args.frames,args.output,args.fullscreen_only)
