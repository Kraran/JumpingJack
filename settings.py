"""Small, validated and atomically saved player preferences."""
import json
import ctypes
import locale
import os
from dataclasses import asdict,dataclass
from pathlib import Path
from localization import CODES


def system_locale():
    """Prefer the Windows display language over Python's numeric locale."""
    if os.name=='nt':
        try:
            function=ctypes.windll.kernel32.GetUserDefaultUILanguage
            function.argtypes=[];function.restype=ctypes.c_ushort
            name=locale.windows_locale.get(function())
            if name:return name
        except (AttributeError,OSError):pass
    for key in ('LANGUAGE','LC_ALL','LC_MESSAGES','LANG'):
        if os.environ.get(key):return os.environ[key].split(':',1)[0]
    try:return locale.getlocale()[0]
    except (ValueError,TypeError):return None


def detect_system_language():
    try:
        name=system_locale()
        if not isinstance(name,str):return 'en'
        name=locale.normalize(name.strip().replace('-','_'))
        code=name.split('.',1)[0].split('@',1)[0].split('_',1)[0].lower()
        if code=='no':code='nb'
        return code if code in CODES else 'en'
    except (OSError,ValueError,TypeError):return 'en'


def detected_settings(**options):
    settings=Settings(language=detect_system_language(),**options)
    settings._language_detected=True
    return settings


@dataclass
class Settings:
    fullscreen:bool=True
    sound:bool=True
    rumble:bool=True
    show_fps:bool=False
    language:str='fr'

    @classmethod
    def load(cls,path):
        if path is None:return cls()
        try:
            values=json.loads(Path(path).read_text(encoding='utf-8'))
            if not isinstance(values,dict):return cls(language='en')
            options={key:value for key,value in values.items()
                     if key in cls.__dataclass_fields__ and key!='language' and type(value) is bool}
            if 'language' not in values:return detected_settings(**options)
            options['language']=values['language'] if isinstance(values['language'],str) and values['language'] in CODES else 'en'
            return cls(**options)
        except FileNotFoundError:return detected_settings()
        except (OSError,ValueError):return cls(language='en')

    def save(self,path):
        if path is None:return True
        path=Path(path);temporary=path.with_suffix(path.suffix+'.tmp')
        try:
            temporary.write_text(json.dumps(asdict(self),indent=2)+'\n',encoding='utf-8')
            temporary.replace(path)
            return True
        except OSError:return False
