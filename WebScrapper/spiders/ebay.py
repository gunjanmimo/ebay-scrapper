import scrapy
import pandas as pd
import json
from tqdm import tqdm
import os

# from urllib import urlopen


class EbaySpider(scrapy.Spider):
    name = "ebay"
    allowed_domains = [
        "ebay.com",
        "vi.vipr.ebaydesc.com",
    ]
    start_urls = ["https://www.ebay.com"]

    def __init__(self):

        SUFFIX_KEYWORDS = [
            "t-shirt",
            "shirt",
            "jacket",
            "jeans",
            "sweatshirt",
            "hat",
            "shorts",
            "coat",
            "sweater",
            "tank",
            "top",
            "activewear",
            "blazer",
        ]
        PREFIX_KEYWORDS = ["men", "women", "kid", "boy", "girl"]
        self.keywords = [
            prefix + " " + suffix
            for prefix in PREFIX_KEYWORDS
            for suffix in SUFFIX_KEYWORDS
        ]
        # ITEM ID POOL
        self.item_id_pool = []

    def parse(self, response):
        # EBAY _trksid IS A PART OF SEARCH URL
        _trksid = (
            response.css("input[type='hidden'][name='_trksid']")
            .xpath("@value")
            .extract()[0]
        )

        # STOP SPIDER
        if len(self.item_id_pool) > 15000:
            raise scrapy.exceptions.CloseSpider(
                "COLLECTED 15K PRODUCT DATA\nSTOPPING SPIDER..........."
            )
        for keyword in tqdm(
            self.keywords, position=0, leave=False, ascii=True, desc="SCRAPPING"
        ):
            for pageNo in tqdm(
                range(0, 150),
                position=1,
                leave=True,
                ascii=True,
                desc=f"KEYWORD > {keyword}",
            ):
                page_url = (
                    "http://www.ebay.com/sch/i.html?_from=R40&_trksid="
                    + _trksid
                    + "&_nkw="
                    + keyword.replace(" ", "+")
                    + f"&_ipg=200&_pgn={pageNo}"
                )

                yield scrapy.Request(
                    page_url, callback=self.parse_search_page, meta={"keyword": keyword}
                )

    def parse_search_page(self, response):
        keyword = response.meta.get("keyword")
        results = response.xpath('//div/div/ul/li[contains(@class, "s-item" )]')
        product_ids_page = []

        for product in tqdm(
            results,
            position=2,
            leave=True,
            ascii=True,
            desc=f"KEYWORD: {keyword} | COLLECTING PRODUCT DETAILS",
        ):

            product_url = product.xpath(
                './/a[@class="s-item__link"]/@href'
            ).extract_first()

            product_id = product_url.split("itm/")[1].lstrip().split("?")[0]

            # CHECK EXISTENCE OF PRODUCT ID IN uct_POOL
            if int(product_id) not in self.item_id_pool:
                self.item_id_pool.append(int(product_id))
                product_ids_page.append(product_id)
                yield scrapy.Request(
                    product_url,
                    callback=self.parse_product_page,
                    meta={"product_id": product_id, "keyword": keyword},
                )
            else:
                continue

    def parse_product_page(self, response):

        product_id = response.meta.get("product_id")
        keyword = response.meta.get("keyword")
        product_details = {}
        product_details["product_id"] = product_id
        product_details["keyword"] = keyword

        # CURRENT PRODUCT URL
        product_url = response.request.url
        product_details["product_url"] = product_url

        # 1. TITLE
        title = response.xpath(
            './/h1[contains(@class, "x-item-title__mainTitle" )]/span/text()'
        ).get()

        product_details["title"] = title
        # 2. CONDITION
        condition = response.xpath(
            '//*[@id="mainContent"]/form/div[1]/div[1]/div/div[2]/div[1]/div/div/span[1]/span//text()'
        ).get()
        product_details["item_condition"] = condition

        # 3. PRICE
        price = response.xpath(
            './/div[contains(@class, "x-price-primary" )]/span/span//text()'
        ).get()
        price_was = response.xpath(
            './/div[contains(@class, "x-additional-info" )]/div/span/span[2]//text()'
        ).get()

        product_details["price"] = price
        product_details["price_was"] = price_was

        # 4. SPECIFICATION TABLE

        for spec in response.xpath(
            '//*[@id="viTabs_0_is"]/div/*/div[contains(@class, "ux-layout-section" )]'
        ):

            selectors = spec.xpath("./div")
            for selector in selectors:
                key_1 = selector.xpath("./div[1]//text()").get().replace(":", "")
                val_1 = selector.xpath("./div[2]//text()").get()

                product_details[key_1] = val_1
                try:
                    key_2 = selector.xpath("./div[3]//text()").get().replace(":", "")
                    val_2 = selector.xpath("./div[4]//text()").get()
                    product_details[key_2] = val_2
                except:
                    pass

        # 4. IMAGES
        product_img_urls = []
        all_img_url = response.xpath("//img/@src")
        for url in all_img_url:
            url = url.get()
            if "s-l64" in url:
                url = url.replace("s-l64", "s-l2000")
                product_img_urls.append(url)

        product_details["product_img_urls"] = product_img_urls

        # 5. DESCRIPTION
        iframe_url = response.xpath("//iframe/@src").get()
        # print(iframe_url)
        # print("#" * 100)
        yield scrapy.Request(
            iframe_url,
            callback=self.parse_iframe,
            meta={"product_id": product_id, "product_details": product_details},
        )

    def parse_iframe(self, response):
        product_id = response.meta.get("product_id")
        product_details = response.meta.get("product_details")

        description = []
        # print(response.request.url)
        # print("#" * 200)
        for p_selector in response.xpath('//*[@id="ds_div"]//p'):
            text = p_selector.xpath(".//text()").extract()
            description.extend(text)
        for p_selector in response.xpath('//*[@id="ds_div"]//font'):
            text = p_selector.xpath(".//text()").extract()
            description.extend(text)
        for p_selector in response.xpath('//*[@id="ds_div"]//span'):
            text = p_selector.xpath(".//text()").extract()
            description.extend(text)

        text = response.xpath('//*[@id="ds_div"]//text()').extract()
        description.extend(text)
        description = " ".join(description)

        # description = " ".join(response.xpath("//body//text()").extract()).strip()
        # print(description)
        # print("~" * 100)
        # description = re.sub("<[^<]+?>", "", description)
        product_details["description"] = description

        # SAVE JSON DATA
        JSON_PATH = os.path.join(
            "/home/mimo/Desktop/InTheLoop/SCRAPED_DATA/GENERAL_PRODUCT_DATA/jsons",
            f"{product_id}.json",
        )
        with open(JSON_PATH, "w+") as file:
            json.dump(product_details, file)
        # IMAGE DOWNLOAD DATA
        yield {
            "image_urls": product_details["product_img_urls"],
            "product_id": product_id,
        }
