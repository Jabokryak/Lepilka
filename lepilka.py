import datetime
import json
import re
import sys
from typing import Any
from pydub import AudioSegment
from pathlib import Path
 
with open(sys.argv[1], encoding='utf-8') as p: 
    y = json.load(p) 

def do(
        doItems:        Any
        ,parentAudio:    AudioSegment = AudioSegment.empty()
        ,parentFileName: str = ''
        ,level:         int = 0
        ,fileArr:       list[str] = ['']
        ,exportFolder:  str = None
    ):
    for f in fileArr:
        q = parentAudio
        n = parentFileName
        #print(f)

        for s in doItems:
            #print(s['method'])

            match s['method']:
                case 'add' | 'add_oneofeach':
                    if s['method'] == 'add_oneofeach':
                        s['file'] = f
                    
                    q = q.append(
                        AudioSegment.silent(s['duration'] * 1000) if 'silence' in s 
                            else AudioSegment.from_file(**s)
                        ,crossfade = 100 if len(q) > 200 else 0
                    )

                    if 'file' in s:
                        if len(n) < 200:
                            n = n + re.search(r'([^./\\]++)(\.[^.]++)?$', s['file']).group(1) + '~'

                        print(''.ljust(level, chr(9)) + '+ ' + s['file'])
                case 'overlay':
                    q = q.overlay(
                        seg                     = AudioSegment.from_file(**s) + (s['vol'] if 'vol' in s else 0)
                        ,position               = s['position'] * 1000
                        ,times                  = s['times']
                        ,gain_during_overlay    = s['song_gain']
                    )

                    print(''.ljust(level, chr(9)) + f"~ {s['file']} с {s['position']} секунды {s['times']} раз")
                case 'export':
                    folder_name = (
                        exportFolder if exportFolder != None else
                        datetime.datetime.now().strftime(s['folder']) if 'folder' in s else
                        ''
                    )
                     
                    n = folder_name + n.rstrip('~') + ".mp3"

                    if folder_name != '':
                        Path(folder_name).mkdir(mode = 0o777, parents = True, exist_ok = True)

                    q.export(n).close()
                    
                    print("=" + n)
                case 'foreach':
                    do(
                        doItems         = s['do']
                        ,parentAudio    = q
                        ,parentFileName = n
                        ,level          = level + 1
                        ,fileArr        = [str(path) for path in Path(s['import_folder']).rglob('*.*') if re.match(s['file_mask'], str(path))]
                        ,exportFolder   = datetime.datetime.now().strftime(s['export_folder']) if 'export_folder' in s else None
                    )

do(y)

