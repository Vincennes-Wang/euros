import json
import shutil
from pathlib import Path

import pytest
import requests

from scraper import ecb, scrape
from scraper.scrape import same_page


def test_same_page_ignores_server_time():
    a = "<script>ECB.clientTimeError = 1791490689 - (new Date().getTime());</script><p>x</p>"
    b = "<script>ECB.clientTimeError = 1791492313 - (new Date().getTime());</script><p>x</p>"
    assert same_page(a, b)
    assert not same_page(a, b.replace("<p>x</p>", "<p>y</p>"))


REPO = Path(__file__).resolve().parent.parent
YEAR = 2004


class FakeResponse:
    def __init__(self, status: int, text: str = "", content_type: str = "text/html") -> None:
        self.status_code = status
        self.ok = 200 <= status < 300
        self.text = text
        self.content = text.encode("utf-8")
        self.headers = {"Content-Type": content_type}
        self.encoding = None


class FailingFetcher:
    """Every request fails, as when the ECB is unreachable."""

    def get(self, url: str):
        raise requests.ConnectionError("network down")


class PageOnlyFetcher:
    """Serves the archived year page; every image request returns 404."""

    def __init__(self, html: str) -> None:
        self.html = html

    def get(self, url: str):
        return FakeResponse(200, self.html) if url == ecb.page_url(YEAR) else FakeResponse(404)


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Point scrape at a temp data/ holding the real 2004 page and its images."""
    data = tmp_path / "data"
    raw = data / "raw"
    raw.mkdir(parents=True)
    shutil.copy(REPO / "data" / "raw" / f"comm_{YEAR}.en.html", raw)
    monkeypatch.setattr(scrape, "ROOT", tmp_path)
    monkeypatch.setattr(scrape, "RAW", raw)
    monkeypatch.setattr(scrape, "IMAGES", data / "images")
    monkeypatch.setattr(scrape, "COINS_JSON", data / "coins.json")
    return tmp_path


def copy_images(root: Path) -> None:
    shutil.copytree(REPO / "data" / "images" / str(YEAR), root / "data" / "images" / str(YEAR))


def test_offline_strict_passes_on_clean_archive(sandbox):
    copy_images(sandbox)
    assert scrape.main(["--offline", "--years", str(YEAR), "--strict"]) == 0


def test_strict_fails_when_fetch_falls_back_to_archive(sandbox, monkeypatch, capsys):
    copy_images(sandbox)
    monkeypatch.setattr(scrape, "Fetcher", FailingFetcher)
    assert scrape.main(["--years", str(YEAR)]) == 0
    assert scrape.main(["--years", str(YEAR), "--strict"]) == 1
    assert "used archive" in capsys.readouterr().err


def test_strict_fails_when_coin_disappears(sandbox, capsys):
    copy_images(sandbox)
    assert scrape.main(["--offline", "--years", str(YEAR)]) == 0
    coins_json = sandbox / "data" / "coins.json"
    coins = json.loads(coins_json.read_text(encoding="utf-8"))
    coins.append({**coins[0], "id": f"{YEAR}-xx-gone", "title": "Gone"})
    coins_json.write_text(json.dumps(coins), encoding="utf-8")
    assert scrape.main(["--offline", "--years", str(YEAR), "--strict"]) == 1
    assert f"{YEAR}-xx-gone no longer on the page (dropped)" in capsys.readouterr().err


def test_strict_fails_when_image_download_fails(sandbox, monkeypatch, capsys):
    html = (sandbox / "data" / "raw" / f"comm_{YEAR}.en.html").read_text(encoding="utf-8")
    monkeypatch.setattr(scrape, "Fetcher", lambda: PageOnlyFetcher(html))
    monkeypatch.setattr(scrape, "DELAY_SECONDS", 0)
    assert scrape.main(["--years", str(YEAR), "--strict"]) == 1
    assert "image failed" in capsys.readouterr().err
