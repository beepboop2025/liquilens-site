from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_investor_demo_is_visible_in_the_nav_and_hero():
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    nav = html.split("<nav>", 1)[1].split("</nav>", 1)[0]
    hero = html.split("<!-- hero -->", 1)[1].split('<p class="lede"', 1)[0]
    demo_entry = "https://demo.liquilens.in/?demo=1"

    assert demo_entry in nav
    assert demo_entry in hero
    assert "sign in required" in nav.lower()
    assert "same password" in hero.lower()
    assert nav.count('data-funnel="investor_demo_clicked"') == 1
    assert hero.count('data-funnel="investor_demo_clicked"') == 1
