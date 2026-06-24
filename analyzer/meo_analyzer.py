import requests
from bs4 import BeautifulSoup
from google import genai
import json
import re


def analyze_meo(url: str, api_key: str) -> dict:
    """MEO（Googleマップ・ローカル検索）対策度をWebサイトから分析（API費用ゼロ）"""

    # サイトからローカルSEOシグナルを収集
    signals = _collect_local_signals(url)

    # AIで評価
    return _ai_meo_judgment(signals, api_key)


def _collect_local_signals(url: str) -> dict:
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    signals = {'url': url}

    try:
        res = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(res.text, 'lxml')

        text = soup.get_text(separator=' ', strip=True)

        # Googleマップ埋め込み
        iframes = soup.find_all('iframe')
        has_map_embed = any('google.com/maps' in (f.get('src', '') + f.get('data-src', ''))
                            for f in iframes)

        # LocalBusiness schema.org
        import json as _json
        schemas = soup.find_all('script', attrs={'type': 'application/ld+json'})
        schema_types = []
        has_local_business = False
        nap_in_schema = False
        for s in schemas:
            try:
                d = _json.loads(s.string or '')
                t = d.get('@type', '')
                schema_types.append(t)
                if any(x in str(t) for x in ['LocalBusiness', 'Restaurant', 'Store',
                                               'MedicalBusiness', 'Hotel', 'Organization']):
                    has_local_business = True
                    if d.get('address') or d.get('telephone'):
                        nap_in_schema = True
            except Exception:
                pass

        # NAP（店名・住所・電話）テキスト検出
        tel_patterns = ['tel:', 'TEL', '電話', '℡', 'phone']
        address_patterns = ['〒', '都', '道', '府', '県', '市', '区', '町', '番地']
        has_tel = any(p.lower() in text.lower() or p in text for p in tel_patterns)
        has_address = any(p in text for p in address_patterns)

        # 営業時間
        hours_patterns = ['営業時間', '定休日', '受付時間', '開店', '閉店']
        has_hours = any(p in text for p in hours_patterns)

        # 口コミ・レビュー関連
        review_patterns = ['口コミ', 'レビュー', 'お客様の声', '評判']
        has_reviews = any(p in text for p in review_patterns)

        # Googleマップリンク
        links = soup.find_all('a', href=True)
        has_map_link = any('google.com/maps' in a['href'] or 'goo.gl/maps' in a['href']
                           for a in links)

        # SNSリンク
        sns_patterns = ['twitter.com', 'x.com', 'instagram.com', 'facebook.com',
                        'line.me', 'tiktok.com']
        sns_links = [a['href'] for a in links
                     if any(s in a.get('href', '') for s in sns_patterns)]

        signals.update({
            'has_map_embed': has_map_embed,
            'has_map_link': has_map_link,
            'has_local_business_schema': has_local_business,
            'nap_in_schema': nap_in_schema,
            'schema_types': schema_types,
            'has_tel': has_tel,
            'has_address': has_address,
            'has_hours': has_hours,
            'has_reviews': has_reviews,
            'sns_count': len(sns_links),
            'sns_links': sns_links[:5],
        })

    except Exception as e:
        signals['scrape_error'] = str(e)

    return signals


def _ai_meo_judgment(signals: dict, api_key: str) -> dict:
    client = genai.Client(api_key=api_key)

    prompt = f"""あなたはMEO（マップエンジン最適化・Googleビジネスプロフィール対策）の専門家です。
以下のウェブサイトのローカルSEOシグナルをもとに、MEO対策度を診断してください。

## サイトデータ
URL: {signals.get('url')}

### ローカルSEOシグナル
- Googleマップ埋め込み: {signals.get('has_map_embed')}
- Googleマップリンク: {signals.get('has_map_link')}
- LocalBusiness構造化データ: {signals.get('has_local_business_schema')}
- 構造化データ内NAP情報: {signals.get('nap_in_schema')}
- 構造化データ種類: {signals.get('schema_types')}
- 電話番号の記載: {signals.get('has_tel')}
- 住所の記載: {signals.get('has_address')}
- 営業時間の記載: {signals.get('has_hours')}
- 口コミ・レビュー掲載: {signals.get('has_reviews')}
- SNSリンク数: {signals.get('sns_count')}

## MEO評価観点
1. NAP（店名・住所・電話）情報の一貫性・充実度
2. Googleマップとの連携（埋め込み・リンク）
3. LocalBusiness schema.orgの設定
4. 営業時間・定休日の明記
5. 口コミ促進・返信施策
6. SNS連携（ローカル信頼シグナル）
7. Googleビジネスプロフィールとの整合性

以下のJSON形式のみで回答してください:

{{
  "meo_score": 0から100の整数,
  "meo_status": "良好または要改善または要対応",
  "meo_summary": "MEO対策状況の要約（2-3文）",
  "nap_score": 0から100の整数,
  "nap_comment": "NAP情報の評価",
  "issues": [
    {{"severity": "高または中または低", "title": "課題タイトル", "detail": "詳細", "fix": "改善方法"}}
  ],
  "priority_actions": [
    {{"rank": 1, "action": "具体的な改善アクション", "expected_effect": "期待効果", "difficulty": "簡単または普通または難しい"}}
  ],
  "gbp_checklist": [
    {{"item": "Googleビジネスプロフィール確認項目", "status": "要確認または推奨または済み"}}
  ]
}}

issuesは最大5件、priority_actionsは最大4件、gbp_checklistは5件。JSONのみ返してください。"""

    candidate_models = [
        'gemini-2.5-flash-lite',
        'gemini-2.5-flash',
        'gemini-2.0-flash-lite',
        'gemini-1.5-flash-8b',
        'gemini-1.5-flash',
    ]

    response = None
    last_error = None
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            break
        except Exception as e:
            last_error = e

    if response is None:
        return {'error': str(last_error)}

    try:
        text = response.text.strip()
        json_match = re.search(r'```(?:json)?\s*([\s\S]+?)\s*```', text)
        if json_match:
            text = json_match.group(1)
        else:
            start = text.find('{')
            end = text.rfind('}') + 1
            if start != -1 and end > start:
                text = text[start:end]
        return json.loads(text)
    except Exception as e:
        return {'error': str(e)}
