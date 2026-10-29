import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import cache  # noqa: E402
import paths  # noqa: E402


class PathsTest(unittest.TestCase):
    def test_env_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(paths.data_home(env={"DOMOVED_HOME": tmp}), os.path.abspath(tmp))

    def test_plugin_root_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, "work", "domoved")
            self.assertEqual(paths.data_home(plugin_root=root, env={}, home_dir=tmp), root)

    def test_installed_copy_goes_to_documents(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = os.path.join(tmp, ".claude", "plugins", "cache", "lp-personal-claude-plugins", "lpp-domoved", "1.0.0")
            os.makedirs(root)
            self.assertEqual(paths.data_home(plugin_root=root, env={}, home_dir=tmp),
                             os.path.join(tmp, "Documents", "Домовед"))

    def test_system_locations(self):
        env = {}
        self.assertEqual(paths.system_cache_root(env=env, platform="darwin", home_dir="/h"), "/h/Library/Caches/domoved")
        self.assertEqual(paths.system_cache_root(env={"XDG_CACHE_HOME": "/x"}, platform="linux", home_dir="/h"), "/x/domoved")
        self.assertEqual(paths.system_cache_root(env={}, platform="linux", home_dir="/h"), "/h/.cache/domoved")
        self.assertTrue(paths.system_cache_root(env={"LOCALAPPDATA": "C:/L"}, platform="win32", home_dir="/h").endswith("domoved/Cache"))
        with tempfile.TemporaryDirectory() as tmp:
            import tempfile as tf
            old_tmp = tf.tempdir
            tf.tempdir = tmp
            try:
                self.assertEqual(paths.work_root(env={}), os.path.join(tmp, "domoved-work"))
            finally:
                tf.tempdir = old_tmp

    def test_new_work_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = os.environ.get("DOMOVED_HOME")
            os.environ["DOMOVED_HOME"] = tmp
            try:
                p = paths.new_work_dir("Мурино 8368369095")
                self.assertTrue(os.path.isdir(p))
                self.assertTrue(p.startswith(os.path.join(tmp, "work")))
                self.assertTrue(os.path.isdir(paths.cache_dir()))
            finally:
                if old is None:
                    os.environ.pop("DOMOVED_HOME", None)
                else:
                    os.environ["DOMOVED_HOME"] = old


class CacheTest(unittest.TestCase):
    def test_house_key_normalization(self):
        a = cache.key_house("194362, Россия, Ленинградская обл., Мурино, Петровский б-р, 11к1")
        b = cache.key_house("ленинградская обл  мурино петровский б-р 11к1")
        self.assertEqual(a, b)
        self.assertEqual(cache.key_house("Ёлочная 1"), cache.key_house("елочная 1"))
        with self.assertRaises(ValueError):
            cache.key_house("  ")

    def test_coords_key_grid(self):
        k1 = cache.key_coords(60.058457, 30.42443, 300)
        k2 = cache.key_coords(60.058500, 30.42450, 300)
        k3 = cache.key_coords(60.070000, 30.42443, 300)
        self.assertEqual(k1, k2)
        self.assertNotEqual(k1, k3)

    def test_put_get_ttl(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = cache.put("rates", "rates", data="{}", root=tmp)
            self.assertEqual(cache.get("rates", "rates", root=tmp), p)
            old = time.time() - 2 * 86400
            os.utime(p, (old, old))
            self.assertIsNone(cache.get("rates", "rates", root=tmp))       # TTL 1 day
            self.assertEqual(cache.get("rates", "rates", max_age_days=3, root=tmp), p)
            self.assertIsNone(cache.get("house", "nope", root=tmp))

    def test_bad_kind_and_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                cache.put("unknown", "k", data="", root=tmp)
            with self.assertRaises(ValueError):
                cache.put("osm", "../evil", data="", root=tmp)


if __name__ == "__main__":
    unittest.main()
