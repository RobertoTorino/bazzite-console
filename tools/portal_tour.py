#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A video tour of the Bazzite Console portal, for the wiki and YouTube: the real portal view from this checkout, driven by a
script and rendered frame by frame into an MP4 (H.264, 1920 x 1080, 30 fps), with the portal's own intro sound and
welcome, then music under it that fades out over the last two seconds (tools/sounds/the_quiet_engine_remix.ogg, the
remix of the app tours' track, three minutes long so it does not loop within the tour; made with generative AI
tools).

    python3 tools/portal_tour.py [OUT.mp4] [--music FILE | --no-music] [--no-voice] [--wiki] [--fps 30]
                                 [--size 1080p|1440p|2160p]

The tour opens as the portal does (owner, 24-11-2026): the title card in silence, then the intro with its sound and
the welcome after it. The music starts when the welcome has ended. A voice reads every caption out (Nexus TTS's
engine, dev/text, with its default voice). The music under the voice is quiet (VOICE_MUSIC). A few words are spoken as
tools/tour_frames.py's SPOKEN says, so the voice says them right. --no-voice records the tour without the voice, with
the music at full volume. A caption stays until it is spoken, or read without the voice, before the view changes.
The voice needs the speech engine: set it up once in Nexus TTS (Set up the speech engine).

--size 2160p renders the same tour at 3840 x 2160 for YouTube, which shows a 4K upload far sharper than a 1080p one
(about four times the time); the wiki's copy is the same whatever the size.

--wiki also writes the copy on the wiki's Portal Tour page: docs/videos/portal-tour.mp4 (1280 x 720, smaller) and its
poster, docs/images/portal/portal-tour-poster.webp (the title card).

The wiki's video must keep up with the portal (owner, 14-11-2026). --wiki also writes tools/portal-tour.stamp: a
fingerprint of what the video shows (the portal's code and pictures, and this script). --check says whether the
portal changed since (exit 1 when it did), and tools/tests runs it, so CI fails until the tour is recorded again
with --wiki. For a change that does not show in the video (a fix behind the window), --stamp writes the stamp
without recording: look at the video first.

It runs offscreen in a temporary home folder: a few apps "installed" (their detect paths and records), one of them
behind its pinned release so the update notice shows, no network, and nothing from the machine it runs on (no user
or host names, no checkout path), no sound from the portal while it records and no controller. The pointer, the
clicks and the captions are drawn into the frames. Needs PyQt6 (the dev venv) and ffmpeg with libx264.
The frames are drawn by tools/tour_frames.py, which tools/app_tour.py uses too."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
from pathlib import Path

SUITE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SUITE / "tools"))            # tour_frames.py, the Nexus tools'

import tour_frames  # noqa: E402
from tour_frames import SCALE, Recorder  # noqa: E402

INSTALLED = ("board", "rpcs3", "remoteplay", "shadps4", "datstation")
BEHIND = "shadps4"
MUSIC = tour_frames.MUSIC_DIR / "the_quiet_engine_remix.ogg"    # the portal tour's own: longer than the tour
FADE = 2.0                                          # the music fades out over the video's last seconds
VOICE_MUSIC = 0.12                                  # the music under the voice (owner, 24-11-2026: 35 % too loud)
VOICE_VOLUME = 2.0                                  # the voice twice as loud as the engine makes it (owner)
READ = 0.25                                         # seconds a caption stays per word before the view changes
GAP = 0.4                                           # seconds of quiet after a spoken caption
CLOSING = "Thank you and have fun using the Portal."   # over the end card (owner, 24-11-2026)
TTS = SUITE / "dev" / "text"                        # Nexus TTS: its speech engine reads the captions
WIKI_VIDEO = SUITE / "docs" / "videos" / "portal-tour.mp4"
WIKI_POSTER = SUITE / "docs" / "images" / "portal" / "portal-tour-poster.webp"
STAMP = SUITE / "tools" / "portal-tour.stamp"       # the fingerprint of the portal the wiki's video was recorded from
SHOWN = (SUITE / "portal" / "bazzite_console_portal", SUITE / "portal" / "images")    # what the video shows, with this script
MANIFEST = SUITE / "portal" / "apps.toml"            # its tiles show in the video (tiles())


