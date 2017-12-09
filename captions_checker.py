#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Captions Checker
#
# Author: Simon Lachaîne


import datetime
import os
from collections import OrderedDict

import pandas as pd
from bs4 import BeautifulSoup
from pycaption import SCCReader, CaptionConverter, DFXPWriter
from timecode import Timecode


class FileNotSupported(Exception):
    """
    The file is not supported by the program.
    """


class CaptionApp(object):
    """
    Application object
    """
    def __init__(self):
        """
        Defines the object attributes
        """
        self.captions = OrderedDict()  # start tc: stop tc, text
        self.subs = OrderedDict()  # start tc: stop tc, text
        self.faulty_subs = OrderedDict()  # start tc: stop tc, text
        self.faulty_captions = OrderedDict()  # start tc: stop tc, text
        self.scc = ""  # filename
        self.itt = ""  # filename

    def read_file(self, afile):
        """
        Opens a file and reads its contents
        """
        with open(afile, "r", encoding="utf-8") as file_open:
            if os.path.splitext(file_open.name)[1] == ".scc":
                self.scc = file_open.name

            elif os.path.splitext(file_open.name)[1] == ".itt":
                self.itt = file_open.name

            else:
                print(
                    "File not supported: {}".format(
                        file_open.name
                    )
                )
                input("Press Enter to quit.")
                raise FileNotSupported()

            contents = file_open.read()
            return contents

    @staticmethod
    def convert_captions(caps):
        """
        Converts .scc to .dfxp
        """
        converter = CaptionConverter()
        converter.read(caps, SCCReader())
        dfxp = converter.write(DFXPWriter())
        return dfxp

    @staticmethod
    def parse_html(html):
        """
        Parses html code
        """
        html_obj = BeautifulSoup(html, "html.parser")
        return html_obj

    @staticmethod
    def fps_to_seconds(fps, framerate):
        """
        Converts frames per seconds to seconds
        """
        if isinstance(fps, str):
            _zip_ft = zip((3600, 60, 1, 1 / framerate), fps.split(':'))
            return sum(
                f * float(t)
                for f, t in _zip_ft
            )

        elif isinstance(fps, (int, float)):
            return fps / framerate

        else:
            return 0

    @staticmethod
    def convert_timecode(source_tc):
        """
        Converts timecode between two framerates
        """
        tc_obj = Timecode("23.98", source_tc)
        mod_tc = Timecode("29.97", frames=tc_obj.frames)
        tc_str = "{}:{}:{}.{}".format(
            mod_tc.hrs,
            mod_tc.mins,
            mod_tc.secs,
            mod_tc.frs
        )
        return tc_str

    def read_captions(self, html_obj):
        """
        Fills the captions dictionary from the html object
        """
        caps_lst = []
        for p in html_obj.find_all("p"):
            # create datetime object from seconds
            start = datetime.datetime.strptime(p["begin"], "%H:%M:%S.%f")
            stop = datetime.datetime.strptime(p["end"], "%H:%M:%S.%f")

            # add values to list
            caps_lst.append((start.time(), stop.time(), p.text))

            # add values to dictionary
            self.captions[start.time()] = (stop.time(), p.text)

        return self.captions

    def read_subs(self, html_obj):
        """
        Fills the subs dictionary from the html object
        """
        for p in html_obj.find_all("p"):
            # convert timecode to seconds
            start_time = self.fps_to_seconds(p["begin"], 23.98)
            stop_time = self.fps_to_seconds(p["end"], 23.98)

            # create datetime object from seconds
            start = datetime.datetime.fromtimestamp(start_time)
            stop = datetime.datetime.fromtimestamp(stop_time)

            # standardize the subs to the captions
            start_clean = start.replace(year=1900, month=1, day=1, hour=start.hour - 19)
            stop_clean = stop.replace(year=1900, month=1, day=1, hour=start.hour - 19)

            # add values to dictionary
            self.subs[start_clean.time()] = (stop_clean.time(), p.text.replace("&apos;", "'"))

    def compare_timecodes(self):
        """
        Checks if the timecodes overlap
        """
        for cap_start, cap_stop in self.captions.items():
            for sub_start, sub_stop in self.subs.items():

                # if the sub starts after the caption starts
                if sub_start >= cap_start:
                    # if the sub starts before the caption stops
                    if sub_start <= cap_stop[0]:
                        self.faulty_subs[sub_start] = (sub_stop[0], sub_stop[1])
                        self.faulty_captions[cap_start] = (cap_stop[0], cap_stop[1])

                # if the sub stops after the caption starts
                if sub_stop[0] >= cap_start:
                    # if the sub stops before the caption stops
                    if sub_stop[0] <= cap_stop[0]:
                        self.faulty_subs[sub_start] = (sub_stop[0], sub_stop[1])
                        self.faulty_captions[cap_start] = (cap_stop[0], cap_stop[1])

    def create_report(self):
        """
        Writes a text report of the overlapping subs
        """
        with open("overlap_report_rev1.txt", "w", encoding="utf-8") as report:
            report.write(
                "OVERLAP REPORT\n"
                "Captions: {}\n"
                "Subs: {}\n".format(
                    self.scc,
                    self.itt
                )
            )
            report.write("\nOverlapping subs:\n")

            # for k, v in self.faulty_subs.items():
            #     report.write(
            #         "\nSub:\n{} - {}\n{}\n".format(
            #             k,
            #             v[0],
            #             v[1]
            #         ),
            #     )

            subs_lst = list(
                [
                    (k, v[0], v[1])
                    for k, v in self.faulty_subs.items()
                ]
            )
            cap_lst = list(
                [
                    (k, v[0], v[1])
                    for k, v in self.faulty_captions.items()
                ]
            )

            for index_v, values in enumerate(subs_lst):
                # index_lst = subs_lst.index(values)
                sub_start = values[0]
                sub_stop = values[1]
                sub_text = values[2]
                cap_start = cap_lst[index_v][0]
                cap_stop = cap_lst[index_v][1]
                cap_text = cap_lst[index_v][2]

                report.write(
                    "\nSub:\n{} - {}\n{}\n\nOverlaps with caption:\n{} - {}\n{}\n".format(
                        sub_start,
                        sub_stop,
                        sub_text,
                        cap_start,
                        cap_stop,
                        cap_text
                    ),
                )

    def create_dataframe(self):
        """
        Creates a dataframe from the captions and subs dictionaries
        """
        captions_df = pd.DataFrame(
            list(
                [
                    (k, v[0], v[1])
                    for k, v in self.faulty_captions.items()
                ]
            )
        )
        captions_df.columns = ["Timecode In", "Timecode Out", "Text"]

        subs_df = pd.DataFrame(
            list(
                [
                    (k, v[0], v[1])
                    for k, v in self.faulty_subs.items()
                ]
            )
        )
        subs_df.columns = ["Timecode In", "Timecode Out", "Text"]

        return subs_df, captions_df

    @staticmethod
    def print_dataframe(*args):
        """
        Saves the dataframe to a text file
        """
        for index_a, arg in enumerate(args):
            arg.to_csv("dataframe_{}.txt".format(index_a), header=True, index=True, sep='\t', mode='a')

    def plot_dataframe(self):
        """
        Plots the dataframe
        """
        pass


def main():
    """
    Program flow
    """
    # create object instance
    app = CaptionApp()

    # process captions
    captions = app.read_file("captions_subs/000031_FR_full_caption_fr-FR.scc")
    dfxp = app.convert_captions(captions)
    app.read_captions(app.parse_html(dfxp))

    # process subs
    subs = app.read_file("captions_subs/000031_FR_full_forcedsubtitle_fr-FR.itt")
    app.read_subs(app.parse_html(subs))

    # check overlap:
    app.compare_timecodes()
    app.create_report()

    # prepare and present results
    subs_df, cap_df = app.create_dataframe()
    app.print_dataframe(subs_df, cap_df)
    # app.plot_dataframe()

    # quit program
    print("\n\nProgram completed.")
    raise SystemExit


if __name__ == "__main__":
    main()
