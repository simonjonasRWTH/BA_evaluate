#!/usr/bin/env python3
import argparse
import datetime
import gzip
import json
import logging
import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt

import evaluate.settings as settings

IDSs = []
ATTACKFILE = None
DATASETNAME = ""
GAPTIME = 30  # Gap has to be at least x minutes to be skipped
SCORE = None
MIN_WIDTH = 0
MARKEDATTACKS = []


# Wrapper for hiding .gz files
def open_file(filename, mode):
    if filename.endswith(".gz"):
        return gzip.open(filename, mode=mode, compresslevel=settings.compresslevel)
    elif filename == "-":
        return sys.stdin
    else:
        return open(filename, mode=mode, buffering=1)


# Initialize logger
def initialize_logger(args):
    if args.log:
        settings.log = getattr(logging, args.log.upper(), None)

        if not isinstance(settings.log, int):
            logging.getLogger("ipal-ploat-alerts").error(
                "Option '--log' parameter not found"
            )
            exit(1)

    if args.logfile:
        settings.logfile = args.logfile
        logging.basicConfig(
            filename=settings.logfile, level=settings.log, format=settings.logformat
        )
    else:
        logging.basicConfig(level=settings.log, format=settings.logformat)

    settings.logger = logging.getLogger("ipal-plot-alerts")


# Get the IDS suspicion scores if available
def get_score(js):
    global SCORE

    if SCORE is None:
        return None

    elif SCORE == "default":
        if len(js["scores"]) != 1:
            settings.logger.error(
                "--score 'default' was provided but multiple IIDSs are present!"
            )
            settings.logger.error(
                "Use any of {} instead".format(
                    ", ".join([f"'{ids}'" for ids in js["scores"].keys()])
                )
            )
            exit(1)

        return list(js["scores"].values())[0]

    else:
        if SCORE not in js["scores"]:
            settings.logger.error(
                "--score '{}' was provided but no such IIDS was found!".format(SCORE)
            )
            settings.logger.error(
                "Use any of {} instead".format(
                    ", ".join([f"'{ids}'" for ids in js["scores"].keys()])
                )
            )
            exit(1)

        return js["scores"][SCORE]


def normalize_scores(scores):  # normalize min/max to 0 1
    M = max(scores)
    m = min(scores)
    return [(s - m) / (1 if M - m == 0 else M - m) for s in scores]


