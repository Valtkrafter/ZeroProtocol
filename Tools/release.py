#!/usr/bin/env python3
"""Zero Protocol release tool (Semantic Versioning 2.0.0): version bump, changelog, git tag and GitHub release.

The rules are in Docs/VERSIONING.md. The file VERSION in the project folder is the one source of the version number.
Run it from anywhere, it finds the project folder itself. Needs git and the GitHub CLI (gh) logged in.

  python Tools/release.py show                      show the current version and what every command would make of it
  python Tools/release.py alpha|beta|rc|release     prepare a release in the pre-release channels (see below)
  python Tools/release.py patch|minor|major         prepare a release from a final version (0.1.0 -> 0.1.1 / 0.2.0 / 1.0.0)
  python Tools/release.py set 0.3.0-alpha.1         prepare a release with an exact version
  python Tools/release.py publish --asset FILE ...  push commit and tag, create the GitHub release (pre-release for alpha/beta/rc)
  python Tools/release.py selftest                  check the version arithmetic

"Prepare" = write VERSION, the Unity setting (ProjectSettings.asset) and CHANGELOG.md, commit "chore(release): vX", tag vX.
Everything has to be committed before and the changes have to stand under "## [Unreleased]" in CHANGELOG.md.
Add --dry-run to see what would happen without changing anything.
"""
import argparse
import datetime
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "VERSION"
CHANGELOG = ROOT / "CHANGELOG.md"
SETTINGS = ROOT / "ProjectSettings" / "ProjectSettings.asset"
README = ROOT / "README.md"
NOTES_DIR = ROOT / "Docs" / "releases"
REPO = "Valtkrafter/ZeroProtocol"
CHANNELS = ["alpha", "beta", "rc"]
RE_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-(alpha|beta|rc)\.(\d+))?$")


class ReleaseError(Exception):
    pass


def parse(text):
    m = RE_VERSION.match(text.strip())
    if not m:
        raise ReleaseError("not a valid version (X.Y.Z or X.Y.Z-alpha.N, also beta and rc): " + repr(text))
    major, minor, patch, channel, number = m.groups()
    return int(major), int(minor), int(patch), channel, (int(number) if number else None)


def fmt(v):
    major, minor, patch, channel, number = v
    return "%d.%d.%d" % (major, minor, patch) + ("-%s.%d" % (channel, number) if channel else "")


def next_version(current, kind, explicit=None):
    major, minor, patch, channel, number = parse(current)
    if kind == "set":
        if not explicit:
            raise ReleaseError("set needs a version, e.g.: set 0.3.0-alpha.1")
        return fmt(parse(explicit))
    if kind == "release":
        if not channel:
            raise ReleaseError(current + " is already a final version; use patch, minor or major")
        return fmt((major, minor, patch, None, None))
    if kind in ("patch", "minor", "major"):
        if channel:
            raise ReleaseError(current + " is a pre-release; use release to finish it, or alpha, beta, rc to continue")
        if kind == "patch":
            return fmt((major, minor, patch + 1, None, None))
        if kind == "minor":
            return fmt((major, minor + 1, 0, None, None))
        return fmt((major + 1, 0, 0, None, None))
    if kind in CHANNELS:
        if not channel:
            return fmt((major, minor + 1, 0, kind, 1))
        if kind == channel:
            return fmt((major, minor, patch, channel, number + 1))
        if CHANNELS.index(kind) > CHANNELS.index(channel):
            return fmt((major, minor, patch, kind, 1))
        raise ReleaseError("cannot go back from %s to %s; use set if you really want that" % (channel, kind))
    raise ReleaseError("unknown command: " + kind)


def git(*args):
    r = subprocess.run(["git"] + list(args), cwd=ROOT, text=True, capture_output=True, encoding="utf-8")
    if r.returncode != 0:
        raise ReleaseError("git %s failed:\n%s%s" % (" ".join(args), r.stdout, r.stderr))
    return r.stdout.strip()


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def current_version():
    return read(VERSION_FILE).strip()


def unreleased_text(log):
    start = log.find("## [Unreleased]")
    if start < 0:
        raise ReleaseError("CHANGELOG.md has no '## [Unreleased]' section")
    start += len("## [Unreleased]")
    end = log.find("\n## [", start)
    return log[start:end if end >= 0 else len(log)]


