#!/usr/bin/python3
# -*- coding: utf-8 -*-

# Captions Checker
#
# Author: Simon Lachaîne


import datetime
import os

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import lxml.etree as etree
from bs4 import BeautifulSoup
from pycaption import SCCReader, CaptionConverter, DFXPWriter
from timecode import Timecode


class FileNotSupported(Exception):
    """
    The file type must be .scc or .itt
    """
    pass


class OverlapChecker(object):
    """
    Application object
    """
    def __init__(self):
        """
        Defines the object attributes
        """
        # lists of tuples: (start timecode, stop timecode, region, text)
        self.captions = []
        self.subs = []

        # list of tuples: (caption tuple, sub tuple)
        self.overlaps = []

        # file paths
        self.scc = ""
        self.itt = ""

    def set_filename(self, filename):
        """
        Validates the file types and sets the file paths
        """
        if os.path.splitext(filename)[1] == ".scc":
            self.scc = os.path.basename(filename)
            return self.scc

        elif os.path.splitext(filename)[1] == ".itt":
            self.itt = os.path.basename(filename)
            return self.itt

        else:
            raise FileNotSupported()

    def read_file(self, afile):
        """
        Opens a file and reads its contents
        """
        with open(afile, "r", encoding="utf-8") as file_open:
            self.set_filename(file_open.name)
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
    def parse_xml(data):
        """
        Parses xml code
        """
        print(type(data))  # DEBUG
        parser = etree.XMLParser(remove_blank_text=True, encoding="utf-8")

        if isinstance(data, str):
            print("Converting string")  # DEBUG
            # data = StringIO(data)
            binary_data = data.encode(encoding="utf-8")
            print("Data type: {}".format(type(binary_data)))  # DEBUG
            source_xml = etree.parse(binary_data)
            source_root = source_xml.getroot()
            return source_root

        # source_xml = etree.parse(source=data, parser=parser)
        # source_root = source_xml.getroot()

        # return source_root

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
    def convert_timecode(source_tc, source_framerate, end_framerate):
        """
        Converts timecode between two framerates
        """
        tc_obj = Timecode(source_framerate, source_tc)
        mod_tc = Timecode(end_framerate, frames=tc_obj.frames)
        tc_str = "{}:{}:{}.{}".format(
            mod_tc.hrs,
            mod_tc.mins,
            mod_tc.secs,
            mod_tc.frs
        )
        return tc_str

    def read_captions(self, html_obj):
        """
        Fills the captions list from the html object
        """
        for p in html_obj.find_all("p"):

            # create datetime object from seconds
            start = datetime.datetime.strptime(p["begin"], "%H:%M:%S.%f")
            stop = datetime.datetime.strptime(p["end"], "%H:%M:%S.%f")

            # set region info
            region = "bottom"

            try:
                p["region"]

            except KeyError:
                pass

            else:
                region = p["region"]

            # add tuple of values to list
            self.captions.append(
                (
                    start.time(), stop.time(), region, p.text
                )
            )

        return self.captions

    def read_subs(self, html_obj):
        """
        Fills the subs list from the html object
        """
        for br in html_obj.find_all("br"):
            br.replace_with("\n")

        for p in html_obj.find_all("p"):

            # convert timecode to seconds
            start_time = self.fps_to_seconds(p["begin"], 23.976)
            stop_time = self.fps_to_seconds(p["end"], 23.976)

            # create datetime object from seconds
            temp_time = datetime.datetime(1900, 1, 1, 0, 0, 0)
            start = temp_time + datetime.timedelta(seconds=start_time)
            stop = temp_time + datetime.timedelta(seconds=stop_time)

            # set region info
            region = "bottom"

            try:
                p["region"]

            except KeyError:
                pass

            else:
                region = p["region"]

            # add tuple of values to list
            self.subs.append(
                (
                    start.time(),
                    stop.time(),
                    region,
                    p.text.replace("&apos;", "'").replace("&amp;", "&")
                )
            )

    def compare_timecodes(self):
        """
        Checks if the timecodes overlap
        """
        # checking caps on subs
        for sub_start, sub_stop, sub_region, sub_text in self.subs:
            for cap_start, cap_stop, cap_region, cap_text in self.captions:
                cap_tuple = (cap_start, cap_stop, cap_region, cap_text)
                sub_tuple = (sub_start, sub_stop, sub_region, sub_text)

                # if the cap starts after the sub starts
                if cap_start >= sub_start:
                    # if the cap starts before the sub stops
                    if cap_start <= sub_stop:

                        # timecode overlap detected
                        if (cap_tuple, sub_tuple) not in self.overlaps:
                            self.overlaps.append((cap_tuple, sub_tuple))

                # if the cap stops after the sub starts
                if cap_stop >= sub_start:
                    # if the cap stops before the sub stops
                    if cap_stop <= sub_stop:

                        # timecode overlap detected
                        if (cap_tuple, sub_tuple) not in self.overlaps:
                            self.overlaps.append((cap_tuple, sub_tuple))

        # checking subs on caps
        for cap_start, cap_stop, cap_region, cap_text in self.captions:
            for sub_start, sub_stop, sub_region, sub_text in self.subs:
                cap_tuple = (cap_start, cap_stop, cap_region, cap_text)
                sub_tuple = (sub_start, sub_stop, sub_region, sub_text)

                # if the sub starts after the caption starts
                if sub_start >= cap_start:
                    # if the sub starts before the caption stops
                    if sub_start <= cap_stop:

                        # timecode overlap detected
                        if (cap_tuple, sub_tuple) not in self.overlaps:
                            self.overlaps.append((cap_tuple, sub_tuple))

                # if the sub stops after the caption starts
                if sub_stop >= cap_start:
                    # if the sub stops before the caption stops
                    if sub_stop <= cap_stop:

                        # timecode overlap detected
                        if (cap_tuple, sub_tuple) not in self.overlaps:
                            self.overlaps.append((cap_tuple, sub_tuple))

        return self.overlaps

    def create_dataframes(self):
        """
        Creates dataframes from the list of overlaps
        """
        captions_df = pd.DataFrame([x[0] for x in self.overlaps])
        captions_df.drop_duplicates(inplace=True)
        captions_df.columns = ["Timecode In", "Timecode Out", "Region", "Text"]

        subs_df = pd.DataFrame([x[1] for x in self.overlaps])
        subs_df.drop_duplicates(inplace=True)
        subs_df.columns = ["Timecode In", "Timecode Out", "Region", "Text"]

        return captions_df, subs_df

    @staticmethod
    def save_dataframe(**kwargs):
        """
        Saves the dataframe to a text file
        """
        if kwargs is not None:
            for filename, df in kwargs.items():
                if isinstance(df, pd.DataFrame):
                    df.to_csv(
                        "results/{}_overlaps.txt".format(os.path.basename(filename)),
                        header=True, index=True, sep='\t', mode='a')

    def plot_overlaps(self):
        """
        Plots the captions and subs overlaps
        """
        # region definitions
        r0 = {
            "origin": (25, 93.33),
            "extent": (75, 6.67)
        }
        r1 = {
            "origin": (12.5, 93.33),
            "extent": (87.5, 6.67)
        }
        r2 = {
            "origin": (0, 86.67),
            "extent": (100, 13.33)
        }
        r3 = {
            "origin": (0, 93.33),
            "extent": (100, 6.67)
        }
        r4 = {
            "origin": (12.5, 86.67),
            "extent": (87.5, 13.33)
        }
        r5 = {
            "origin": (25, 86.67),
            "extent": (75, 13.33)
        }
        r6 = {
            "origin": (37.5, 93.33),
            "extent": (62.5, 6.67)
        }
        r7 = {
            "origin": (37.5, 86.67),
            "extent": (62.5, 13.33)
        }
        r8 = {
            "origin": (25, 0),
            "extent": (75, 100)
        }
        top = {
            "origin": (0, 0),
            "extent": (100, 15)
        }
        bottom = {
            "origin": (0, 85),
            "extent": (100, 15)
        }

        regions_dct = {
            "r0": r0,
            "r1": r1,
            "r2": r2,
            "r3": r3,
            "r4": r4,
            "r5": r5,
            "r6": r6,
            "r7": r7,
            "r8": r8,
            "top": top,
            "bottom": bottom
        }
        # print regions
        # for r_name, r in regions_dct.items():
        #     x = r["origin"][0]
        #     y = r["origin"][1]
        #     width = r["extent"][0]
        #     height = r["extent"][1]
        # 
        #     fig, ax = plt.subplots(1, figsize=(9, 6), dpi=80)
        #     plt.axis([0, 100, 100, 0], clip_on=False)
        #     plt.title("{}\n{}".format(r_name, r))
        #     plt.xlabel("Width")
        #     plt.ylabel("Height")
        # 
        #     rect = mpatches.Rectangle(
        #         (x, y),
        #         width=width, height=height,
        #         fill=False, hatch="x", edgecolor="black", linewidth=10, label=r
        #     )
        #     ax.add_patch(rect)
        #     plt.show()

        for index_o, (cap, sub) in enumerate(self.overlaps, start=1):
            fig, ax = plt.subplots(1, figsize=(9, 6), dpi=80)
            plt.axis([0, 100, 100, 0], clip_on=False)
    
            # caption region
            cap_region = regions_dct[cap[2]]
            cap_x = cap_region["origin"][0]
            cap_y = cap_region["origin"][1]
            cap_width = cap_region["extent"][0]
            cap_height = cap_region["extent"][1]
            cap_rect = mpatches.Rectangle(
                (cap_x, cap_y),
                width=cap_width, height=cap_height,
                fill=True, color="b", zorder=80
            )
            # ax.add_patch(cap_rect)

            # sub region
            sub_region = regions_dct[sub[2]]
            sub_x = sub_region["origin"][0]
            sub_y = sub_region["origin"][1]
            sub_width = sub_region["extent"][0]
            sub_height = sub_region["extent"][1]
            sub_rect = mpatches.Rectangle(
                (sub_x, sub_y),
                width=sub_width, height=sub_height,
                fill=True, color="g"
            )
            # ax.add_patch(sub_rect)

            # text and legends
            plt.title("Caption: {} - {}\nSubtitle: {} - {}".format(
                cap[0], cap[1], sub[0], sub[1]
            ))
            cap_text = cap[3]
            sub_text = sub[3]

            plt.annotate(
                "Caption:\n{}\nSubtitle:\n{}".format(
                    cap_text, sub_text
                ),
                (0, 0),
                (0, -15),
                xycoords='axes fraction',
                textcoords='offset points',
                va="top"
            )
            frame1 = plt.gca()
            frame1.axes.xaxis.set_ticklabels([])
            frame1.axes.yaxis.set_ticklabels([])
            frame1.axes.xaxis.set_ticks([])
            frame1.axes.yaxis.set_ticks([])

            # draw caption
            bbox_props = dict(boxstyle="square,pad=0", fill=True, color="black", alpha=0.5, zorder=80)
            cap_font = {"fontname": "DejaVu Sans Mono"}
            cap_box = ax.text(
                cap_x,
                cap_y + cap_height,
                "{}".format(
                    cap_text
                ),
                ha="left",
                size=10,
                zorder=100,
                color="white",
                bbox=bbox_props,
                **cap_font
            )

            # draw subtitle
            bbox_props = dict(boxstyle="square,pad=0.3", fill=False, ec="b", lw=2)
            sub_font = {"fontname": "Arial"}
            pad = sub_height / 4
            sub_box = ax.text(
                50,
                (sub_y + (sub_height - pad)),
                "{}".format(
                    sub_text
                ),
                ha="center",
                size=10,
                zorder=60,
                # bbox=bbox_props,
                **sub_font
            )

            plt.tight_layout()
            plt.subplots_adjust(bottom=0.25)

            # Check collisions
            renderer = fig.canvas.get_renderer()
            cb = cap_box.get_window_extent(renderer=renderer)
            # print(cb.width, cb.height)
            sb = sub_box.get_window_extent(renderer=renderer)
            # print(sb.width, sb.height)

            # fig.savefig("results/{}_overlap_{}.png".format(os.path.splitext(self.scc)[0], index_o), dpi=120)
            plt.show()


def main():
    """
    Program flow
    """
    # create object instance
    app = OverlapChecker()

    # process captions
    print("Reading captions file...")
    captions = app.read_file("captions_subs/000031_FR_full_caption_fr-FR.scc")
    print("Converting scc to dfxp...")
    dfxp = app.convert_captions(captions)
    print("Parsing captions...")
    app.read_captions(app.parse_html(dfxp))

    # process subs
    print("Reading subs file...")
    subs = app.read_file("captions_subs/000031_FR_full_forcedsubtitle_fr-FR.itt")
    print("Parsing subs...")
    app.read_subs(app.parse_html(subs))

    # check overlap:
    print("Checking for timecode overlaps...")
    app.compare_timecodes()

    # prepare and present results
    # print("Creatings dataframes...")
    # cap_df, subs_df = app.create_dataframes()
    # print("Saving dataframes to files...")
    # kwargs = {app.scc: cap_df, app.itt: subs_df}
    # app.save_dataframe(**kwargs)
    print("Preparing graphics...")
    app.plot_overlaps()

    # quit program
    print("\nProgram completed.")
    raise SystemExit


if __name__ == "__main__":
    main()
