#!/usr/bin/env python3
"""Cleanup of Domoved data, so the folder does not grow.

What is removed:
- analysis working folders reports/work/<...> older than --work-days (default 30):
  they are needed only to rebuild the report;
- expired cache entries .cache/<kind>/*.json (older than the lifetime of their kind);
- reports reports/*.html and *.pdf only if --reports-days > 0 is set
  (or the DOMOVED_KEEP_REPORTS_DAYS variable); by default reports are kept forever.

Usage:
  cleanup.py [--work-days 30] [--reports-days 0] [--dry-run] [--quiet]
"""
import argparse
import os
import shutil
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import cache  # noqa: E402
import paths  # noqa: E402

DAY = 86400


def _age_days(path, now):
    return (now - os.path.getmtime(path)) / DAY


def _size(path):
    if os.path.isfile(path):
        return os.path.getsize(path)
    total = 0
    for base, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(base, f))
            except OSError:
                pass
    return total


def plan(reports, work, cache_root, work_days=30, reports_days=0, now=None):
    """List of (path, reason) to remove. Removes nothing."""
    now = now or time.time()
    out = []
    if os.path.isdir(work) and work_days > 0:
        for name in sorted(os.listdir(work)):
            p = os.path.join(work, name)
            if os.path.isdir(p) and _age_days(p, now) > work_days:
                out.append((p, "working files older than %d days" % work_days))
    if os.path.isdir(cache_root):
        for kind in sorted(os.listdir(cache_root)):
            folder = os.path.join(cache_root, kind)
            if not os.path.isdir(folder):
                continue
            ttl = cache.TTL_DAYS.get(kind, 30)
            for f in sorted(os.listdir(folder)):
                p = os.path.join(folder, f)
                if os.path.isfile(p) and _age_days(p, now) > ttl:
                    out.append((p, "cache %s expired" % kind))
    if os.path.isdir(reports) and reports_days > 0:
        for f in sorted(os.listdir(reports)):
            p = os.path.join(reports, f)
            if os.path.isfile(p) and f.lower().endswith((".html", ".pdf")) and _age_days(p, now) > reports_days:
                out.append((p, "report older than %d days" % reports_days))
    return out


def run(items, dry_run=False):
    freed = 0
    for p, _why in items:
        freed += _size(p)
        if dry_run:
            continue
        if os.path.isdir(p):
            shutil.rmtree(p, ignore_errors=True)
        else:
            try:
                os.remove(p)
            except OSError:
                pass
    return freed


def main(argv=None):
    ap = argparse.ArgumentParser(description="Cleanup of Domoved working files, cache and (optionally) old reports")
    ap.add_argument("--work-days", type=int, default=30, help="remove working folders older than N days (0 = do not remove)")
    env_days = os.environ.get("DOMOVED_KEEP_REPORTS_DAYS", "0")
    ap.add_argument("--reports-days", type=int, default=int(env_days) if env_days.isdigit() else 0,
                    help="remove reports older than N days (0 = keep forever)")
    ap.add_argument("--dry-run", action="store_true", help="only show what would be removed")
    ap.add_argument("--quiet", action="store_true", help="print only the summary line")
    args = ap.parse_args(argv)

    items = plan(paths.reports_dir(), paths.work_root(), paths.cache_dir(),
                 args.work_days, args.reports_days)
    freed = run(items, args.dry_run)
    if not args.quiet:
        for p, why in items:
            print("%s: %s" % (why, p))
    verb = "Would free" if args.dry_run else "Freed"
    print("%s %.1f MB, items: %d" % (verb, freed / 1048576.0, len(items)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
