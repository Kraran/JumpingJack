"""Bounded full Greek campaign replays with live enemies and finite energy."""
import json
import sys
import copy
import argparse
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from main import Game,STEP,ROOT
from greece_levels import LEVELS


def next_jump(game,support):
    """Search real no-glide trajectories from the current moving hero."""
    walker=copy.copy(game.hero);best=None
    for walking in range(301):
        if walking%6==0 and walker.grounded:
            probe=copy.copy(walker)
            for flying in range(240):
                probe.update(STEP,1,False,flying==0,game.platforms,allow_glide=False)
                if probe.spike_hit or probe.y>700:break
                if probe.grounded:
                    target=next((p for p in game.platforms if p.kind!='greek_ceiling'
                                 and abs(probe.y-p.y)<1 and p.x-15<probe.x<p.x+p.w+15),None)
                    if target is not None and target is not support and probe.x>game.hero.x+100:
                        guards=[e for e in [*game.scorpions,*game.hoplites] if e.alive]
                        unsafe=any(abs(e.x-probe.x)<240 and abs(e.y-probe.y)<100 for e in guards)
                        quality=probe.x-(1500 if unsafe else 0)
                        if best is None or quality>best[0]:best=(quality,walking,flying+1)
                    break
        walker.update(STEP,1,False,False,game.platforms,allow_glide=False)
        if not walker.grounded or walker.spike_hit:break
    return best


def replay(game,level_id):
    game.new_game();game.start_level(level_id);game.state='play';game.sound_on=False;game.invuln=0
    fire_requests=0;walking=None;previous_deaths=0;glide_used=False;death_events=[]
    for tick in range(120*240):
        h=game.hero
        support=next((p for p in game.platforms if p.kind!='greek_ceiling'
                      and abs(h.y-p.y)<1 and p.x-15<=h.x<=p.x+p.w+15),None)
        gap_distance=support.x+support.w-h.x if support else 1000
        if game.deaths!=previous_deaths:
            walking=None;previous_deaths=game.deaths
        dying=game.hero_death.active or game.resurrection.active
        jump=False
        if not dying:
            if walking is None and h.grounded and support and (not support.ground or gap_distance<700):
                plan=next_jump(game,support)
                if plan:_,walking,_=plan
            if walking is not None:
                if walking>0:walking-=1
                else:jump=True;walking=None
        enemies=[(m.x+m.vx*.20,m.y+m.vy*.20) for m in game.beetle_motions if m.index not in game.dead_beetles]
        enemies += [(e.x,e.y-22) for e in game.scorpions if e.alive]
        enemies += [(e.x+e.vx*.20,e.y+e.vy*.20) for e in game.gyrospheres if e.alive]
        enemies += [e.position(1) for e in game.vultures if e.alive]
        enemies += [(e.x,e.y-54) for e in game.hoplites if e.alive]
        # Jump over ground guards when a ray is unavailable; retain the same
        # pit approach rather than depending on energy to cross any gap.
        future_y=h.y+(-790 if jump else h.vy)*.20+.5*1550*.20**2-54 if not h.grounded or jump else h.y-54
        targets=[(x,y) for x,y in enemies if 0<x-h.x<600 and abs(y-future_y)<42]
        fire=bool(targets and game.energy.value>=30 and not game.solar.active and game.solar.cooldown<=0)
        # Ground scorpions are deliberately low targets: use the game's actual
        # crouch-and-shoot command rather than grazing their shells while running.
        down=bool(h.grounded and h.recovery<=0 and game.energy.value>=30 and any(
            e.alive and 80<e.x-h.x<600 and abs(e.y-h.y)<2 for e in game.scorpions))
        if down:
            walking=None;jump=False
            fire=not game.solar.active and game.solar.cooldown<=0
        # Briefly glide just before a landing, as a player can, to soften a
        # high drop and avoid standing helpless in a guard's line of fire.
        held=False
        if level_id==7 and not dying and not h.grounded and h.vy>0 and game.energy.value>0:
            distances=[p.y-h.y for p in game.platforms if p.ground and p.kind!='greek_ceiling'
                       and p.y>=h.y and p.y-h.fall_origin_y>=280
                       and p.x+64<h.x<p.x+p.w-64]
            held=bool(distances and min(distances)<=max(10,h.vy*STEP*2))
            glide_used=glide_used or held
        fire_requests+=int(fire)
        game.time+=STEP;game.update(STEP,0 if down else 1,held,jump,fire=fire,down=down)
        if game.deaths>previous_deaths:
            death_events.append({'kind':game.hero_death.kind,'x':round(game.hero.x,2),
                                 'y':round(game.hero.y,2),'energy':round(game.energy.value,2)})
        if game.state in ('win','game_over'):break
    result={'level':level_id,'state':game.state,'frames':tick+1,'deaths':game.deaths,
            'lives':game.lives,'energy':round(game.energy.value,2),'fire_requests':fire_requests,
            'crystals':len(game.taken),'score':game.score,'checkpoint':game.check_index,
            'hero':[round(game.hero.x,2),round(game.hero.y,2)],
            'hoplites':len(game.hoplites),'hoplites_defeated':sum(not e.alive for e in game.hoplites),
            'death_events':death_events,
            'enemies_active':True,'initial_protection':False,'glide_used':glide_used}
    print(result,flush=True)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--level',type=int,choices=tuple(LEVELS))
    args=parser.parse_args()
    game=Game(True)
    try:results=[replay(game,i) for i in ([args.level] if args.level else LEVELS)]
    finally:game.close()
    filename=f'greece-gameplay-level{args.level:02}.json' if args.level else 'greece-gameplay-validation.json'
    (ROOT/'output'/filename).write_text(json.dumps(results,indent=2),encoding='utf-8')
    assert all(r['state']=='win' for r in results),'A bounded bot replay did not finish'
