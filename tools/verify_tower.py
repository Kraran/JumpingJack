"""Climb every route platform with the real Hero physics, no teleport/glide."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
from main import Hero,Platform,STEP
import tower_level as tower


def verify(inspect_spikes=False):
    platforms,gems=tower.build(Platform)
    targets=tower.route_platforms(platforms)
    hero=Hero(*tower.START);hero.grounded=True;frames=0;landings=[];unsafe=set()
    from spikes import upward_contact
    def inspect(old_top):
        if inspect_spikes:
            for x,y,w,row in tower.BRANCHES:
                if upward_contact(Platform(x,y,w,32),hero.x,old_top,hero.y-hero.body_height) is not None:unsafe.add(row)
    for number,target in enumerate(targets):
        # Center on the current support and release the landing recovery.
        source=tower.START[0] if number==0 else targets[number-1].x+targets[number-1].w/2
        for _ in range(120):
            error=source-(hero.x+hero.vx*abs(hero.vx)/4800)
            axis=1 if error>2 else -1 if error<-2 else 0
            old_top=hero.y-hero.body_height
            hero.update(STEP,axis,False,False,platforms);frames+=1
            inspect(old_top)
            if hero.spike_hit:raise AssertionError(f'Spikes during centering at {number}')
            if abs(hero.x-source)<4 and abs(hero.vx)<8 and hero.recovery<=0:break
        center=target.x+target.w/2
        for tick in range(260):
            error=center-(hero.x+hero.vx*abs(hero.vx)/3500)
            axis=1 if error>2 else -1 if error<-2 else 0
            old_top=hero.y-hero.body_height
            hero.update(STEP,axis,False,tick==0,platforms);frames+=1
            inspect(old_top)
            if hero.spike_hit:raise AssertionError(f'Spikes during jump {number}')
            if hero.grounded and abs(hero.y-target.y)<1 and target.x-14<hero.x<target.x+target.w+14:
                landings.append({'index':number,'position':[round(hero.x,2),round(hero.y,2)]});break
        else:raise AssertionError(f'Unreachable ascent {number}: hero={hero.x,hero.y}, target={target.x,target.y,target.w}')
    assert tower.completed(hero)
    report={'platforms_reached':len(landings),'route_platforms':len(targets),'simulation_frames':frames,
            'glide_used':False,'teleports_used':False,'landings':landings,
            'spiked_platforms':sum(p.spiked for p in platforms)}
    if inspect_spikes:report.update(unsafe_spike_rows=sorted(unsafe),safe_spike_rows=sorted({r for x,y,w,r in tower.BRANCHES}-unsafe))
    return report


if __name__=='__main__':
    data=verify();Path('output/tower-layout-validation.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print({k:v for k,v in data.items() if k!='landings'})
