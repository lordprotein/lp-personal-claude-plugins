import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cleanup  # noqa: E402

DAY = 86400


def touch(path, age_days, now, content="x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    t = now - age_days * DAY
    os.utime(path, (t, t))


class CleanupTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        r = self.tmp.name
        self.reports = os.path.join(r, "reports")
        self.work = os.path.join(self.reports, "work")
        self.cache = os.path.join(r, ".cache")
        self.now = time.time()
        old_run = os.path.join(self.work, "old")
        new_run = os.path.join(self.work, "new")
        touch(os.path.join(old_run, "a.json"), 40, self.now)
        os.utime(old_run, (self.now - 40 * DAY,) * 2)
        touch(os.path.join(new_run, "a.json"), 1, self.now)
        os.utime(new_run, (self.now - DAY,) * 2)
        touch(os.path.join(self.cache, "rates", "r.json"), 2, self.now)      # ttl 1: expired
        touch(os.path.join(self.cache, "osm", "o.json"), 10, self.now)       # ttl 30: fresh
        touch(os.path.join(self.reports, "Домовед. X.html"), 400, self.now)
        touch(os.path.join(self.reports, "Домовед. X.pdf"), 10, self.now)

    def tearDown(self):
        self.tmp.cleanup()

    def names(self, items):
        return sorted(os.path.basename(p) for p, _ in items)

    def test_default_keeps_reports(self):
        items = cleanup.plan(self.reports, self.work, self.cache, now=self.now)
        self.assertEqual(self.names(items), ["old", "r.json"])

    def test_reports_days(self):
        items = cleanup.plan(self.reports, self.work, self.cache, reports_days=180, now=self.now)
        self.assertIn("Домовед. X.html", self.names(items))
        self.assertNotIn("Домовед. X.pdf", self.names(items))

    def test_dry_run_and_run(self):
        items = cleanup.plan(self.reports, self.work, self.cache, now=self.now)
        cleanup.run(items, dry_run=True)
        self.assertTrue(os.path.isdir(os.path.join(self.work, "old")))
        freed = cleanup.run(items)
        self.assertGreater(freed, 0)
        self.assertFalse(os.path.exists(os.path.join(self.work, "old")))
        self.assertTrue(os.path.isdir(os.path.join(self.work, "new")))
        self.assertTrue(os.path.exists(os.path.join(self.cache, "osm", "o.json")))

    def test_missing_dirs(self):
        self.assertEqual(cleanup.plan("/nonexistent/r", "/nonexistent/w", "/nonexistent/c"), [])


if __name__ == "__main__":
    unittest.main()
