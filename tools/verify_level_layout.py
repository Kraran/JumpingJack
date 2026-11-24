"""Find actual physics-based jumps between every support, without enemies.

This verifies geometry, not enemy difficulty or human execution. Starts use a
running approach; normal jumps and gliding are both considered.
"""
import json
import sys
from collections import deque
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from main import Hero,STEP,level,ROOT,PLATFORM_WIDTHS


def verify():
    platforms,gems=level();queue=deque([0]);reachable={0};links={}
    while queue and len(reachable)<len(platforms):
        source_index=queue.popleft();source=platforms[source_index]
        starts={source.x+18,source.x+source.w-18,source.x+source.w/2}
        starts.update(range(round(source.x+30),round(source.x+source.w-20),45))
        for start in sorted(starts):
            for direction in (-1,1):
                for glide in (False,True):
                    hero=Hero(start,source.y);hero.grounded=True;hero.vx=direction*340
                    if any(p is not source and hero.rect.colliderect(p.rect) for p in platforms):continue
                    for tick in range(240):
                        hero.update(STEP,direction,glide,tick==0,platforms)
                        if hero.y>850 or hero.spike_hit:break
                        if hero.grounded:
                            for index,p in enumerate(platforms):
                                if abs(hero.y-p.y)<.001 and hero.x+15>p.x and hero.x-15<p.x+p.w:
                                    if index not in reachable:
                                        reachable.add(index);queue.append(index)
                                        links[index]={'from':source_index,'start':start,
                                                      'direction':direction,'glide':glide,'ticks':tick+1}
                                    break
                            break
    missing=[i for i in range(len(platforms)) if i not in reachable]
    result={'widths':list(PLATFORM_WIDTHS),'platforms':len(platforms)-7,'shards':len(gems),
            'reachable_supports':len(reachable),'total_supports':len(platforms),
            'missing_supports':missing,'jumps':links,
            'scope':'Geometry only; running approaches, no enemies; normal jump or glide.'}
    (ROOT/'output'/'level-layout-validation.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='jumps'}))
    if missing:raise AssertionError(f'Unreached platforms: {missing}')


if __name__=='__main__':verify()
