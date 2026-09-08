import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import isolation
import publish


class BoundaryTests(unittest.TestCase):
    def test_builder_environment_drops_publishing_credentials(self):
        with patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": "private-sentinel",
                                     "GITHUB_TOKEN": "private-sentinel"}):
            self.assertNotIn("CLOUDFLARE_API_TOKEN", isolation.clean_env())
            self.assertNotIn("GITHUB_TOKEN", isolation.clean_env())

    def test_hardlinks_and_symlinks_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "module.js"
            source.write_bytes(b"export default {}")
            os.link(source, root / "hard.js")
            with self.assertRaises(RuntimeError):
                isolation.read_regular(source, 100)
            (root / "hard.js").unlink()
            (root / "link.js").symlink_to(source)
            with self.assertRaises(OSError):
                isolation.read_regular(root / "link.js", 100)
            (root / "parent").symlink_to(root, target_is_directory=True)
            with self.assertRaises(RuntimeError):
                isolation.read_regular(root / "parent/module.js", 100)

    def test_source_root_and_ancestor_symlinks_are_rejected_before_copy(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            private = root / "private"
            private.mkdir()
            (private / "credential").write_text("must-not-copy")
            link = root / "link"
            link.symlink_to(private, target_is_directory=True)
            target = root / "target"
            target.mkdir()
            for source in (link, link / "child"):
                if source != link:
                    (private / "child").mkdir()
                with self.assertRaises(RuntimeError):
                    isolation.copy_tree(source, target)
            self.assertEqual(list(target.iterdir()), [])

    def test_oversized_module_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "module.js"
            path.write_bytes(b"x" * 11)
            with self.assertRaises(RuntimeError):
                isolation.read_regular(path, 10)

    def test_module_imports_are_only_upload_bytes(self):
        module = b'import stolen from "/proc/self/environ"; export default stolen;'
        body, content_type = publish.multipart(module, "a" * 40)
        self.assertIn(module, body)
        self.assertIn(b'filename="catalog-worker.mjs"', body)
        self.assertIn("multipart/form-data", content_type)
        metadata = publish.version_metadata("a" * 40)
        self.assertEqual(metadata["main_module"], "catalog-worker.mjs")
        self.assertNotIn("source", metadata)
        self.assertNotIn("routes", metadata)
        self.assertNotIn("observability", metadata)

    def test_api_cannot_target_other_scripts_accounts_or_resources(self):
        client = publish.Cloudflare("test-only")
        for path in ("/secrets", "/versions/../../other", "/deployments?force=true",
                     "https://attacker.example", "/versions?bindings_inherit=permissive"):
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                client.request(path)

    def test_secret_bearing_api_requests_never_follow_redirects(self):
        with self.assertRaises(RuntimeError):
            publish.NoRedirect().redirect_request(None, None, 302, "", {}, "https://attacker.example")

    def test_split_existing_deployment_is_rejected(self):
        with self.assertRaises(RuntimeError):
            publish.stable_version({"versions": [{"version_id": "a", "percentage": 50}]})

    def test_rollback_does_not_overwrite_a_concurrent_release(self):
        class API:
            def latest(self):
                return {"versions": [{"version_id": "third-party", "percentage": 100}]}

            def deploy(self, *args):
                raise AssertionError("must not change a concurrent release")
        with self.assertRaises(RuntimeError):
            publish.rollback(API(), "previous", "candidate")

    def test_changed_deployment_id_or_traffic_prevents_stage_or_promotion(self):
        class API:
            def latest(self):
                return {"id": "concurrent", "versions": [{"version_id": "same-version", "percentage": 100}]}
        with self.assertRaises(RuntimeError):
            publish.assert_active(API(), "previous-deployment", [("same-version", 100)])
        with self.assertRaises(RuntimeError):
            publish.assert_active(API(), "concurrent", [("same-version", 100), ("candidate", 0)])

    def test_rollback_refuses_concurrent_redeployment_of_the_same_version(self):
        class API:
            def latest(self):
                return {"id": "concurrent", "versions": [{"version_id": "previous", "percentage": 100}]}
            def deploy(self, *args):
                raise AssertionError("must preserve concurrent deployment even for same bytes")
        with self.assertRaises(RuntimeError):
            publish.rollback(API(), "previous", "candidate",
                             {"previous_deployment_id": "original", "operation_id": "ours"})

    def test_second_manual_invocation_cannot_acquire_publication_lock(self):
        with tempfile.TemporaryDirectory() as directory:
            with publish.publication_lock(Path(directory)):
                with self.assertRaises(RuntimeError):
                    with publish.publication_lock(Path(directory)):
                        self.fail("Second publisher acquired the lock")

    def test_missing_explicit_source_is_rejected_before_network_or_build(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(RuntimeError):
            publish.main()


@unittest.skipUnless(sys.platform == "linux" and os.geteuid() == 0,
                     "Linux image build runs real UID isolation under tini")
class LinuxProcessTests(unittest.TestCase):
    def test_builder_cannot_read_root_secret_or_inherit_token(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o755)
            secret = root / "secret"
            secret.write_text("private-sentinel")
            secret.chmod(0o600)
            code = ("import os,pathlib; assert 'CLOUDFLARE_API_TOKEN' not in os.environ; "
                    "p=pathlib.Path(" + repr(str(secret)) + "); "
                    "assert not os.access(p,os.R_OK)")
            with patch.dict(os.environ, {"CLOUDFLARE_API_TOKEN": "private-sentinel"}):
                isolation.run(["python", "-c", code], root, builder=True)

    def test_detached_builder_child_cannot_change_the_sealed_candidate_later(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o777)
            target = root / "late-mutation"
            child = ("import os,time,pathlib; os.setsid(); time.sleep(1); "
                     "pathlib.Path(" + repr(str(target)) + ").symlink_to('/proc/1/environ')")
            parent = "import subprocess; subprocess.Popen(['python','-c'," + repr(child) + "])"
            isolation.run(["python", "-c", parent], root, builder=True)
            subprocess.run(["sleep", "1.1"], check=True)
            self.assertFalse(target.is_symlink())
            self.assertEqual(subprocess.run(["pgrep", "-u", "10001"], capture_output=True).returncode, 1)


if __name__ == "__main__":
    unittest.main()
