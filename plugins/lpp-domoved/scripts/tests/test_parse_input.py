import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import parse_input as pi  # noqa: E402


def one(text):
    items = pi.parse([text])["items"]
    assert len(items) == 1, items
    return items[0]


class TestListings(unittest.TestCase):
    def test_cian_flat(self):
        it = one("https://www.cian.ru/sale/flat/312345678/")
        self.assertEqual(it["source"], "cian")
        self.assertEqual(it["listing_id"], "312345678")
        self.assertEqual(it["object_type_hint"], "secondary")
        self.assertTrue(it["needs_fetch"])

    def test_cian_suburban(self):
        it = one("https://spb.cian.ru/sale/suburban/298765432/")
        self.assertEqual(it["source"], "cian")
        self.assertEqual(it["listing_id"], "298765432")
        self.assertEqual(it["object_type_hint"], "private_house")

    def test_cian_zhk(self):
        it = one("https://zhk-level-michurinskiy-i.cian.ru/")
        self.assertEqual(it["source"], "cian")
        self.assertEqual(it["object_type_hint"], "new_build")

    def test_domclick_flat(self):
        it = one("https://domclick.ru/card/sale__flat__1987654321")
        self.assertEqual(it["source"], "domclick")
        self.assertEqual(it["listing_id"], "1987654321")
        self.assertEqual(it["object_type_hint"], "secondary")

    def test_domclick_new(self):
        it = one("https://domclick.ru/card/sale__new_flat__2001112223")
        self.assertEqual(it["object_type_hint"], "new_build")

    def test_domclick_house(self):
        it = one("https://domclick.ru/card/sale__house__1555444333")
        self.assertEqual(it["object_type_hint"], "private_house")

    def test_avito_flat(self):
        it = one("https://www.avito.ru/moskva/kvartiry/2-k._kvartira_54m_512et._3456789012")
        self.assertEqual(it["source"], "avito")
        self.assertEqual(it["listing_id"], "3456789012")
        self.assertEqual(it["object_type_hint"], "secondary")

    def test_avito_house(self):
        it = one("https://www.avito.ru/moskovskaya_oblast/doma_dachi_kottedzhi/dom_120m_na_uchastke_8sot._4123456789?context=abc")
        self.assertEqual(it["listing_id"], "4123456789")
        self.assertEqual(it["object_type_hint"], "private_house")

    def test_yandex_realty(self):
        it = one("https://realty.yandex.ru/offer/7712345678901234567/")
        self.assertEqual(it["source"], "yandex_realty")
        self.assertEqual(it["listing_id"], "7712345678901234567")


