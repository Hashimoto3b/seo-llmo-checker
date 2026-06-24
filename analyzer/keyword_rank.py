import requests
from urllib.parse import urlparse


def search_keyword(keyword: str, api_key: str, cx: str, num: int = 20) -> dict:
    """Google Custom Search APIでキーワード検索して順位を返す"""
    endpoint = 'https://www.googleapis.com/customsearch/v1'
    results = []

    # 10件ずつ2回取得（最大20件）
    for start in [1, 11]:
        if start == 11 and num <= 10:
            break
        params = {
            'key': api_key,
            'cx': cx,
            'q': keyword,
            'num': min(10, num - start + 1),
            'start': start,
            'lr': 'lang_ja',
            'gl': 'jp',
        }
        try:
            res = requests.get(endpoint, params=params, timeout=15)
            data = res.json()

            if 'error' in data:
                return {'error': data['error'].get('message', 'APIエラー')}

            items = data.get('items', [])
            for i, item in enumerate(items):
                rank = start + i
                url = item.get('link', '')
                domain = urlparse(url).netloc
                results.append({
                    'rank': rank,
                    'title': item.get('title', ''),
                    'url': url,
                    'domain': domain,
                    'snippet': item.get('snippet', '').replace('\n', ' '),
                })

            if len(items) < 10:
                break

        except Exception as e:
            return {'error': str(e)}

    return {'results': results, 'keyword': keyword}


def highlight_urls(results: list, target_urls: list) -> list:
    """指定URLが含まれる結果にフラグを立てる"""
    target_domains = []
    for u in target_urls:
        if u:
            u = u.strip()
            if not u.startswith('http'):
                u = 'https://' + u
            target_domains.append(urlparse(u).netloc.replace('www.', ''))

    for r in results:
        domain = r['domain'].replace('www.', '')
        r['is_target'] = any(t in domain or domain in t for t in target_domains if t)

    return results
