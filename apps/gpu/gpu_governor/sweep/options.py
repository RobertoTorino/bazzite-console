# SPDX-License-Identifier: GPL-3.0-or-later

"""The Advanced choices of the GPU sweep window as a ps5-gpu-sweep.sh command line, and the checks that go with them.
No Qt here, so the tests read it alone. The defaults and rails are the script's."""

from __future__ import annotations

from dataclasses import dataclass

DEFAULT_TIME_SECS = 180
MIN_TIME_SECS = 60
DEFAULT_ROUNDS = 3
MIN_ROUNDS, MAX_ROUNDS = 2, 9
DEFAULT_MAX_FREQ, HARD_MAX_FREQ = 2200, 2500
DEFAULT_MIN_VOLT, HARD_MIN_VOLT, HARD_MAX_VOLT = 850, 700, 1100
DEFAULT_FREQ_STEP, MIN_FREQ_STEP = 50, 25
DEFAULT_VOLT_STEP, MIN_VOLT_STEP = 25, 5


@dataclass
class SweepOptions:
    time_secs: int = DEFAULT_TIME_SECS
    rounds: int = DEFAULT_ROUNDS
    max_freq: int = DEFAULT_MAX_FREQ
    min_volt: int = DEFAULT_MIN_VOLT
    freq_step: int = DEFAULT_FREQ_STEP
    volt_step: int = DEFAULT_VOLT_STEP
    oc_volt: int = 0                    # 0: the config's top voltage
    per_boot: bool = False

    def validate(self) -> list[str]:
        errors = []
        if self.time_secs < MIN_TIME_SECS:
            errors.append(f"Load per attempt must be at least {MIN_TIME_SECS} seconds.")
        if not MIN_ROUNDS <= self.rounds <= MAX_ROUNDS:
            errors.append(f"Rounds must be between {MIN_ROUNDS} and {MAX_ROUNDS}.")
        if self.max_freq > HARD_MAX_FREQ:
            errors.append(f"The highest clock can be at most {HARD_MAX_FREQ} MHz.")
        if self.min_volt < HARD_MIN_VOLT:
            errors.append(f"The lowest voltage must be at least {HARD_MIN_VOLT} mV.")
        if self.oc_volt and self.oc_volt > HARD_MAX_VOLT:
            errors.append(f"The clock ladder's voltage can be at most {HARD_MAX_VOLT} mV.")
        if self.freq_step < MIN_FREQ_STEP:
            errors.append(f"The clock step must be at least {MIN_FREQ_STEP} MHz.")
        if self.volt_step < MIN_VOLT_STEP:
            errors.append(f"The voltage step must be at least {MIN_VOLT_STEP} mV.")
        return errors

    def to_args(self, only: str = "") -> list[str]:
        args = ["-t", str(self.time_secs), "-r", str(self.rounds), "--max-freq", str(self.max_freq),
                "--min-volt", str(self.min_volt), "--freq-step", str(self.freq_step),
                "--volt-step", str(self.volt_step)]
        if self.oc_volt:
            args += ["--oc-volt", str(self.oc_volt)]
        if self.per_boot:
            args.append("--per-boot")
        if only:
            args += ["--only", only]
        return args
