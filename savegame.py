"""Five private save slots: validated JSON and atomic replacement."""
import copy
import json
import math
import os
import tempfile
import tower_level
import greece_levels
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

VERSION=1
SLOT_COUNT=5
SKIP={
    'hero':{'contacts','drop_support','ignored_platform'},
    'energy':set(), 'solar':{'effect'}, 'rest':set(),
    'animation':{'solar','rest','hero'},'temple_exit':set(),'hero_death':set(),'resurrection':set(),
    'beetles':{'index','spawns'}, 'vultures':{'index','home'},
    'crocodiles':{'spawn_x','patrol_left','patrol_right','floor_left','floor_right','y','initial_facing'},
    'hoplites':{'spawn_x','patrol_left','patrol_right','floor_left','floor_right','y','initial_facing'},
    'obelisks':{'x','y'},'vases':{'index','center','floor'},
    'scorpions':{'index','spawn','left','right','y'},'laser_bolts':set(),
    'gyrospheres':{'index','home','route','plan_timer'},
}
STATES={
    'hero':{'landing_kind':{'land','land_medium','land_heavy'}},
    'beetles':{'state':{'patrol','chase','return'}},
    'vultures':{'state':{'patrol','warning','dive','pullup','return','death'}},
    'crocodiles':{key:{'patrol','turn','warning','lunge','recover','burn'} for key in ('state','previous_state','turn_next')},
    'hoplites':{key:{'patrol','turn','alert','chase','return','attack','dead'} for key in ('state','previous_state','turn_next')},
    'rest':{'state':{'awake','sitting','seated','rising'}},
    'hero_death':{'kind':{'crocodile','beetle','vulture','scorpion','gyrosphere','blade','sword','laser','fire','water','pit'}},
    'scorpions':{key:{'patrol','turn','charge','recoil','dead'} for key in ('state','previous_state')},
    'gyrospheres':{'state':{'idle','chase','dead'}},
}


def record(obj,kind):
    return {key:copy.deepcopy(value) for key,value in vars(obj).items() if key not in SKIP[kind]}


def platform_key(platform):
    return {key:getattr(platform,key) for key in ('x','y','w','kind')}


def resolve_platform(reference,level_id,platforms):
    if reference is None:return None
    if type(reference) is int:
        # Original saves used list indices, before the final rock and ledge
        # were removed. Resolve against that geometry, then match by identity.
        legacy=platforms
        if level_id==2:
            from main import Platform
            import desert_level as desert
            legacy=desert.build(Platform,rocks=desert.ROCKS+(desert.REMOVED_ROCK,),
                                ledges=desert.LEDGES+(desert.REMOVED_LEDGE,))[0]
        number(reference,0,len(legacy)-1,integer=True)
        reference=platform_key(legacy[reference])
    if not isinstance(reference,dict) or reference.keys()!={'x','y','w','kind'}:raise ValueError('Plateforme invalide')
    for key in ('x','y','w'):number(reference[key])
    match=next((p for p in platforms if platform_key(p)==reference),None)
    if match is None:
        import desert_level as desert
        from main import Platform
        legacy=desert.build(Platform,rocks=desert.ROCKS+(desert.REMOVED_ROCK,),
                            ledges=desert.LEDGES+(desert.REMOVED_LEDGE,))[0]
        removed=[platform_key(p) for p in legacy if (p.x,p.kind) in
                 ((desert.REMOVED_ROCK[0],'rock'),(desert.REMOVED_LEDGE[0],'stone'))]
        if level_id!=2 or reference not in removed:raise ValueError('Plateforme inconnue')
    return match


