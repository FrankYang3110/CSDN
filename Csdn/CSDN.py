import re
from fake_useragent import UserAgent
import json
import asyncio
import aiohttp
from asyncio import Queue
import csv
from lxml import etree


re_url = 'https://blog.csdn.net/api/articles?type=more&category=home&shown_offset='
url_queue = Queue(maxsize=1000)
old_urls = set()

ua = UserAgent()
headers = {'User-Agent': ua.chrome,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'accept-encoding': 'gzip, deflate, br',
            'accept-language': 'zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7',
           }
file_name = 'CSDN.csv'


async def csv_writer_headers(file_name):
    with open(file_name, 'w', encoding='utf-8') as f:
        writer = csv.DictWriter(f, ['网页', '文章标题', '创建时间','作者','阅读量','点赞数','评论数','详细内容'])
        writer.writeheader()


async def save_csv(file_name, dict):
    with open(file_name, 'a', encoding='utf-8') as f:
        writer = csv.DictWriter(f, dict.keys())
        writer.writerow(dict)


async def parse_article(url,session):
    async with session.get(url, headers=headers) as resp:
        article_dict = {}
        if resp.status in [200, 201]:
            html = await resp.text()
            tree = etree.HTML(html)
            article_dict['url'] = url
            article_dict['title'] = tree.xpath('//h1[@class="title-article"]/text()')[0]
            article_dict['time'] = tree.xpath('//span[@class="time"]/text()')[0]
            article_dict['follow-nickName'] = tree.xpath('//a[@class="follow-nickName"]/text()')[0]
            article_dict['read-count'] = tree.xpath('//span[@class="read-count"]/text()')[0].replace('阅读数：', '')
            article_dict['praise'] = tree.xpath('//a[@class="btn-like-a"]/p/text()')[0]
            article_dict['comment-count'] = re.findall('\d+',tree.xpath('//p[@class="tool-comment-count"]/text()')[0])[0]
            article_dict['content'] = (''.join(tree.xpath('//div[@id="article_content"]//p//text()'))).replace('\n','').replace('\t','')

            await save_csv(file_name, article_dict)


async def get_article_url(session):
    while True:
        page_url = await url_queue.get()
        page_json_data = await get_json_data(page_url,session)
        await asyncio.ensure_future(get_next_url(page_json_data))
        for data in page_json_data.get('articles'):
            article_url = data.get('url')
            await parse_article(article_url,session)


async def get_next_url(json_data):
    next_url = re_url + str(json_data.get('shown_offset'))
    await url_queue.put(next_url)


async def get_json_data(url, session):
    async with session.get(url, headers=headers) as resp:
        if resp.status in [200, 201]:
            json_data = json.loads(await resp.text())
            return json_data


async def main():
    await csv_writer_headers(file_name)
    start_url = 'https://blog.csdn.net/api/articles?type=more&category=home&shown_offset=1555721691286504'
    async with aiohttp.ClientSession() as session:
        json_data = await get_json_data(start_url, session)
        old_urls.add(start_url)
        await get_next_url(json_data)
        await asyncio.ensure_future(get_article_url(session))


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    asyncio.ensure_future(main())
    loop.run_forever()



