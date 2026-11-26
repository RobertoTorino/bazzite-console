# SPDX-License-Identifier: GPL-3.0-or-later
"""The article keeps up with the portal: a line for every app and category of portal/apps.toml, the links, the
stills, the license and the disclaimer from the README, and only the portal's apps (no development app)."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

from nexus_marketing import CHECKOUT, article

APPS_TOML = CHECKOUT / "portal" / "apps.toml"


def test_copy_has_a_line_for_every_app_and_category():
    """A new app in the portal fails here until copy.md has its line (owner, 25-11-2026: kept in sync)."""
    assert article.missing() == []


def test_missing_names_an_app_without_a_line_and_a_line_for_nothing(tmp_path):
    first, last = article.apps()[0].key, article.apps()[-1].key
    copy = article.COPY.read_text(encoding="utf-8")
    copy = re.sub(rf"^\| {first} \|.*\n", "", copy, flags=re.M).replace(f"| {last} |", "| gone |")
    path = tmp_path / "copy.md"
    path.write_text(copy, encoding="utf-8")
    problems = article.missing(path=path)
    assert f"No line for the app {first}." in problems
    assert f"No line for the app {last}." in problems
    assert "A line for gone, which the portal does not have." in problems


def test_every_part_of_the_copy_is_there():
    words = article.read_copy()
    assert all(words.get(name) for name in article.SECTIONS)


def test_the_page_shows_every_portal_app_and_no_development_app():
    page = article.build().html
    data = tomllib.loads(APPS_TOML.read_text(encoding="utf-8"))["apps"]
    for key, entry in data.items():
        if not entry.get("withdrawn"):
            assert f'href="{article.SUITE_MANUAL_URL}apps/{key}/"' in page
    dev_names = [re.search(r'^APP_NAME = "([^"]+)"', init.read_text(encoding="utf-8"), re.M)
                 for init in (CHECKOUT / "dev").glob("*/*/__init__.py")]
    for found in filter(None, dev_names):
        assert found.group(1) not in page


def test_the_count_comes_from_the_portal():
    count = len([e for e in tomllib.loads(APPS_TOML.read_text(encoding="utf-8"))["apps"].values()
                 if not e.get("withdrawn")])
    assert f"brings {count} apps" in article.build().html


def test_the_page_links_the_release_the_wiki_the_video_and_github():
    page = article.build().html
    assert f'href="{article.SUITE_REPO_URL}/releases/latest"' in page
    assert f'href="{article.SUITE_MANUAL_URL}"' in page
    assert f'href="{article.SUITE_MANUAL_URL}portal-tour/"' in page
    # Watch the tour and the poster play the video itself, not its wiki page (owner, 26-11-2026)
    assert page.count(f'href="{article.SUITE_MANUAL_URL}videos/portal-tour.mp4"') == 4      # the hero, See it in action, Get it
    assert page.count(f'href="{article.SUITE_MANUAL_URL}portal-tour/"') == 1               # the footer's link
    assert f'href="{article.SUITE_REPO_URL}"' in page


def test_the_license_and_the_disclaimer_are_the_readmes():
    page = article.build().html
    for heading in ("License", "Disclaimer"):
        paragraphs = article.readme_section(heading)
        assert paragraphs
        assert article.inline(paragraphs[0]) in page
    assert "not affiliated with or endorsed by AMD" in page


def test_a_readme_link_points_at_the_repository():
    assert article.inline("See [LICENSE](LICENSE).") == (
        f'See <a href="{article.SUITE_REPO_URL}/blob/main/LICENSE">LICENSE</a>.')


def test_the_changes_board_mark_follows_apps_toml():
    page = article.build().html
    cards = re.findall(r'<a class="card" href="[^"]*apps/([a-z0-9]+)/">(.*?)</a>', page, flags=re.S)
    data = tomllib.loads(APPS_TOML.read_text(encoding="utf-8"))["apps"]
    for key, card in cards:
        assert ("Changes the board" in card) == bool(data[key].get("changes_board")), key


def test_stills_and_hero_go_along_when_there_are_some(tmp_path):
    shots = tmp_path / "shots"
    shots.mkdir()
    for name in ("sustainable", "settings"):
        (shots / f"{name}.webp").write_bytes(b"RIFF")
    hero = tmp_path / "hero.webp"
    page = article.build(shot_folder=shots, hero=hero)
    assert "images/portal-sustainable.webp" in page.files and "images/portal-gaming.webp" not in page.files
    assert "hero--placeholder" in page.html                 # no hero picture: the drawn placeholder
    hero.write_bytes(b"RIFF")
    page = article.build(shot_folder=shots, hero=hero)
    assert "hero--placeholder" not in page.html and page.files["images/hero.webp"] == hero


def test_write_puts_every_file_beside_the_page(tmp_path):
    built = article.build()
    page = article.write(built, tmp_path / "out")
    assert page.read_text(encoding="utf-8") == built.html
    assert all((tmp_path / "out" / name).is_file() for name in built.files)
    for target in re.findall(r'(?:src|href)="((?!https?:|data:|#)[^"]+)"', built.html):
        assert (tmp_path / "out" / target).is_file(), target


def test_every_file_of_the_page_exists():
    assert all(Path(source).is_file() for source in article.build().files.values())


def test_the_preview_is_one_file_with_nothing_beside_it():
    """A browser in a sandbox (a Flatpak) gets only the file it opens: the preview refers to no file beside it."""
    page = article.single(article.build())
    assert '<link rel="stylesheet"' not in page and "<style>" in page
    assert not re.findall(r'(?:src|href)="(?!https?:|data:|#)[^"]+"', page)
    assert not re.findall(r'url\("?(?!data:)[^)"]+"?\)', page)


def test_the_quickfix_card_has_only_its_line_from_the_copy():
    """The quickfix card is like every other card: its one line from copy.md, no list of names under it (owner,
    26-11-2026)."""
    page = article.build().html
    card = re.search(r'<a class="card" href="[^"]*apps/quickfix/">(.*?)</a>', page, flags=re.S).group(1)
    assert re.findall(r"<p>(.*?)</p>", card) == [article.inline(article.table(article.read_copy()["Apps"])["quickfix"])]


def test_and_more_sits_above_the_safety_band():
    page = article.build().html
    assert page.index('<section class="more">') < page.index('<section class="safety">')
    assert page.count('<ul class="chips"><li>') == 1


def test_changes_and_publish_touch_only_the_articles_files(tmp_path):
    built = article.build()
    site = tmp_path / "site"
    site.mkdir()
    (site / ".nojekyll").write_text("")
    (site / "README.md").write_text("mine")
    assert "index.html" in article.changes(built, site)
    (site / "images").mkdir()
    (site / "images" / "gone.webp").write_bytes(b"old")
    changed = article.publish(built, site)
    assert "images/gone.webp" in changed and not (site / "images" / "gone.webp").exists()
    assert article.changes(built, site) == []                    # published: nothing left to change
    assert (site / ".nojekyll").exists() and (site / "README.md").read_text() == "mine"
    assert (site / "index.html").read_text(encoding="utf-8") == built.html


def test_publish_commands_commit_the_articles_files_and_push(tmp_path):
    """Run against a local bare repository: the commit has the article's files, its message, and reaches the remote."""
    import subprocess

    remote, site = tmp_path / "remote.git", tmp_path / "site"
    git = ["git", "-c", "user.name=Test", "-c", "user.email=test@example.invalid"]
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(remote)], check=True)
    subprocess.run(["git", "clone", "-q", str(remote), str(site)], check=True, capture_output=True)
    (site / ".nojekyll").write_text("")
    (site / "notes.txt").write_text("not the article's")
    subprocess.run([*git, "-C", str(site), "add", ".nojekyll"], check=True)
    subprocess.run([*git, "-C", str(site), "commit", "-qm", "start"], check=True)
    subprocess.run([*git, "-C", str(site), "push", "-q", "-u", "origin", "main"], check=True, capture_output=True)
    article.publish(article.build(), site)
    for command in article.publish_commands(site):
        subprocess.run([command[0], *git[1:], *command[1:]], check=True, capture_output=True)
    log = subprocess.run(["git", "-C", str(remote), "log", "-1", "--format=%s", "--name-only"],
                         capture_output=True, text=True, check=True).stdout
    assert log.splitlines()[0] == "see the changelog"
    assert "index.html" in log and "article.css" in log and "notes.txt" not in log


