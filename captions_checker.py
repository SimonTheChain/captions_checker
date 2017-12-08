#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Captions Checker
#
# Author: Simon Lachaîne


import datetime
import pandas as pd
from timecode import Timecode
from bs4 import BeautifulSoup
from pycaption import SCCReader, CaptionConverter, DFXPWriter


def timecode_to_frames(timecode, framerate):
    return sum(f * int(t) for f, t in zip((3600*framerate, 60*framerate, framerate, 1), timecode.split(':')))


def frames_to_timecode(frames, framerate):
    return '{0:02d}:{1:02d}:{2:02d}:{3:02d}'.format(frames / (3600*framerate),
                                                    frames / (60*framerate) % 60,
                                                    frames / framerate % 60,
                                                    frames % framerate)


def seconds(value, framerate):
    if isinstance(value, str):  # value seems to be a timestamp
        _zip_ft = zip((3600, 60, 1, 1/framerate), value.split(':'))
        return sum(f * float(t) for f,t in _zip_ft)
    elif isinstance(value, (int, float)):  # frames
        return value / framerate
    else:
        return 0


with open("000031_FR_full_caption_fr-FR.scc", "r") as caps_file:
    caps = caps_file.read()

converter = CaptionConverter()
converter.read(caps, SCCReader())
captions = BeautifulSoup(converter.write(DFXPWriter()), "html.parser")
captions_lst = []

for p in captions.find_all("p"):
    # print(Timecode("1000", p["begin"]).frames)%f
    # print(timecode_to_frames(timecode=p["begin"], framerate=1000))
    # tc_out = Timecode("1000", p["end"])
    tm = datetime.datetime.strptime(p["begin"], "%H:%M:%S.%f")
    print(datetime.datetime.strftime(tm, "%H:%M:%S.%f"))
    break



# print(captions_lst[0])

with open("000031_FR_full_forcedsubtitle_fr-FR.itt", "r") as subs_file:
    subs = subs_file.read()

subtitles = BeautifulSoup(subs, "html.parser")
subtitles_lst = []

for p in subtitles.find_all("p"):
    tm1 = seconds(p["begin"], 23.98)
    print(tm1)
    tm2 = datetime.datetime.fromtimestamp(tm1)
    print(datetime.datetime.strftime(tm2, "%H:%M:%S.%f"))
    # tc1 = Timecode("23.98", p["begin"])
    # tc2 = Timecode("29.97", frames=tc1.frames)
    # print(tc2)
    break

# print(subtitles_lst[0])
#
# tc3 = captions_lst[0] - subtitles_lst[0]

# captions_df = pd.DataFrame(list(captions_lst.items()))
# captions_df.columns = ["Timecode In", "Timecode Out"]
# captions_df.set_index("Timecode In", inplace=True)
# print(captions_df.head())
