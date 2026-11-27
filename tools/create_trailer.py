"""Build the 30-second presentation trailer from actual game footage and user music."""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import tempfile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import imageio_ffmpeg
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output'
WORK=OUT/'trailer-work-v2'
FF=imageio_ffmpeg.get_ffmpeg_exe()


def run(args):
    result=subprocess.run([FF,'-hide_banner','-nostdin','-y',*map(str,args)],capture_output=True)
    if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace')[-4000:])
    return result


def capture_egypt():
    from capture_trailer_v2 import capture
    capture()


def title_card(name,title,subtitle=None,center=False):
    image=Image.new('RGBA',(1920,1080));draw=ImageDraw.Draw(image)
    gold=(237,194,105,255);white=(249,239,214,255)
    if center:
        draw.rectangle((0,0,1920,1080),fill=(5,15,23,105))
        font=ImageFont.truetype('C:/Windows/Fonts/georgiab.ttf',124)
        draw.text((960,405),title,font=font,fill=white,anchor='mm',stroke_width=2,stroke_fill=(8,20,27,220))
        draw.line((775,500,1145,500),fill=gold,width=3)
        font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',34)
        draw.text((960,555),subtitle,font=font,fill=gold,anchor='mm')
        draw.text((960,1024),'JUMPINGJACK  ·  KRARAN',font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',20),fill=gold,anchor='mm')
    else:
        font=ImageFont.truetype('C:/Windows/Fonts/segoeuib.ttf' if title=='VOUS ALLEZ MOURIR' else 'C:/Windows/Fonts/segoeuisl.ttf',
                                48 if title=='VOUS ALLEZ MOURIR' else 33)
        draw.text((960,1024),title,font=font,fill=white,anchor='mm')
        draw.line((860,985,1060,985),fill=gold,width=2)
    path=WORK/f'{name}.png';image.save(path);return path


def build(reuse_captures=False):
    WORK.mkdir(parents=True,exist_ok=True)
    if not reuse_captures:capture_egypt()
    shots=[
        (WORK/'egypt-1.mp4',0,2.5,'JUMPING JACK','Un saut vers les dieux.',True),
        (WORK/'egypt-2.mp4',0,2.5,'DES SABLES D’ÉGYPTE…',None,False),
        (WORK/'egypt-3.mp4',0,2.,'TRAVERSEZ LES TEMPLES OUBLIÉS',None,False),
        (WORK/'tower.mp4',0,1.5,'PRENEZ DE LA HAUTEUR',None,False),
        (WORK/'greece-5.mp4',0,2.,'…AUX RIVAGES DE LA GRÈCE',None,False),
        (WORK/'greece-6.mp4',0,1.5,'DEUX MONDES · HUIT NIVEAUX',None,False),
        (WORK/'greece-7.mp4',0,1.5,'BRAVEZ LES GALERIES ANTIQUES',None,False),
        (WORK/'solar.mp4',0,3.5,'LIBÉREZ LA PUISSANCE DU SOLEIL',None,False),
        (WORK/'crocodile.mp4',0,2.,'VOUS ALLEZ MOURIR',None,False),
        (WORK/'fire.mp4',0,2.,'VOUS ALLEZ MOURIR',None,False),
        (WORK/'sword.mp4',0,2.,'VOUS ALLEZ MOURIR',None,False),
        (WORK/'laser.mp4',0,2.,'VOUS ALLEZ MOURIR',None,False),
        (WORK/'water.mp4',0,2.,'VOUS ALLEZ MOURIR',None,False),
        (WORK/'acropolis.mp4',0,3.,'JUMPING JACK','L’aventure prend son envol.',True),
    ]
    for index,(source,start,duration,title,subtitle,center) in enumerate(shots):
        overlay=title_card(f'card-{index}',title,subtitle,center)
        # Crop HUD and developer captions, preserving the original 16:9 composition in a letterbox.
        if title=='VOUS ALLEZ MOURIR':
            crop_y=560 if source.stem=='water' else 455
            framing=f'crop=1280:520:125:{crop_y},scale=1920:780:flags=lanczos'
        else:framing='crop=1920:780:0:190'
        filters=(f'[0:v]scale=1920:1080:flags=lanczos,{framing},'
                 'pad=1920:1080:0:150:black,setsar=1,fps=60[base];'
                 '[base][1:v]overlay=0:0:format=auto,format=yuv420p')
        if index==0:filters+=',fade=t=in:st=0:d=0.4'
        if index==len(shots)-1:filters+=f',fade=t=out:st={duration-.5}:d=0.5'
        run(['-loglevel','error','-ss',start,'-i',source,'-loop','1','-i',overlay,
             '-filter_complex',filters,'-t',duration,'-an','-c:v','libx264','-preset','fast',
             '-crf','18','-pix_fmt','yuv420p','-threads','4',WORK/f'shot-{index}.mp4'])
        print(f'Edited shot {index+1}/{len(shots)}',flush=True)
    concat=WORK/'montage.txt'
    concat.write_text(''.join(f"file 'shot-{index}.mp4'\n" for index in range(len(shots))),encoding='utf-8')
    target=OUT/'JumpingJack-Trailer-30s.mp4'
    # Original Suno recording, so the soundtrack starts with the original intro rather than the menu loop seam.
    music=ROOT/'JumpingJack - The Lone Flyer.m4a'
    run(['-loglevel','error','-f','concat','-safe','0','-i',concat,'-i',music,
         '-map','0:v:0','-map','1:a:0','-c:v','copy','-af',
         'loudnorm=I=-16:TP=-1.5:LRA=11,afade=t=in:st=0:d=0.5,afade=t=out:st=28.4:d=1.6',
         '-c:a','aac','-b:a','192k','-ar','48000','-t','30','-movflags','+faststart',target])
    run(['-loglevel','error','-ss','10.2','-i',target,'-frames:v','1',OUT/'JumpingJack-Trailer-30s-cover.jpg'])
    # Decode every frame and audio packet to catch broken joins or incomplete files.
    run(['-v','error','-i',target,'-f','null','-'])
    report={'file':target.name,'seconds':30,'size_bytes':target.stat().st_size,'resolution':[1920,1080],
            'fps':60,'video':'H.264','audio':'AAC stereo, The Lone Flyer, fades in/out',
            'footage':'Fresh native GPU captures, current solar FX and real enemy damage; no invulnerability',
            'solar_speed':.5,'death_montage':['crocodile','fire','sword','laser','water'],
            'shots':[{'source':str(s[0].relative_to(ROOT)),'start':s[1],'duration':s[2],'caption':s[3]} for s in shots],
            'full_decode':'passed','user_settings_and_saves':'temporary files only'}
    (OUT/'trailer-30s-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--reuse-captures',action='store_true')
    build(parser.parse_args().reuse_captures)
