import requests


def get_pagespeed_data(url: str, api_key: str = None) -> dict:
    endpoint = 'https://www.googleapis.com/pagespeedonline/v5/runPagespeed'
    results = {}

    for strategy in ['mobile', 'desktop']:
        params = {
            'url': url,
            'strategy': strategy,
            'category': ['performance', 'accessibility', 'seo', 'best-practices'],
        }
        if api_key:
            params['key'] = api_key

        try:
            response = requests.get(endpoint, params=params, timeout=60)
            data = response.json()

            if 'error' in data:
                results[strategy] = {'error': data['error'].get('message', 'APIエラー')}
                continue

            categories = data.get('lighthouseResult', {}).get('categories', {})
            audits = data.get('lighthouseResult', {}).get('audits', {})

            def score(key):
                s = categories.get(key, {}).get('score')
                return int(s * 100) if s is not None else None

            results[strategy] = {
                'performance_score': score('performance'),
                'accessibility_score': score('accessibility'),
                'seo_score': score('seo'),
                'best_practices_score': score('best-practices'),
                'fcp': audits.get('first-contentful-paint', {}).get('displayValue', 'N/A'),
                'lcp': audits.get('largest-contentful-paint', {}).get('displayValue', 'N/A'),
                'cls': audits.get('cumulative-layout-shift', {}).get('displayValue', 'N/A'),
                'tbt': audits.get('total-blocking-time', {}).get('displayValue', 'N/A'),
                'si': audits.get('speed-index', {}).get('displayValue', 'N/A'),
            }

        except requests.exceptions.Timeout:
            results[strategy] = {'error': 'PageSpeed APIがタイムアウトしました'}
        except Exception as e:
            results[strategy] = {'error': str(e)}

    return results
