#!/usr/bin/env python3
"""Where Domoved stores reports, working files and the cache.

Everything lives in one folder (data_home):
  - $DOMOVED_HOME, if set;
  - otherwise the plugin root (the folder above scripts/);
  - but if the plugin is installed via a marketplace (a copy inside ~/.claude/plugins
    that updates overwrite), then ~/Documents/Домовед (user-visible folder name, kept in Russian).

Reports (HTML, PDF on request) live in data_home/reports.
Working files of analyses and the cache are stored where the system cleans them itself:
  - work: the system temp folder (tempfile.gettempdir()/domoved-work);
    macOS and Linux remove long unused files from there on their own;
  - cache: the system cache folder (macOS ~/Library/Caches/domoved,
    Linux $XDG_CACHE_HOME or ~/.cache/domoved, Windows %LOCALAPPDATA%/domoved/Cache).
If DOMOVED_HOME is set, everything (reports, work, cache) lives inside it (handy for tests).

CLI:
  paths.py                    JSON {home, reports, work, cache}
  paths.py --new-work <slug>  create reports/work/<YYYYMMDD-HHMM>-<slug> and print the path
"""
import argparse
import datetime
import json
import os
import re
import sys
import tempfile

PLUGIN_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _is_installed_copy(root, home_dir=None):
    plugins = os.path.join(home_dir or os.path.expanduser("~"), ".claude", "plugins")
    root = os.path.realpath(root)
    plugins = os.path.realpath(plugins)
    return root == plugins or root.startswith(plugins + os.sep)


def data_home(plugin_root=None, env=None, home_dir=None):
    env = os.environ if env is None else env
    if env.get("DOMOVED_HOME"):
        return os.path.abspath(os.path.expanduser(env["DOMOVED_HOME"]))
    root = plugin_root or PLUGIN_ROOT
    if _is_installed_copy(root, home_dir):
        return os.path.join(home_dir or os.path.expanduser("~"), "Documents", "Домовед")
    return root


def _ensure(path):
    os.makedirs(path, exist_ok=True)
    return path


def reports_dir():
    return _ensure(os.path.join(data_home(), "reports"))


def system_cache_root(env=None, platform=None, home_dir=None):
    """System cache folder for the current OS."""
    env = os.environ if env is None else env
    platform = platform or sys.platform
    home = home_dir or os.path.expanduser("~")
    if platform == "darwin":
        return os.path.join(home, "Library", "Caches", "domoved")
    if platform.startswith("win"):
        base = env.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
        return os.path.join(base, "domoved", "Cache")
    return os.path.join(env.get("XDG_CACHE_HOME") or os.path.join(home, ".cache"), "domoved")


def work_root(env=None):
    env = os.environ if env is None else env
    if env.get("DOMOVED_HOME"):
        return _ensure(os.path.join(data_home(env=env), "work"))
    return _ensure(os.path.join(tempfile.gettempdir(), "domoved-work"))


def cache_dir(env=None):
    env = os.environ if env is None else env
    if env.get("DOMOVED_HOME"):
        return _ensure(os.path.join(data_home(env=env), ".cache"))
    return _ensure(system_cache_root(env=env))


def safe_slug(slug):
    slug = re.sub(r"[^\w.-]+", "-", (slug or "object").strip().lower(), flags=re.UNICODE).strip("-.")
    return slug[:60] or "object"


def new_work_dir(slug, now=None):
    stamp = (now or datetime.datetime.now()).strftime("%Y%m%d-%H%M")
    path = os.path.join(work_root(), "%s-%s" % (stamp, safe_slug(slug)))
    return _ensure(path)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Domoved data folders")
    ap.add_argument("--new-work", metavar="SLUG", help="create an analysis working folder and print the path")
    a = ap.parse_args(argv)
    if a.new_work is not None:
        print(new_work_dir(a.new_work))
        return 0
    print(json.dumps({"home": data_home(), "reports": reports_dir(), "work": work_root(),
                      "cache": cache_dir()}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
