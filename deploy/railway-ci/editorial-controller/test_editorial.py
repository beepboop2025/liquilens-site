import json
import os
from pathlib import Path
import tempfile
import time
import unittest

import editorial
from isolation import digest, read_regular


class EditorialTests(unittest.TestCase):
    def test_publication_paths_cannot_include_executable_or_hidden_files(self):
        for name in ("articles/2026-09-08-example.md", "articles/example/share.png",
                     "articles/index.json", "llms.txt", "sitemap.xml"):
            self.assertTrue(editorial.allowed_output(name), name)
        for name in ("articles/.git/config", "articles/../script.py", "articles/run.py",
                     "articles/example/worker.js", "scripts/daily_article.py", "config.env"):
            self.assertFalse(editorial.allowed_output(name), name)

    def test_file_reader_rejects_symbolic_and_hard_links(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.write_text("reviewed")
            symbolic = root / "symbolic"
            symbolic.symlink_to(target)
            with self.assertRaises(OSError):
                read_regular(symbolic)
            linked = root / "linked"
            os.link(target, linked)
            with self.assertRaises(ValueError):
                read_regular(linked)

    def test_failed_quality_gate_and_modified_code_block_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "articles/example").mkdir(parents=True)
            code = root / "code.py"
            code.write_text("reviewed")
            baseline = {"code.py": digest(b"reviewed")}
            (root / "articles/index.json").write_text(json.dumps([
                {"date": "2026-09-08", "slug": "example"}]))
            sidecar = root / "articles/example.json"
            value = {"date": "2026-09-08", "slug": "example",
                     "canonical_url": "https://liquilens.in/articles/example/",
                     "quality_gate": {"status": "FAIL"}}
            sidecar.write_text(json.dumps(value))
            for suffix in (".md", "/index.html", "/share.png"):
                (root / f"articles/example{suffix}").write_bytes(b"content")
            with self.assertRaisesRegex(ValueError, "quality gate"):
                editorial.validate_outputs(root, baseline, "2026-09-08")
            value["quality_gate"]["status"] = "PASS"
            sidecar.write_text(json.dumps(value))
            changed, slug = editorial.validate_outputs(root, baseline, "2026-09-08")
            self.assertEqual(slug, "example")
            self.assertNotIn("code.py", changed)
            code.write_text("unreviewed")
            with self.assertRaisesRegex(ValueError, "unapproved changed"):
                editorial.validate_outputs(root, baseline, "2026-09-08")

    @unittest.skipUnless(os.geteuid() == 0 and os.path.exists("/proc"), "Linux root image test")
    def test_writer_cannot_read_publisher_key_or_inherited_descriptor(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o755)
            private = root / "private"
            private.mkdir(mode=0o700)
            key = private / "key"
            key.write_text("fake-publisher-key")
            fd = os.open(key, os.O_RDONLY)
            os.set_inheritable(fd, True)
            try:
                program = """import os,sys
assert 'GITHUB_DEPLOY_KEY' not in os.environ
for path in sys.argv[1:]:
    try:
        open(path, 'rb').read()
    except (PermissionError, FileNotFoundError):
        pass
    else:
        raise AssertionError('private publisher resource was readable')
"""
                editorial.run_writer(root, root / "scratch", ["-c", program, str(key),
                    f"/proc/{os.getpid()}/environ", f"/proc/self/fd/{fd}"], {}, 10)
            finally:
                os.close(fd)

    @unittest.skipUnless(os.geteuid() == 0 and os.path.exists("/proc"), "Linux root image test")
    def test_detached_child_cannot_mutate_sealed_outputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o755)
            writable = root / "output"
            writable.mkdir()
            os.chown(writable, editorial.COLLECTOR_UID, editorial.COLLECTOR_UID)
            sentinel = writable / "late"
            child = "import time,pathlib;time.sleep(2);pathlib.Path(%r).write_text('late')" % str(sentinel)
            program = "import subprocess,sys;subprocess.Popen([sys.executable,'-c',%r],start_new_session=True)" % child
            editorial.run_writer(root, root / "scratch", ["-c", program], {}, 10)
            time.sleep(2.2)
            self.assertFalse(sentinel.exists())


if __name__ == "__main__":
    unittest.main()
