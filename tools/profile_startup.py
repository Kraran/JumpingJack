"""Measure the very first gameplay frames, including lazy CPU/GPU cache work."""
import argparse
import json
import statistics
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pygame as pg
from main import Game,STEP,ROOT


def stats(rows):
    result={'frames':len(rows)}
    for key in ('update_ms','draw_ms','present_ms','cpu_ms','interval_ms'):
        values=sorted(row[key] for row in rows)
        result[key]={'median':round(statistics.median(values),3),
                     'p95':round(values[min(len(values)-1,int(len(values)*.95))],3),
                     'max':round(max(values),3)}
    result['new_texture_uploads']=sum(row['uploads'] for row in rows)
    result['new_texts']=sum(len(row['texts']) for row in rows)
    result['primitive_misses']=sum(row['primitive_misses'] for row in rows)
    return result


def profile(output,frames=300):
    game=Game(False,fullscreen=True)
    rows=[];current={};present_ms=0.
    original_present=game.native_canvas.present;original_raster=game.native_canvas.raster
    def present(screen):
        nonlocal present_ms
        start=time.perf_counter();original_present(screen);present_ms=(time.perf_counter()-start)*1000
    def raster(key,size,paint,position):
        if key not in game.native_canvas.primitives:current['primitive_misses']=current.get('primitive_misses',0)+1
        return original_raster(key,size,paint,position)
    game.native_canvas.present=present;game.native_canvas.raster=raster
    try:
        for _ in range(3):pg.event.pump();game.draw(1)
        for phase in ('first_run','replay'):
            game.reset();game.state='play';game.invuln=100
            previous=time.perf_counter()
            for frame in range(frames):
                game.pacer.wait(game.presentation.vsync,game.presentation.refresh_hz)
                events=pg.event.get()
                if any(e.type==pg.QUIT or e.type==pg.KEYDOWN and e.key==pg.K_ESCAPE for e in events):raise KeyboardInterrupt
                current={};before_upload=game.native_canvas.uploads;before_text=set(game.text_cache)
                start=time.perf_counter()
                for step in range(2):
                    game.time+=STEP
                    game.update(STEP,1,30<=frame<90,frame==30 and step==0,
                                fire=frame in (10,170) and step==0,down=110<=frame<145)
                updated=time.perf_counter();game.draw(.5);ended=time.perf_counter()
                rows.append({'phase':phase,'frame':frame,'update_ms':(updated-start)*1000,
                             'draw_ms':(ended-updated)*1000,'present_ms':present_ms,
                             'cpu_ms':(ended-start)*1000-present_ms,'interval_ms':(ended-previous)*1000,
                             'uploads':game.native_canvas.uploads-before_upload,
                             'texts':[str(key[0]) for key in set(game.text_cache)-before_text],
                             'primitive_misses':current.get('primitive_misses',0)})
                previous=ended
        summaries={}
        for phase in ('first_run','replay'):
            phase_rows=[row for row in rows if row['phase']==phase]
            summaries[phase]={'first_second':stats(phase_rows[:60]),'later':stats(phase_rows[60:])}
        result={'gpu':game.native_canvas.gpu,'renderer':game.presentation.renderer,
                'refresh_hz':game.presentation.refresh_hz,'summary':summaries,'frames':rows}
        output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
        print(json.dumps(summaries,ensure_ascii=False))
    finally:game.close()


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'output'/'startup-profile.json')
    parser.add_argument('--frames',type=int,default=300)
    args=parser.parse_args();profile(args.output,args.frames)
