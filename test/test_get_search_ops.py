import unittest
from scraper import Scraper

class TestScraper(unittest.IsolatedAsyncioTestCase):
    async def test_get_search_ops(self):
        scraper = Scraper(cache_timeout_min=30)
        manufacturers: str = "41,27,37,48"
        models: str = "2333,2842,1315,3866,2829,3484"
        submodels: str = ""
        manufs, models, submodels = await scraper.get_meta(manufacturers, models, submodels)
        print(f"manufacturers: {manufs}, models: {models}, submodels: {submodels}")

if __name__ == '__main__':
    unittest.main()
