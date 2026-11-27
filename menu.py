"""Egyptian start, pause and settings menus, with one navigation model."""
import pygame as pg
from datetime import datetime
from gpu_render import draw
from localization import LANGUAGES,CODES
from language_flags import LanguageFlags
from bezel_catalog import MODES as BEZEL_MODES,LABELS as BEZEL_LABELS

GOLD=(237,194,105)
WHITE=(246,236,210)
MUTED=(174,191,191)
PAGES=('title','settings','controls','pause','save','load','overwrite','languages','bezels')
LABELS={
    'title':('Jouer','Configuration','Charger une partie','Quitter'),
    'pause':('Reprendre','Configuration','Sauvegarder','Menu principal','Quitter'),
    'settings':('Affichage','Effets sonores','Vibrations manette','Compteur FPS','Commandes','Langue','Musique des menus','Cadre d’écran','Retour'),
    'bezels':(*BEZEL_LABELS,'Retour'),
    'controls':('Retour',),
    'save':tuple(f'Emplacement {i+1}' for i in range(5))+('Retour',),
    'load':tuple(f'Emplacement {i+1}' for i in range(5))+('Retour',),
    'overwrite':('Écraser cette sauvegarde','Annuler'),
    'languages':tuple(name for code,name in LANGUAGES)+('Retour',),
}
CONTROL_ROWS=(
    ('Se déplacer','← → / Q D','Stick gauche / croix'),
    ('Sauter / planer','Espace / ↑','A / croix haut'),
    ('Descendre d’une plateforme','Bas + saut','Bas + A'),
    ('S’accroupir','Bas / S','Stick / croix bas'),
    ('Rayon solaire','F','RT / B'),
    ('Pause','Échap','Start'),
)


