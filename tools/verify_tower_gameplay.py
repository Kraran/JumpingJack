"""Full tower replay with live enemies, lethal hazards and finite energy/lives."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import json
import math
from main import Game,Hero,STEP
from energy import RAY_COST
import tower_level as tower


def replay():
    g=Game(True);frames=shots=0;landings=[]
    try:
        g.start_level(4);g.state='play';g.sound_on=False;g.invuln=0
        route=tower.route_platforms(g.platforms)
        def step(axis,jump=False):
            nonlocal frames,shots
            h=g.hero;lead=.20
            future=(h.y-54 if h.grounded and not jump else
                    h.y+(-790 if jump else h.vy)*lead+.5*1550*lead**2-54)
            candidates=[(m.x+m.vx*lead,m.y+m.vy*lead) for m in g.beetle_motions if m.index not in g.dead_beetles]
            candidates += [(e.x,e.y-22) for e in g.scorpions if e.alive]
            candidates=[(x,y) for x,y in candidates if abs(x-h.x)<650 and abs(y-future)<32]
            fire=bool(candidates and g.energy.value>=RAY_COST and not g.solar.active and g.solar.cooldown<=0)
            if fire:
                x,y=min(candidates,key=lambda p:math.hypot(p[0]-h.x,p[1]-future))
                axis=1 if x>=h.x else -1;shots+=1
            before=(round(h.x,2),round(h.y,2));motions=list(g.beetle_motions)
            ray=(g.solar.elapsed,g.solar.facing,g.solar.cooldown,g.energy.value,fire)
            g.time+=STEP;g.update(STEP,axis,False,jump,fire=fire)
            frames+=1
            if g.deaths:
                nearest=sorted([(m.index,round(m.x-h.x,1),round(m.y-(h.y-h.body_height/2),1)) for m in motions],key=lambda p:abs(p[1])+abs(p[2]))[:2]
                raise AssertionError(f'Death on ascent {len(landings)}, frame {frames}, at {before}; spike={h.spike_hit}; fire={g.temple_art.flame_hits(h,g.elapsed,tower.TORCHES)}; enemies={nearest}; ray={ray}')
        for number,target in enumerate(route):
            source=tower.START[0] if number==0 else route[number-1].x+route[number-1].w/2
            support=g.platforms[0] if number==0 else route[number-1]
            # Walk to the energy on this support before leaving it. This is
            # real collection, not a refill or an invulnerability shortcut.
            for index,(gx,gy) in enumerate(g.gems):
                if (index in g.taken or abs(gy-(support.y-42))>1
                        or not support.x+15<gx<support.x+support.w-15):continue
                for _ in range(420):
                    h=g.hero;error=gx-(h.x+h.vx*abs(h.vx)/4800)
                    step(1 if error>2 else -1 if error<-2 else 0)
                    if index in g.taken:break
            for _ in range(420):
                h=g.hero;error=source-(h.x+h.vx*abs(h.vx)/4800)
                step(1 if error>2 else -1 if error<-2 else 0)
                if abs(g.hero.x-source)<4 and abs(g.hero.vx)<8 and g.hero.recovery<=0:break
            center=target.x+target.w/2
            for tick in range(260):
                h=g.hero;error=center-(h.x+h.vx*abs(h.vx)/3500)
                step(1 if error>2 else -1 if error<-2 else 0,tick==0)
                if g.hero.grounded and abs(g.hero.y-target.y)<1:
                    landings.append([number,round(g.hero.x,2),round(g.hero.y,2)]);break
            else:raise AssertionError(f'Missed platform {number}, hero={g.hero.x,g.hero.y}')
        assert g.state=='win'
        return {'state':g.state,'deaths':g.deaths,'lives':g.lives,'frames':frames,'shots':shots,
                'crystals':len(g.taken),'energy':g.energy.value,'checkpoint':g.check_index,
                'scorpions_killed':sum(not e.alive for e in g.scorpions),'scarabs_killed':len(g.dead_beetles),
                'protection_disabled':True,'enemies_active':True,'glide_used':False,
                'landings':landings}
    finally:g.close()


if __name__=='__main__':
    data=replay();Path('output/tower-gameplay-validation.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    print({k:v for k,v in data.items() if k!='landings'})
