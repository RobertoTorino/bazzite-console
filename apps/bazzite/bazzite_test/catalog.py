# SPDX-License-Identifier: GPL-3.0-or-later
"""Test catalog, grouped the same way as the categories in the manual. PS5 version (from BC-250 Bazzite Test 2.0.1):
tests 54-57 are the PS5's own; the BC-250's system score is left out (a PS5 has no disabled CUs or cores to
compare against)."""

from __future__ import annotations

from dataclasses import dataclass, field

STRESS_TEST_ID = "41"
BENCH_TEST_ID = "42"
DISK_TEST_ID = "43"
SPEEDTEST_TEST_ID = "44"


@dataclass(frozen=True)
class TestDef:
    id: str
    name: str
    checks: str


@dataclass(frozen=True)
class Category:
    key: str
    title: str
    tests: list[TestDef] = field(default_factory=list)

    @property
    def test_ids(self) -> list[str]:
        return [t.id for t in self.tests]


CATEGORIES: list[Category] = [
    Category("system", "System", [
        TestDef("00", "Platform Identification",
                "Confirms a PlayStation 5 (DMI) on the ps5-linux kernel (its PS5 drivers), Bazzite, the kernel, and "
                "that the loader's bzImage on /boot/efi is the running kernel."),
        TestDef("01", "Running Services", "Lists every active systemd service."),
        TestDef("02", "Failed Units", "Errors on any unit in a failed state."),
        TestDef("03", "System Uptime", "Reports uptime and load average."),
        TestDef("11", "Resource Consumption", "Top CPU and memory consumers."),
        TestDef("12", "Boot Time", "systemd-analyze breakdown, warns on units taking over a minute."),
        TestDef("31", "File and Directory Integrity", "Verifies /var/log exists and is writable."),
    ]),
    Category("network", "Network", [
        TestDef("04", "Network Connectivity", "Pings an external host."),
        TestDef("05", "DNS Resolution", "Resolves a known hostname."),
        TestDef("06", "Public Internet Access", "Fetches a URL over HTTPS."),
        TestDef("07", "Open Ports", "Lists listening TCP/UDP sockets."),
        TestDef("08", "NTP Synchronization", "Confirms the clock is synchronized."),
        TestDef("30", "SSH Service", "Reports sshd.service / sshd.socket state (off by default on Bazzite)."),
        TestDef("53", "Wi-Fi Adapter",
                "Every Wi-Fi adapter, its driver, firmware and connection; the PS5's IW620 on moal and its firmware staging."),
        TestDef(SPEEDTEST_TEST_ID, "Internet Speed",
                "Opt-in. Ookla speedtest (or speedtest-cli): download, upload, idle and loaded latency "
                "(bufferbloat), packet loss, and whether the network port is the limit. Uses ~1 GB of data "
                "on a fast line."),
    ]),
    Category("storage", "Storage and memory", [
        TestDef("09", "Disk Configuration", "Filesystem usage and mount points."),
        TestDef("10", "NVMe Devices",
                "Detection, PCIe link speed/width vs. what drive and slot support, DRAM cache or host memory "
                "buffer (DRAM-less), and SMART health: wear, errors, temperature, unsafe shutdowns."),
        TestDef("14", "Memory and Swap",
                "RAM usage and the full swap topology: zram, zswap, disk swap, overlaps and swappiness."),
        TestDef("37", "Unified Memory and VRAM Pressure",
                "VRAM/GTT usage, OOM-kill history, vm.max_map_count, swappiness."),
        TestDef("49", "CPU Memory Bandwidth",
                "stress-ng STREAM-like bandwidth on 1 thread and all threads; shows the GDDR6 latency cost "
                "the CPU pays for the GPU's console-class bandwidth."),
        TestDef(DISK_TEST_ID, "Disk Speed (read, write, SLC cache)",
                "Opt-in. Sequential and random 4K read of the system disk (read-only); optionally writes a "
                "temporary file to measure write speed and where the SLC cache runs out."),
    ]),
    Category("logs", "System logs", [
        TestDef("15", "Boot Logs",
                "Current-boot kernel errors, with known-benign PS5 and Bazzite noise filtered out."),
        TestDef("16", "System Journal", "Journal errors from the last 7 days, same filtering."),
    ]),
    Category("gpu", "GPU and graphics", [
        TestDef("17", "amdgpu Driver",
                "Confirms amdgpu is bound to the PS5 APU (Oberon, Cyan Skillfish family)."),
        TestDef("18", "GPU Governor",
                "The kernel's ps5-gpufreq (devfreq) sets the GPU clock: its governor and the temperature limit. Warns when a BC-250 governor is installed."),
        TestDef("19", "GPU Frequency Scaling",
                "The ps5-gpufreq clock steps (500-2230 MHz), the allowed range and the clock changes since boot."),
        TestDef("20", "Vulkan / Mesa", "Confirms RADV reports GFX1013 and not the llvmpipe software fallback."),
        TestDef("21", "Compute Unit Count",
                "Active CUs from the kernel (36 on a PS5, 60 on a Pro), and RADV's view when vulkaninfo is there."),
        TestDef("47", "Vulkan Futureproof Matrix",
                "Vulkan API level and the feature set modern games need: ray tracing, mesh shaders, VRS, "
                "pipeline libraries and the VRAM carveout vs today's 8 GiB recommendation. Hard evidence of "
                "which current and upcoming titles can run at all."),
        TestDef("50", "Video Decode and Encode (VCN)",
                "vainfo codec matrix: H.264/HEVC/VP9/AV1 decode and encode. Matters for streaming, OBS "
                "recording and video playback while gaming."),
        TestDef("51", "HDMI-CEC",
                "The PS5's CEC adapter (the kernel's ps5-cec), whether the TV answers, and Bazzite's CEC mode. Whether the PS5 can turn the TV on and off."),
        TestDef("52", "HDMI-CEC Services",
                "Whether the services behind the TV control run: Valve's CEC daemon (cecd), HDMI CEC Manager's background service when installed, and Bazzite's dGPU CEC services when enabled."),
        TestDef("29", "Display Session",
                "Display manager, session and compositor, and the PS5 HDMI state (recovery status, HDCP, FRL)."),
    ]),
    Category("cpu", "CPU and firmware", [
        TestDef("23", "IOMMU",
                "Counts IOMMU groups. Information only: on the PS5 the IOMMU may stay on."),
        TestDef("24", "CPU Mitigations",
                "Whether mitigations=off is set (the ps5-linux cmdline does, for speed) and what the CPU reports."),
        TestDef("25", "CPU Core and Thread Count",
                "Reports cores and threads: the PS5 CPU has 8 cores and 16 threads."),
        TestDef("26", "CPU Power Management",
                "The PS5 has no cpufreq: the CPU clock now, and ps5-linux-tools' boost (3.5 GHz) when installed."),
    ]),
    Category("stability", "Stability and thermals", [
        TestDef("22", "Hardware Sensors",
                "ps5_fan (SoC and board temperatures, the fan's duty and curve), k10temp, the GPU (kernel 7.3.1 on) and NVMe."),
        TestDef("27", "Handheld Daemon",
                "Confirms hhd.service is masked: the PS5 has no handheld controls and it can cause micro-stuttering."),
        TestDef("28", "Suspend Targets",
                "Whether the kernel can suspend (s2idle), whether systemd may, the sleep hooks and the suspends since boot."),
        TestDef("40", "Power Delivery and Throttling",
                "The GPU's clock ceiling and temperature limit, and the kernel's throttle messages."),
    ]),
    Category("crash", "Crash forensics", [
        TestDef("34", "Previous Boot Shutdown Integrity",
                "Flags previous boots that ended with no shutdown sequence — the signature of a hard lockup."),
        TestDef("35", "GPU Hang and Reset History",
                "Ring timeouts, GPU resets, VM faults and soft recoveries across retained boots."),
        TestDef("36", "Kernel Panic, Lockup and Crash Dump",
                "Oopses, soft/hard lockups, call traces, coredumpctl records and NMI watchdog state."),
    ]),
    Category("gaming", "Gaming", [
        TestDef("38", "Steam and Gaming Stack", "Steam, gamescope, gamemode, MangoHud, umu; library paths and free space."),
        TestDef("39", "Audio Stack", "PipeWire/WirePlumber state, default sink and ALSA cards."),
        TestDef(STRESS_TEST_ID, "CPU + GPU Stress and Telemetry",
                "Opt-in. Loads the PS5 and records the GPU clock, temperatures (GPU, SoC, CPU), the fan's duty and the "
                "load throughout; includes a sustained-performance verdict (first minute vs last minute)."),
        TestDef("48", "Real-Game Frametime (MangoHud logs)",
                "Reads the most recent MangoHud logs from real play sessions: average FPS, 1% and 0.1% lows "
                "and stutter share — evidence from actual games, which synthetic benchmarks cannot give."),
    ]),
    Category("performance", "Performance", [
        TestDef(BENCH_TEST_ID, "Performance Benchmark (CPU / GPU score)",
                "Opt-in. CPU single/multi-thread (stress-ng) and GPU FP32 compute (vkpeak), scored against a baseline "
                "saved on this PS5 (= 100) to compare kernels and settings, plus a ladder against known systems."),
    ]),
    Category("ps5", "PS5", [
        TestDef("54", "Loader and Boot Partition",
                "Where the loader's FAT partition is (USB stick or SSD) and that it is /boot/efi, cmdline.txt and "
                "vram.txt, a second partition labelled boot (the wrong one may be mounted), free space."),
        TestDef("55", "HDMI Output (ps5-linux)",
                "The HDMI bridge's state: recovery status, mode, colour depth, HDCP mode and failures, FRL."),
        TestDef("56", "Bluetooth (IW620 / MediaTek)",
                "Whether the IW620's Bluetooth half runs its firmware (480 Mbit/s) or fell back to ROM mode, the "
                "controller, and the sleep hook that keeps it across suspend; a MediaTek combo on other consoles."),
        TestDef("57", "ps5-linux-tools",
                "The boost (ps5boost: CPU 3.5 GHz) and fan (ps5fan) services of ps5-linux-tools, when installed."),
        TestDef("58", "Firmware Versions",
                "The model (CFI-...), the south bridge revision, the GPU's firmware (PSP, VCN, ...), the IW620's driver "
                "and firmware, the last DualSense's. The PS5 system software version is not visible to Linux."),
        TestDef("59", "USB Storage",
                "USB drives (the loader's drive, data SSDs): the bridge chip, UAS or usb-storage, the link speed, "
                "SMART polling (reported to upset some USB-NVMe bridges) and USB resets."),
    ]),
    Category("updates", "Updates", [
        TestDef("13", "Security Configuration", "firewalld zones and SELinux enforcement mode."),
        TestDef("32", "OSTree Deployment",
                "Atomic Bazzite: the deployments and a staged one waiting for a reboot. A flattened PS5 image has none."),
        TestDef("33", "Update and Patch",
                "Available updates: dnf on a flattened image, rpm-ostree on an Atomic one; Flatpak remotes."),
        TestDef("45", "Installed Packages",
                "Counts installed software per source: image RPMs, layered and overridden packages, Flatpak "
                "apps (system and user), Homebrew, AppImages and Distrobox containers. Names and versions only."),
    ]),
]

TESTS: dict[str, TestDef] = {t.id: t for c in CATEGORIES for t in c.tests}
CATEGORY_OF: dict[str, Category] = {t.id: c for c in CATEGORIES for t in c.tests}
