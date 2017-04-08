# -*- coding: utf-8 -*-
import logging
import json
from urlparse import urljoin

import scrapy
import scrapy_splash
from django.utils.datetime_safe import date

from common.models import SKU, ImageStore
from img_acquist_sys.items import ImgAcquistSysItem
from img_acquist_sys.settings import CATEGORIES
from img_acquist_sys.spiders.base_spider import BaseSpider


class SaksfifthavenueSpider(BaseSpider):
    name = "saksfifthavenue"
    allowed_domains = ["saksfifthavenue.com"]
    site_url = "http://www.saksfifthavenue.com"
    start_urls = [
        "http://www.saksfifthavenue.com/Shoes/shop/_/N-52k0s7/Ne-6lvnb5?FOLDER%3C%3Efolder_id=2534374306624247&Ns=P_arrivaldate%7C1%7C%7CP_306624247_sort%7C%7CP_brandname%7C%7CP_product_code",
    ]
    category_name = CATEGORIES[0].decode('UTF-8')

    def parse(self, response):
        BaseSpider.parse(self, response)

        sites = response.xpath('//div[contains(@class, "pa-product-large")]')
        # logging.info('response : %s' % response.body_as_unicode())
        for site in sites:
            source_url = site.xpath('.//div[@class="image-container-large"]//a[contains(@id, "image-url")]')
            # logging.info('source_url : %s' % source_url)
            if source_url:
                url = source_url.xpath('./@href').extract()[0]
                # logging.info('url : %s' % url)
                sku_thumb_url = source_url.xpath('.//img[contains(@class, "pa-product-large")]/@src').extract().pop()
                sku_name = site.xpath(
                    './/div[@class="product-text"]//a//p[@class="product-description"]/text()').extract()
                if sku_name:
                    sku_name = sku_name.pop().lstrip().rstrip()
                else:
                    sku_name = response.xpath(
                        '//span[@class="product-designer-name"]/text()').extract()
                # logging.info('sku_thumb_url %s : sku_name %s' % (sku_thumb_url, sku_name))
                sku = SKU(name=sku_name, rel=self.websiteCategoryRel, source_url=url, created=date.today())
                try:
                    sku = SKU.objects.get(source_url=url)
                    if sku.thumb_image:
                        sku_thumb_url = None
                except:
                    sku.save()
                yield scrapy.Request(url, self.parse_content, meta={'sku_thumb_url': sku_thumb_url,'sku_name': sku_name})
                # yield scrapy_splash.SplashRequest(url, self.parse_content, args={'wait': 10},
                #                                       meta={'sku_thumb_url': sku_thumb_url,'sku_name': sku_name})

        next_pages = response.xpath('//li[@class="pa-enh-pagination-right-arrow"]//a/@href')
        if next_pages:
            next_page = urljoin(self.site_url, next_pages[0].extract())
            msg = "下一页 Url".decode('UTF-8')
            logging.info('%s : %s' % (msg, next_page))
            yield scrapy.Request(next_page, callback=self.parse)

    def parse_content(self, response):
        BaseSpider.parse_content(self, response)

        json_object = json.loads(response.xpath('//script[@type="application/json"]/text()').extract().pop())

        image_urls = []
        thumb_urls = []
        asset_prefix = json_object['ProductDetails']['main_products'][0]['media']['asset_prefix']
        server_url = json_object['ProductDetails']['main_products'][0]['media']['zoom_player']['html_links']['server_url']
        for image_data in json_object['ProductDetails']['main_products'][0]['media']['images']:
            if image_data:
                image_url = 'http:' + server_url + asset_prefix + '/' + image_data
                try:
                    imageStore = ImageStore.objects.get(orig_image_url=image_url)
                    msg = "该图片已经存在".decode('UTF-8')
                    logging.info("%s : %s " % (msg, image_url))
                    continue
                except:
                    # thumb_urls.append(thumb_url)
                    image_urls.append(image_url)

        # for image_data in response.xpath('//div[@class="s7thumb"]/@style').extract():
        #     index1 = image_data.find('http://')
        #     index2 = image_data.find('?fit=')
        #     # logging.info('image_data : %s index1:%d index2:%d' % (image_data, index1, index2))
        #     thumb_url = image_data[index1:index2]
        #     image_url = thumb_url + '?wid=615&hei=820'
        #     try:
        #         imageStore = ImageStore.objects.get(orig_image_url=image_url)
        #         msg = "该图片已经存在".decode('UTF-8')
        #         logging.info("%s : %s " % (msg, image_url))
        #         continue
        #     except:
        #         thumb_urls.append(thumb_url)
        #         image_urls.append(image_url)

        if len(image_urls) == 0:
            logging.info("%s" % "没有需要采集的图片,跳过".decode('UTF-8'))
            return

        item = ImgAcquistSysItem()
        item['domain'] = self.allowed_domains[0]
        item['website_name'] = self.name
        item['category_name'] = CATEGORIES[0].decode('UTF-8')
        item['sku_thumb_url'] = response.meta['sku_thumb_url']
        item['sku_name'] = response.meta['sku_name']
        sku_brand_name = response.xpath('//a[@class="product-overview__brand-link"]/text()').extract()
        if sku_brand_name:
            item['sku_brand_name'] = sku_brand_name.pop().lstrip().rstrip()
        else:
            item['sku_brand_name'] = None
        item['source_url'] = response.url
        item['image_urls'] = image_urls
        item['thumb_urls'] = thumb_urls
        # logging.info('item : %s' % item)
        return item