def test_each_headline_line_in_the_copy_is_a_line_on_the_page(tmp_path, monkeypatch):
    """copy.md sets where the headline breaks: a line there is a line on the page (owner, 25-11-2026)."""
    copy = re.sub(r"(## Headline\n\n).*?\n\n", r"\1One portal. Every part\nof your board.\n\n",
                  article.COPY.read_text(encoding="utf-8"), count=1, flags=re.S)
    path = tmp_path / "copy.md"
    path.write_text(copy, encoding="utf-8")
    monkeypatch.setattr(article, "COPY", path)
    assert "<h1>One portal. Every part<br>of your board.</h1>" in article.build().html


def test_the_specs_row_has_its_numbers_and_their_notes(tmp_path, monkeypatch):
    """The board's numbers sit under the hero, a label with asterisks has its note at the bottom (owner,
    26-11-2026), and a copy.md without the "Specs" part has no row."""
    plain = re.sub(r"## Specs.*?(?=## Portal)", "", article.COPY.read_text(encoding="utf-8"), flags=re.S)
    copy = tmp_path / "copy.md"
    copy.write_text(plain.replace("## Portal", "## Specs\n\n- 3.5 GHz\n- 40 COMPUTE UNITS*\n- 2 TB**\n\n"
                                  "## Spec notes\n\n- * In theory.\n- ** An example.\n\n## Portal"), encoding="utf-8")
    monkeypatch.setattr(article, "COPY", copy)
    assert article.specs(article.read_copy(copy)["Specs"]) == [("3.5", "GHz", ""), ("40", "COMPUTE UNITS", "*"),
                                                               ("2", "TB", "**")]
    page = article.build().html
    assert page.index("</header>") < page.index('class="band band--specs"') < page.index("<span>Apps</span>")
    assert '<span>COMPUTE UNITS<sup><a href="#spec-notes">*</a></sup></span>' in page
    assert page.index('id="spec-notes"') > page.index("<h4>Disclaimer</h4>")
    assert '<p><span class="mark">**</span> An example.</p>' in page
    copy.write_text(plain, encoding="utf-8")
    page = article.build().html
    assert "band--specs" not in page and "spec-notes" not in page
