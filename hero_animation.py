"""Preloaded hero poses, sampled on the same fixed-step timeline as movement."""
from dataclasses import dataclass
import json
import math
from pathlib import Path
import pygame as pg
from solar import SHOT_TIME

CELL=120
STRIDE=136.0  # world units per complete left/right cycle: 0.4 s at full speed
TURN_TIME=.16
CROUCH_TIME=.24
LAND_TIME=.24
DROP_TIME=.36
DROP_RELEASE=.18
MEDIUM_FALL_HEIGHT=160.
HEAVY_FALL_HEIGHT=280.
LAND_DURATIONS={'land':LAND_TIME,'land_medium':.32,'land_heavy':.60}


def landing_clip(height):
    if height>=HEAVY_FALL_HEIGHT:return 'land_heavy'
    if height>=MEDIUM_FALL_HEIGHT:return 'land_medium'
    return 'land'


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


def load_sheet(path,columns,rows,pivot=(.53,.96),pivots=None,align_floor=False):
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
        floor=frame.get_bounding_rect(min_alpha=32).bottom-1 if align_floor else round(anchor[1]*CELL)
        poses.append(Pose((frame,pg.transform.flip(frame,True,False)),
                          (round(anchor[0]*CELL),floor)))
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
    landing=directory/'hero-land-v1.png'
    if landing.exists():clips['land']=load_sheet(landing,4,2,pivot=(.54,.96),align_floor=True)
    for name,filename,rows in (
        ('drop','hero-drop-v1.png',3),
        ('solar_ground','hero-solar-ground-v1.png',2),
        ('solar_air','hero-solar-air-v2.png',2),
        ('crouch','hero-crouch-v1.png',2),
        ('land_medium','hero-land-medium-v2.png',2),
        ('land_heavy','hero-land-heavy-v1.png',3)):
        path=directory/filename
        if path.exists():clips[name]=load_sheet(path,4,rows,pivot=(.54,.96),align_floor=name!='solar_air')
    crouch_fire=directory/'hero-solar-crouch-v1.png'
    if crouch_fire.exists():
        # The authored crouch attack uses a larger common source scale.
        # Correct the whole clip uniformly, never resize individual silhouettes.
        poses=load_sheet(crouch_fire,4,2,pivot=(.54,.96),align_floor=True)
        clips['solar_crouch']=[]
        for pose in poses:
            image=pg.transform.smoothscale(pose.images[0],(102,102))
            frame=pg.Surface((CELL,CELL),pg.SRCALPHA)
            pivot=(round(.54*CELL),CELL-1)
            frame.blit(image,(pivot[0]-round(pose.pivot[0]*.85),pivot[1]-round(pose.pivot[1]*.85)))
            clips['solar_crouch'].append(Pose((frame,pg.transform.flip(frame,True,False)),pivot))
    pivots=[(.5+.04*math.cos(math.pi*i/7),.96) for i in range(8)]
    for mode in ('ground','air'):
        path=directory/f'hero-turn-{mode}.png'
        if path.exists():clips[f'turn_{mode}']=load_sheet(path,4,2,pivots=pivots)
    lower=directory/'hero-rest-lower-v2.png';seated=directory/'hero-rest-seated-v1.png'
    if lower.exists() and seated.exists():
        clips['rest']=load_rest_sheet(lower)+load_rest_sheet(seated,.8)
    return AnimationBank(clips)


def load_rest_sheet(path,scale=1.):
    """The authored row gutters vary; keep one common source scale per atlas."""
    sheet=pg.image.load(str(path)).convert_alpha();poses=[]
    rows=(0,304,586,840,sheet.get_height())
    source_scale=CELL/(sheet.get_width()/6)*scale
    for row in range(4):
        for col in range(6):
            x0,x1=round(col*sheet.get_width()/6),round((col+1)*sheet.get_width()/6)
            cell=sheet.subsurface((x0,rows[row],x1-x0,rows[row+1]-rows[row]))
            image=pg.transform.smoothscale(cell,(round(cell.get_width()*source_scale),round(cell.get_height()*source_scale)))
            bounds=image.get_bounding_rect(min_alpha=32)
            if not bounds.w:raise ValueError(f'{path.name}: pose de repos vide')
            frame=pg.Surface((CELL,CELL),pg.SRCALPHA)
            pivot=(round(.59*CELL),CELL-1)
            frame.blit(image,(pivot[0]-round(.59*image.get_width()),pivot[1]-bounds.bottom+1))
            poses.append(Pose((frame,pg.transform.flip(frame,True,False)),pivot))
    return poses


