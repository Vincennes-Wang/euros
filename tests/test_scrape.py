from scraper.scrape import same_page


def test_same_page_ignores_server_time():
    a = "<script>ECB.clientTimeError = 1791490689 - (new Date().getTime());</script><p>x</p>"
    b = "<script>ECB.clientTimeError = 1791492313 - (new Date().getTime());</script><p>x</p>"
    assert same_page(a, b)
    assert not same_page(a, b.replace("<p>x</p>", "<p>y</p>"))