def prepare_home(home: Path) -> None:
    tour_frames.prepare_home(home)
    sys.path[:0] = [str(SUITE / "portal")]


class Tour(Recorder):
    def __init__(self, out: Path, fps: int, home: Path, speaker: tour_frames.Speaker | None = None):
        from PyQt6.QtCore import QSettings
        from PyQt6.QtWidgets import QApplication

        from bazzite_console_core.app import create_app
        from bazzite_console_portal import INFO, LOGO_PATH, MANIFEST, audio, music, state_dir
        from bazzite_console_portal.gamepad import Gamepad
        from bazzite_console_portal.manifest import load
        from bazzite_console_portal.sources import Records, Sources

        self.home = home
        self.speaker = speaker
        self.cues: list[tuple[float, Path, float]] = []     # the sounds under the video: second, file, volume
        self.music_at = 0.0                                 # the music starts when the welcome has ended
        self.until = 0                                      # the frame the caption is spoken or read by
        app = QApplication.instance() or create_app(INFO, [])
        for fmt in (QSettings.Format.NativeFormat, QSettings.Format.IniFormat):
            QSettings.setPath(fmt, QSettings.Scope.UserScope, str(home / ".config"))
        entries = load(MANIFEST)
        records = {}
        for entry in entries:
            if entry.key in INSTALLED:
                for path in entry.detect:
                    target = Path(os.path.expanduser(os.path.expandvars(path)))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.touch()
                records[entry.key] = entry.tag
                if entry.key == BEHIND:
                    major, minor, _ = entry.version.split(".")
                    records[entry.key] = f"{entry.key}-v{major}.{max(int(minor) - 1, 0)}.0"
        state_dir().mkdir(parents=True, exist_ok=True)
        (state_dir() / "installed.json").write_text(json.dumps(records), encoding="utf-8")
        from bazzite_console_portal.main_window import MainWindow

        class Silent(audio.Sounds):                 # the Sound pill as on a board with an output, but nothing plays
            def available(self) -> bool:
                return True

            def play(self, name: str) -> bool:
                return False

        def no_controller():
            raise OSError("no controller in the tour")

        window = MainWindow(entries, Sources(state_dir() / "releases", checkout=None, download=None),
                            Records(state_dir() / "installed.json"), desktop=home / "Desktop",
                            menu=home / ".local/share/applications", sounds=Silent(),
                            gamepad=Gamepad(source_factory=no_controller), music_player=music.Silent())
        window.setWindowTitle(INFO.display_name)
        window.big.version.setText("")              # no version in the video: it stays right through a release
        tour_frames.place(window)
        window.show()
        for _ in range(3):
            app.processEvents()
        super().__init__(out, fps, window, LOGO_PATH)

    # --- the tour -------------------------------------------------------------------------------------------
    def run(self) -> None:
        from bazzite_console_core.appinfo import SUITE_MANUAL_URL
        from bazzite_console_portal.main_window import CATEGORY_HINTS
        from bazzite_console_portal.manifest import CATEGORIES

        w = self.window
        title = self.card("Bazzite Console Suite", ["A tour of the portal"])
        self.overlay = title
        self.emit(title, round(3.5 * self.fps))
        self.overlay = None
        self.intro(title)

        self.say("The portal installs, updates and starts every app of the suite on Bazzite.")
        self.hold(3.5)
        self.say("One fullscreen view, for the keyboard, the mouse or a controller: its header, the suite's icon and name.")
        self.move(self.at(w.big.logo))
        self.hold(3)
        self.say("A click on the icon plays this tour, over the whole screen.")
        self.hold(2.5)
        self.move(self.at(w.big.title))
        self.say("A click on the name opens the wiki: everything about each app.")
        self.hold(1.2)
        self.click()                                # only the ring: the tour opens no browser
        self.hold(0.8)
        shown = self.frame()
        wiki = self.card("Wiki", [SUITE_MANUAL_URL.removeprefix("https://").rstrip("/")])
        self.fade(shown, wiki, 0.6)
        self.emit(wiki, round(2.8 * self.fps))
        self.fade(wiki, shown, 0.6)
        self.say("The symbols: Refresh looks again at which apps are installed.")
        self.move(self.at(w.refresh_button), 0.6)
        self.hold(2.6)
        self.say("☰ opens the Settings page, as the ☰ button on a controller does.")
        self.move(self.at(w.settings_button), 0.6)
        self.click(w.toggle_settings)
        self.hold(1.4)
        for pill, text in ((w.icons_box, "Icons on Desktop: one icon per app on the Desktop, or only the portal's."),
                           (w.music_box, "Music: a quiet track while the portal is in front, its own or yours."),
                           (w.theme_pill, "The theme switcher: one look for every app in the suite."),
                           (w.wallpaper_pill, "And a wallpaper of your own behind the portal, seen through the pills.")):
            self.say(text)
            self.move(self.at(pill), 0.6)
            self.hold(2.6)
        self.say("B, Escape or ☰ again goes back to the apps.")
        self.move(self.at(w.settings_button), 0.6)
        self.click(w.toggle_settings)
        self.hold(1.4)

        self.say("An app with a newer release gets a red dot, and the notice beside the categories counts it.")
        self.move(self.at(w.big.notice))
        self.hold(3.5)
        first = w.big.tiles["board"]
        self.say("Every app has a tile: its own icon, its name, and under it whether it is installed.")
        self.move(self.at(first, 0.5, 0.3))
        self.hold(3.5)
        self.say("Board Test checks the board. It is always installed, as the first tile on Sustainable.")
        self.hold(3)
        self.say("Hover over a tile and a tip pops up: what the app does, its release, and how to open it.")
        self.show_tip(first)
        self.hold(4.5)
        self.hide_tip()
        other = self.top_row_tile(installed=False)
        if other is not None:
            self.move(self.at(other, 0.5, 0.3), 0.7)
            self.say("Every tile has one, installed or not. The symbols and the pills have their own tips too.")
            self.show_tip(other)
            self.hold(4.5)
            self.hide_tip()
        self.say("A press on a tile opens its app; its menu installs, updates and uninstalls it, in a terminal.")
        self.move(self.at(first, 0.5, 0.6))
        self.click(lambda: self.open_tile_menu(first))
        self.hold(3.5)
        self.popup.close()
        self.popup = None
        self.pump()
        board = next((w.big.tiles[k] for k, s in w.states.items() if s.entry.changes_board and s.installed), None)
        if board is not None:
            self.say("Apps that change how the board runs carry a mark, and the portal asks first. "
                     "All of them are software-only and can be undone.")
            self.move(self.at(board, 0.5, 0.3))
            self.show_tip(board)                    # its tip says what it changes, under "Changes the board"
            self.hold(5)
            self.hide_tip()

        self.say("")
        for index, category in enumerate(w.big.categories[1:], 1):
            self.move(self.tab_at(w.big.bar, index), 0.7)
            self.click(lambda i=index: w.big.bar.setCurrentIndex(i))
            self.say(f"{CATEGORIES[category]}: {CATEGORY_HINTS[category]}")
            self.hold(3.8)
        self.say("")
        self.move(self.tab_at(w.big.bar, 0), 0.7)
        self.click(lambda: w.big.bar.setCurrentIndex(0))
        self.hold(0.6)

        self.move(self.at(w.settings_button), 0.6)
        self.click(w.toggle_settings)
        self.hold(0.6)
        self.say("The Wallpaper pill: your own picture, the example the portal starts with, one used before, or none.")
        self.move(self.at(w.wallpaper_pill))
        self.click(lambda: self.open_menu())
        self.hold(2.5)
        slider = w.transparency_slider
        self.move(self.at_slider(slider, slider.value()), 0.5)
        self.say("Transparency sets the veil of the theme's color over it, and the view changes while you move it.")
        self.hold(0.6)
        for target in (85, 40):
            self.drag(slider, target, 1.2)
            self.hold(0.5)
        self.hold(1)
        self.popup.close()
        self.popup = None
        self.pump()
        self.move(self.at(w.settings_button), 0.6)
        self.click(w.toggle_settings)
        self.hold(0.6)

        self.controller()

        self.move(self.at(w.settings_button), 0.6)
        self.click(w.toggle_settings)
        self.hold(0.6)
        self.say("Gunmetal, Silver or Warm: each app takes the theme the next time it starts.")
        self.move(self.at(w.theme_pill))
        self.click(w._next_theme)
        self.hold(1.5)
        last = self.frame()
        for name in ("silver", "warm"):
            still = self.still(name)
            self.fade(last, still, 0.5)
            self.emit(still, round(2.2 * self.fps))
            last = still
        self.caption = ""
        end = self.card("Bazzite Console Suite", ["Everything about each app is in the wiki:",
                                               SUITE_MANUAL_URL.removeprefix("https://").rstrip("/")])
        self.fade(last, end, 0.8)
        self.overlay = end
        self.say(CLOSING)
        self.hold(5)
        self.wait()

    def intro(self, before) -> None:
        """The intro the portal opens with, frame by frame from the title card (the intro follows the video's
        frames, not the clock), ending with the focus on the first tile. Its sound plays as the animation starts and
        the welcome when it has ended, as in the portal, at the portal's volumes. The music starts after the
        welcome."""
        from bazzite_console_portal import audio
        from bazzite_console_portal.bigpicture import INTRO_MS

        w = self.window
        w.start_up()
        intro = w.intro
        intro.animation.stop()
        pointer, self.pointer = self.pointer, (-100, -100)
        self.say("")
        intro._step(0.0)
        self.pump()
        self.fade(before, self.frame(), 0.8)
        self.sound(audio.SOUNDS / f"{audio.INTRO}.wav", audio.VOLUMES.get(audio.INTRO, audio.VOLUME))
        frames = round(INTRO_MS / 1000 * self.fps)
        for i in range(1, frames + 1):
            intro._step(i / frames)
            self.pump()
            self.emit(self.frame())
        intro._done()
        self.pump()
        welcome = audio.SOUNDS / f"{audio.WELCOME}.wav"
        if welcome.is_file():                       # a suite without the file plays none, as the portal
            self.sound(welcome, audio.VOLUMES.get(audio.WELCOME, audio.VOLUME))
            self.hold(tour_frames.duration(welcome) + 0.3)
        else:
            self.hold(0.8)
        self.music_at = self.frames / self.fps
        self.pointer = pointer

    def controller(self) -> None:
        """The focus moved as a controller moves it, and the categories changed with the shoulder buttons."""
        w = self.window
        pointer, self.pointer = self.pointer, (-100, -100)
        w.big.focus_first()
        self.pump()
        self.say("The d-pad, the stick or the arrow keys move the focus; A or Enter opens the app, X its menu, Y updates.")
        self.hold(1.2)
        for direction in ("right", "right", "right", "right", "left", "left"):     # the top row: above the captions
            w.big.move_focus(direction)
            self.hold(0.7)
        self.hold(1)
        self.say("LB and RB, or Page Up and Page Down, change the category.")
        for _ in range(2):
            w.big.change_category(1)
            self.hold(1.8)
        w.big.change_category(-2)
        self.hold(0.6)
        self.say("Up from the top row reaches the symbols and the notices; everything works the same with a mouse.")
        w.big.move_focus("up")
        self.hold(2.5)
        w.big.focus_first()
        self.hold(0.8)
        self.pointer = pointer

    def open_tile_menu(self, tile) -> None:
        self.popup = self.window.tile_menu(self.window.states[tile.key].entry)
        self.popup.popup(tile.mapToGlobal(tile.rect().bottomLeft()))
        self.pump()

    def top_row_tile(self, installed: bool):
        """A tile of the top row (above the captions) after the first, installed or not; None when there is none."""
        w = self.window
        shown = sorted((t for t in w.big.tiles.values() if t.isVisible()), key=lambda t: (t.y(), t.x()))
        return next((t for t in shown[1:] if t.y() == shown[0].y() and w.states[t.key].installed == installed), None)

    def show_tip(self, widget) -> None:
        """*widget*'s tooltip as the portal shows it under the mouse, at the pointer: core's RoundedToolTip, with its
        rounded border and padding, drawn into the frames as a menu is. It stays until hide_tip()."""
        from PyQt6.QtCore import QPoint

        from bazzite_console_core.widgets import RoundedToolTip, show_tooltip
        x, y = self.pointer
        y += 30                                     # below the drawn arrow, as under a real pointer
        show_tooltip(self.window.mapToGlobal(QPoint(round(x / SCALE), round(y / SCALE))), widget.toolTip(), widget)
        self.pump()
        self.popup = RoundedToolTip._instance.popup if RoundedToolTip._instance is not None else None

    def hide_tip(self) -> None:
        from bazzite_console_core.widgets import hide_tooltip
        hide_tooltip()
        self.popup = None
        self.pump()

    # --- the sound and the captions' time ------------------------------------------------------------------
    def sound(self, path: Path, volume: float) -> None:
        """*path* plays from the frame the video is at."""
        self.cues.append((self.frames / self.fps, path, volume))

    def wait(self, image=None) -> None:
        """The picture stays until the caption is spoken (with the voice) or read (READ a word)."""
        left = self.until - self.frames
        if left > 0:
            if image is None:
                self.pump()
                image = self.frame()
            self.emit(image, left)

    def say(self, text: str) -> None:
        """A new caption, spoken with the voice. It waits for the caption before it, with the voice; "" (none) always
        waits, so a caption is never cut short."""
        if not text or self.speaker is not None:
            self.wait()
        super().say(text)
        if not text:
            return
        self.until = self.frames + round(len(text.split()) * READ * self.fps)
        if self.speaker is not None:
            sound, seconds = self.speaker.speak(text)
            self.sound(sound, VOICE_VOLUME)
            self.until = max(self.until, self.frames + round((seconds + GAP) * self.fps))

    def click(self, action=None) -> None:
        self.wait()                                 # the view changes only after the caption
        super().click(action)

    def fade(self, first, second, seconds: float = 0.6) -> None:
        self.wait(first)
        super().fade(first, second, seconds)

    def open_menu(self) -> None:
        self.popup = self.window.wallpaper_menu()
        pill = self.window.wallpaper_pill
        self.popup.popup(pill.mapToGlobal(pill.rect().bottomLeft()))
        self.pump()

    def at_action(self, action) -> tuple[float, float]:
        rect = self.popup.actionGeometry(action)
        top_left = self.popup.pos() - self.window.pos()
        return (top_left.x() + rect.center().x()) * SCALE, (top_left.y() + rect.center().y()) * SCALE

    def at_slider(self, slider, value: int) -> tuple[float, float]:
        from PyQt6.QtCore import QPoint
        from PyQt6.QtWidgets import QStyle, QStyleOptionSlider
        option = QStyleOptionSlider()
        slider.initStyleOption(option)
        option.sliderPosition = value
        handle = slider.style().subControlRect(QStyle.ComplexControl.CC_Slider, option,
                                               QStyle.SubControl.SC_SliderHandle, slider)
        point = slider.mapToGlobal(handle.center()) - self.window.pos() + QPoint(0, 0)
        return point.x() * SCALE, point.y() * SCALE

    def drag(self, slider, target: int, seconds: float) -> None:
        start, frames = slider.value(), max(1, round(seconds * self.fps))
        for i in range(1, frames + 1):
            t = i / frames
            value = round(start + (target - start) * t * t * (3 - 2 * t))
            slider.setValue(value)
            self.pointer = self.at_slider(slider, value)
            self.pump()
            self.emit(self.frame())

    def still(self, theme: str):
        """The portal in another theme: a fresh process (the theme is read at start) renders one frame."""
        from PyQt6.QtGui import QImage
        out = self.home / f"still-{theme}.png"
        size = next(name for name, zoom in tour_frames.SIZES.items() if zoom == tour_frames.ZOOM)
        subprocess.run([sys.executable, __file__, "--still", theme, str(out), "--size", size], check=True)
        return QImage(str(out)).convertToFormat(QImage.Format.Format_RGB888)


