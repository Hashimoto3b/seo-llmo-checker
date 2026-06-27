import requests
from urllib.parse import urlparse


def search_keyword(keyword: str, api_key: str, num: int = 20) -> dict:
    """SerpAPIでキーワード検索して順位を返す"""
    endpoint = 'https://serpapi.com/search'
    results = []

    params = {
        'q': keyword,
        'api_key': api_key,
        'engine': 'google',
        'hl': 'ja',
        'gl': 'jp',
        'num': min(num, 20),
    }

    try:
        res = requests.get(endpoint, params=params, timeout=30)
        data = res.json()

        if 'error' in data:
            return {'error': data['error']}

        organic = data.get('organic_results', [])
        for i, item in enumerate(organic):
            url = item.get('link', '')
            results.append({
                'rank': i + 1,
                'title': item.get('title', ''),
                'url': url,
                'domain': urlparse(url).netloc,
                'snippet': item.get('snippet', '').replace('\n', ' '),
            })

        return {'results': results, 'keyword': keyword}

    except Exception as e:
        return {'error': str(e)}


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
