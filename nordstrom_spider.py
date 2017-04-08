# -*- coding: utf-8 -*-
import logging
import json
import urllib
from math import ceil
from urlparse import urljoin

import scrapy
from django.utils.datetime_safe import date

from common.models import SKU, ImageStore
from img_acquist_sys.items import ImgAcquistSysItem
from img_acquist_sys.settings import CATEGORIES
from img_acquist_sys.spiders.base_spider import BaseSpider


class NordstromSpider(BaseSpider):
    name = "nordstrom"
    allowed_domains = ["nordstrom.com"]
    site_url = "http://shop.nordstrom.com/c/womens-shoes"
    start_urls = [
        "http://shop.nordstrom.com/c/womens-shoes?origin=leftnav",
    ]
    category_name = CATEGORIES[0].decode('UTF-8')

    def parse(self, response):
        BaseSpider.parse(self, response)

        json_content = response.xpath('//script[contains(., "React.render(React.createElement")]')[0].extract()
        json_content = json_content[json_content.find('{"data":'):json_content.find('), document')]
        json_object = json.loads(json_content)

        for item in json_object['data']['ProductResult']['Products']:
            ProductPageUrl = 'http://shop.nordstrom.com' + item['ProductPageUrl'] + '?origin=category-personalizedsort&fashioncolor='
            if item['Colors']:
                for color in item['Colors']:
                    sku_name = item['Title'] + '(' + color['Name'] + ')'
                    url = ProductPageUrl + urllib.quote(color['Name'])
                    for media in color['Media']:
                        if media['Type'] == 'MainImage':
                            sku_thumb_url = media['Url']
                            # logging.info('url : %s' % url)
                            # logging.info('sku_thumb_url %s : sku_name %s' % (sku_thumb_url, sku_name))
                            sku = SKU(name=sku_name, rel=self.websiteCategoryRel, source_url=url, created=date.today())
                            try:
                                sku = SKU.objects.get(source_url=url)
                                if sku.thumb_image:
                                    sku_thumb_url = None
                            except:
                                sku.save()
                            yield scrapy.Request(url, callback=self.parse_content,
                                                 meta={'sku_thumb_url': sku_thumb_url, 'sku_name': sku_name})
            else:
                sku_name = item['Title']
                for media in item['Media']:
                    if media['Type'] == 'MainImage':
                        sku_thumb_url = media['Url']
                        # logging.info('url : %s' % url)
                        # logging.info('sku_thumb_url %s : sku_name %s' % (sku_thumb_url, sku_name))
                        sku = SKU(name=sku_name, rel=self.websiteCategoryRel, source_url=ProductPageUrl, created=date.today())
                        try:
                            sku = SKU.objects.get(source_url=ProductPageUrl)
                            if sku.thumb_image:
                                sku_thumb_url = None
                        except:
                            sku.save()
                        yield scrapy.Request(ProductPageUrl, callback=self.parse_content,
                                             meta={'sku_thumb_url': sku_thumb_url, 'sku_name': sku_name})

        pagination = json_object['data']['ProductResult']['Pagination']
        current_page = pagination['Page']
        total_pages = ceil(pagination['TotalHits'] / pagination['Top'])
        if current_page < total_pages:
            next_page = 'http://shop.nordstrom.com/c/womens-shoes?page=' + str(current_page + 1)
            msg = "下一页 Url".decode('UTF-8')
            logging.info('%s : %s' % (msg, next_page))
            yield scrapy.Request(next_page, callback=self.parse)

    def parse_content(self, response):
        BaseSpider.parse_content(self, response)

        image_urls = []
        thumb_urls = []
        for thumb_url in response.xpath('//li[contains(@class, "image-thumbnail")]//a//img/@src').extract():
            if thumb_url:
                image_url = thumb_url.replace('w=60&h=90', 'w=860&h=1318')
                try:
                    imageStore = ImageStore.objects.get(orig_image_url=image_url)
                    msg = "该图片已经存在".decode('UTF-8')
                    logging.info("%s : %s " % (msg, image_url))
                    continue
                except:
                    thumb_urls.append(thumb_url)
                    image_urls.append(image_url)

        if len(image_urls) == 0 and len(thumb_urls) == 0:
            return

        item = ImgAcquistSysItem()
        item['domain'] = self.allowed_domains[0]
        item['website_name'] = self.name
        item['category_name'] = CATEGORIES[0].decode('UTF-8')
        item['sku_thumb_url'] = response.meta['sku_thumb_url']
        item['sku_name'] = response.meta['sku_name']
        item['sku_brand_name'] = response.xpath('//section[@class="brand-title"]//h2//a//span/text()').extract().pop().lstrip().rstrip()
        item['source_url'] = response.url
        item['image_urls'] = image_urls
        item['thumb_urls'] = thumb_urls
        # logging.info('item : %s' % item)
        return item