def render_still(theme: str, out: Path) -> None:
    with tempfile.TemporaryDirectory(prefix="portal-tour-") as folder:
        home = Path(folder)
        prepare_home(home)
        import importlib

        import bazzite_console_core.theme
        bazzite_console_core.theme.save_theme_name(theme)
        importlib.reload(bazzite_console_core.theme)
        tour = Tour(Path(os.devnull), 1, home)
        tour.ffmpeg.kill()
        tour.window.example_wallpaper()
        tour.window.toggle_settings()                   # as the tour shows the theme: on the Settings page
        tour.say({"silver": "Silver", "warm": "Warm"}.get(theme, theme))
        tour.overlay = None
        tour.pointer = (-100, -100)
        tour.pump()
        tour.frame().save(str(out))


def speech_engine() -> list[str] | None:
    """The command that starts Nexus TTS's speech engine (dev/text), None when it is not set up. Asked in a process
    of its own, in the real home folder: the tour's home has no engine, and this one's Qt and theme stay unread."""
    code = ("import json, sys; sys.path[:0] = sys.argv[1:]; from textspeech import engine_setup as s; "
            "print(json.dumps(s.serve_command() if s.installed() else None))")
    result = subprocess.run([sys.executable, "-c", code, str(SUITE / "core"), str(TTS)], capture_output=True,
                            text=True)
    try:
        return json.loads(result.stdout) if result.returncode == 0 else None
    except ValueError:
        return None


