#!/usr/bin/env python3
import enum
import gzip
import json
import os
import subprocess
import sys
import time

from ray import tune

import evaluate.settings as settings


class RunStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    SKIP = "skip"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


class IidsTrainable(tune.Trainable):
    # Wrapper for hiding .gz files
    def _open_file(self, filename, mode):
        if filename is None:
            return None
        elif filename.endswith(".gz"):
            return gzip.open(filename, mode=mode, compresslevel=settings.compresslevel)
        elif filename == "-":
            return sys.stdin
        else:
            return open(filename, mode=mode, buffering=1)

    def _save_status(self):
        with self._open_file(self.status_file, "w") as f:
            json.dump(self.status, f, indent=4)

        with self._open_file(self.runtime_file, "w") as f:
            json.dump(self.runtime, f, indent=4)

    def _run_substep(self, substep_name: str, cmd: str) -> int:
        # Executes a command and keeps track of its success status

        # Status management
        if self.status[substep_name] == RunStatus.SKIP:
            return

        elif self.status[substep_name] == RunStatus.SUCCESS:
            return

        elif self.status[substep_name] == RunStatus.ERROR:
            pass  # Retry command

        # Run command
        self.status[substep_name] = RunStatus.RUNNING
        self._save_status()

        start_time = time.time()

        process = subprocess.run("exec " + cmd, capture_output=True, shell=True)
        end_time = time.time()

        # Status management
        if process.returncode == 0:
            self.status[substep_name] = RunStatus.SUCCESS
            self.runtime[substep_name] += end_time - start_time
            self._save_status()

        else:
            self.status[substep_name] = RunStatus.ERROR
            self._save_status()
            raise Exception(f"{substep_name} failed\n{cmd}\n{process.stderr.decode()}")

    def _merge_files(self):
        self.status["merging"] = RunStatus.RUNNING
        self._save_status()

        t1 = time.time()

        with self._open_file(self.output_file, "wt") as fout:
            for testfile in self.settings["test_files"]:
                with self._open_file(os.path.basename(testfile), "rt") as fin:
                    fout.writelines(fin.readlines())

        self.runtime["merging"] += time.time() - t1
        self.status["merging"] = RunStatus.SUCCESS

        self.cleanup()

    def _compute(self):
        logging = f'--log {self.settings["log-level"]} --logfile {self.log_file}'

        # Train IIDS
        cmd = f"ipal-iids {logging}"  # --retrain" # not needed. use restart-experiment
        cmd += f' --config "{self.config_iids}"'
        cmd += f' --train.{self.settings["file_type"]} "{self.settings["train_file"]}"'
        cmd += f' --combiner.config "{self.config_combiner}"'
        if self.settings["combiner_file"] is not None:
            cmd += f' --train.combiner "{self.settings["combiner_file"]}"'
        self._run_substep("train", cmd)

        # Perform live detection
        # TODO this may fail!!! if there are multiple files and it is interrupted in e.g. the second try
        for in_file in self.settings["test_files"]:
            out_file = os.path.basename(in_file)

            # Avoid step being skipped
            self.status["live"] = RunStatus.NOT_STARTED
            self.status["extend_alarms"] = RunStatus.NOT_STARTED
            self.status["minimize"] = RunStatus.NOT_STARTED

            # ipal-iids detection
            cmd = f"ipal-iids {logging}"
            cmd += f' --config "{self.config_iids}"'
            cmd += f' --combiner.config "{self.config_combiner}"'
            cmd += f' --live.{self.settings["file_type"]} "{in_file}"'
            cmd += f' --output "{out_file}"'
            self._run_substep("live", cmd)

            # Extend alarms
            if self.settings["extend_alarms"]:
                cmd = f'ipal-extend-alarms {logging} "{out_file}"'
                self._run_substep("extend_alarms", cmd)
            else:
                self.status["extend_alarms"] = RunStatus.SKIP
                self._save_status()

            # Minimize
            cmd = f'ipal-minimize {logging} --all "{out_file}"'
            self._run_substep("minimize", cmd)

        # Merge files
        try:
            self._merge_files()
        except:  # noqa: E722
            self.status["merging"] = RunStatus.ERROR
            self._save_status()
            raise "Merging failed"
        self.cleanup()

        # Evaluate
        cmd = f"ipal-evaluate {logging}"
        if self.settings["attack_file"] is not None:
            cmd += f' --attacks "{self.settings["attack_file"]}"'
        cmd += f' --timed-dataset "{self.settings["is_timed_dataset"]}"'
        cmd += f' --output "{self.evaluate_file}" "{self.output_file}"'
        self._run_substep("evaluate", cmd)
        self.cleanup()

    def setup(self, config: dict) -> None:
        # Prepare config
        if "_postprocess" in config:
            config = config["_postprocess"](config)
            del config["_postprocess"]
        self.settings = config["tune_config"]

        # File paths
        self.config_iids = "config-iids.json"
        self.config_combiner = "config-combiner.json"
        self.output_file = f'output.{self.settings["file_type"]}.gz'
        self.evaluate_file = "evaluate.json"
        self.log_file = "logfile.txt"
        self.status_file = "status.json"
        self.runtime_file = "runtime.json"

        # Write config files
        with self._open_file(self.config_iids, "w") as f:
            json.dump(config["iids"], f, indent=4)
        with self._open_file(self.config_combiner, "w") as f:
            json.dump(config["combiner"], f, indent=4)

        # Initiate status
        if os.path.exists(self.status_file):
            with self._open_file(self.status_file, "r") as f:
                self.status = json.load(f)
            self.status = {k: RunStatus(v) for k, v in self.status.items()}
        else:
            self.status = {
                "train": RunStatus.NOT_STARTED,
                "live": RunStatus.NOT_STARTED,
                "extend_alarms": RunStatus.NOT_STARTED,
                "minimize": RunStatus.NOT_STARTED,
                "merging": RunStatus.NOT_STARTED,
                "evaluate": RunStatus.NOT_STARTED,
            }

        # Initiate runtime
        if os.path.exists(self.runtime_file):
            with self._open_file(self.runtime_file, "r") as f:
                self.runtime = json.load(f)
        else:
            self.runtime = {
                "train": 0,
                "live": 0,
                "extend_alarms": 0,
                "minimize": 0,
                "merging": 0,
                "evaluate": 0,
            }

    def step(self):
        # If not completed, perform the evaluation
        if self.status["evaluate"] != RunStatus.SUCCESS:
            self._compute()

        # Read results from file
        with open(self.evaluate_file, "r") as f:
            return json.load(f)

    def cleanup(self):
        self._save_status()

        # Remove intermediate test files
        if self.status["merging"] == RunStatus.SUCCESS:
            for file in self.settings["test_files"]:
                file = os.path.basename(file)
                if os.path.exists(file):
                    os.remove(file)

        # Remove combined test file
        if self.status["evaluate"] == RunStatus.SUCCESS:
            if not self.settings["keep_output"]:
                if os.path.exists(self.output_file):
                    os.remove(self.output_file)