def plot(  # noqa: C901
    ax, draw_ticks=False, plot_attack_ids=True, mark_fp=True, mark_skip=False
):  # noqa: C901
    global IDSs, ATTACKFILE, DATASETNAME, GAPTIME, SCORE, MIN_WIDTH, MARKEDATTACKS

    count = 1
    ipalidtotimestamp = {}

    # PLOT IDS ALARMS
    for IDS, label in IDSs:
        count -= 1
        gaps = []
        T = []
        ALERT = []
        FALSE_ALERT = []
        SCORES = []
        SKIPS = []

        ATTACK_START = None
        excess = 0

        settings.logger.info(
            "Processing: {} ({}/{})".format(label, -count + 1, len(IDSs))
        )

        try:  # load file into memory
            with open_file(IDS, "r") as f:
                last_timestamp = None
                line = f.readline()

                while line:
                    js = json.loads(line)
                    t = datetime.datetime.fromtimestamp(js["timestamp"])

                    # Collect ipalIDs
                    if draw_ticks:
                        ipalidtotimestamp[js["id"]] = js["timestamp"]

                    if last_timestamp is None:
                        last_timestamp = t
                        START = js["timestamp"]
                    elif t - last_timestamp > datetime.timedelta(minutes=GAPTIME):
                        delta = t - last_timestamp
                        gaps.append((js["timestamp"] - START, delta))
                        SKIPS.append(
                            js["timestamp"]
                            - START
                            - sum([g[1].total_seconds() for g in gaps])
                        )
                        settings.logger.info(f"Skipped Gap of {delta}")

                    last_timestamp = t

                    relativ_time = js["timestamp"] - START
                    for gap in gaps:
                        relativ_time -= gap[1].total_seconds()

                    # enlarge attacks a tiny bit
                    excess -= 1
                    if ATTACK_START is None and js["ids"]:
                        ATTACK_START = relativ_time
                    elif ATTACK_START is not None and not js["ids"]:
                        if relativ_time - ATTACK_START < MIN_WIDTH:
                            excess = MIN_WIDTH - (relativ_time - ATTACK_START)
                            settings.logger.info(f"Enlarging attack by {excess}")
                        ATTACK_START = None

                    T.append(relativ_time)
                    ALERT.append(js["ids"] or excess > 0)
                    if mark_fp:
                        FALSE_ALERT.append(
                            (js["ids"] and not js["malicious"])
                            or (excess > 0 and FALSE_ALERT[-1])  # enlarge false alert
                        )
                    SCORES.append(get_score(js))

                    line = f.readline()

        except EOFError:  # allow draing incomplete files
            settings.logger.warning(
                "File not closed properly! Some data is still missing!\n"
            )

        if draw_ticks:
            if mark_fp:
                alerts = [t for t, a, fa in zip(T, ALERT, FALSE_ALERT) if a and not fa]
                false_alerts = [t for t, fa in zip(T, FALSE_ALERT) if fa]
                ax.scatter(
                    false_alerts,
                    [count - 0.5] * len(false_alerts),
                    marker="^",
                    color="#a50303",
                    s=5,
                )
            else:
                alerts = [t for t, a in zip(T, ALERT) if a]
            ax.scatter(
                alerts, [count - 0.5] * len(alerts), marker="x", color="#000000", s=5
            )

        else:
            if mark_fp:
                alerts = [(a and not fa) for a, fa in zip(ALERT, FALSE_ALERT)]
                ax.fill_between(
                    T,
                    count - 1,
                    count,
                    where=FALSE_ALERT,
                    facecolor="#a50303",
                    linewidth=0.1,
                )
            else:
                alerts = ALERT
            ax.fill_between(
                T,
                count - 1,
                count,
                where=alerts,
                facecolor="#000000",
                linewidth=0.1,
            )

        if SCORE is not None:
            ax.plot(T, [count - 1 + s for s in normalize_scores(SCORES)])

        if mark_skip:
            ax.scatter(SKIPS, [count - 0.5] * len(SKIPS), marker="1", color="grey")

    END = js["timestamp"]

    # PLOT ATTACKS
    settings.logger.info("Processing attacks")
    ATTACKS = []

    if ATTACKFILE is not None:
        with open_file(ATTACKFILE, "r") as f:
            for attack in json.load(f):
                # Draw attack ticks
                if draw_ticks and "ipalid" in attack:
                    if attack["ipalid"] in ipalidtotimestamp:
                        start = ipalidtotimestamp[attack["ipalid"]] - START
                        for gap in gaps:
                            if ipalidtotimestamp[attack["ipalid"]] - START > gap[0]:
                                start -= gap[1].total_seconds()

                        ATTACKS.append((start, str(attack["id"]) in MARKEDATTACKS))

                        if plot_attack_ids:
                            ax.annotate(
                                attack["id"], (start, 0.5), ha="center", va="center"
                            )
                    else:
                        settings.logger.warning(
                            f"IPAL ID {attack['ipalid']} from attack not found in dataset"
                        )

                # Draw attack ranges
                elif "start" in attack and "end" in attack:
                    start = attack["start"] - START
                    end = attack["end"] - START

                    for gap in gaps:
                        if attack["start"] - START > gap[0]:
                            start -= gap[1].total_seconds()
                            end -= gap[1].total_seconds()

                    borders = (start, end)

                    rect = matplotlib.patches.Rectangle(
                        (borders[0], 0),
                        borders[1] - borders[0],
                        1,
                        color="#510ac9"
                        if str(attack["id"]) in MARKEDATTACKS
                        else "#a50303",
                        linewidth=0,
                    )
                    ax.add_patch(rect)

                    if "id" in attack and plot_attack_ids:
                        rx, ry = rect.get_xy()
                        cx = rx + rect.get_width() / 2.0
                        cy = ry + rect.get_height() / 2.0
                        ax.annotate(attack["id"], (cx, cy), ha="center", va="center")

                else:
                    settings.logger.warning(
                        f"Attack {attack['ipalid']} ignored! Try again with `--draw-ticks`"
                    )

        if draw_ticks:
            ax.scatter(
                [a[0] for a in ATTACKS],
                [0.5] * len(ATTACKS),
                marker="x",
                color=["#510ac9" if a[1] else "#a50303" for a in ATTACKS],
                s=5,
            )

    else:
        settings.logger.warning("No attack file provided (--attacks)")
        settings.logger.warning("Plotting without attacks")
        ax.text(
            T[-1] // 2,
            0.5,
            "No attacks provided",
            verticalalignment="center",
            horizontalalignment="center",
        )

    # plotting settings
    end = END - START
    for gap in gaps:
        end -= gap[1].total_seconds()

    Nticks = 10
    ticksEvery = end // 3600 / Nticks
    ax.set_xticks([ticksEvery * 3600 * i for i in range(Nticks * 2)])
    ax.set_xticklabels(["%.1f" % (ticksEvery * i) for i in range(Nticks * 2)])
    ax.set_xlim(0, end)

    ax.set_ylabel(DATASETNAME, fontweight=1000, fontsize="x-large", labelpad=5)
    ax.yaxis.set_label_position("right")

    ax.set_ylim(count - 1, 1)
    ax.set_yticks([x + 0.5 for x in range(-len(IDSs), 1)][::-1])
    ax.set_yticklabels(["Attacks"] + [x[1] for x in IDSs])
    ax.tick_params(axis="y", which="both", color="white")


