"""Checks of agents and docs: models, tools, digests, style."""
import glob
import json
import os
import re
import unittest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
AGENTS = sorted(glob.glob(os.path.join(ROOT, "agents", "*.md")))
REFS = os.path.join(ROOT, "skills", "property-due-diligence", "references")
SKILL = os.path.join(ROOT, "skills", "property-due-diligence", "SKILL.md")
README = os.path.join(ROOT, "README.md")
ANALYSTS = {"house-inspector", "district-analyst", "market-valuator", "future-scout",
            "local-analyst", "market-future"}


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


class DigestTest(unittest.TestCase):
    def test_agents_exist(self):
        names = {os.path.splitext(os.path.basename(p))[0] for p in AGENTS}
        self.assertTrue(ANALYSTS | {"listing-extractor"} <= names, names)

    def test_frontmatter_model_and_tools(self):
        for path in AGENTS:
            name = os.path.splitext(os.path.basename(path))[0]
            fm = frontmatter(read(path))
            self.assertEqual(fm.get("name"), name, path)
            self.assertIn(fm.get("model"), ("sonnet", "haiku"), path)
            tools = fm.get("tools", "")
            self.assertTrue(tools, "%s: tools not set (otherwise the agent gets all tools, including the browser)" % name)
            self.assertNotIn("mcp", tools.lower(), name)
            self.assertNotIn("browser", tools.lower(), name)
            if name in ANALYSTS:
                self.assertEqual(fm.get("model"), "sonnet", name)
                self.assertEqual([t.strip() for t in tools.split(",")],
                                 ["WebSearch", "WebFetch", "Read", "Write", "Bash"], name)
            if name == "listing-extractor":
                self.assertEqual(fm.get("model"), "haiku")

    def test_every_criterion_covered(self):
        with open(os.path.join(ROOT, "config", "profiles.json"), encoding="utf-8") as f:
            ids = list(json.load(f)["criteria"])
        text = "\n".join(read(p) for p in AGENTS)
        for cid in ids:
            self.assertIn(cid, text, "criterion %s is not mentioned in any agent" % cid)

    def test_stop_flags_exist_in_reference(self):
        ref = read(os.path.join(REFS, "red-flags.md"))
        ref_ids = set(re.findall(r"`([a-z0-9_]+)`", ref))
        ref_stop = set(re.findall(r"`([a-z0-9_]+)`\s*\|\s*stop", ref))
        for path in AGENTS:
            for line in read(path).splitlines():
                if "stop" not in line or "`" not in line:
                    continue
                m = re.search(r"\*\*stop:\*\*|stop:", line)
                if not m:
                    continue
                for fid in re.findall(r"`([a-z0-9_]+)`", line[m.end():]):
                    self.assertIn(fid, ref_ids, "%s: flag %s is missing in red-flags.md" % (path, fid))
                    self.assertIn(fid, ref_stop, "%s: flag %s is not stop in red-flags.md" % (path, fid))

    def test_no_browser_and_no_full_refs_for_analysts(self):
        for path in AGENTS:
            name = os.path.splitext(os.path.basename(path))[0]
            text = read(path)
            self.assertNotIn("Обязательно прочитай", text, name)
            if name in ANALYSTS:
                self.assertIn("Browser is forbidden.", text, name)

    def test_style_and_paths(self):
        for path in AGENTS + [SKILL, README]:
            text = read(path)
            self.assertNotIn("domoved-reports", text, path)
            self.assertNotIn("—", text, "em dash in %s" % path)


if __name__ == "__main__":
    unittest.main()