def section_text(log, version):
    marker = "## [%s]" % version
    start = log.find(marker)
    if start < 0:
        return None
    end = log.find("\n## [", start + len(marker))
    body = log[start:end if end >= 0 else len(log)]
    body = re.split(r"\n\[[^\]]+\]: http", body)[0]
    return body.strip() + "\n"


def prepare(kind, explicit, dry, trailers):
    current = current_version()
    new = next_version(current, kind, explicit)
    tag = "v" + new
    print("version: %s -> %s   (tag %s)" % (current, new, tag))
    if git("rev-parse", "--abbrev-ref", "HEAD") != "main":
        raise ReleaseError("not on branch main")
    if git("status", "--porcelain"):
        raise ReleaseError("there are uncommitted changes; commit them first (git status)")
    if git("tag", "-l", tag):
        raise ReleaseError("tag %s already exists" % tag)
    log = read(CHANGELOG)
    if "- " not in unreleased_text(log):
        raise ReleaseError("nothing is written under '## [Unreleased]' in CHANGELOG.md")
    try:
        previous = git("describe", "--tags", "--abbrev=0", "--match", "v*")
    except ReleaseError:
        previous = ""
    base = "https://github.com/" + REPO
    compare = "%s/compare/%s...%s" % (base, previous, tag) if previous else "%s/releases/tag/%s" % (base, tag)
    today = datetime.date.today().isoformat()
    log = log.replace("## [Unreleased]", "## [Unreleased]\n\n## [%s] - %s" % (new, today), 1)
    links = "[Unreleased]: %s/compare/%s...HEAD\n[%s]: %s" % (base, tag, new, compare)
    if re.search(r"^\[Unreleased\]:.*$", log, re.M):
        log = re.sub(r"^\[Unreleased\]:.*$", lambda m: links, log, count=1, flags=re.M)
    else:
        log = log.rstrip("\n") + "\n\n" + links + "\n"
    settings = read(SETTINGS)
    settings, count = re.subn(r"^(\s*bundleVersion: ).*$", lambda m: m.group(1) + new, settings, count=1, flags=re.M)
    if count != 1:
        raise ReleaseError("bundleVersion not found in ProjectSettings.asset")
    readme = read(README) if README.exists() else ""
    readme = re.sub(r"(<!-- version -->).*?(<!-- /version -->)", lambda m: m.group(1) + new + m.group(2), readme, flags=re.S)
    if dry:
        print("dry run: would write VERSION, ProjectSettings.asset (bundleVersion), CHANGELOG.md, README.md, commit 'chore(release): %s' and tag %s" % (tag, tag))
        return
    write(VERSION_FILE, new + "\n")
    write(SETTINGS, settings)
    write(CHANGELOG, log)
    if readme:
        write(README, readme)
    git("add", "VERSION", "CHANGELOG.md", "ProjectSettings/ProjectSettings.asset", "README.md")
    message = ["commit", "-m", "chore(release): " + tag]
    for t in trailers:
        message += ["-m", t]
    git(*message)
    git("tag", "-a", tag, "-m", "ZeroProtocol " + new)
    print("prepared: commit + tag %s created locally (nothing pushed yet)" % tag)
    print("next: build the game, zip the build folder, then:")
    print("  python Tools/release.py publish --asset Build/ZeroProtocol-%s-win-x64.zip" % new)