class TestMaps(unittest.TestCase):
    def test_yandex_ll_is_lon_first(self):
        it = one("https://yandex.ru/maps/213/moscow/?ll=37.617635%2C55.755814&z=17")
        self.assertEqual(it["source"], "yandex_maps")
        self.assertAlmostEqual(it["lat"], 55.755814, places=5)
        self.assertAlmostEqual(it["lon"], 37.617635, places=5)
        self.assertFalse(it["needs_fetch"])

    def test_yandex_pt_preferred_over_ll(self):
        it = one("https://yandex.ru/maps/?ll=37.60,55.70&pt=37.5064,55.6215&z=16")
        self.assertAlmostEqual(it["lat"], 55.6215, places=4)
        self.assertAlmostEqual(it["lon"], 37.5064, places=4)

    def test_yandex_whatshere(self):
        it = one("https://yandex.ru/maps/?whatshere%5Bpoint%5D=30.315868%2C59.939095&whatshere%5Bzoom%5D=17")
        self.assertAlmostEqual(it["lat"], 59.939095, places=5)
        self.assertAlmostEqual(it["lon"], 30.315868, places=5)

    def test_yandex_short(self):
        it = one("https://yandex.ru/maps/-/CDqZ5L~x")
        self.assertTrue(it["short_link"])
        self.assertTrue(it["needs_fetch"])
        self.assertIsNone(it["lat"])

    def test_yandex_org(self):
        it = one("https://yandex.ru/maps/org/zhiloy_kompleks/1234567890/")
        self.assertEqual(it["listing_id"], "1234567890")
        self.assertTrue(it["needs_fetch"])

    def test_2gis_geo(self):
        it = one("https://2gis.ru/moscow/geo/4504235282717466/37.617635,55.755814")
        self.assertEqual(it["source"], "2gis")
        self.assertAlmostEqual(it["lat"], 55.755814, places=5)
        self.assertAlmostEqual(it["lon"], 37.617635, places=5)

    def test_2gis_m(self):
        it = one("https://2gis.ru/spb?m=30.3158%2C59.9391%2F16")
        self.assertAlmostEqual(it["lat"], 59.9391, places=4)
        self.assertAlmostEqual(it["lon"], 30.3158, places=4)

    def test_google_at_is_lat_first(self):
        it = one("https://www.google.com/maps/place/Red+Square/@55.7539303,37.6185235,17z/data=!3m1")
        self.assertEqual(it["source"], "google_maps")
        self.assertAlmostEqual(it["lat"], 55.7539303, places=5)
        self.assertAlmostEqual(it["lon"], 37.6185235, places=5)

    def test_google_pin_3d4d(self):
        it = one("https://www.google.com/maps/place/X/@55.70,37.50,15z/data=!4m6!3m5!1s0x0:0x0!8m2!3d55.7539!4d37.6208")
        self.assertAlmostEqual(it["lat"], 55.7539, places=4)
        self.assertAlmostEqual(it["lon"], 37.6208, places=4)

    def test_google_q(self):
        it = one("https://maps.google.com/?q=56.8389,60.6057")
        self.assertAlmostEqual(it["lat"], 56.8389, places=4)
        self.assertAlmostEqual(it["lon"], 60.6057, places=4)

    def test_google_short(self):
        it = one("https://maps.app.goo.gl/AbCdEf123")
        self.assertEqual(it["source"], "google_maps")
        self.assertTrue(it["short_link"])

    def test_osm(self):
        it = one("https://www.openstreetmap.org/#map=17/55.75582/37.61763")
        self.assertEqual(it["source"], "osm")
        self.assertAlmostEqual(it["lat"], 55.75582, places=4)

    def test_osm_marker(self):
        it = one("https://www.openstreetmap.org/?mlat=55.6215&mlon=37.5064#map=17/55.6/37.5")
        self.assertAlmostEqual(it["lat"], 55.6215, places=4)

    def test_out_of_range_rejected(self):
        # Swapped order in Google format gives lat=37 (outside Russia): coordinates are rejected.
        it = one("https://www.google.com/maps/@37.6176,55.7558,15z")
        self.assertIsNone(it["lat"])
        self.assertTrue(it["needs_fetch"])


class TestTextInput(unittest.TestCase):
    def test_address(self):
        it = one("Москва, Профсоюзная улица, 140к2")
        self.assertEqual(it["source"], "address")
        self.assertTrue(it["needs_geocode"])

    def test_coordinates(self):
        it = one("55.6215, 37.5064")
        self.assertEqual(it["source"], "coordinates")
        self.assertAlmostEqual(it["lon"], 37.5064, places=4)

    def test_several_and_flags(self):
        items = pi.parse(["https://www.cian.ru/sale/flat/1234567/ https://domclick.ru/card/sale__flat__7654321 --profile family --quick"])["items"]
        self.assertEqual([i["source"] for i in items], ["cian", "domclick"])

    def test_url_without_scheme(self):
        it = one("cian.ru/sale/flat/312345678/")
        self.assertEqual(it["source"], "cian")
        self.assertEqual(it["listing_id"], "312345678")

    def test_other_url(self):
        it = one("https://example.com/flat/1")
        self.assertEqual(it["source"], "other_url")
        self.assertTrue(it["needs_fetch"])

    def test_cli_empty(self):
        self.assertEqual(pi.main(["--profile", "x"]) if False else pi.main(["   "]), 2)


if __name__ == "__main__":
    unittest.main()
