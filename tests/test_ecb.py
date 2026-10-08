import pytest

from scraper import ecb


@pytest.mark.parametrize("raw, expected", [
    ("100,000 coins", 100_000),
    ("70 000 coins", 70_000),
    ("16 million coins", 16_000_000),
    ("1 million", 1_000_000),
    ("1,4 million coins", 1_400_000),
    ("2.49 million coins", 2_490_000),
    ("30 millions coins", 30_000_000),
    ("18 061 940 coins", 18_061_940),
    ("max 750 000 coins", 750_000),
    ("varies from country to country", None),
    ("", None),
    (None, None),
])
def test_parse_volume(raw, expected):
    assert ecb.parse_volume(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("December 2004", "2004-12"),
    ("1 July 2022", "2022-07-01"),
    ("21 October 2019", "2019-10-21"),
    ("Fourth quarter 2022", "2022"),
    ("Spring 2022", "2022"),
    ("April-May 2022", "2022"),
    ("Second/third quarter of 2023", "2023"),
    ("January 2012 for all euro area countries except San Marino (May 2012)", "2012"),
    ("soon", None),
    (None, None),
])
def test_parse_date(raw, expected):
    assert ecb.parse_date(raw) == expected


def test_slugify():
    assert ecb.slugify("Bundesländer series – Thuringia") == "thuringia"
    assert ecb.slugify("75th anniversary of the founding of the Vatican City State") == "75th-founding-vatican-city"
    assert ecb.slugify("100 years of Finland’s independence") == "100-years-finlands-independence"
    assert ecb.slugify("Côte d'Azur") == "cote-dazur"


@pytest.mark.parametrize("src, key", [
    ("comm_2015/joint_comm_2015_Austria.jpg", "at"),
    ("comm_2015/joint_comm_2015_Nederland.jpg", "nl"),
    ("comm_2012/joint_comm_2012_San_Marino.jpg", "sm"),
    ("comm_2009/joint_comm_2009_Luxembourg_Face.jpg", "lu-face"),
    ("comm_2022/Austria1.jpg", "at"),
    ("comm_2022/2022_comm_EU1-erasmus 540x540.jpg", "common"),
])
def test_joint_variant_key(src, key):
    assert ecb.joint_variant_key(src) == key


def box(h3, body, imgs=("comm_2021/x.jpg",)):
    pics = "".join(f'<picture><img src="{s}"/></picture>' for s in imgs)
    return (f'<div class="box"><div class="coins">{pics}</div>'
            f'<div class="content-box"><h3>{h3}</h3><div>{body}</div></div></div>')


def page(*boxes):
    return f'<html><body><main><div class="boxes">{"".join(boxes)}</div></main></body></html>'


def test_parse_page_label_variants():
    html = page(
        # Malta 2021: label split across tags
        box("Malta", "<p><strong>Feature:</strong> A</p><p><strong>Description:</strong> B</p>"
                     "<p><strong>Issuing volume:</strong> 181 000 coins</p>"
                     "<p>I<strong>ssuing date:</strong> October 2021</p>"),
        # Germany 2025: colon outside <strong>; San Marino 2022: colon in its own <strong>
        box("Germany", "<p><strong>Feature</strong>: C</p><p><strong>Description: </strong>D</p>"
                       "<p><strong>Issuing volume</strong><strong>: </strong>30 000 000 coins</p>"
                       "<p><strong>Issuing </strong><strong>date: </strong>Spring 2022</p>"),
        # Malta 2022: <p> inside <h3>, description continues in an unlabelled <p>
        box("<p> Malta</p>", "<p><strong>Feature:</strong> E</p><p><strong>Description:</strong> F1</p>"
                             "<p>F2</p><p><strong>Issuing volume:</strong> 65 500 coins</p>"
                             "<p><strong>Issuing date:</strong> June 2025<br/></p>"),
        # Luxembourg 2023: Feature directly in a <div>, not in a <p>
        box("Luxembourg", "<strong>Feature:</strong> G<div><p><strong><br/></strong></p>"
                          "<p><strong>Description:</strong> H</p><p><strong> Issuing volume:</strong> 500 000 coins </p>"
                          "<p><strong>Issuing date:</strong> February 2023</p></div>"),
    )
    coins, warnings = ecb.parse_page(html, 2021)
    assert warnings == []
    assert [(c["country_code"], c["title"], c["volume"], c["issue_date"]) for c in coins] == [
        ("mt", "A", 181_000, "2021-10"),
        ("de", "C", 30_000_000, "2022"),
        ("mt", "E", 65_500, "2025-06"),
        ("lu", "G", 500_000, "2023-02"),
    ]
    assert coins[2]["description_en"] == "F1 F2"
    assert coins[0]["image_source_url"] == "https://www.ecb.europa.eu/euro/coins/comm/html/comm_2021/x.jpg"


def test_parse_page_joint_issue():
    html = page(box("Euro area countries",
                    "<p><strong>Feature:</strong> Erasmus</p><p><strong>Description:</strong> X</p>"
                    "<p><strong>Issuing volume:</strong> varies from country to country</p>"
                    "<p><strong>Issuing date:</strong> 1 July 2022</p>",
                    imgs=("comm_2022/Austria1.jpg", "comm_2022/2022_comm_EU1-erasmus 540x540.jpg")))
    (coin,), _ = ecb.parse_page(html, 2022)
    assert coin["is_joint_issue"] and coin["country_code"] == "eu" and coin["volume"] is None
    assert coin["image_source_url"].endswith("2022_comm_EU1-erasmus%20540x540.jpg")
    assert list(coin["variant_image_sources"]) == ["at"]