def capture(game):
    references={name:next((platform_key(p) for p in game.platforms if p is getattr(game.hero,name)),None)
                for name in ('drop_support','ignored_platform')}
    return {
        'level':game.level_id,'tower_layout':(tower_level.LAYOUT_VERSION if game.level_id==4 else 0),'lives':game.lives,'deaths':game.deaths,'elapsed':game.elapsed,
        'run_totals':copy.deepcopy(game.run_totals),
        'score':game.score,'level_score':game.level_score,'level_bonus_awarded':game.level_bonus_awarded,
        'camera':game.cam,'camera_y':game.cam_y,'invuln':game.invuln,'checkpoint':list(game.checkpoint),'check_index':game.check_index,
        'medallions':{'count':game.medallions.count,'claimed':sorted(game.medallions.claimed_levels)},
        'taken':sorted(game.taken),'dead_beetles':sorted(game.dead_beetles),'platform_refs':references,
        **{kind:record(getattr(game,attr),kind) for kind,attr in
           (('hero','hero'),('energy','energy'),('solar','solar'),('rest','rest'),('animation','hero_animation'),('temple_exit','temple_exit'),('hero_death','hero_death'),('resurrection','resurrection'))},
        **{kind:[record(obj,kind) for obj in getattr(game,attr)] for kind,attr in
           (('beetles','beetle_motions'),('vultures','vultures'),('crocodiles','crocodiles'),('hoplites','hoplites'),('obelisks','obelisks'),
            ('scorpions','scorpions'),('gyrospheres','gyrospheres'),('laser_bolts','laser_bolts'),('vases','vases'))},
    }


def number(value,low=-1e9,high=1e9,integer=False):
    if type(value) not in ((int,) if integer else (int,float)) or not math.isfinite(value) or not low<=value<=high:
        raise ValueError('Nombre invalide')


def indices(values,length):
    if not isinstance(values,list) or len(values)!=len(set(values)):raise ValueError('Liste invalide')
    for value in values:number(value,0,length-1,integer=True)


def validate_record(data,obj,kind):
    template=record(obj,kind)
    if not isinstance(data,dict) or data.keys()!=template.keys():raise ValueError('État incomplet')
    for key,default in template.items():
        value=data[key]
        if default is None:
            if value is None:continue
            if key in ('target','tail_root'):
                if not isinstance(value,(list,tuple)) or len(value)!=2:raise ValueError('Position invalide')
                for coordinate in value:number(coordinate)
            else:number(value,0)
        elif type(default) is bool:
            if type(value) is not bool:raise ValueError('Booléen invalide')
        elif isinstance(default,(int,float)):number(value)
        elif isinstance(default,str):
            allowed=STATES.get(kind,{}).get(key)
            if not isinstance(value,str) or len(value)>40 or (allowed and value not in allowed):raise ValueError('Animation invalide')
        else:raise ValueError('Type inconnu')
    for key in ('face','facing','previous_facing','turn_to','initial_facing'):
        if key in data and data[key] not in (-1,1):raise ValueError('Orientation invalide')
    if kind=='vultures':
        if data['dive_angle'] not in (15,30,45,60,75,90):raise ValueError('Angle invalide')
        if data['state']=='dive' and data['target'] is None:raise ValueError('Cible absente')
    if kind=='scorpions':
        for key in ('angle','previous_angle'):number(data[key],0,90)
        number(data['turn_from'],-1,1,integer=True)
        if data['turn_from']==0:raise ValueError('Orientation invalide')