def publish(assets, title, notes_file, dry):
    version = current_version()
    channel = parse(version)[3]
    tag = "v" + version
    if git("status", "--porcelain"):
        raise ReleaseError("there are uncommitted changes; commit them first (git status)")
    if not git("tag", "-l", tag):
        raise ReleaseError("tag %s does not exist; run a prepare command first (alpha, beta, ..., set)" % tag)
    if git("rev-parse", tag + "^{commit}") != git("rev-parse", "HEAD"):
        raise ReleaseError("HEAD is not the commit of tag %s" % tag)
    for a in assets:
        if not Path(a).is_file():
            raise ReleaseError("asset not found: " + a)
    notes = Path(notes_file) if notes_file else NOTES_DIR / (tag + ".md")
    temp = None
    if not notes.is_file():
        body = section_text(read(CHANGELOG), version)
        if not body:
            raise ReleaseError("no release notes: neither %s nor a CHANGELOG.md section for %s" % (notes, version))
        temp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
        temp.write(body)
        temp.close()
        notes = Path(temp.name)
    title = title or ("ZeroProtocol " + tag)
    command = ["gh", "release", "create", tag, "--title", title, "--notes-file", str(notes), "--verify-tag"]
    if channel:
        command.append("--prerelease")
    command += [str(a) for a in assets]
    print("title: %s | notes: %s | %s | assets: %s" % (title, notes, "pre-release" if channel else "release", ", ".join(assets) or "none"))
    if dry:
        print("dry run: would push main and %s, then run: %s" % (tag, " ".join(command)))
        return
    git("push", "origin", "main")
    git("push", "origin", tag)
    r = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, encoding="utf-8")
    if r.returncode != 0:
        raise ReleaseError("gh release create failed (commit and tag are pushed, run the gh command again):\n%s%s" % (r.stdout, r.stderr))
    print(r.stdout.strip())


def show():
    current = current_version()
    print("current version: " + current)
    for kind in ["alpha", "beta", "rc", "release", "patch", "minor", "major"]:
        try:
            print("  %-8s -> %s" % (kind, next_version(current, kind)))
        except ReleaseError as e:
            print("  %-8s -> not possible (%s)" % (kind, str(e).split(";")[0]))


def selftest():
    good = [
        ("0.0.1-alpha.1", "set", "0.1.0-alpha.1", "0.1.0-alpha.1"),
        ("0.1.0-alpha.1", "alpha", None, "0.1.0-alpha.2"),
        ("0.1.0-alpha.2", "beta", None, "0.1.0-beta.1"),
        ("0.1.0-beta.1", "rc", None, "0.1.0-rc.1"),
        ("0.1.0-rc.1", "release", None, "0.1.0"),
        ("0.1.0", "patch", None, "0.1.1"),
        ("0.1.1", "minor", None, "0.2.0"),
        ("0.2.0", "major", None, "1.0.0"),
        ("0.1.0", "alpha", None, "0.2.0-alpha.1"),
        ("1.4.2", "beta", None, "1.5.0-beta.1"),
    ]
    bad = [("0.1.0-alpha.1", "patch"), ("0.1.0-beta.1", "alpha"), ("0.1.0", "release"), ("0.1", "alpha")]
    failures = 0
    for cur, kind, explicit, want in good:
        got = next_version(cur, kind, explicit)
        if got != want:
            failures += 1
            print("FAIL %s %s -> %s (wanted %s)" % (cur, kind, got, want))
    for cur, kind in bad:
        try:
            next_version(cur, kind)
            failures += 1
            print("FAIL %s %s should have been refused" % (cur, kind))
        except ReleaseError:
            pass
    print("selftest: %d cases, %d failures" % (len(good) + len(bad), failures))
    return failures == 0


def main():
    parser = argparse.ArgumentParser(description="Zero Protocol release tool (see the top of this file)")
    parser.add_argument("command", choices=["show", "alpha", "beta", "rc", "release", "patch", "minor", "major", "set", "publish", "selftest"])
    parser.add_argument("value", nargs="?", help="the version for 'set'")
    parser.add_argument("--asset", action="append", default=[], help="file to attach to the GitHub release (publish)")
    parser.add_argument("--title", help="release title (publish), default: ZeroProtocol vX")
    parser.add_argument("--notes-file", help="release text (publish), default: Docs/releases/vX.md or the CHANGELOG.md section")
    parser.add_argument("--trailer", action="append", default=[], help="extra line at the end of the release commit message")
    parser.add_argument("--dry-run", action="store_true", help="show what would happen, change nothing")
    args = parser.parse_args()
    try:
        if args.command == "selftest":
            return 0 if selftest() else 1
        if args.command == "show":
            show()
        elif args.command == "publish":
            publish(args.asset, args.title, args.notes_file, args.dry_run)
        else:
            prepare(args.command, args.value, args.dry_run, args.trailer)
    except ReleaseError as e:
        print("ERROR: " + str(e))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