def main():
    global IDSs, ATTACKFILE, DATASETNAME, GAPTIME, SCORE, MIN_WIDTH, MARKEDATTACKS

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--attacks",
        metavar="attacks",
        help="path to attacks.json file of the dataset",
        required=False,
    )

    parser.add_argument(
        "--mark-attacks",
        metavar="list",
        help="plot single attacks in different colour. Specify attacks by attack ids, separated by ','",
        required=False,
    )

    parser.add_argument(
        "--draw-score",
        metavar="score",
        help="plot the score of an IIDS, specify the IIDS name to visualize or use 'default' for a single IIDS",
        required=False,
    )

    parser.add_argument(
        "--draw-attack-id",
        help="plot attack id on the attacks if provided by the attack file",
        required=False,
        action="store_true",
    )

    parser.add_argument(
        "--mark-fp",
        help="plot false alerts in different colour",
        required=False,
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "--draw-ticks",
        help="plot ticks instead of interval ranges, e.g., for communication-based IIDSs",
        required=False,
        action="store_true",
    )

    parser.add_argument(
        "--dataset",
        metavar="dataset",
        help="name of the dataset to put on the plot (Default: '')",
        required=False,
    )

    parser.add_argument(
        "--mark-skip",
        help="Indicate when a gap was introduced during plotting (see --max-gap)",
        required=False,
        default=False,
        action="store_true",
    )

    parser.add_argument(
        "--max-gap",
        metavar="minutes",
        help="Allowed time in minutes of data gaps until after which a gap is skipped. (Default: 30)",
        default=0,
        required=False,
    )

    parser.add_argument(
        "--min-width",
        metavar="seconds",
        help="Minimum width of attack bars in dataset entries (Default: 0)",
        default=0,
        required=False,
    )

    parser.add_argument(
        "--title",
        metavar="title",
        help="title to put on the plot (Default: '')",
        required=False,
    )

    parser.add_argument(
        "--output",
        metavar="output",
        help="file to save the plot to (Default: '': show in matplotlib window)",
        required=False,
    )

    parser.add_argument(
        "IDSs", metavar="IDS", nargs="+", help="IDS classification files"
    )

    # Logging
    parser.add_argument(
        "--log",
        dest="log",
        metavar="STR",
        help="define logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL) (Default: WARNING)",
        required=False,
    )
    parser.add_argument(
        "--logfile",
        dest="logfile",
        metavar="FILE",
        default=False,
        help="file to log to (Default: stderr)",
        required=False,
    )

    # Version number
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {settings.version}"
    )

    args = parser.parse_args()
    initialize_logger(args)

    IDSs = [
        (
            IDS,
            Path(IDS)
            .stem.replace(".json", "")
            .replace(".ipal", "")
            .replace(".state", ""),
        )
        for IDS in args.IDSs
    ]
    ATTACKFILE = args.attacks
    if args.dataset:
        DATASETNAME = args.dataset

    if args.draw_score:
        SCORE = args.draw_score

    if args.min_width:
        MIN_WIDTH = int(args.min_width)

    if args.max_gap:
        GAPTIME = int(args.max_gap)

    if args.mark_attacks:
        MARKEDATTACKS = args.mark_attacks.split(",")

    # Plot
    _, ax = plt.subplots(1)

    plt.xlabel("Elapsed Time [hours]")
    plot(
        ax,
        draw_ticks=args.draw_ticks,
        plot_attack_ids=args.draw_attack_id,
        mark_fp=args.mark_fp,
        mark_skip=args.mark_skip,
    )

    if args.title:
        plt.title(args.title)

    settings.logger.info("Plotting...")
    if args.output is not None:
        plt.savefig(args.output)
    else:
        plt.show()


if __name__ == "__main__":
    main()
