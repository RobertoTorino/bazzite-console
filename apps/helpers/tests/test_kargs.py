# SPDX-License-Identifier: GPL-3.0-or-later
"""The kernel arguments: the line split as the kernel reads it and joined again, and what each known one does."""

from __future__ import annotations

from helpers import kargs

PS5 = ("root=LABEL=bazzite rw rootwait console=ttyTitania0 console=tty0 video=DP-1:1920x1080@60 mitigations=off "
       "idle=halt preempt=full hdmi.frl_4k120=0 nvme.max_host_mem_size_mb=0 nvme_core.default_ps_max_latency_us=0 "
       "hdmi.hdcp_mode=2 plymouth.enable=0 rd.plymouth=0 amd_iommu=off ttm.pages_limit=3145728")


def test_split_and_join_keep_the_line():
    assert kargs.split("  root=UUID=1  rw\tquiet \n") == ["root=UUID=1", "rw", "quiet"]
    assert kargs.split('root=UUID=1 dyndbg="file x.c +p" rw') == ["root=UUID=1", 'dyndbg="file x.c +p"', "rw"]
    assert kargs.join(["root=UUID=1", " ", "rw "]) == "root=UUID=1 rw"
    assert kargs.join(kargs.split(PS5)) == PS5


def test_every_argument_of_the_ps5_lines_is_described():
    for arg in kargs.split(PS5):
        assert kargs.describe(arg), arg
    assert "<" not in kargs.describe("ttm.pages_limit=3145728")                # plain text in the table
    assert "on, with HDCP 2.2" in kargs.describe("hdmi.hdcp_mode=2")
    assert kargs.describe("hdmi.hdcp_mode=7") == kargs.plain(kargs.BY_KEY["hdmi.hdcp_mode"].what)
    assert kargs.describe("my.option=1") == "" and kargs.describe("") == ""


def test_the_add_menu_and_the_list():
    examples = [s.example for s in kargs.SETTINGS if s.example]
    assert all(kargs.describe(e) for e in examples) and "root" not in {s.key for s in kargs.SETTINGS if s.example}
    listed = kargs.info_list()
    assert all(f"<code>{s.key}</code>" in listed for s in kargs.SETTINGS) and "hdmi.hdcp_mode=-1" in listed