class HeroAnimator:
    def __init__(self):self.reset()

    def reset(self):
        self.state='idle'
        self.phase=self.previous_phase=0.
        self.elapsed=self.previous_elapsed=0.
        self.rise=self.previous_rise=0.
        self.landing=0.
        self.landing_clip='land'
        self.last_vy=0.
        self.last_floating=False
        self.turn=self.previous_turn=0.
        self.grounded=True
        self.solar=None
        self.rest=None
        self.hero=None

    def update(self,dt,hero,was_grounded,solar=None,rest=None):
        self.hero=hero
        self.solar=solar
        self.rest=rest
        self.previous_turn=self.turn
        target=0. if getattr(hero,'face',1)>0 else 1.
        step=dt/TURN_TIME
        self.turn=max(target,self.turn-step) if self.turn>target else min(target,self.turn+step)
        self.grounded=hero.grounded
        self.previous_phase=self.phase
        if hero.grounded or was_grounded:self.phase+=abs(hero.x-hero.px)/STRIDE
        self.landing=max(0.,self.landing-dt)
        if self.landing<1e-9:self.landing=0.
        if rest is not None and rest.active:
            state='rest';self.landing=0.
        elif solar is not None and solar.active:
            state=('solar_crouch' if getattr(solar,'crouched',False) else 'solar_ground') if hero.grounded else 'solar_air'
        elif getattr(hero,'drop_elapsed',None) is not None:
            state='drop';self.landing=0.
        elif hero.grounded and getattr(hero,'crouch',0)>0:
            state='crouch';self.landing=0.
        elif hero.grounded:
            impact=getattr(hero,'impact_vy',self.last_vy)
            gliding=getattr(hero,'landed_gliding',self.last_floating)
            if not was_grounded and impact>100 and not gliding:
                self.landing_clip=getattr(hero,'landing_kind','land')
                self.landing=LAND_DURATIONS[self.landing_clip]
            state=self.landing_clip if self.landing else ('run' if abs(hero.vx)>20 else 'idle')
        elif hero.floating:state='float'
        elif hero.vy< -80:state='rise'
        elif hero.vy<=80:state='apex'
        else:state='fall'
        if not hero.grounded:self.landing=0.
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
        self.last_floating=hero.floating

    def turn_progress(self,alpha=1):
        return self.previous_turn+(self.turn-self.previous_turn)*max(0.,min(1.,alpha))

    def render_facing(self,alpha=1):
        if self.state=='rest' and self.rest is not None:return self.rest.facing
        if self.state.startswith('solar_') and self.solar is not None and self.solar.active:return self.solar.facing
        if self.state=='crouch':return self.hero.face
        if self.state in LAND_DURATIONS or self.state=='drop':return -1 if self.turn_progress(alpha)>=.5 else 1
        # Turn sprites already rotate from right to left; do not mirror midway.
        return -1 if self.turn_progress(alpha)>=1-1e-9 else 1

    def sample(self,bank,alpha=1):
        alpha=max(0.,min(1.,alpha))
        t=self.previous_elapsed+(self.elapsed-self.previous_elapsed)*alpha
        if self.state=='rest' and self.rest is not None:
            return self.rest.sample(bank.clips.get('rest',bank.clips['idle']),alpha)
        if self.state=='crouch':
            progress=self.hero.previous_crouch+(self.hero.crouch-self.hero.previous_crouch)*alpha
            clip=bank.clips.get('crouch',bank.clips['idle'])
            return clip[min(len(clip)-1,round(progress*(len(clip)-1)))]
        if self.state.startswith('solar_'):
            if self.solar is None or not self.solar.active:
                return bank.clips['idle' if self.grounded else 'fall'][0]
            t=self.solar.previous_elapsed+(self.solar.elapsed-self.solar.previous_elapsed)*alpha
            clip=bank.clips.get(self.state,bank.clips['fall'])
            return clip[min(len(clip)-1,int(t/SHOT_TIME*len(clip)))]
        if self.state=='drop':
            clip=bank.clips.get('drop',bank.clips['fall'])
            return clip[min(len(clip)-1,int(t/DROP_TIME*len(clip)))]
        if self.state in LAND_DURATIONS:
            clip=bank.clips.get(self.state,bank.clips['land'])
            return clip[min(len(clip)-1,int(t/LAND_DURATIONS[self.state]*len(clip)))]
        rotation=self.turn_progress(alpha)
        key='turn_ground' if self.grounded else 'turn_air'
        if 1e-9<rotation<1-1e-9 and key in bank.clips:
            clip=bank.clips[key]
            return clip[min(len(clip)-1,int(rotation*len(clip)))]
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