def tiles() -> list:
    """What the video shows of portal/apps.toml (owner, 15-11-2026: new tiles need a new video): each app's tiles in
    their order, with their names, categories and marks. Its tags and checksums are left out: a release changes
    them, and the video does not show them."""
    try:
        apps = tomllib.loads(MANIFEST.read_text(encoding="utf-8")).get("apps", {})
    except (OSError, tomllib.TOMLDecodeError):
        return []
    shown = ("name", "short", "category", "required", "changes_board", "withdrawn")
    return [[key, {field: app.get(field) for field in shown},
             [[h.get("key"), h.get("name"), h.get("changes_board", False)] for h in app.get("quickfixes", [])]]
            for key, app in apps.items() if isinstance(app, dict)]


def fingerprint() -> str:
    """A hash of what the video shows: the portal's code and pictures (SHOWN), its tiles (tiles()) and this script.
    The portal's version is left out: the video does not show it (a release changes only that line, and the video
    is recorded before it)."""
    digest = hashlib.sha256()
    files = [path for folder in SHOWN for path in folder.rglob("*")
             if path.is_file() and "__pycache__" not in path.parts]
    for path in sorted([*files, Path(__file__).resolve()]):
        data = path.read_bytes()
        if path.suffix == ".py":
            data = b"\n".join(line for line in data.split(b"\n") if not line.startswith(b"__version__ = "))
        digest.update(path.relative_to(SUITE).as_posix().encode() + b"\0" + hashlib.sha256(data).digest())
    digest.update(b"tiles\0" + hashlib.sha256(json.dumps(tiles(), sort_keys=True).encode()).digest())
    return digest.hexdigest()


