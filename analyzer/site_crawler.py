import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urldefrag
import xml.etree.ElementTree as ET
from collections import defaultdict
import re


def crawl_site(base_url: str, max_pages: int = 20) -> dict:
    """サイト全体をクロールしてページ一覧とSEOデータを収集"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    parsed = urlparse(base_url)
    base_domain = parsed.netloc
    base_origin = f"{parsed.scheme}://{parsed.netloc}"

    pages_to_visit = []
    visited = set()

    # まずsitemap.xmlを試みる
    sitemap_urls = _fetch_sitemap(base_url, headers)
    if sitemap_urls:
        pages_to_visit = sitemap_urls[:max_pages]
    else:
        pages_to_visit = [base_url]

    results = []
    errors = []

    # クロール実行
    queue = list(pages_to_visit)
    internal_found = set(queue)

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        url, _ = urldefrag(url)
        if url in visited:
            continue
        if not url.startswith('http'):
            continue

        try:
            res = requests.get(url, headers=headers, timeout=10)
            if 'text/html' not in res.headers.get('Content-Type', ''):
                continue
            res.raise_for_status()
        except Exception as e:
            errors.append({'url': url, 'error': str(e)})
            visited.add(url)
            continue

        visited.add(url)
        soup = BeautifulSoup(res.text, 'lxml')

        # ページデータ収集
        page = _analyze_page(url, soup, base_domain)
        results.append(page)

        # 内部リンクを追加（sitemapがない場合のみ）
        if not sitemap_urls and len(internal_found) < max_pages * 2:
            for a in soup.find_all('a', href=True):
                href = a['href'].strip()
                if href.startswith('/'):
                    full = urljoin(base_origin, href)
                elif href.startswith(base_origin):
                    full = href
                else:
                    continue
                full, _ = urldefrag(full)
                if full not in internal_found and _is_crawlable(full):
                    internal_found.add(full)
                    queue.append(full)

    return {
        'base_url': base_url,
        'total_pages': len(results),
        'pages': results,
        'errors': errors,
        'from_sitemap': bool(sitemap_urls),
    }


def _is_crawlable(url: str) -> bool:
    skip_ext = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.svg', '.zip',
                '.css', '.js', '.ico', '.mp4', '.mp3', '.woff', '.woff2')
    return not any(url.lower().endswith(e) for e in skip_ext)


def _fetch_sitemap(base_url: str, headers: dict) -> list:
    """sitemap.xmlからURL一覧を取得"""
    parsed = urlparse(base_url)
    sitemap_url = f"{parsed.scheme}://{parsed.netloc}/sitemap.xml"
    urls = []
    try:
        res = requests.get(sitemap_url, headers=headers, timeout=8)
        if res.status_code != 200:
            return []
        root = ET.fromstring(res.content)
        ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        # sitemapindex対応
        for sitemap in root.findall('sm:sitemap/sm:loc', ns):
            try:
                sub = requests.get(sitemap.text, headers=headers, timeout=8)
                sub_root = ET.fromstring(sub.content)
                for loc in sub_root.findall('sm:url/sm:loc', ns):
                    urls.append(loc.text)
            except Exception:
                pass
        # 通常のsitemap
        for loc in root.findall('sm:url/sm:loc', ns):
            urls.append(loc.text)
    except Exception:
        pass
    return list(dict.fromkeys(urls))  # 重複除去


def _analyze_page(url: str, soup: BeautifulSoup, base_domain: str) -> dict:
    """1ページのSEOデータを収集"""
    title_tag = soup.find('title')
    title = title_tag.get_text().strip() if title_tag else ''

    meta_desc = soup.find('meta', attrs={'name': 'description'})
    meta_description = meta_desc.get('content', '').strip() if meta_desc else ''

    h1s = [h.get_text().strip() for h in soup.find_all('h1')]
    h2s = [h.get_text().strip() for h in soup.find_all('h2')]

    images = soup.find_all('img')
    images_without_alt = sum(1 for img in images if not img.get('alt', '').strip())

    # テキスト抽出（スクリプト・スタイルのみ除去）
    for tag in soup(['script', 'style']):
        tag.decompose()
    text = soup.get_text(separator=' ', strip=True)
    word_count = len(text.split())

    canonical = soup.find('link', attrs={'rel': 'canonical'})
    has_canonical = canonical is not None
    canonical_url = canonical.get('href', '') if canonical else ''

    # 内部リンク数
    base_origin = f"{urlparse(url).scheme}://{base_domain}"
    internal_links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        if href.startswith('/') or base_domain in href:
            internal_links.add(href)

    # SEO問題を自動判定
    issues = []
    if not title:
        issues.append('タイトルなし')
    elif len(title) < 20:
        issues.append(f'タイトル短すぎ({len(title)}文字)')
    elif len(title) > 70:
        issues.append(f'タイトル長すぎ({len(title)}文字)')

    if not meta_description:
        issues.append('メタディスクリプションなし')
    elif len(meta_description) > 160:
        issues.append(f'メタディスクリプション長すぎ({len(meta_description)}文字)')

    if len(h1s) == 0:
        issues.append('H1なし')
    elif len(h1s) > 1:
        issues.append(f'H1が複数({len(h1s)}個)')

    if word_count < 300:
        issues.append(f'テキスト不足({word_count}語)')

    if images_without_alt > 0:
        issues.append(f'altなし画像{images_without_alt}枚')

    # スコア算出（簡易）
    score = 100
    score_deductions = {
        'タイトルなし': 25, 'メタディスクリプションなし': 15,
        'H1なし': 20, 'H1が複数': 10,
    }
    for issue in issues:
        for key, deduct in score_deductions.items():
            if key in issue:
                score -= deduct
    if word_count < 300:
        score -= 15
    if images_without_alt > 3:
        score -= 10
    score = max(0, score)

    return {
        'url': url,
        'title': title,
        'title_length': len(title),
        'meta_description': meta_description,
        'meta_description_length': len(meta_description),
        'h1_count': len(h1s),
        'h1_texts': h1s,
        'h2_texts': h2s[:5],
        'word_count': word_count,
        'images_total': len(images),
        'images_without_alt': images_without_alt,
        'has_canonical': has_canonical,
        'canonical_url': canonical_url,
        'internal_links': len(internal_links),
        'issues': issues,
        'score': score,
    }


def aggregate_site_data(crawl_result: dict) -> dict:
    """クロール結果を集計してAI判定用データを作成"""
    pages = crawl_result.get('pages', [])
    if not pages:
        return {}

    all_issues = defaultdict(int)
    total_score = 0
    low_score_pages = []
    no_title_pages = []
    no_meta_pages = []
    low_word_pages = []

    for p in pages:
        total_score += p.get('score', 0)
        for issue in p.get('issues', []):
            for key in ['タイトルなし', 'タイトル短すぎ', 'タイトル長すぎ',
                        'メタディスクリプションなし', 'H1なし', 'H1が複数',
                        'テキスト不足', 'altなし画像']:
                if key in issue:
                    all_issues[key] += 1

        if p.get('score', 100) < 60:
            low_score_pages.append({'url': p['url'], 'score': p['score'],
                                    'issues': p['issues']})

    avg_score = total_score / len(pages) if pages else 0

    return {
        'base_url': crawl_result['base_url'],
        'total_pages': len(pages),
        'avg_score': round(avg_score),
        'issue_summary': dict(all_issues),
        'low_score_pages': sorted(low_score_pages, key=lambda x: x['score'])[:5],
        'sample_pages': [
            {k: v for k, v in p.items() if k in
             ['url', 'title', 'title_length', 'meta_description_length',
              'h1_count', 'word_count', 'score', 'issues']}
            for p in pages[:10]
        ],
    }
