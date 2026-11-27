"""Prepare the user-provided Suno track as a quiet, circular menu music loop.

Developer-only: numpy and imageio-ffmpeg from requirements-dev.txt.
The source recording is never modified. Runtime only needs the resulting Ogg.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

import imageio_ffmpeg
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
RATE=48000
CROSSFADE=1.5
TARGET_LUFS=-20


def command(args,**kwargs):
    return subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(),'-hide_banner','-nostdin',*args],
                          check=True,capture_output=True,**kwargs)


def prepare(source):
    source=Path(source)
    decoded=command(['-i',str(source),'-vn','-ac','2','-ar',str(RATE),'-f','f32le','-'])
    samples=np.frombuffer(decoded.stdout,dtype='<f4').reshape(-1,2)
    length=round(CROSSFADE*RATE)
    if len(samples)<length*4:raise ValueError('Music is too short for this loop edit')
    angle=np.linspace(0,np.pi/2,length,dtype=np.float32)[:,None]
    seam=samples[-length:]*np.cos(angle)+samples[:length]*np.sin(angle)
    loop=np.concatenate((seam,samples[length:-length])).astype('<f4')
    # The file starts with the tail-to-intro crossfade, followed by the body.
    # Both the crossfade/body join and the actual file wrap are sample-contiguous.
    destination=ROOT/'assets'/'audio'/'menu-the-lone-flyer.ogg'
    destination.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='jumpingjack-menu-audio-') as directory:
        raw=Path(directory)/'loop.f32';raw.write_bytes(loop.tobytes())
        inputs=['-f','f32le','-ar',str(RATE),'-ac','2','-i',str(raw)]
        analysis=command([*inputs,'-af',f'loudnorm=I={TARGET_LUFS}:TP=-2:LRA=11:print_format=json','-f','null','-'])
        stats=json.loads(re.findall(r'\{[^{}]+\}',analysis.stderr.decode(errors='replace'))[-1])
        normalization=(f'loudnorm=I={TARGET_LUFS}:TP=-2:LRA=11:linear=true:'
                       f'measured_I={stats["input_i"]}:measured_TP={stats["input_tp"]}:'
                       f'measured_LRA={stats["input_lra"]}:measured_thresh={stats["input_thresh"]}:'
                       f'offset={stats["target_offset"]}')
        command(['-y',*inputs,'-af',normalization,'-ar',str(RATE),'-ac','2','-c:a','libvorbis','-q:a','5',
                 '-map_metadata','-1','-metadata','title=JumpingJack - The Lone Flyer',str(destination)])
    measured=command(['-i',str(destination),'-af','loudnorm=I=-20:TP=-2:LRA=11:print_format=json','-f','null','-'])
    output_stats=json.loads(re.findall(r'\{[^{}]+\}',measured.stderr.decode(errors='replace'))[-1])
    report={'source':source.name,'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
            'source_seconds':len(samples)/RATE,'loop_seconds':len(loop)/RATE,
            'crossfade_seconds':CROSSFADE,'sample_rate':RATE,'channels':2,
            'normalization':'two-pass linear loudness normalization; dynamics preserved',
            'target_lufs':TARGET_LUFS,'measured_lufs':float(output_stats['input_i']),
            'measured_true_peak_db':float(output_stats['input_tp']),
            'output':str(destination.relative_to(ROOT)).replace('\\','/'),
            'output_bytes':destination.stat().st_size,'source_unchanged':True}
    (ROOT/'output'/'menu-music-preparation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('source',nargs='?',default=str(ROOT/'JumpingJack - The Lone Flyer.m4a'))
    prepare(parser.parse_args().source)