def validate(data):
    # Construct lightweight physics models only; never create a display or touch
    # the current game until the whole file has passed validation.
    from main import Hero,level,HeroAnimator,WORLD,EXIT_MARGIN
    from beetle import BeetleMotion,SPAWNS
    from crocodile import Crocodile,create_crocodiles
    from hoplite import Hoplite,DEATH_TIME as HOPLITE_DEATH_TIME
    from vulture import Vulture,SPAWNS as VULTURES
    from obelisk import Obelisk,CHECKPOINT_X
    from solar import SolarRay
    from energy import SolarEnergy
    from rest import RestPose
    from scorpion import Scorpion,LaserBolt,SPAWNS as SCORPION_SPAWNS
    from gyrosphere import Gyrosphere,DEATH_TIME as GYRO_DEATH_TIME,SPEED as GYRO_SPEED
    import desert_level as desert
    import temple_level as temple
    import tower_level as tower
    from temple_exit import TempleExit,DURATION
    from hero_death import CrocodileDeath,DURATION as DEATH_DURATION,BEETLE_DURATION,BLADE_DURATION,LASER_LIMIT,FIRE_REACTION,WATER_DURATION,PIT_DURATION
    from resurrection import Resurrection,DURATION as RESURRECTION_DURATION,REAPPEAR
    from vase import Vase,SPAWNS as VASE_SPAWNS,BREAK_TIME
    required={'level','lives','deaths','elapsed','camera','invuln','checkpoint','check_index','medallions',
              'taken','dead_beetles','platform_refs','camera_y','tower_layout','run_totals',
              'score','level_score','level_bonus_awarded',*SKIP}
    if isinstance(data,dict) and 'hoplites' not in data:
        data=copy.deepcopy(data)
        config=greece_levels.LEVELS.get(data.get('level'))
        data['hoplites']=[record(Hoplite(*spawn),'hoplites') for spawn in getattr(config,'HOPLITES',())]
        # An older Greek slot may resume exactly where a newly added guard
        # spawns. Give that overlap the normal two-second reappearance grace.
        hero=data.get('hero',{})
        if (isinstance(hero,dict) and type(hero.get('x')) in (int,float)
                and type(hero.get('y')) in (int,float) and type(data.get('invuln')) in (int,float)
                and 0<=data['invuln']<=100):
            if any(abs(hero['x']-spawn[0])<80 and abs(hero['y']-spawn[5])<100
                   for spawn in getattr(config,'HOPLITES',())):
                data['invuln']=max(data['invuln'],2.)
    if isinstance(data,dict) and 'gyrospheres' not in data:
        data=copy.deepcopy(data)
        spawns=getattr({2:desert,3:temple,4:tower}.get(data.get('level')),'GYROSPHERES',())
        data['gyrospheres']=[record(Gyrosphere(i,spawns),'gyrospheres') for i in range(len(spawns))]
    elif isinstance(data,dict) and isinstance(data.get('gyrospheres'),list):
        spawns=getattr({2:desert,3:temple,4:tower}.get(data.get('level')),'GYROSPHERES',())
        old_count={2:0,3:0,4:3}.get(data.get('level'))
        if len(data['gyrospheres'])==old_count and len(spawns)>old_count:
            data=copy.deepcopy(data)
            data['gyrospheres'] += [record(Gyrosphere(i,spawns),'gyrospheres') for i in range(old_count,len(spawns))]
    if isinstance(data,dict) and not {'score','level_score','level_bonus_awarded'} & data.keys():
        data=copy.deepcopy(data)
        data.update(score=0,level_score=0,level_bonus_awarded=False)
    if isinstance(data,dict) and 'resurrection' not in data:
        data=copy.deepcopy(data);data['resurrection']=record(Resurrection(),'resurrection')
    if isinstance(data,dict) and 'hero_death' not in data:
        data=copy.deepcopy(data);data['hero_death']=record(CrocodileDeath(),'hero_death')
    if isinstance(data,dict) and isinstance(data.get('hero_death'),dict) and 'kind' not in data['hero_death']:
        data=copy.deepcopy(data);data['hero_death']['kind']='crocodile'
    if isinstance(data,dict) and isinstance(data.get('hero_death'),dict) and 'landed_at' not in data['hero_death']:
        data=copy.deepcopy(data);data['hero_death']['landed_at']=None
    if isinstance(data,dict) and 'run_totals' not in data:
        data=copy.deepcopy(data);data['run_totals']=dict(shards=0,elapsed=0.,deaths=0)
    if isinstance(data,dict) and 'tower_layout' not in data:
        data=copy.deepcopy(data);data['tower_layout']=1 if data.get('level')==4 else 0
    if isinstance(data,dict) and 'camera_y' not in data:
        data=copy.deepcopy(data);data['camera_y']=0.
    if isinstance(data,dict) and 'vases' not in data:
        data=copy.deepcopy(data)
        data['vases']=[record(Vase(i),'vases') for i in range(len(VASE_SPAWNS))] if data.get('level')==3 else []
    if isinstance(data,dict) and 'temple_exit' not in data:
        data=copy.deepcopy(data);data['temple_exit']=record(TempleExit(),'temple_exit')
    if isinstance(data,dict) and data.keys()==required-{'scorpions','laser_bolts'}:
        data=copy.deepcopy(data)
        data['scorpions']=[record(Scorpion(i),'scorpions') for i in range(len(SCORPION_SPAWNS))] if data['level']==3 else []
        data['laser_bolts']=[]
    if not isinstance(data,dict) or data.keys()!=required:raise ValueError('Sauvegarde incomplète')
    # The first pottery revision had four ground vases. Preserve their state
    # and add the three later platform vases without invalidating those slots.
    if data['level']==3 and isinstance(data['vases'],list) and len(data['vases'])==4:
        data=copy.deepcopy(data)
        data['vases'] += [record(Vase(i),'vases') for i in range(4,len(VASE_SPAWNS))]
    number(data['level'],1,8,integer=True);level_id=data['level']
    number(data['tower_layout'],1 if level_id==4 else 0,tower.LAYOUT_VERSION if level_id==4 else 0,integer=True)
    if level_id==4 and data['tower_layout']<tower.LAYOUT_VERSION:
        data=copy.deepcopy(data)
        if not isinstance(data['hero'],dict):raise ValueError('Héros invalide')
        old_guards=data['scorpions'];old_pots=data['vases']
        if not isinstance(old_guards,list) or len(old_guards) not in (0,3):raise ValueError('Scorpions incomplets')
        if not isinstance(old_pots,list) or len(old_pots) not in (0,len(tower.VASES)):raise ValueError('Vases incomplets')
        for i,value in enumerate(old_guards):validate_record(value,Scorpion(i,tower.SCORPIONS),'scorpions')
        for i,value in enumerate(old_pots):validate_record(value,Vase(i,tower.VASES),'vases')
        old_rows=100 if not old_pots else 95
        indices(data['taken'],205 if old_rows==100 else 237)
        rows={min(len(tower.LEDGES)-1,(index//2)*len(tower.LEDGES)//old_rows)
              for index in data['taken'] if index<old_rows*2}
        branches={(index-old_rows*2-5)//2 for index in data['taken'] if index>=old_rows*2+5}
        base=any(old_rows*2<=index<old_rows*2+3 for index in data['taken'])
        summit=any(old_rows*2+3<=index<old_rows*2+5 for index in data['taken'])
        data['taken']=[i for i,(kind,row,slot,gx,gy) in enumerate(tower.GEM_SITES)
                       if kind=='route' and row in rows or kind=='branch' and row in branches
                       or kind=='base' and base or kind=='summit' and summit]
        data['tower_layout']=tower.LAYOUT_VERSION
        old_y=data['hero'].get('y',tower.BASE_Y);number(old_y,-2000,tower.HEIGHT+1000)
        support=next(((x,y,w) for x,y,w in reversed(tower.LEDGES) if y>=old_y),None)
        x,y=(support[0]+support[2]/2,support[1]) if support else tower.START
        hero=Hero(x,y);hero.grounded=True
        data['hero']=record(hero,'hero');data['animation']=record(HeroAnimator(),'animation')
        data['solar']=record(SolarRay(),'solar');data['rest']=record(RestPose(),'rest')
        data['platform_refs']={'drop_support':None,'ignored_platform':None}
        data['camera_y']=tower.camera_target(y)
        number(data['check_index'],0,2,integer=True)
        data['checkpoint']=list(tower.START if data['check_index']==0 else
                                (tower.CHECKPOINTS[data['check_index']-1][0]-60,tower.CHECKPOINTS[data['check_index']-1][1]))
        data['scorpions']=[record(Scorpion(i,tower.SCORPIONS),'scorpions') for i in range(3)]
        data['vases']=[record(Vase(i,tower.VASES),'vases') for i in range(len(tower.VASES))]
        for i,value in enumerate(old_guards):
            if not value['alive']:data['scorpions'][i].update(alive=False,state='dead',previous_state='dead',death_timer=2.,previous_death_timer=2.)
        for i,value in enumerate(old_pots):
            if value['broken']:data['vases'][i].update(broken=True,age=BREAK_TIME,previous_age=BREAK_TIME)
        data['beetles']=[record(BeetleMotion(i,spawns=tower.BEETLES),'beetles') for i in range(len(tower.BEETLES))]
    if not isinstance(data['hero_death'],dict):raise ValueError('Mort invalide')
    number(data['lives'],0 if data['hero_death'].get('active') is True else 1,99,integer=True);number(data['deaths'],0,100000,integer=True)
    number(data['elapsed'],0);number(data['invuln'],0,100)
    number(data['score'],0,10**12,integer=True)
    number(data['level_score'],0,data['score'],integer=True)
    if type(data['level_bonus_awarded']) is not bool:raise ValueError('Bonus invalide')
    totals=data['run_totals']
    if not isinstance(totals,dict) or totals.keys()!={'shards','elapsed','deaths'}:raise ValueError('Bilan invalide')
    number(totals['shards'],0,100000,integer=True);number(totals['deaths'],0,100000,integer=True)
    number(totals['elapsed'],0)
    config={2:desert,3:temple,4:tower,**greece_levels.LEVELS}.get(level_id)
    length=config.LENGTH if config else WORLD
    number(data['camera'],0,0 if level_id==4 else length)
    number(data['camera_y'],-240 if level_id==8 else 0,tower.HEIGHT-720 if level_id==4 else 0)
    platforms,gems=level(level_id)
    homes=config.BEETLES if config else SPAWNS
    birds=config.VULTURES if config else VULTURES
    gyro_spawns=getattr(config,'GYROSPHERES',())
    models={'hero':Hero(),'energy':SolarEnergy(),'solar':SolarRay(),'rest':RestPose(),'animation':HeroAnimator(),'temple_exit':TempleExit(),'hero_death':CrocodileDeath(),'resurrection':Resurrection(),
            'beetles':[BeetleMotion(i,spawns=homes) for i in range(len(homes))],
            'vultures':[Vulture(i,birds) for i in range(len(birds))],
            'gyrospheres':[Gyrosphere(i,gyro_spawns) for i in range(len(gyro_spawns))],
            'crocodiles':[Crocodile(*spawn) for spawn in config.CROCODILES] if config else create_crocodiles(),
            'hoplites':[Hoplite(*spawn) for spawn in getattr(config,'HOPLITES',())],
            'obelisks':([Obelisk(x,y) for x,y in config.CHECKPOINTS] if level_id>=4 else
                        [Obelisk(x) for x in (config.CHECKPOINTS if config else (CHECKPOINT_X,))]),
            'scorpions':([Scorpion(i,tower.SCORPIONS) for i in range(3)] if level_id==4 else
                         [Scorpion(i) for i in range(len(SCORPION_SPAWNS))] if level_id==3 else
                         [Scorpion(i,config.SCORPIONS) for i in range(len(config.SCORPIONS))] if level_id>=5 else []),
            'vases':([Vase(i,tower.VASES) for i in range(len(tower.VASES))] if level_id==4 else
                     [Vase(i) for i in range(len(VASE_SPAWNS))] if level_id==3 else [])}
    for kind,model in models.items():
        if isinstance(model,list):
            values=data[kind]
            if not isinstance(values,list) or len(values)!=len(model):raise ValueError('Ennemis incomplets')
            for value,obj in zip(values,model):validate_record(value,obj,kind)
        else:validate_record(data[kind],model,kind)
    revival=data['resurrection']
    number(revival['elapsed'],0,RESURRECTION_DURATION);number(revival['previous_elapsed'],0,revival['elapsed'])
    number(revival['life_index'],0,5,integer=True)
    if revival['active']:
        if data['hero_death']['active'] or data['lives']<1 or data['deaths']<1:raise ValueError('Résurrection invalide')
        if revival['spawned']!=(revival['elapsed']>=REAPPEAR-1e-9):raise ValueError('Résurrection incohérente')
    death=data['hero_death']
    electrical=death['kind'] in ('beetle','vulture','scorpion','gyrosphere')
    number(death['elapsed'],0,PIT_DURATION if death['kind']=='pit' else WATER_DURATION if death['kind']=='water' else LASER_LIMIT if death['kind'] in ('laser','fire','sword') else BLADE_DURATION if death['kind']=='blade' else BEETLE_DURATION if electrical else DEATH_DURATION)
    number(death['previous_elapsed'],0,death['elapsed'])
    for key in ('facing','source_face','hero_face'):
        if death[key] not in (-1,1):raise ValueError('Orientation de mort invalide')
    for key in ('x','hero_x'):number(death[key],-100,length+EXIT_MARGIN+100)
    for key in ('y','hero_y'):number(death[key],-2000,15000)
    if death['landed_at'] is not None:
        number(death['landed_at'],FIRE_REACTION if death['kind']=='fire' else .28,death['elapsed'])
        if death['kind'] not in ('laser','fire','sword'):raise ValueError('Atterrissage de mort invalide')
    if death['kind']=='water':
        if level_id!=2 or not desert.RIVER[0]<=death['x']<=desert.RIVER[1] or death['y']!=desert.WATER_Y:raise ValueError('Noyade invalide')
    maximum=(0 if death['kind'] in ('blade','laser','fire','water','pit') else len(models['beetles'])-1 if death['kind']=='beetle' else
             len(models['vultures'])-1 if death['kind']=='vulture' else
             len(models['scorpions'])-1 if death['kind']=='scorpion' else
             len(models['gyrospheres'])-1 if death['kind']=='gyrosphere' else 2)
    if death['kind']=='sword':maximum=len(models['hoplites'])-1
    number(death['index'],0,maximum,integer=True)
    if death['active']:
        if death['kind']=='beetle':
            indices(data['dead_beetles'],len(homes))
            if death['index'] in data['dead_beetles']:raise ValueError('Scarabée invalide')
        elif death['kind']=='vulture':
            if not data['vultures'][death['index']]['alive']:raise ValueError('Vautour invalide')
        elif death['kind']=='scorpion':
            if not data['scorpions'][death['index']]['alive']:raise ValueError('Scorpion invalide')
        elif death['kind']=='gyrosphere':
            if not data['gyrospheres'][death['index']]['alive']:raise ValueError('Gyrosphère invalide')
        elif death['kind']=='sword':
            if not data['hoplites'][death['index']]['alive']:raise ValueError('Hoplite invalide')
        elif death['kind']=='crocodile' and (death['index']>=len(models['crocodiles']) or not data['crocodiles'][death['index']]['alive']):raise ValueError('Crocodile invalide')
        if data['lives']==0 and data['deaths']==0:raise ValueError('Mort invalide')
    for vase in data['vases']:
        for key in ('age','previous_age'):number(vase[key],0,BREAK_TIME)
    for guard,spawn in zip(data['hoplites'],getattr(config,'HOPLITES',())):
        for key in ('x','px'):number(guard[key],spawn[3]+32,spawn[4]-32)
        for key in ('death_timer','previous_death_timer'):number(guard[key],0,HOPLITE_DEATH_TIME)
        number(guard['timer'],0);number(guard['previous_timer'],0)
        number(guard['lost'],0);number(guard['distance'],0);number(guard['previous_distance'],0)
        if guard['alive']!=(guard['state']!='dead'):raise ValueError('Hoplite incohérent')
    for orb in data['gyrospheres']:
        for key in ('x','px'):number(orb[key],50 if level_id==4 else -100,1230 if level_id==4 else length+100)
        for key in ('y','py'):number(orb[key],-100,tower.HEIGHT+100 if level_id==4 else 900)
        for key in ('vx','vy'):number(orb[key],-GYRO_SPEED,GYRO_SPEED)
        for key in ('death_timer','previous_death_timer'):number(orb[key],0,GYRO_DEATH_TIME)
        if orb['facing'] not in (-1,1):raise ValueError('Orientation de gyrosphère invalide')
        if orb['previous_death_timer']>orb['death_timer']:raise ValueError('Explosion de gyrosphère invalide')
        if orb['alive']!=(orb['state']!='dead'):raise ValueError('Gyrosphère incohérente')
    ending=data['temple_exit']
    for key in ('elapsed','previous_elapsed'):number(ending[key],0,DURATION)
    number(ending['start_x'],0,14600);number(ending['start_y'],-2000,1000)
    if ending['active'] and level_id!=3:raise ValueError('Fin de temple invalide')
    bolts=data['laser_bolts']
    if not isinstance(bolts,list) or len(bolts)>64 or (level_id not in (3,4,6,7,8) and bolts):raise ValueError('Projectiles invalides')
    for bolt in bolts:
        validate_record(bolt,LaserBolt(0.,0.,1.,0.),'laser_bolts')
        number(bolt['age'],0,2.5);number(bolt['vy'],-2000,0)
        number(math.hypot(bolt['vx'],bolt['vy']),1,2000)
    for key in ('state','landing_clip'):
        allowed={'land','land_medium','land_heavy'}
        if key=='state':allowed|={'idle','run','rise','apex','fall','float','rest','drop','crouch','solar_ground','solar_air','solar_crouch'}
        if data['animation'][key] not in allowed:raise ValueError('Animation inconnue')
    for key in ('rise','previous_rise','turn','previous_turn'):number(data['animation'][key],0,1)
    number(data['hero']['x'],-100,length+EXIT_MARGIN+100)
    falling_death=(death['active'] or revival['active'] and not revival['spawned']) and (electrical or death['kind'] in ('blade','sword','laser','fire','pit'))
    number(data['hero']['y'],-2000,(tower.HEIGHT if level_id==4 else 0)+(2000 if falling_death else 1000))
    number(data['energy']['value'],0,100)
    for key in ('crouch','previous_crouch'):number(data['hero'][key],0,1)
    number(data['rest']['progress'],0,1);number(data['rest']['previous_progress'],0,1)
    indices(data['taken'],len(gems));indices(data['dead_beetles'],len(homes))
    medals=data['medallions']
    if not isinstance(medals,dict) or medals.keys()!={'count','claimed'}:raise ValueError('Inventaire invalide')
    number(medals['count'],0,3,integer=True);indices(medals['claimed'],9)
    if 0 in medals['claimed']:raise ValueError('Niveau invalide')
    number(data['check_index'],0,len(models['obelisks']),integer=True)
    checkpoint=data['checkpoint']
    if not isinstance(checkpoint,(list,tuple)) or len(checkpoint)!=2:raise ValueError('Reprise invalide')
    number(checkpoint[0],0,length);number(checkpoint[1],-2000,tower.HEIGHT+200 if level_id==4 else 720)
    refs=data['platform_refs']
    if not isinstance(refs,dict) or refs.keys()!={'drop_support','ignored_platform'}:raise ValueError('Plateforme invalide')
    for reference in refs.values():resolve_platform(reference,level_id,platforms)
    return data


def restore(game,data):
    from scorpion import LaserBolt
    data=validate(data)
    game.start_level(data['level'])
    for kind,attr in (('hero','hero'),('energy','energy'),('solar','solar'),('rest','rest'),('animation','hero_animation'),('temple_exit','temple_exit'),('hero_death','hero_death'),('resurrection','resurrection')):
        vars(getattr(game,attr)).update(copy.deepcopy(data[kind]))
    for kind,attr in (('beetles','beetle_motions'),('vultures','vultures'),('crocodiles','crocodiles'),('hoplites','hoplites'),('obelisks','obelisks'),('scorpions','scorpions'),('gyrospheres','gyrospheres'),('vases','vases')):
        for obj,values in zip(getattr(game,attr),data[kind]):vars(obj).update(copy.deepcopy(values))
    game.laser_bolts=[LaserBolt(**values) for values in data['laser_bolts']]
    for name,reference in data['platform_refs'].items():
        setattr(game.hero,name,resolve_platform(reference,data['level'],game.platforms))
    if data['platform_refs']['drop_support'] is not None and game.hero.drop_support is None:
        game.hero.drop_elapsed=None;game.hero.drop_jump_latched=False;game.hero.grounded=False
    game.hero_animation.hero=game.hero;game.hero_animation.solar=game.solar;game.hero_animation.rest=game.rest
    game.lives=data['lives'];game.deaths=data['deaths'];game.elapsed=game.previous_elapsed=data['elapsed']
    game.run_totals=copy.deepcopy(data['run_totals'])
    game.score=data['score'];game.level_score=data['level_score'];game.level_bonus_awarded=data['level_bonus_awarded']
    game.cam=game.prev_cam=data['camera'];game.cam_y=game.prev_cam_y=data['camera_y'];game.invuln=data['invuln']
    game.checkpoint=tuple(data['checkpoint']);game.check_index=data['check_index']
    game.medallions.count=data['medallions']['count'];game.medallions.claimed_levels=set(data['medallions']['claimed'])
    game.taken=set(data['taken']);game.dead_beetles=set(data['dead_beetles'])


@dataclass
class Slot:
    status:str='empty'
    timestamp:str=''
    data:dict|None=None


class SaveSlots:
    def __init__(self,directory=None):
        self.directory=Path(directory) if directory is not None else None
        self.memory={}

    def path(self,index):
        if type(index) is not int or not 0<=index<SLOT_COUNT:raise ValueError('Emplacement invalide')
        return self.directory/f'slot-{index+1}.json' if self.directory else None

    def read(self,index):
        path=self.path(index)
        try:
            if path:
                if path.stat().st_size>512*1024:raise ValueError('Fichier trop volumineux')
                document=json.loads(path.read_text(encoding='utf-8'))
            else:
                if index not in self.memory:return Slot()
                document=copy.deepcopy(self.memory[index])
            if not isinstance(document,dict):raise ValueError('Format invalide')
            if type(document.get('version')) is not int or document['version']!=VERSION:return Slot('incompatible')
            stamp=document['saved_at'];date=datetime.fromisoformat(stamp)
            if date.tzinfo is None:raise ValueError('Date invalide')
            return Slot('ready',stamp,validate(document['game']))
        except FileNotFoundError:return Slot()
        except (OSError,ValueError,TypeError,KeyError,OverflowError,RecursionError):return Slot('corrupt')

    def list(self):return [self.read(index) for index in range(SLOT_COUNT)]

    def write(self,index,data):
        path=self.path(index);validate(data)
        document={'version':VERSION,'saved_at':datetime.now().astimezone().isoformat(timespec='seconds'),'game':data}
        encoded=json.dumps(document,ensure_ascii=False,allow_nan=False,indent=2)+'\n'
        if path is None:self.memory[index]=json.loads(encoded);return
        temporary=None
        try:
            path.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=path.parent,prefix=path.name+'.',suffix='.tmp',delete=False) as stream:
                temporary=Path(stream.name);stream.write(encoded);stream.flush();os.fsync(stream.fileno())
            temporary.replace(path)
        finally:
            if temporary is not None:
                try:temporary.unlink(missing_ok=True)
                except OSError:pass
