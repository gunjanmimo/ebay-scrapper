# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import os
from itemadapter import ItemAdapter
from scrapy.pipelines.images import ImagesPipeline
from scrapy.http.request import Request
import uuid


class WebscrapperPipeline:
    def process_item(self, item, spider):
        return item


class customImagePipeline(ImagesPipeline):
    def get_media_requests(self, item, info):
        product_id = item["product_id"]
        image_urls = item["image_urls"]

        for idx, url in enumerate(image_urls):
            yield Request(
                url=url, meta={"path": os.path.join(product_id, f"{idx}.jpg")}
            )

    def file_path(self, request, response=None, info=None):
        path = request.meta.get("path")
        return path
