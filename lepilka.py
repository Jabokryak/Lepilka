import datetime
import json
import time
import re
import sys
from typing import Any
import typing
import aiohttp
from pydub import AudioSegment
from pathlib import Path
import asyncio
from pytubefix import YouTube

class EventAndFileName:
    event:      asyncio.Event
    file_name:  str

    def __init__(self):
        self.event      = asyncio.Event()

class LepilkaStep: 
    common_step_num:    list[int]                   = [0]
    audio:              list[list[AudioSegment]]    = []
    downloaded_audio:   dict[str, EventAndFileName] = {}
    session:            aiohttp.ClientSession       = None
    
    def __init__(
        self
        ,level:                 int
        ,branch:                int
        ,step_num:              int
        ,do_step_obj:           Any
        ,oneofeach_file_name:   str
        ,export_folder:         str
        ,parent_step:           typing.Self
        ,previous_step:         typing.Self
    ):
        self.level:                 int             = level
        self.branch:                int             = branch
        self.step_num:              int             = step_num
        self.do_step_obj:           Any             = do_step_obj
        self.oneofeach_file_name:   str             = oneofeach_file_name
        self.export_folder:         str             = export_folder
        self.parent_step:           typing.Self     = parent_step
        self.previous_step:         typing.Self     = previous_step

        self.is_finished:           asyncio.Event   = asyncio.Event()
        self.import_file_name:      str             = None
        self.export_file_name:      str             = ''
        self.common_step_num[0]                     += 1 

    def form_import_export_file_name(self):
        if self.import_file_name == None:
            self.import_file_name   = (
                self.oneofeach_file_name if self.do_step_obj['method'] == 'add_oneofeach' else
                self.do_step_obj['file'] if 'file' in self.do_step_obj else
                None
            )

        self.export_file_name   = self.previous_step.export_file_name if self.previous_step != None else ''
        
        if (
            self.import_file_name != None
            and len(self.export_file_name) < 200
            and (
                self.do_step_obj['method'] == 'add'
                or self.do_step_obj['method'] == 'add_oneofeach'
            )
        ):
            self.export_file_name   += (
                '~' 
                + re.search(
                    r'([^./\\]++)(\.[^.]++)?$'
                    ,self.import_file_name
                ).group(1)
            )

    async def do_step(self):  
        s   = self.do_step_obj
        l   = self.level
        b   = self.branch
        sn  = self.step_num

        #print(f"{l}_{b}_{sn}: in do_step {s['method']}")

        if 'url' in s:
            self.import_file_name = await LepilkaStep.get_audio_from_url(s['url'], s['file'] if 'file' in s else None)

        if s['method'] in ('add', 'add_oneofeach', 'overlay', 'export'):
            if self.previous_step != None:
                await self.previous_step.is_finished.wait()
            
            if len(LepilkaStep.audio) - 1 < l :
                LepilkaStep.audio.append([])
                    
            if len(LepilkaStep.audio[l]) - 1 < b :
                LepilkaStep.audio[l].append(
                    LepilkaStep.audio[l - 1][len(LepilkaStep.audio[l - 1]) - 1].append(AudioSegment.empty(), crossfade = 0) if 
                        l > 0 and len(LepilkaStep.audio[l - 1]) > 0
                    else AudioSegment.empty()
                )
        
            q = LepilkaStep.audio[l][b]
        
        self.form_import_export_file_name()
        
        match s['method']:
            case 'add' | 'add_oneofeach':
                s['file'] = self.import_file_name
                
                LepilkaStep.audio[l][b] = q.append(
                    AudioSegment.silent(s['duration'] * 1000) if 'silence' in s
                        else AudioSegment.from_file(**s)
                    ,crossfade = 100 if len(q[0]) > 200 else 0
                )

                if self.import_file_name != None:
                    print(f'{l}_{b}_{sn}:' + ''.ljust(self.level, chr(9)) + '+ ' + self.import_file_name)
            case 'overlay':
                s['file'] = self.import_file_name
                
                LepilkaStep.audio[self.level][self.branch] = q.overlay(
                    seg                     = AudioSegment.from_file(**s) + (s['vol'] if 'vol' in s else 0)
                    ,position               = s['position'] * 1000
                    ,times                  = s['times']
                    ,gain_during_overlay    = s['song_gain']
                )

                print(f'{l}_{b}_{sn}:' + ''.ljust(l, chr(9)) + f"~ {self.import_file_name} с {s['position']} секунды {s['times']} раз")
            case 'export':
                folder_name = (
                    self.export_folder if self.export_folder != None else
                    datetime.datetime.now().strftime(s['folder']) if 'folder' in s else
                    ''
                )
                
                if folder_name != '':
                    Path(folder_name).mkdir(mode = 0o777, parents = True, exist_ok = True)

                if self.previous_step != None:
                    await self.previous_step.is_finished.wait()

                n = folder_name + self.export_file_name.lstrip('~') + ".mp3"

                q.export(n).close()
                
                print(f"{l}_{b}_{sn}: ={n}")
            case 'foreach':
                await LepilkaStep.do(
                    do_items        = s['do']
                    ,level          = l + 1
                    ,file_arr       = [str(path) for path in Path(s['import_folder']).rglob('*.*') if re.match(s['file_mask'], str(path))]
                    ,export_folder  = datetime.datetime.now().strftime(s['export_folder']) if 'export_folder' in s else None
                    ,parent_step    = self
                    ,previous_step  = self.previous_step
                )

        self.is_finished.set()


    async def do(
        do_items:       Any
        ,level:         int             = 0
        ,file_arr:      list[str]       = ['']
        ,export_folder: str             = None
        ,parent_step:   typing.Self     = None
        ,previous_step: typing.Self     = None
    ):
        cn = LepilkaStep.common_step_num

        loop = asyncio.get_running_loop()
        t:      list[asyncio.Task] = []
        
        branch: int = 0

        for f in file_arr:
            prev_stp        = previous_step
            sn:        int  = 0
        
            for s in do_items:
                #print(f"{level}_{branch}_{sn}: {s['method']} {f}")

                ls = LepilkaStep(
                    level                   = level
                    ,branch                 = branch
                    ,step_num               = sn
                    ,do_step_obj            = s
                    ,oneofeach_file_name    = f
                    ,export_folder          = export_folder
                    ,parent_step            = parent_step
                    ,previous_step          = prev_stp
                )

                sn      += 1
                cn[0]   += 1

                t.append(loop.create_task(
                    ls.do_step()
                ))

                prev_stp = ls

            branch += 1
        
        await asyncio.gather(*t)
    
    async def get_audio_from_url(url: str, file_name: str):
        if url in LepilkaStep.downloaded_audio:
            await LepilkaStep.downloaded_audio[url].event.wait()

            audio_filename = LepilkaStep.downloaded_audio[url].file_name

            print("File taken from cache: " + audio_filename)
        else:
            e = EventAndFileName()
            
            LepilkaStep.downloaded_audio[url] = e
            
            if LepilkaStep.session == None:
                LepilkaStep.session = aiohttp.ClientSession(raise_for_status = True)
            
            folder_name = "URL_downloads"
            Path(folder_name).mkdir(mode = 0o777, parents = True, exist_ok = True)
            
            if url.startswith("https://www.youtube.com"):
                yt = YouTube(url)
                
                audio_filename = folder_name + '/' + (file_name or yt.title + ".mp3")
 
                ys = yt.streams.get_audio_only()
                ys.download(filename = audio_filename)
            elif url.startswith("https://www.tiktok.com"):
                i = 20
                while i > 0:
                    i -= 1

                    async with LepilkaStep.session.get("https://www.tikwm.com/api", params = {"url": url, "hd": 1}) as response:
                        data = await response.json()

                    if 'data' in data:
                        break
                    elif 'msg' in data and data['msg'] == 'Free Api Limit: 1 request/second.':
                        time.sleep(2)
                    else:
                        raise Exception("tikwm.com api error: " + data)

                music_info = data['data']['music_info']
                
                audio_filename = folder_name + '/' + (file_name or music_info['title'] + ".mp3")

                async with LepilkaStep.session.get(music_info['play']) as response:
                    with open(audio_filename, 'wb') as file:
                        while chunk := await response.content.read(1024):
                            file.write(chunk)

            e.file_name = audio_filename
            e.event.set()

            print("Downloaded file: " + audio_filename)
        
        return audio_filename


if __name__ == '__main__':
    with open((sys.argv[1] if len(sys.argv) >= 2 else 'my_example1.json'), encoding='utf-8') as p: 
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        loop.run_until_complete(
            LepilkaStep.do(json.load(p))
        )
        
        loop.close()
    
    if LepilkaStep.session != None:
            asyncio.run(LepilkaStep.session.close())
