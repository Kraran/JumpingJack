"""Preloaded hero poses, sampled on the same fixed-step timeline as movement."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import pygame as pg

CELL=120
STRIDE=136.0  # world units per complete left/right cycle: 0.4 s at full speed
TURN_TIME=.16


@dataclass(frozen=True)
class Pose:
    images: tuple
    pivot: tuple[int,int]

    def draw(self,canvas,x,y,facing):
        image=self.images[0 if facing>0 else 1]
        px,py=self.pivot
        if facing<0:px=image.get_width()-1-px
        root_x,root_y=canvas.point((x,y))
        canvas.native.blit(image,(root_x-px,root_y-py))


@dataclass
class AnimationBank:
    clips: dict

    @property
    def images(self):
        return [im for clip in self.clips.values() for pose in clip for im in pose.images]

    @property
    def pose_count(self):return sum(len(clip) for clip in self.clips.values())


def load_sheet(path,columns,rows,pivot=(.53,.96),pivots=None):
    image=pg.image.load(str(path)).convert_alpha()
    if image.get_at((0,0)).a>8:raise ValueError(f'{path.name}: fond non transparent')
    poses=[]
    for i in range(columns*rows):
        column,row=i%columns,i//columns
        x0=round(column*image.get_width()/columns)
        x1=round((column+1)*image.get_width()/columns)
        y0=round(row*image.get_height()/rows)
        y1=round((row+1)*image.get_height()/rows)
        cell=image.subsurface((x0,y0,x1-x0,y1-y0))
        if not cell.get_bounding_rect(min_alpha=32).w:
            raise ValueError(f'{path.name}: pose {i} vide')
        # Keep a common canvas and scale: trimming/scaling each silhouette makes
        # the head grow/shrink and the character slide as the cape changes shape.
        frame=pg.transform.smoothscale(cell,(CELL,CELL))
        anchor=pivots[i] if pivots is not None else pivot
        poses.append(Pose((frame,pg.transform.flip(frame,True,False)),
                          (round(anchor[0]*CELL),round(anchor[1]*CELL))))
    return poses


def load_bank(directory: Path):
    run=directory/'hero-run-v3.png'
    air=directory/'hero-actions-v3.png'
    if not run.exists() or not air.exists():return None
    metadata=json.loads((directory/'hero-animation.json').read_text(encoding='utf-8'))
    running=load_sheet(run,6,4,pivot=metadata['run_pivot'])
    actions=load_sheet(air,4,3,pivots=metadata['action_pivots'])
    float_path=directory/'hero-float-v4.png'
    hovering=load_sheet(float_path,4,2,pivot=metadata['float_pivot']) if float_path.exists() else actions[8:10]
    clips={'run':running,'idle':actions[:4],
                          'rise':actions[4:8],'float':hovering,
                          'fall':actions[10:11],'land':actions[11:12]}
    pivots=[(.5+.04*math.cos(math.pi*i/7),.96) for i in range(8)]
    for mode in ('ground','air'):
        path=directory/f'hero-turn-{mode}.png'
        if path.exists():clips[f'turn_{mode}']=load_sheet(path,4,2,pivots=pivots)
    return AnimationBank(clips)


class HeroAnimator:
    def __init__(self):self.reset()

    def reset(self):
        self.state='idle'
        self.phase=self.previous_phase=0.
        self.elapsed=self.previous_elapsed=0.
        self.rise=self.previous_rise=0.
        self.landing=0.
        self.last_vy=0.
        self.turn=self.previous_turn=0.
        self.grounded=True

    def update(self,dt,hero,was_grounded):
        self.previous_turn=self.turn
        target=0. if getattr(hero,'face',1)>0 else 1.
        step=dt/TURN_TIME
        self.turn=max(target,self.turn-step) if self.turn>target else min(target,self.turn+step)
        self.grounded=hero.grounded
        self.previous_phase=self.phase
        if hero.grounded or was_grounded:self.phase+=abs(hero.x-hero.px)/STRIDE
        self.landing=max(0.,self.landing-dt)
        if hero.grounded:
            if not was_grounded and self.last_vy>100:self.landing=.065
            state='land' if self.landing else ('run' if abs(hero.vx)>20 else 'idle')
        elif hero.floating:state='float'
        elif hero.vy< -80:state='rise'
        elif hero.vy<=80:state='apex'
        else:state='fall'
        changed=state!=self.state
        if changed:
            self.state=state
            self.elapsed=self.previous_elapsed=0.
        else:
            self.previous_elapsed=self.elapsed
        self.elapsed+=dt
        self.previous_rise=self.rise
        self.rise=max(0.,min(1.,1+hero.vy/790))
        if state=='rise' and changed:self.previous_rise=self.rise
        self.last_vy=hero.vy

    def turn_progress(self,alpha=1):
        return self.previous_turn+(self.turn-self.previous_turn)*max(0.,min(1.,alpha))

    def render_facing(self,alpha=1):
        # Turn sprites already rotate from right to left; do not mirror midway.
        return -1 if self.turn_progress(alpha)>=1-1e-9 else 1

    def sample(self,bank,alpha=1):
        alpha=max(0.,min(1.,alpha))
        rotation=self.turn_progress(alpha)
        key='turn_ground' if self.grounded else 'turn_air'
        if 1e-9<rotation<1-1e-9 and key in bank.clips:
            clip=bank.clips[key]
            return clip[min(len(clip)-1,int(rotation*len(clip)))]
        t=self.previous_elapsed+(self.elapsed-self.previous_elapsed)*alpha
        state=self.state
        if state=='run':
            clip=bank.clips['run']
            phase=self.previous_phase+(self.phase-self.previous_phase)*alpha
            return clip[int((phase%1)*len(clip)+1e-9)%len(clip)]
        if state=='idle':
            order=(0,1,2,3,2,1)
            return bank.clips['idle'][order[int(t*4+1e-9)%len(order)]]
        if state=='rise':
            progress=self.previous_rise+(self.rise-self.previous_rise)*alpha
            clip=bank.clips['rise']
            return clip[min(len(clip)-1,int(progress*len(clip)))]
        if state=='apex':return bank.clips['rise'][-1]
        clip=bank.clips[state]
        return clip[int(t*(16 if state=='float' else 8)+1e-9)%len(clip)]
