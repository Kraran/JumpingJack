"""Greek geometry reachability, using real jumps without energy or gliding."""
import json
import sys
from collections import deque
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from main import Hero, STEP, level, ROOT
from greece_levels import LEVELS
from terrain import overlaps_rect


def verify(level_id):
    platforms,gems=level(level_id)
    supports={i for i,p in enumerate(platforms) if p.kind!='greek_ceiling'}
    reachable={0};pending=deque([0]);links={}
    while pending and reachable!=supports:
        source_id=pending.popleft();source=platforms[source_id]
        starts={source.x+20,source.x+source.w-20,source.x+source.w/2}
        starts.update(range(round(source.x+30),round(source.x+source.w-20),60))
        for start in sorted(starts):
            for direction in (-1,1):
                hero=Hero(start,source.y);hero.grounded=True;hero.vx=direction*340
                if any(p is not source and overlaps_rect(p,hero.rect) for p in platforms):continue
                for tick in range(250):
                    hero.update(STEP,direction,False,tick==0,platforms,allow_glide=False)
                    if hero.y>700 or hero.spike_hit:break
                    if hero.grounded:
                        target=next((i for i in supports if abs(hero.y-platforms[i].y)<.001
                                     and hero.x+15>platforms[i].x and hero.x-15<platforms[i].x+platforms[i].w),None)
                        if target is not None and target not in reachable:
                            reachable.add(target);pending.append(target)
                            links[target]={'from':source_id,'start':start,'direction':direction,'ticks':tick+1}
                        break
    config=LEVELS[level_id]
    # A rare reward must be reachable by a jump from a nearby support too.
    medal_reachable=False
    from medallion import touches
    for i in reachable:
        p=platforms[i]
        if not p.x-400<config.MEDALLION[0]<p.x+p.w+400:continue
        for start in (max(p.x+20,min(p.x+p.w-20,config.MEDALLION[0]-100)),
                      max(p.x+20,min(p.x+p.w-20,config.MEDALLION[0]))):
            for direction in (0,1,-1):
                h=Hero(start,p.y);h.grounded=True;h.vx=direction*340
                for tick in range(200):
                    h.update(STEP,direction,False,tick==0,platforms,allow_glide=False)
                    if h.spike_hit:break
                    if touches(h,0,config.MEDALLION):medal_reachable=True;break
                if medal_reachable:break
            if medal_reachable:break
        if medal_reachable:break
    result={'level':level_id,'length':config.LENGTH,'supports':len(supports),
            'reachable':len(reachable),'missing':sorted(supports-reachable),
            'medallion_reachable':medal_reachable,'glide_used':False,'energy_used':0,
            'scope':'Geometry only; real physics with running approaches, enemies excluded.',
            'jumps':links}
    print({key:value for key,value in result.items() if key!='jumps'},flush=True)
    return result


if __name__=='__main__':
    results=[verify(i) for i in LEVELS]
    (ROOT/'output'/'greece-layout-validation.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    assert all(not r['missing'] and r['medallion_reachable'] for r in results), 'Unreachable Greek geometry'
