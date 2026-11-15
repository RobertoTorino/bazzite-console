# SPDX-License-Identifier: GPL-3.0-or-later
"""The kernel arguments of the PS5 loader's cmdline.txt: the line split into arguments (and joined again), and what
each argument the PS5 Linux command lines use does. Boot Command Line shows the line one argument per row, with its
description, and its info lists them all."""

from __future__ import annotations

import html
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Setting:
    key: str                                    # what comes before the "=", or the whole flag
    what: str                                   # what it does
    values: dict[str, str] = field(default_factory=dict)    # a value's own meaning
    example: str = ""                           # the argument the Add menu puts on the line


SETTINGS = (
    Setting("root", "The partition Linux starts its system from: <code>root=LABEL=&lt;name&gt;</code> by the "
            "partition's label, <code>root=UUID=&lt;id&gt;</code> by its file system's ID (the safe choice when two "
            "drives carry the same label). Without it Linux does not start."),
    Setting("rw", "Mounts the system read-write from the start.", example="rw"),
    Setting("rootwait", "Waits until the system's drive appears instead of stopping with an error: a USB drive or an "
            "SSD comes up a few seconds after the kernel starts.", example="rootwait"),
    Setting("console", "A console for the kernel's messages. The last <code>console=</code> on the line gets "
            "<code>/dev/console</code>: keep <code>console=tty0</code> last for the boot messages on the screen.",
            {"ttyTitania0": "the PS5's own serial port (the Titania UART inside the console); harmless without a "
                            "cable on it",
             "tty0": "the screen"}, "console=tty0"),
    Setting("video", "Starts a display output in a fixed mode: <code>video=DP-1:1920x1080@60</code> starts the HDMI "
            "port (the GPU calls it DP-1) at 1080p60, which avoids a black screen on a TV that mishandles the mode "
            "picked by itself. The desktop can still switch to 4K after login.", example="video=DP-1:1920x1080@60"),
    Setting("mitigations", "The kernel's guards against the CPU's speculative execution flaws (Spectre, Meltdown and "
            "the like).",
            {"off": "turns them off, for speed in games; without them a program could, in principle, read the memory "
                    "of other programs: keep them on where the console runs code you do not trust",
             "auto": "the kernel's default: on"}, "mitigations=off"),
    Setting("idle", "How the CPU idles.",
            {"halt": "plain HLT instead of the deeper MWAIT C-states, which works around hangs in the APU's "
                     "low-power states; remove it only if you see microstutter"}, "idle=halt"),
    Setting("preempt", "How far the kernel lets itself be interrupted (the kernel is built PREEMPT_DYNAMIC).",
            {"full": "fully preemptible: lower latency for the desktop and games",
             "voluntary": "only at points the kernel offers", "none": "never in the kernel: for servers"},
            "preempt=full"),
    Setting("hdmi.frl_4k120", "The PS5 HDMI driver and 4K120 over HDMI 2.1 FRL; it can be changed while Linux runs, "
            "in <code>/sys/module/hdmi/parameters/frl_4k120</code>.",
            {"0": "does not try FRL and stays on TMDS, up to 4K60: avoids a black screen on a TV whose FRL "
                  "negotiation fails",
             "1": "tries 4K120 over FRL"}, "hdmi.frl_4k120=0"),
    Setting("hdmi.hdcp_mode", "The PS5 HDMI driver's HDCP mode; it can be changed while Linux runs, in "
            "<code>/sys/module/hdmi/parameters/hdcp_mode</code>, from the next mode change.",
            {"-1": "keeps what is set", "0": "on", "1": "off", "2": "on, with HDCP 2.2: fixes a TV that shows a "
             "signal but a black picture and no sound, also at 4K60", "3": "off, with the HDCP 2.2 bit set (the "
             "kernel's default)"}, "hdmi.hdcp_mode=2"),
    Setting("nvme.max_host_mem_size_mb", "The NVMe Host Memory Buffer: system memory an SSD without DRAM of its own "
            "borrows as its cache.",
            {"0": "turns it off, a workaround of the PS5 patches for SSDs without DRAM"},
            "nvme.max_host_mem_size_mb=0"),
    Setting("nvme_core.default_ps_max_latency_us", "NVMe APST: the SSD's own switching to its low-power states.",
            {"0": "turns it off: the SSD never enters its low-power states, so it cannot drop off the bus"},
            "nvme_core.default_ps_max_latency_us=0"),
    Setting("plymouth.enable", "The boot splash (Plymouth) in the started system.", {"0": "off"},
            "plymouth.enable=0"),
    Setting("rd.plymouth", "The boot splash (Plymouth) in the initramfs.", {"0": "off"}, "rd.plymouth=0"),
    Setting("amd_iommu", "The IOMMU.",
            {"off": "keeps the kernel from using it. By default leave the IOMMU off. If it is on and you experience "
                    "an unstable system, turn it off again"}, "amd_iommu=off"),
    Setting("ttm.pages_limit", "How many 4 KiB pages of system memory the GPU may use: GB × 262144 "
            "(<code>ttm.pages_limit=3145728</code> is 12 GB). The other way to give the GPU more memory is the "
            "fixed VRAM in the loader's <code>vram.txt</code>.", example="ttm.pages_limit=3145728"),
)
BY_KEY = {s.key: s for s in SETTINGS}


def split(line: str) -> list[str]:
    """The arguments on *line*, as the kernel reads them: separated by spaces, a double-quoted part kept whole."""
    args, current, quoted = [], "", False
    for char in line.strip():
        if char == '"':
            quoted = not quoted
        if char.isspace() and not quoted:
            if current:
                args.append(current)
            current = ""
        else:
            current += char
    if current:
        args.append(current)
    return args


def join(args: list[str]) -> str:
    return " ".join(arg.strip() for arg in args if arg.strip())


def describe(arg: str) -> str:
    """What *arg* does, as plain text ("" for an argument this list does not know)."""
    key, _, value = arg.strip().partition("=")
    setting = BY_KEY.get(key)
    if setting is None:
        return ""
    text = plain(setting.what)
    meaning = setting.values.get(value)
    if meaning:
        text += f" {value}: {plain(meaning)}."
    return text


def plain(text: str) -> str:
    return html.unescape(text.replace("<code>", "").replace("</code>", ""))


def info_list() -> str:
    """Every argument and its values, as the info symbol's HTML."""
    rows = []
    for s in SETTINGS:
        values = "".join(f"<br>&nbsp;&nbsp;<code>{s.key}={v}</code>: {meaning}." for v, meaning in s.values.items())
        rows.append(f"<b><code>{s.key}</code></b>: {s.what}{values}")
    return "<br>".join(rows)
