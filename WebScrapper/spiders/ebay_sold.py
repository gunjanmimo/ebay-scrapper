import scrapy
import pandas as pd
import os
import json
import uuid
from tqdm import tqdm
import pickle
from scrapy.http import FormRequest


class EbaySoldSpider(scrapy.Spider):
    name = "ebay_sold"
    allowed_domains = ["ebay.com", "vi.vipr.ebaydesc.com"]
    start_urls = ["https://www.ebay.com"]

    def __init__(self):
        self.json_dir = "/home/mimo/Desktop/InTheLoop/SCRAPED_DATA/BID_DATA"
        self.all_data = []
        for folder in os.listdir(self.json_dir):
            file_path = os.path.join(self.json_dir, folder, "bid_data.json")
            file = open(file_path)
            data = json.load(file)
            self.all_data.append(data)

    def parse(self, response):
        for bid_data in tqdm(self.all_data):
            product_url = bid_data["bid_url"]
            yield scrapy.Request(
                product_url,
                callback=self.parse_product_page,
                meta={"product_id": bid_data["product_id"]},
            )

    def parse_product_page(self, response):
        product_id = response.meta.get("product_id")
        product_data = {}
        # TITLE
        title = response.xpath('.//h1[contains(@class, "product-title" )]/text()').get()
        if title is None:
            title = response.xpath('//*[@id="itemTitle"]/text()').extract()
        product_data["title"] = title
        product_data["product_id"] = product_id
        product_data["product_url"] = response.request.url
        # PRODUCT SPECIFICATIONS
        for idx, spec in enumerate(
            response.xpath('//*[@id="ProductDetails"]/div[1]/div/section//div')
        ):
            for li in spec.xpath("./ul/li"):
                text = li.xpath(".//text()").extract()
                key = text[0]
                value = text[1]
                product_data[key] = value
        for spec in response.xpath(
            '//*[@id="viTabs_0_is"]/div/*/div[contains(@class, "ux-layout-section" )]'
        ):

            selectors = spec.xpath("./div")
            for selector in selectors:
                key_1 = selector.xpath("./div[1]//text()").get().replace(":", "")
                val_1 = selector.xpath("./div[2]//text()").get()

                product_data[key_1] = val_1
                try:
                    key_2 = selector.xpath("./div[3]//text()").get().replace(":", "")
                    val_2 = selector.xpath("./div[4]//text()").get()
                    product_data[key_2] = val_2
                except:
                    pass
        # 5. DESCRIPTION
        iframe_url = response.xpath("//iframe/@src").get()

        # with open(
        #     f"/home/mimo/Desktop/InTheLoop/SCRAPED_DATA/BID_DATA/{product_id}/product_data.json",
        #     "w",
        # ) as file:
        #     json.dump(product_data, file)

        yield scrapy.Request(
            iframe_url,
            callback=self.parse_iframe,
            meta={"product_id": product_id, "product_details": product_data},
        )

    def parse_iframe(self, response):
        product_id = response.meta.get("product_id")
        product_details = response.meta.get("product_details")

        description = []
        print(response.request.url)
        print("#" * 100)
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

        product_details["description"] = description

        with open(
            f"/home/mimo/Desktop/InTheLoop/SCRAPED_DATA/BID_DATA/{product_id}/product_data.json",
            "w",
        ) as file:
            json.dump(product_details, file)
