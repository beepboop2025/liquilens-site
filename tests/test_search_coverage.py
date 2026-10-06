"""Fault-injection tests for public discovery monitoring; no live requests."""

import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "search_coverage", Path(__file__).resolve().parents[1] / "scripts/check_search_coverage.py")
monitor = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(monitor)
ORIGIN = "https://example.test"
PRODUCT = {"name": "Example", "origin": ORIGIN, "minimum_urls": 2,
           "pages": ("/", "/guide/"), "sitemaps": ("/sitemap.xml",)}


def response(url, body, content_type="text/plain", status=200, headers=None):
    return {"url": url, "body": body.encode(), "status": status, "error": None,
            "headers": {"content-type": content_type, **(headers or {})}}


def page(url, extra=""):
    return response(url, f'<title>Useful example</title><meta name="description" content="Dated evidence">'
                    f'<link rel="canonical" href="{url}">{extra}', "text/html")


def xml(urls, index=False):
    root, item = ("sitemapindex", "sitemap") if index else ("urlset", "url")
    return (f'<{root} xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + "".join(f'<{item}><loc>{url}</loc></{item}>' for url in urls) + f'</{root}>')


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.fixtures = {
            ORIGIN + "/robots.txt": response(ORIGIN + "/robots.txt", f"User-agent: *\nAllow: /\nSitemap: {ORIGIN}/sitemap.xml\n"),
            ORIGIN + "/llms.txt": response(ORIGIN + "/llms.txt", ORIGIN + " useful evidence" * 30),
            ORIGIN + "/.well-known/ai-catalog.json": response(ORIGIN + "/.well-known/ai-catalog.json", '{"name":"Example"}', "application/json"),
            ORIGIN + "/sitemap.xml": response(ORIGIN + "/sitemap.xml", xml([ORIGIN + "/", ORIGIN + "/guide/"]), "application/xml"),
            ORIGIN + "/": page(ORIGIN + "/"),
            ORIGIN + "/guide/": page(ORIGIN + "/guide/"),
        }
        self.calls = []

    def fetch(self, url, origin, plain=False):
        self.calls.append((url, plain))
        self.assertEqual(origin, ORIGIN)
        return self.fixtures[url]

    def audit(self, full=True, fetcher=None):
        return monitor.audit_product(PRODUCT, full=full, fetcher=fetcher or self.fetch)

    def test_follows_declared_article_sitemap_and_nested_indexes(self):
        robot = self.fixtures[ORIGIN + "/robots.txt"]
        robot["body"] += f"Sitemap: {ORIGIN}/articles-index.xml\n".encode()
        self.fixtures[ORIGIN + "/articles-index.xml"] = response(ORIGIN + "/articles-index.xml", xml([ORIGIN + "/articles.xml"], True), "application/xml")
        self.fixtures[ORIGIN + "/articles.xml"] = response(ORIGIN + "/articles.xml", xml([ORIGIN + "/article/"]), "application/xml")
        self.fixtures[ORIGIN + "/article/"] = page(ORIGIN + "/article/")
        result = self.audit()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["pages_checked"], 3)
        self.assertEqual(len(result["sitemaps"]), 3)

    def test_changed_discovery_expands_to_full_inventory(self):
        extra = ORIGIN + "/new-research/"
        self.fixtures[extra] = page(extra)
        self.fixtures[ORIGIN + "/sitemap.xml"]["body"] = xml([ORIGIN + "/", ORIGIN + "/guide/", extra]).encode()
        first = monitor.audit_product(PRODUCT, fetcher=self.fetch, full_on_change=True)
        self.assertTrue(first["full_page_audit"])
        self.assertEqual(first["pages_checked"], 3)
        same = monitor.audit_product(PRODUCT, fetcher=self.fetch, full_on_change=True,
                                     previous_revision=first["discovery_revision"])
        self.assertFalse(same["full_page_audit"])
        self.assertEqual(same["pages_checked"], 2)
        self.fixtures[ORIGIN + "/.well-known/ai-catalog.json"]["body"] = b'{"release":"updated"}'
        changed = monitor.audit_product(PRODUCT, fetcher=self.fetch, full_on_change=True,
                                        previous_revision=first["discovery_revision"])
        self.assertTrue(changed["full_page_audit"])

    def test_topic_content_jsonld_and_snippet_controls(self):
        valid = '<h1>Bank evidence</h1><p>' + 'Research evidence with source dates. ' * 12 + '</p>'
        self.assertEqual(monitor.validate_topic_page(page(ORIGIN, valid))["jsonld_blocks"], 0)
        for suffix in ['<script type="application/ld+json">{bad}</script>',
                       '<meta name="robots" content="nosnippet">',
                       '<meta name="Googlebot" content="max-snippet:0">']:
            with self.subTest(suffix=suffix), self.assertRaises(ValueError):
                monitor.validate_topic_page(page(ORIGIN, valid + suffix))
        with self.assertRaises(ValueError):
            monitor.validate_topic_page(page(ORIGIN, '<div id="app"></div>'))

    def test_gemini_policy_is_observed_separately_from_search(self):
        self.fixtures[ORIGIN + "/robots.txt"]["body"] += b'\nUser-agent: Google-Extended\nDisallow: /\n'
        self.fixtures[ORIGIN + "/guide/"] = page(ORIGIN + "/guide/", '<h1>Guide</h1><p>' + 'Evidence and limits. ' * 20 + '</p>')
        result = monitor.audit_product(PRODUCT, fetcher=self.fetch, topics=("/guide/",))
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["gemini_policy"], {ORIGIN + "/guide/": False})

    def test_sitemap_loss_and_missing_entry_are_failures(self):
        self.fixtures[ORIGIN + "/sitemap.xml"]["body"] = xml([ORIGIN + "/"]).encode()
        result = self.audit()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("below reviewed minimum" in row["problem"] for row in result["errors"]))
        self.assertTrue(any("required entry" in row["problem"] for row in result["errors"]))

    def test_offsite_sitemap_is_rejected_before_a_network_request(self):
        self.fixtures[ORIGIN + "/robots.txt"]["body"] += b"Sitemap: https://other.example/sitemap.xml\n"
        result = self.audit()
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(any("other.example" in url for url, _ in self.calls))

    def test_rejects_unsafe_urls_invalid_xml_and_entities(self):
        for body in [b"<urlset/>", b"<html>challenge</html>",
                     b'<!DOCTYPE urlset [<!ENTITY x "x">]><urlset/>',
                     xml(["http://example.test/"]).encode(),
                     xml(["https://user:secret@example.test/"]).encode(),
                     xml(["https://example.test.evil/"]).encode(),
                     xml([ORIGIN + "/", ORIGIN + "/"]).encode()]:
            with self.subTest(body=body), self.assertRaises(ValueError):
                monitor.sitemap_locations(body, ORIGIN)

    def test_robots_blocks_search_but_training_opt_out_is_not_failure(self):
        self.fixtures[ORIGIN + "/robots.txt"]["body"] += b"\nUser-agent: GPTBot\nDisallow: /\n"
        self.assertEqual(self.audit()["status"], "PASS")
        self.fixtures[ORIGIN + "/robots.txt"]["body"] += b"\nUser-agent: OAI-SearchBot\nDisallow: /\n"
        result = self.audit()
        self.assertEqual(result["status"], "FAIL")
        self.assertTrue(any("OAI-SearchBot" in row["problem"] for row in result["errors"]))

    def test_canonical_noindex_and_missing_title_are_detected(self):
        url = ORIGIN + "/guide/"
        for bad in [page(url, '<meta name="Googlebot" content="NOINDEX, follow">'),
                    response(url, '<title>Guide</title><link rel="canonical" href="https://other.example/">', "text/html"),
                    page(url + "wrong/"),
                    response(url, '<meta name="description" content="Still here">', "text/html"),
                    {**page(url), "headers": {"content-type": "text/html", "x-robots-tag": "googlebot: none"}}]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                monitor.validate_page(bad, url)

    def test_http_failures_redirects_and_html_challenges_cannot_pass(self):
        for status, body, media in [(403, "blocked", "text/plain"),
                                    (302, "", "application/xml"),
                                    (200, "<html>challenge</html>", "text/html")]:
            with self.subTest(status=status, media=media):
                url = ORIGIN + "/sitemap.xml"
                self.fixtures[url] = response(url, body, media, status)
                self.assertEqual(self.audit()["status"], "FAIL")

    def test_missing_or_malformed_catalog_cannot_pass(self):
        for body in ["{}", "[]", "not-json"]:
            self.fixtures[ORIGIN + "/.well-known/ai-catalog.json"]["body"] = body.encode()
            self.assertEqual(self.audit()["status"], "FAIL")

    def test_plain_client_block_stays_visible_without_claiming_google_block(self):
        def fetch(url, origin, plain=False):
            if plain:
                return response(url, "blocked", status=403)
            return self.fetch(url, origin)
        result = self.audit(fetcher=fetch)
        self.assertEqual(result["status"], "PASS_WITH_WARNINGS")
        self.assertEqual(len(result["warnings"]), 4)
        self.assertEqual(result["errors"], [])

    def test_lightweight_audit_checks_all_robot_permissions_but_only_entry_pages(self):
        self.fixtures[ORIGIN + "/sitemap.xml"]["body"] = xml([ORIGIN + "/", ORIGIN + "/guide/", ORIGIN + "/private/"]).encode()
        self.fixtures[ORIGIN + "/robots.txt"]["body"] = f"User-agent: *\nDisallow: /private/\nSitemap: {ORIGIN}/sitemap.xml\n".encode()
        result = self.audit(full=False)
        self.assertEqual(result["pages_checked"], 2)
        self.assertEqual(result["status"], "FAIL")
        self.assertFalse(any(url.endswith("/private/") for url, _ in self.calls))

    def test_cyclic_indexes_are_bounded_and_do_not_report_missing_pages_as_success(self):
        url = ORIGIN + "/sitemap.xml"
        self.fixtures[url]["body"] = xml([url], True).encode()
        result = self.audit()
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(sum(u == url and not plain for u, plain in self.calls), 1)

    def test_redirect_handler_never_follows_remote_locations(self):
        self.assertIsNone(monitor.NoRedirect().redirect_request(None, None, 302, "", {}, "http://127.0.0.1/"))

    def test_reviewed_machine_readable_documents_are_valid_without_html_metadata(self):
        monitor.validate_page(response(ORIGIN + "/data.json", '{"source":"dated"}', "application/json"), ORIGIN + "/data.json")
        monitor.validate_page(response(ORIGIN + "/guide.md", "# Guide\n" + "Evidence and limitations. " * 10, "text/markdown"), ORIGIN + "/guide.md")
        for path, body, media in [("/data.json", "[]", "application/json"),
                                   ("/data.json", "<html>challenge</html>", "text/html"),
                                   ("/guide.md", "", "text/markdown")]:
            with self.assertRaises(ValueError):
                monitor.validate_page(response(ORIGIN + path, body, media), ORIGIN + path)

    def test_robots_specific_path_overrides_earlier_allow_root(self):
        policy = monitor.RobotsPolicy("User-agent: *\nAllow: /\nDisallow: /private/\nAllow: /private/public/\n")
        self.assertFalse(policy.can_fetch("Googlebot", ORIGIN + "/private/a"))
        self.assertTrue(policy.can_fetch("Googlebot", ORIGIN + "/private/public/a"))

    def test_robots_merges_specific_groups_ignoring_unsupported_fields_and_blank_lines(self):
        policy = monitor.RobotsPolicy("User-agent: *\nDisallow: /\n\nUser-agent: Googlebot\nAllow: /\n\nUser-agent: Googlebot/1.2\nDisallow: /private/\n")
        self.assertTrue(policy.can_fetch("Googlebot", ORIGIN + "/"))
        self.assertFalse(policy.can_fetch("Googlebot", ORIGIN + "/private/"))
        self.assertFalse(policy.can_fetch("Bingbot", ORIGIN + "/"))
        shared = monitor.RobotsPolicy("User-agent: Googlebot\nSitemap: https://example.test/sitemap.xml\n\nUser-agent: Bingbot\nDisallow: /\n")
        self.assertFalse(shared.can_fetch("Googlebot", ORIGIN + "/"))
        self.assertFalse(shared.can_fetch("Bingbot", ORIGIN + "/"))

    def test_robots_wildcards_end_markers_allow_ties_and_encoded_paths(self):
        policy = monitor.RobotsPolicy("User-agent: *\nAllow: /page\nDisallow: /*.htm\nDisallow: /*.ph\nDisallow: /secret$\nDisallow: /café/\nDisallow: /%67uide/\n")
        self.assertFalse(policy.can_fetch("Googlebot", ORIGIN + "/page.htm"))
        self.assertTrue(policy.can_fetch("Googlebot", ORIGIN + "/page.php5"))
        self.assertFalse(policy.can_fetch("Googlebot", ORIGIN + "/secret"))
        self.assertTrue(policy.can_fetch("Googlebot", ORIGIN + "/secret?public=1"))
        self.assertFalse(policy.can_fetch("Googlebot", ORIGIN + "/caf%C3%A9/a"))
        self.assertFalse(policy.can_fetch("Googlebot", ORIGIN + "/guide/a"))


if __name__ == "__main__":
    unittest.main()
