# SPDX-License-Identifier: GPL-3.0-or-later
"""Help page content."""

from __future__ import annotations

from PyQt6.QtWidgets import QTextBrowser, QWidget

from . import APP_NAME, GOVERNOR_URL, REPO_URL, __version__, fmt


def help_html(config: str) -> str:
    text = ("""
<h1>%1 <small>v%2</small></h1>
<p>This app lets you set up and watch <b>cyan-skillfish-governor-smu</b>, the GPU governor of the <b>AMD
PS5</b> on <b>Bazzite</b>. The board's APU is the Cyan Skillfish, gfx1013. The governor must already be
installed. This app edits one section of its configuration and controls its systemd service. It touches nothing
else on the system.</p>

<h2>Overview</h2>
<p>The Overview shows these:</p>
<ul>
<li>whether the service runs</li>
<li>whether the governor's patched <code>gpu_metrics</code> table is mounted over sysfs</li>
<li>whether a GPU load sensor is available</li>
<li>a chart of the GPU load (%), temperature (°C, left axis) and clock (MHz, right axis)</li>
</ul>
<p>A missing reading leaves a gap, never a fake zero. While it runs, the app keeps the last hour of samples, one
every two seconds. <b>Window</b> picks how much of it the chart shows: 2, 10, 30 or 60 minutes. <b>Export CSV…</b>
writes every kept sample to a file. A sample holds the time, load, clock, temperature, socket power, performance
mode and runtime range. <b>Compare…</b> loads such a file back and draws it dashed behind the live lines. Its
newest sample sits at the right edge, like the live window. Under the chart you see both sessions' averages and
peaks of load, clock, temperature and socket power. That way you can judge a profile or safe-point change against
an earlier run. <b>Clear</b> removes it.</p>
<p>The <b>gpu_metrics table</b> box decodes the table that the kernel or the governor exposes. It shows these:</p>
<ul>
<li>activities and temperatures</li>
<li>socket, GFX and CPU power</li>
<li>the GFX, SoC, memory and fabric clocks</li>
<li>the throttle status and the CPU core clocks</li>
</ul>
<p><i>(patched)</i> means the governor's table is mounted. <i>(raw)</i> is the kernel's own table. On a PS5 its
GFX activity is the broken 655% value, and the app does not use it as load.</p>
<p>The PS5 usually has no <code>gpu_busy_percent</code> sensor. The governor measures the load itself. With
<b>fix-metrics</b> on, it publishes the load in the patched <code>gpu_metrics</code> table it mounts over sysfs.
The app reads the load from there. <code>gpu_busy_percent</code> and <code>radeontop</code> are fallbacks. Without
any source it shows <b>N/A</b>, never a misleading 0%. The tooltip then tells you what is missing. The GPU clock
and temperature come from the amdgpu hwmon sensors. With <code>fix-freq</code> on, the clock is the real SMU
value.</p>

<h2>GPU Usage</h2>
<p>This page edits the <code>[gpu-usage]</code> section of <code>%3</code>:</p>
<table cellpadding="4" cellspacing="0" border="1" width="100%">
<tr><th>Key</th><th>Default</th><th>Meaning</th></tr>
<tr><td><b>fix-metrics</b></td><td>true</td><td>Write the measured load into a patched <code>gpu_metrics</code>
table and bind-mount it over sysfs. Fixes the 655% GPU usage of MangoHud, the Steam overlay and radeontop.</td></tr>
<tr><td><b>fix-freq</b></td><td>false</td><td>Also patch <code>current_gfxclk_frequency</code> with the clock read
from the SMU. Fixes the wrong sysfs frequency, mainly after the 8-core unlock. Independent of fix-metrics.</td></tr>
<tr><td><b>method</b></td><td>busy-flag</td><td><i>busy-flag</i> samples the GPU's busy bit.
<i>process</i> scans every process that uses the GPU, which costs more CPU work. <i>kernel</i> needs a patched
kernel.</td></tr>
<tr><td><b>temp-read</b></td><td>drm</td><td>Where the governor reads the GPU temperature. The DRM ioctl keeps a DRM
handle open. The other choice is the hwmon <code>temp1_input</code> file. Same sensor.</td></tr>
<tr><td><b>flush-every</b></td><td>10</td><td>Flush the patched table every N update cycles.</td></tr>
</table>
<p>The page also edits the <code>[gpu]</code> section with <b>set-method</b>. <i>smu</i> is the default. It
applies clock and voltage through the SMU directly. <i>kernel</i> goes through the amdgpu sysfs interface
instead.</p>
<p><b>Apply changes</b> on this page or on Tuning asks for your password once (pkexec). It copies the current
file to <code>config.toml.bak-YYYYMMDD-HHMMSS</code> and writes the pending edits of both pages. Only the known
keys change. Every other line of the file stays, including comments. The governor reads the file at start, so
the app restarts the service afterward. To skip the restart, uncheck that option.</p>

<h2>Tuning</h2>
<p>This page edits the other sections of <code>%3</code>:</p>
<table cellpadding="4" cellspacing="0" border="1" width="100%">
<tr><th>Section</th><th>Keys</th><th>Meaning</th></tr>
<tr><td><b>[frequency-range]</b></td><td>min, max</td><td>Clock limits in MHz the governor starts with. <i>No limit</i>
(0) leaves the limit open. The governor clamps values outside the safe-points table.</td></tr>
<tr><td><b>[load-target]</b></td><td>upper, lower</td><td>Ramp the clock up when the load is above <i>upper</i>,
down when it is below <i>lower</i>. A wide gap keeps the clock steady. A narrow one follows the load closely.
The governor's own defaults when the section is missing are 95% / 80%. The shipped file uses 65% / 50%.</td></tr>
<tr><td><b>[temperature]</b></td><td>throttling, throttling_recovery</td><td>Throttle above the first value, by
default 85 °C. Recover below the second. It is optional (<i>Not set</i>) and must be lower.</td></tr>
<tr><td><b>[dbus]</b></td><td>enabled</td><td>Publish <code>com.cyanskillfish.Governor</code> on the system bus. The
Performance page needs it. The shipped file turns it on. The governor's built-in default is off.</td></tr>
<tr><td><b>[timing]</b></td><td>intervals.sample, intervals.adjust, ramp-rates.normal, ramp-rates.burst, burst-samples,
down-events</td><td>The control loop. These keys set:
<ul>
<li>how often the governor samples the load and adjusts the clock (µs)</li>
<li>how fast the clock moves toward its target (MHz/ms)</li>
<li>how many busy samples in a row switch to the faster burst ramp. <i>Off</i> leaves the key out.</li>
<li>how many low-load adjust cycles pass before the clock steps down</li>
</ul>
Governor defaults: 2000 µs / 10 × sample, 1 / 200 × normal, off, 10. The shipped file uses 250 µs / 100 000 µs,
1 / 50, 60, 5.</td></tr>
<tr><td><b>[frequency-thresholds]</b></td><td>adjust</td><td>Dead band in MHz. The governor skips a non-burst change
smaller than this. The default is 10.</td></tr>
</table>
<p><b>Presets</b> fill in the frequency range, load target and temperature at once. They leave timing alone. The
presets are these:</p>
<ul>
<li><i>Shipped defaults</i>, the package's config</li>
<li><i>Quiet</i>, with lower clocks and a late ramp-up</li>
<li><i>Responsive</i>, with an early ramp-up and the full range</li>
<li><i>Maximum clock</i>, which stays near the top</li>
</ul>
<p>The combo box shows <i>Custom</i> as soon as a value differs from every preset. The app flags invalid
combinations under the form, and they block Apply:</p>
<ul>
<li>min above max</li>
<li>recovery not below throttling</li>
<li>an adjust interval shorter than sample</li>
<li>a burst rate not above normal</li>
</ul>
<p><b>Profiles</b> are named snapshots of every value on this page and the GPU Usage page. Safe points are not
included. The app stores them for your user in <code>~/.config/ps5-governor-manager/profiles.json</code>.</p>
<ul>
<li><i>Save current as…</i> stores what the forms show right now, applied or not.</li>
<li><i>Load into forms</i> fills both pages, so you can review and apply as usual.</li>
<li><i>Apply now</i> writes the profile to <code>config.toml</code> and restarts the governor. It makes a backup
first. It discards pending edits. You will be asked for your password.</li>
</ul>
<p>With the tray icon on, the tray menu's <i>Apply profile</i> submenu does the same without opening the window.
For a <b>keyboard shortcut</b>, <i>Copy hotkey command</i> puts <code>ps5-governor-manager --profile 'Name'</code>
on the clipboard. Bind it in System Settings → Shortcuts (KDE) or Keyboard → Custom Shortcuts (GNOME). The app runs
once per user. That command reaches the running instance over a local socket and applies the profile there. You get
a tray notice, and you will be asked for your password. When nothing is running, the command starts the app and
applies the profile.
A plain second launch just raises the window. <code>--list-profiles</code> prints the saved names.</p>

<h2>Safe points</h2>
<p>This page shows the <code>[[safe-points]]</code> of <code>%3</code> as an editable table and a frequency/voltage
curve. The governor scales along this curve and never leaves its range. It clamps <code>[frequency-range]</code>
and the runtime controls to it.</p>
<ul>
<li><b>Add point</b> inserts a point halfway to the next one.</li>
<li><b>Remove</b> deletes the selected row.</li>
<li><b>Shipped defaults</b> loads the governor's own table.</li>
<li><b>Revert</b> goes back to the file.</li>
</ul>
<p><b>Apply safe points</b> turns on only when the list passes the governor's rules:</p>
<ul>
<li>at least two points</li>
<li>unique frequencies</li>
<li>a voltage that never drops as the frequency rises</li>
</ul>
<p>The list must also pass the hard rails shared with the GPU sweep: 700–1100 mV, up to 2500 MHz. You get a
warning above 2000 MHz or 1000 mV. You also get one when a change raises the top frequency or lowers an existing
voltage. An unstable point freezes the board under load. Apply makes a backup and asks for your password. To find
a board's own ceiling safely, use the GPU sweep: the <b>GPU sweep</b> pill at the bottom of the Safe points page
opens it.</p>
<p><b>Test a point before saving it</b> uses the governor's root-only <code>TestMode</code> D-Bus interface, with
one <code>pkexec</code> prompt. It pins the GPU to the frequency and voltage you enter and stops the automatic
scaling. Thermal throttling stays active. Nothing changes in <code>config.toml</code>. The app fills in the
fields from the selected row. A warning appears above 2000 MHz / 1000 mV. It also appears when the voltage is
below what the curve above would give.</p>
<p><b>Load</b> picks a GPU load generator found on PATH. The app prefers vkmark, then glmark2, vkcube and
glxgears. The tool starts with the test and is killed when the test ends. If it dies while the point is pinned,
the status says so. Without one, load the GPU yourself and watch the Overview.</p>
<p>These end the test:</p>
<ul>
<li><b>Stop test</b></li>
<li>the timer, 60 s by default, where <i>Until stopped</i> = 0</li>
<li>closing the app</li>
<li>any action on the Performance page</li>
</ul>
<p>The test ends by switching performance mode off. That returns the governor to normal scaling with its start-up
range. The result line then reports how long the point held, the peak temperature and the clock range seen.
<b>Add to table</b> puts the tested pair into the safe-points table, so you can apply it. The table stays sorted,
and the pair replaces a point at the same frequency.</p>
<p>While a point is pinned, the app watches the <b>kernel log</b> (<code>journalctl -k -f</code>) for amdgpu
trouble:</p>
<ul>
<li>ring timeouts</li>
<li>GPU resets</li>
<li><code>*ERROR*</code> lines</li>
<li>SMU failures</li>
</ul>
<p>The first such line aborts the test at once and releases the point before the board freezes. The result
quotes it. A clean run says so too. To read the kernel ring, your user must be in the
<code>systemd-journal</code> or <code>wheel</code> group. Otherwise the status says the log is not watched, and
the test runs blind. A point the silicon cannot hold can still freeze the board faster than the kernel can log
it. So save your work first. Only the smu governor has D-Bus.</p>

<h2>Performance</h2>
<p>This page controls the governor at runtime over D-Bus. It does exactly what the governor's own
<code>cyan-skillfish-performance-mode</code> wrapper does. The changes apply at once and need no password. They
last until the next governor restart. The app leaves <code>config.toml</code> unchanged. <i>Copy runtime values to
the Tuning page</i> carries the current range and thresholds over to the Tuning page, so you can save them.</p>
<ul>
<li><b>Performance mode</b> is a toggle, red while on. On opens the full allowed safe-points range. Off returns
to the range of <code>[frequency-range]</code>.</li>
<li><b>Pin clock</b> fixes the frequency and turns performance mode on.</li>
<li><b>Set range</b> applies a runtime min/max.</li>
<li><b>Set load target</b> and <b>Set temperatures</b> change the load band (lower/upper %) and the throttling and
recovery temperatures the governor scales with. They leave performance mode and a running safe-point test alone.
The fields follow the governor's current values and refill when they change. An impossible pair turns the button
off. Lower must be below upper, and recovery below throttling.</li>
</ul>
<p>The controls are off when the service is not running or the bus name is not published. The reason shows under
the controls. If needed, turn on <code>[dbus] enabled</code> on the Tuning page and restart the governor.</p>
<p><b>Per game</b> builds the launch line for the governor's <code>cyan-skillfish-performance-mode</code> wrapper.
It offers plain performance mode, <code>--fixed-frequency</code>, <code>--range</code>, <code>--load-target</code>
and <code>--temperature</code>. It fills them in with the governor's current numbers. The line comes in three
formats:</p>
<ul>
<li>Steam launch options (<code>… %command%</code>)</li>
<li>a Heroic/Lutris wrapper command</li>
<li>a terminal</li>
</ul>
<p><b>Copy</b> puts it on the clipboard. The wrapper applies the setting and runs the game. When the game exits,
it turns performance mode off. That also puts the governor back on its start-up range. Like the controls above, it
needs D-Bus turned on.</p>

<h2>Backups</h2>
<p>Every write makes a copy <code>config.toml.bak-YYYYMMDD-HHMMSS</code> next to the config. The page lists the
copies and shows how a copy differs from the current file. <b>Restore selected</b> puts the copy back. It backs up
the current file first and asks for your password once. The app then restarts the governor. To skip the restart,
uncheck that option.</p>

<h2>Service</h2>
<p>Start, stop, restart, enable or disable <code>cyan-skillfish-governor-smu.service</code> here. The page shows the
output of <code>systemctl status</code> and a <b>live journal</b> (<code>journalctl -u … -f</code>). The journal
starts with the last 200 lines and adds everything that follows while the page is shown. The app keeps up to
2000 lines. The filter box takes text or a regular expression and ignores case. Uncheck <b>Follow</b> to read
while the view stays put. To read system units, your user must be in the <code>wheel</code> or
<code>systemd-journal</code> group. On Bazzite it is. Each service action asks for your password.</p>
<p><b>Check for updates</b> compares the installed <code>cyan-skillfish-governor-smu</code> RPM with the latest
release of <a href="https://github.com/filippor/cyan-skillfish-governor/releases">filippor/cyan-skillfish-governor</a>
on GitHub. It sends one request to api.github.com. It also runs at start, unless you turn that off in Settings. A
newer release shows in orange with a link to its notes. Update the package the way you installed it. When it is
layered from COPR <code>filippor/bazzite</code>, use <code>rpm-ostree upgrade</code>. Otherwise use the release
tarball.</p>
<p><b>Export diagnostics…</b> writes one text file for a bug report. It holds these:</p>
<ul>
<li>the app, governor and Bazzite versions</li>
<li>the CPU and GPU</li>
<li><code>config.toml</code> and its backups</li>
<li><code>systemctl status</code>/<code>cat</code> and the last 300 journal lines</li>
<li>the D-Bus interface and the kernel command line</li>
<li>the amdgpu kernel messages and the hwmon sensors</li>
<li>the raw <code>gpu_metrics</code> table, parsed and as a hex dump</li>
</ul>
<p>Read the file and remove what you do not want to share before you attach it to an issue.</p>

<h2>Settings</h2>
<p>These are the app's own settings, kept for each user.</p>
<p><b>System tray</b> shows a tray icon. Its tooltip carries the GPU load, clock, temperature, performance mode and
governor state. A left-click shows or hides the window. The menu quits the app. While D-Bus is reachable, the menu
also toggles performance mode. Check <i>Closing the window keeps the app running in the tray</i> to make the close
button hide the window in the tray instead. Then use the tray menu to quit.</p>
<p><b>Start at login</b> writes <code>~/.config/autostart/ps5-governor-manager.desktop</code>. It writes nothing
system-wide. The app can start hidden in the tray with <code>--start-in-tray</code>. Bazzite's KDE Plasma session
has a native tray, so this works out of the box. A GNOME session would need the AppIndicator extension.</p>
<p><b>Alerts</b> are desktop notifications through the tray icon. When the tray is off, they show in the status
bar only. You can get an alert for each of these:</p>
<ul>
<li>the GPU reaches a temperature you choose</li>
<li>the GPU reaches the governor's own throttling temperature</li>
<li>the governor service stops or fails after the app has seen it running</li>
</ul>
<p>The throttling temperature is the runtime value when D-Bus is reachable. Otherwise it is the one in
<code>config.toml</code>. A temperature alert fires once per crossing and re-arms 5 °C below its threshold. The
same alert repeats at most every 5 minutes.</p>

<h2>The older tt governor</h2>
<p>With <code>--backend tt</code> the app manages <code>/etc/cyan-skillfish-governor-tt/config.toml</code> instead.
It also does that by itself when only <code>cyan-skillfish-governor-tt.service</code> is loaded. That governor has
no fix-metrics, frequency range, D-Bus or GitHub releases. So the app hides these:</p>
<ul>
<li>the GPU Usage and Performance pages</li>
<li>those Tuning sections and the <code>down-events</code> field</li>
<li>the update check</li>
</ul>
<p>The GPU load sensor stays unavailable. Everything else works the same, including <code>[timing]</code> and
<code>[frequency-thresholds]</code>.</p>

<h2>Privileges</h2>
<p>The app runs as your normal user. Only three things need root and go through <code>pkexec</code>:</p>
<ul>
<li>the backup and write of <code>config.toml</code>, in a single call</li>
<li>the <code>systemctl</code> actions</li>
<li>the safe-point test, with <code>busctl</code> on the root-only TestMode interface</li>
</ul>
<p>The desktop's polkit agent handles the password. The app never sees it.</p>

<h2>Install and update</h2>
<p>The release tarball contains <code>install.sh</code>. It installs the app for your user only, so it appears in
the application menu. It installs these:</p>
<ul>
<li>a private venv with PyQt6 under <code>~/.local/share/ps5-governor-manager</code></li>
<li>the launcher <code>~/.local/bin/ps5-governor-manager</code></li>
<li>a desktop entry and the icon</li>
</ul>
<p>Run it again from a newer release to update. <code>./install.sh --uninstall</code> removes it. It layers nothing
with rpm-ostree and never touches the governor's config.</p>

<h2>Links</h2>
<ul>
<li>This app: <a href="%4">%4</a></li>
<li>The governor (filippor, SMU branch): <a href="%5">%5</a></li>
</ul>
<p>Licensed under the GNU General Public License v3.0 or later. The Inter font (SIL Open Font License) is bundled.</p>
""")
    return fmt(text, APP_NAME, str(__version__), config, REPO_URL, GOVERNOR_URL)


class HelpView(QTextBrowser):
    def __init__(self, config_path: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setOpenExternalLinks(True)
        self.setHtml(help_html(config_path))
