import tempfile
import unittest
from pathlib import Path

from src.phase4_search_snapshot import (
    canonical_product_url,
    deduplicate_cards,
    parse_snapshot,
    product_platform,
    run_snapshot_search,
    source_page_url,
)


CARD_HTML = """
<!doctype html>
<!-- saved from url=(0060)https://s.taobao.com/search?q=%E9%85%B8%E6%9E%A3%E4%BB%81 -->
<a id="item_id_123" data-spm="2" class="doubleCardWrapperAdapt--observed"
   href="https://detail.tmall.com/item.htm?id=123&amp;spm=tracking">
  <div class="title--observed" title="酸枣仁膏"><span>酸枣仁膏</span></div>
  <span class="shopNameText--observed">真实店铺</span>
  <div class="procity--observed"><span>山西</span></div>
  <div class="procity--observed"><span>太原</span></div>
  <div class="priceInt--observed">19</div><div class="priceFloat--observed">.90</div>
  <span class="realSales--observed">20人付款</span>
</a>
<a id="item_id_123" data-spm="3" href="https://detail.tmall.com/item.htm?id=123">
  <div class="title--observed" title="重复商品"></div>
</a>
<a id="item_id_456" data-spm="4" href="https://item.taobao.com/item.htm?id=456">
  <div class="title--observed" title="酸枣仁茶"></div>
</a>
"""


class PhaseFourSnapshotTest(unittest.TestCase):
    def test_parses_observed_card_fields(self):
        cards, selectors = parse_snapshot(CARD_HTML)
        self.assertEqual(len(cards), 3)
        self.assertEqual(cards[0]["product_id"], "123")
        self.assertEqual(cards[0]["product_name"], "酸枣仁膏")
        self.assertEqual(cards[0]["shop_name"], "真实店铺")
        self.assertEqual(cards[0]["region"], "山西 太原")
        self.assertEqual(cards[0]["price_text"], "19.90")
        self.assertEqual(cards[0]["sales_text"], "20人付款")
        self.assertIn("title--observed", selectors["title"])

    def test_deduplicates_by_product_id_in_dom_order(self):
        cards, _ = parse_snapshot(CARD_HTML)
        selected = deduplicate_cards(cards)
        self.assertEqual([item["product_id"] for item in selected], ["123", "456"])
        self.assertEqual(selected[0]["product_name"], "酸枣仁膏")

    def test_canonical_urls_and_saved_source(self):
        self.assertEqual(
            canonical_product_url("https://detail.tmall.com/item.htm?id=123&x=1", "123"),
            "https://detail.tmall.com/item.htm?id=123",
        )
        self.assertIn("s.taobao.com/search", source_page_url(CARD_HTML))
        redirect = "https://click.simba.taobao.com/cc_im?id=123"
        self.assertEqual(canonical_product_url(redirect, "123"), redirect)
        self.assertEqual(product_platform(redirect), "ad_redirect")

    def test_run_writes_real_snapshot_outputs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            snapshot = root / "search.html"
            snapshot.write_text(CARD_HTML, encoding="utf-8")
            outputs = run_snapshot_search(snapshot, root / "output", limit=20)
            self.assertTrue(all(path.exists() for path in outputs.values()))
            csv_text = outputs["csv"].read_text(encoding="utf-8-sig")
            self.assertIn("酸枣仁膏", csv_text)
            self.assertEqual(csv_text.count("https://detail.tmall.com/item.htm?id=123"), 1)


if __name__ == "__main__":
    unittest.main()