def stale() -> bool:
    """Whether the portal changed since the wiki's video was recorded (or no stamp says when it was)."""
    try:
        return STAMP.read_text(encoding="utf-8").strip() != fingerprint()
    except OSError:
        return True


def write_stamp() -> None:
    STAMP.write_text(fingerprint() + "\n", encoding="utf-8", newline="\n")


def wiki_copy(video: Path) -> int:
    """The wiki's copy of *video*: 1280 x 720 and about a third of the size, so the repository stays small, and the
    title card as its poster. ffmpeg's exit code."""
    WIKI_POSTER.parent.mkdir(parents=True, exist_ok=True)
    WIKI_VIDEO.parent.mkdir(parents=True, exist_ok=True)
    code = subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-i", str(video), "-vf", "scale=1280:720:flags=lanczos",
         "-c:v", "libx264", "-preset", "slow", "-crf", "26", "-tune", "stillimage", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(WIKI_VIDEO)]).returncode
    return code or subprocess.run(
        ["ffmpeg", "-loglevel", "error", "-y", "-ss", "1", "-i", str(video), "-frames:v", "1",
         "-vf", "scale=1280:720:flags=lanczos", "-c:v", "libwebp", "-quality", "85", str(WIKI_POSTER)]).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("out", nargs="?", default="portal-tour.mp4")
    parser.add_argument("--music", type=Path, default=MUSIC, help="the track under the video (default: the suite's)")
    parser.add_argument("--no-music", action="store_true", help="a video without music")
    parser.add_argument("--no-voice", action="store_true",
                        help="no voice reading the captions out (it needs Nexus TTS's speech engine)")
    parser.add_argument("--wiki", action="store_true", help="also write the copy on the wiki's Portal Tour page")
    parser.add_argument("--check", action="store_true",
                        help="only say whether the portal changed since the wiki's video was recorded (exit 1)")
    parser.add_argument("--stamp", action="store_true",
                        help="mark the wiki's video as current without recording: the change does not show in it")
    parser.add_argument("--fps", type=int, default=30)
    parser.add_argument("--size", choices=tuple(tour_frames.SIZES), default="1080p",
                        help="the video's size: 1080p (the default), 1440p or 2160p (4K, for YouTube)")
    parser.add_argument("--still", nargs=2, metavar=("THEME", "PNG"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.stamp:
        write_stamp()
        print(f"{STAMP.relative_to(SUITE).as_posix()}: the wiki's video is marked as current")
        return 0
    if args.check:
        if stale():
            print("The portal changed since the wiki's Portal Tour was recorded: record it again with\n"
                  "  tools/record-tour.sh --wiki\n"
                  "or, when the change does not show in the video, python3 tools/portal_tour.py --stamp\n"
                  "When the change is one the wiki describes, its Portal page (docs/portal.md) changes with it.",
                  file=sys.stderr)
            return 1
        print("The wiki's Portal Tour is current.")
        return 0
    tour_frames.set_size(args.size)
    if args.still:
        render_still(args.still[0], Path(args.still[1]))
        return 0
    if not shutil.which("ffmpeg"):
        print("ffmpeg is needed", file=sys.stderr)
        return 1
    music = None if args.no_music else args.music.resolve()
    if music is not None and not music.is_file():
        print(f"No music at {music} (--no-music for a video without music)", file=sys.stderr)
        return 1
    engine = None if args.no_voice else speech_engine()
    if not args.no_voice and engine is None:
        print("The voice needs Nexus TTS's speech engine. Set it up once in Nexus TTS (dev/text/run.sh: Set up the "
              "speech engine), or record with --no-voice.", file=sys.stderr)
        return 1
    out = Path(args.out).resolve()
    with tempfile.TemporaryDirectory(prefix="portal-tour-") as folder:
        home = Path(folder)
        speaker = tour_frames.Speaker(engine, home) if engine else None     # before the home is the tour's own
        prepare_home(home)
        silent = home / "silent.mp4"
        tour = Tour(silent, args.fps, home, speaker)
        try:
            tour.run()
        finally:
            code = tour.finish()
            if speaker is not None:
                speaker.close()
        if code == 0:
            code = tour_frames.mix(silent, out, tour.frames / tour.fps, tour.cues, music, tour.music_at,
                                   VOICE_MUSIC if speaker is not None else 1.0, FADE)
    if code == 0 and args.wiki:
        code = wiki_copy(out)
        if code == 0:
            write_stamp()
            print(WIKI_VIDEO.relative_to(SUITE).as_posix(), WIKI_POSTER.relative_to(SUITE).as_posix())
    print(out if code == 0 else f"ffmpeg failed ({code})")
    return code


if __name__ == "__main__":
    # The video is written and the temporary home removed when main() returns. os._exit skips the interpreter's
    # shutdown, where Python destroys the Qt objects in no fixed order: that crashed now and then (exit code 139)
    # after a complete recording.
    try:
        status = main()
    except SystemExit as exc:                       # argparse: --help, or a wrong argument
        status = exc.code if isinstance(exc.code, int) else (0 if exc.code is None else 1)
    except BaseException:
        import traceback
        traceback.print_exc()
        status = 1
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(status)
