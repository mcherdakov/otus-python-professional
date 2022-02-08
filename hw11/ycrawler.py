import argparse
import asyncio
import logging
from dataclasses import dataclass, field
import os
from random import random
from typing import Awaitable

import aiofiles
import aiofiles.os as ios
import aiohttp
import bs4 as bs

URL = 'https://news.ycombinator.com'
MAIN_PAGE_URL = f'{URL}/best'

TIMEOUT_SECONDS = 10.
POLL_TIME_SECONDS = 60
RETRIES_COUNT = 3
RETRY_INITIAL_INTERVAL_SECONDS = 2
RETRY_BACKOFF = 2
JITTER_MAX = 5

logging.basicConfig()
logger = logging.getLogger("ycrawler")
logger.setLevel(logging.INFO)


@dataclass
class CommentLink:
    link: str
    content: str


@dataclass
class ArticleComments:
    link: str
    comment_links: list[CommentLink] = field(default_factory=lambda: [])


@dataclass
class Article:
    id: int
    title: str
    link: str
    comments: ArticleComments
    content: str = ''


async def get_page(url: str, session: aiohttp.ClientSession) -> str:
    retries = 0
    while True:

        try:
            async with session.get(url) as resp:
                resp.raise_for_status()
                try:
                    return await resp.text()
                except Exception as e:
                    logger.error("Exception occured during url %s content decoding: %s", url, e)
        except asyncio.TimeoutError:
            logger.error("Timeout error for url %s", url)
        except Exception as e:
            logger.error("Cannot fetch %s: %s", url, e)

        retries += 1
        if retries >= RETRIES_COUNT:
            logger.error("Too many retries for %s, skipping", url)
            return ""

        await asyncio.sleep(RETRY_INITIAL_INTERVAL_SECONDS * RETRY_BACKOFF ** (retries - 1) + random() * JITTER_MAX)


async def crawl_comment_link(url: str, session: aiohttp.ClientSession) -> CommentLink:
    return CommentLink(
        link=url,
        content=await get_page(url, session),
    )


async def crawl_comments(
    url: str,
    session: aiohttp.ClientSession,
    path: str,
    save_queue: asyncio.Queue
) -> list[CommentLink]:
    comments_page = await get_page(url, session)

    soup = bs.BeautifulSoup(comments_page, features='html.parser')
    comments = soup.find_all(attrs={'class': 'commtext'})
    links = []
    for comment in comments:
        linktags = comment.find_all('a')
        for linktag in linktags:
            links.append(linktag.attrs.get('href'))

    comment_links = []
    link_tasks = [crawl_comment_link(link, session) for link in links]
    for i, task in enumerate(asyncio.as_completed(link_tasks)):
        comment_link = await task
        comment_links.append(comment_link)

        save_queue.put_nowait(
            (
                os.path.join(path, 'comments', f'{i}.html'),
                '\n'.join([comment_link.link, comment_link.content]),
            ),
        )

    return comment_links


async def crawl_article(article: Article, session: aiohttp.ClientSession, save_queue: asyncio.Queue):
    article_folder_name = ''.join(s for s in article.title if s.isalnum() or s == ' ')
    article_folder_name = article_folder_name.replace(' ', '_')

    content_task = asyncio.create_task(
        get_page(article.link, session),
    )
    comments_task = asyncio.create_task(
        crawl_comments(article.comments.link, session, article_folder_name, save_queue),
    )

    article.content = await content_task
    save_queue.put_nowait(
        (
            os.path.join(article_folder_name, 'content.html'),
            article.content,
        ),
    )
    article.comments.comment_links = await comments_task


def parse_rows(rows: list[bs.element.Tag]) -> list[Article]:
    articles = []
    for i in range(0, len(rows), 3):
        tds = rows[i].find_all('td')
        if len(tds) < 2:
            # news table finished
            break
        title_link = tds[2].a
        title = title_link.string
        article_link = title_link.attrs.get('href')
        if article_link.startswith('item'):
            # must be internal page
            article_link = f'{URL}/{article_link}'

        comments_link = rows[i + 1].find_all('td')[1].find_all('a')[-1]
        href = comments_link.attrs.get('href')
        articles.append(
            Article(
                id=int(href.split('=')[-1]),
                title=title,
                link=article_link,
                comments=ArticleComments(link=f'{URL}/{href}')
            ),
        )

    return articles


async def crawl_main_page(
    session: aiohttp.ClientSession,
    crawled_articles: set[int],
    save_queue: asyncio.Queue
) -> set[int]:
    main_page = await get_page(MAIN_PAGE_URL, session)
    soup = bs.BeautifulSoup(main_page, features="html.parser")
    rows = (
        soup.html.body.center
        .table.find_all('tr')[3]
        .td.table.find_all('tr')
    )

    articles = parse_rows(rows)

    ids = set(article.id for article in articles)
    new_ids = ids - crawled_articles

    logger.info('Got %d new articles, crawling...', len(new_ids))
    new_articles = [article for article in articles if article.id in new_ids]

    await asyncio.gather(*[
        crawl_article(article, session, save_queue)
        for article in new_articles
    ])

    return crawled_articles | new_ids


async def file_save_processor(path: str, q: asyncio.Queue) -> None:
    while True:
        file_path, content = await q.get()
        full_path = os.path.join(path, file_path)

        dirname = os.path.dirname(full_path)
        exists = await ios.path.exists(dirname)
        if not exists:
            await ios.makedirs(dirname)

        async with aiofiles.open(full_path, 'w') as w:
            await w.write(content)


async def crawl(path: str) -> None:
    crawled_articles: set[int] = set()
    save_queue: asyncio.Queue = asyncio.Queue()

    asyncio.create_task(file_save_processor(path, save_queue))
    while True:
        logger.info('Starting new iteration')
        timer: Awaitable = asyncio.create_task(asyncio.sleep(POLL_TIME_SECONDS))

        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(TIMEOUT_SECONDS)) as session:
            crawled_articles = await crawl_main_page(session, crawled_articles, save_queue)

        logger.info('Parsing finished, waiting next iteration')
        await timer


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', dest='d', help="directory to store files", required=True)
    args = parser.parse_args()

    asyncio.run(crawl(args.d))


if __name__ == '__main__':
    main()