class StartMenu:
    def __init__(self,assets):
        self.flags=LanguageFlags()
        self.selected={page:0 for page in PAGES}
        self.origin='title';self.direction=(0,0);self.next_repeat=0.
        self.volume_drag=None
        self.save_failed=False
        self.slots=[];self.slot_index=0;self.message=''
        self.code='';self.code_time=0.
        self.code_level=2
        self.shade=pg.Surface((1920,1080),pg.SRCALPHA)
        for x in range(1920):
            alpha=round(235-140*min(1,x/1600))
            pg.draw.line(self.shade,(7,23,31,alpha),(x,0),(x,1080))
        sheet=pg.image.load(str(assets/'hero-atlas-v2.png')).convert_alpha()
        y=round(sheet.get_height()*.465)
        cell=sheet.subsurface((0,y,sheet.get_width()//4,sheet.get_height()-y))
        image=cell.subsurface(cell.get_bounding_rect(min_alpha=32))
        self.hero=pg.transform.smoothscale(image,(round(image.get_width()*620/image.get_height()),620))

    @property
    def images(self):return [self.shade,self.hero,self.flags.atlas]

    def enter(self,page):
        self.volume_drag=None
        self.direction=(0,0);self.next_repeat=0.
        self.code=''
        self.message=''

    def refresh_slots(self,game):
        self.slots=game.saves.list()
        self.slot_rows=[self.slot_text(index) for index in range(5)]
        for header,detail,date in self.slot_rows:
            for color in (GOLD,WHITE):game.cache_text(header,17,color)
            game.cache_text(detail,12,MUTED)
            if date:game.cache_text(date,13,GOLD)
        for color in (GOLD,WHITE):game.cache_text('Retour',20,color)

    def slot_text(self,index):
        slot=self.slots[index]
        if slot.status!='ready':
            detail={'empty':'Case vide','corrupt':'Fichier illisible ou endommagé','incompatible':'Version de sauvegarde incompatible'}[slot.status]
            return f'Emplacement {index+1}',detail,''
        data=slot.data;level=data['level']
        # Get the actual collectible count from level geometry, without loading art.
        from main import level as geometry
        total=len(geometry(level)[1])
        from greece_levels import LEVELS
        duration=int(data['elapsed']);length=LEVELS[level].LENGTH if level in LEVELS else 9600 if level==1 else 14400
        if level==4:
            from tower_level import progress as ascent_progress
            progress=ascent_progress(data['hero']['y'])
        else:progress=max(0,min(100,round(data['hero']['x']/length*100)))
        header=f'Emplacement {index+1} · Niveau {level:02} · {data["lives"]} vies'
        detail=(f'Parcours {progress} % · Éclats {len(data["taken"])}/{total} · Médaillons {data["medallions"]["count"]}/3'
                f' · Énergie {round(data["energy"]["value"])} % · Temps {duration//60:02}:{duration%60:02}')
        date=datetime.fromisoformat(slot.timestamp).astimezone().strftime('%d/%m/%Y  %H:%M:%S')
        return header,detail,date

    def feed_code(self,text,now):
        if now-self.code_time>8:self.code=''
        self.code_time=now
        for character in text.upper():
            self.code=(self.code+character)[-4:]
            codes=tuple(f'LV{i:02}' for i in range(2,9))
            while self.code and not any(code.startswith(self.code) for code in codes):self.code=self.code[1:]
            if self.code in codes:
                self.code_level=int(self.code[-1]);self.code='';return True
        return False

    def rectangles(self,page):
        if page=='languages':
            return [pg.Rect(108+i%2*540,258+i//2*33,520,30) for i in range(len(LANGUAGES))]+[pg.Rect(108,608,280,42)]
        if page in ('save','load'):return [pg.Rect(108,268+i*59,1060,52) for i in range(6)]
        if page=='controls':return [pg.Rect(108,596,280,48)]
        if page=='settings':return [pg.Rect(108,270+i*42,760,38) for i in range(9)]
        if page=='bezels':return [pg.Rect(108,280+i*58,760,48) for i in range(6)]
        start=322 if page=='pause' else 336 if page=='title' else 350
        step=60 if page in ('pause','title') else 66
        return [pg.Rect(108,start+i*step,460,54) for i in range(len(LABELS[page]))]

    def move(self,page,direction):
        if page=='languages':
            index=self.selected[page]
            if index==len(CODES):self.selected[page]=len(CODES)-2 if direction<0 else 0
            else:
                target=index+direction*2
                self.selected[page]=target if 0<=target<len(CODES) else len(CODES)
            return
        self.selected[page]=(self.selected[page]+direction)%len(LABELS[page])

    def pointer(self,page,position):
        for index,rect in enumerate(self.rectangles(page)):
            if rect.collidepoint(position):
                self.selected[page]=index;return True
        return False

    def volume_gauge(self,index):
        rect=self.rectangles('settings')[index]
        return pg.Rect(rect.x+580,rect.y+19,96,5)

    def click_volume(self,game,position):
        if game.state!='settings':return False
        for index,kind in ((1,'sound'),(6,'music')):
            gauge=self.volume_gauge(index)
            if gauge.inflate(2,30).collidepoint(position):
                self.selected['settings']=index
                self.volume_drag=index
                game.set_volume(kind,round((position[0]-gauge.left)/gauge.width*100))
                return True
        return False

    def drag_volume(self,game,position):
        if self.volume_drag is None or game.state!='settings':return False
        index=self.volume_drag;gauge=self.volume_gauge(index)
        self.selected['settings']=index
        game.set_volume('sound' if index==1 else 'music',
                        round((position[0]-gauge.left)/gauge.width*100),persist=False)
        return True

    def end_volume_drag(self,game):
        if self.volume_drag is not None:
            self.volume_drag=None
            game.save_settings()

    def pad_move(self,page,vertical,horizontal,now):
        direction=(vertical,horizontal)
        if direction==(0,0):self.direction=direction;return False
        changed=direction!=self.direction
        if not changed and now<self.next_repeat:return False
        self.direction=direction;self.next_repeat=now+(.32 if changed else .13)
        if vertical:self.move(page,vertical)
        return not vertical and bool(horizontal) and changed

    def values(self,game):
        return ('Plein écran' if game.fullscreen else 'Fenêtre',
                f'{game.settings.sound_volume if game.sound_on else 0} %',
                'Activées' if game.gamepads.rumble_enabled else 'Coupées',
                'Affiché' if game.show_fps else 'Masqué','',dict(LANGUAGES)[game.settings.language],
                f'{game.settings.music_volume if game.settings.music else 0} %',
                BEZEL_LABELS[BEZEL_MODES.index(game.settings.bezel)],'')

    def prepare(self,game):
        # Preload both choices, all rows and both highlight colors before play.
        labels=[label for rows in LABELS.values() for label in rows]
        for label in labels:
            for color in (WHITE,GOLD):game.cache_text(label,22,color)
        for value in ('Plein écran','Fenêtre','Activés','Coupés','Activées','Coupées','Activée','Coupée','Affiché','Masqué'):
            game.cache_text(value,17,GOLD)
        for value in range(101):game.cache_text(f'{value} %',17,GOLD)
        for label in BEZEL_LABELS:game.cache_text(label,17,GOLD)
        for code,name in LANGUAGES:
            for color in (GOLD,WHITE):game.cache_text(name,19,color)
        self.refresh_slots(game)
        for page in PAGES:self.draw(game,page)
        game.cache_text('Impossible d’enregistrer les réglages.',12,GOLD)
        game.cache_text('MANETTE CONNECTÉE',12,GOLD)
        game.cache_text('Manette déconnectée. Rebranchez-la ou reprenez au clavier.',17,MUTED)

    def draw(self,game,page=None):
        page=page or game.state
        game.canvas.blit_native(self.shade,(0,0))
        game.text('LES SABLES D’HORUS',(110,88),14,GOLD)
        if page=='title':
            game.text('JUMPING JACK',(104,152),62,WHITE,True)
            game.text('Un saut vers les dieux. Une cape contre le vent.',(110,248),17,MUTED)
            draw.line(game.canvas,GOLD,(110,299),(230,299),2)
            game.canvas.blit_native(self.hero,(970,670),'midbottom')
            game.text('01  /  LE SEUIL DU DÉSERT',(110,600),12,GOLD)
            game.text('Trois vies. Un désert à traverser.',(110,626),16,MUTED)
        elif page=='pause':
            game.text('PAUSE',(104,155),58,WHITE,True)
            message='Manette déconnectée. Rebranchez-la ou reprenez au clavier.' if game.controller_lost else 'L’aventure vous attend.'
            game.text(message,(110,247),17,MUTED)
        elif page=='languages':
            game.text('LANGUE',(108,156),42,WHITE,True,max_width=1040)
            game.text('Le changement est immédiat et conservé.',(110,222),17,MUTED,max_width=1040)
            for index,rect in enumerate(self.rectangles(page)):
                selected=index==self.selected[page]
                draw.rect(game.canvas,(34,52,58) if selected else (15,34,42),rect)
                if selected:draw.rect(game.canvas,GOLD,rect,1)
                if index==len(LANGUAGES):
                    game.text('Retour',(rect.x+20,rect.y+8),20,GOLD if selected else WHITE)
                else:
                    code,name=LANGUAGES[index]
                    self.flags.draw(game.canvas,code,(rect.x+16,rect.y+5))
                    game.text(name,(rect.x+62,rect.y+4),19,GOLD if selected else WHITE,max_width=390)
                    if code==game.settings.language:
                        draw.line(game.canvas,GOLD,(rect.right-29,rect.y+17),(rect.right-24,rect.y+22),2)
                        draw.line(game.canvas,GOLD,(rect.right-24,rect.y+22),(rect.right-14,rect.y+10),2)
            if self.save_failed:game.text('Impossible d’enregistrer les réglages.',(110,648),12,GOLD,max_width=1060)
            game.text('↑ ↓ / Stick  Choisir     Entrée / A  Valider     Échap / B  Retour',(110,674),13,MUTED,max_width=1060)
            return
        elif page in ('save','load'):
            game.text('SAUVEGARDER' if page=='save' else 'CHARGER UNE PARTIE',(108,156),40,WHITE,True,max_width=1060)
            game.text('Choisissez un emplacement.' if page=='save' else 'Choisissez la partie à reprendre.',(110,222),17,MUTED)
            for index,rect in enumerate(self.rectangles(page)):
                selected=index==self.selected[page]
                draw.rect(game.canvas,(34,52,58) if selected else (15,34,42),rect)
                if selected:draw.rect(game.canvas,GOLD,rect,1)
                if index==5:
                    game.text('Retour',(rect.x+20,rect.y+12),20,GOLD if selected else WHITE)
                    continue
                header,detail,date=self.slot_rows[index]
                game.text(header,(rect.x+20,rect.y+4),17,GOLD if selected else WHITE,max_width=760)
                game.text(detail,(rect.x+20,rect.y+29),12,MUTED,max_width=1020)
                if date:game.text(date,(rect.right-245,rect.y+7),13,GOLD)
            if self.message:game.text(self.message,(110,638),13,GOLD)
            game.text('↑ ↓ / Stick  Choisir     Entrée / A  Valider     Échap / B  Retour',(110,674),13,MUTED)
            return
        elif page=='overwrite':
            game.text('REMPLACER LA SAUVEGARDE ?',(108,156),34,WHITE,True)
            game.text(f'L’emplacement {self.slot_index+1} contient déjà une partie.',(110,238),18,MUTED)
            game.text('Cette action remplace uniquement cette case.',(110,274),16,MUTED)
        elif page=='bezels':
            game.text('CADRE D’ÉCRAN',(108,156),42,WHITE,True,max_width=1040)
            game.text('Décor adapté aux marges de l’écran.',(110,222),17,MUTED,max_width=1040)
        elif page=='settings':
            game.text('CONFIGURATION',(108,156),42,WHITE,True)
            game.text('Réglez votre aventure.',(110,222),17,MUTED)
            game.text('FULL HD',(988,306),23,GOLD,center=True)
            game.text('1920 × 1080',(988,351),18,WHITE,center=True)
            game.text('Les choix sont conservés',(988,415),13,MUTED,center=True)
            game.text('au prochain lancement.',(988,438),13,MUTED,center=True)
        else:
            game.text('COMMANDES',(108,156),42,WHITE,True)
            game.text('CLAVIER',(498,233),12,GOLD)
            game.text('MANETTE',(858,233),12,GOLD)
            for index,(action,key,pad) in enumerate(CONTROL_ROWS):
                y=278+index*47
                draw.rect(game.canvas,(15,34,42),(104,y-4,1060,42))
                game.text(action,(110,y),17,WHITE,max_width=360)
                game.text(key,(498,y),17,GOLD,max_width=330)
                game.text(pad,(858,y),17,GOLD,max_width=300)
            game.text('R / View  Recommencer     M / RB  Son     F11  Affichage     F12  Capture',(110,568),12,MUTED,max_width=1060)
        values=self.values(game) if page=='settings' else None
        for index,(label,rect) in enumerate(zip(LABELS[page],self.rectangles(page))):
            selected=index==self.selected[page]
            draw.rect(game.canvas,(34,52,58) if selected else (15,34,42),rect)
            if selected:
                draw.rect(game.canvas,GOLD,rect,1)
                draw.rect(game.canvas,GOLD,(rect.x,rect.y,4,rect.h))
            game.text(label,(rect.x+23,rect.y+8),22,GOLD if selected else WHITE,max_width=430)
            if page=='bezels' and index<len(BEZEL_MODES) and game.settings.bezel==BEZEL_MODES[index]:
                draw.line(game.canvas,GOLD,(rect.right-38,rect.y+23),(rect.right-31,rect.y+30),3)
                draw.line(game.canvas,GOLD,(rect.right-31,rect.y+30),(rect.right-19,rect.y+16),3)
            if values and values[index]:
                if index in (1,6):
                    amount=(game.settings.sound_volume if game.sound_on else 0) if index==1 else (game.settings.music_volume if game.settings.music else 0)
                    gauge=self.volume_gauge(index)
                    draw.rect(game.canvas,(65,78,78),gauge)
                    if amount:draw.rect(game.canvas,GOLD,(gauge.x,gauge.y,round(gauge.width*amount/100),gauge.h))
                if index==5:self.flags.draw(game.canvas,game.settings.language,(rect.x+456,rect.y+10))
                game.text(values[index],(rect.x+500,rect.y+12),17,GOLD,max_width=185)
                if selected:game.text('←  →',(rect.right-63,rect.y+14),17,GOLD)
        back='Quitter' if page=='title' else 'Reprendre' if page=='pause' else 'Retour'
        game.text(f'↑ ↓ / Stick  Choisir     Entrée / A  Valider     Échap / B  {back}',(110,674),13,MUTED,max_width=1060)
        if self.save_failed:game.text('Impossible d’enregistrer les réglages.',(110,648),12,GOLD)
        elif game.pad.connected:game.text('MANETTE CONNECTÉE',(970,688) if page=='title' else (988,635),12,GOLD,center=True)
