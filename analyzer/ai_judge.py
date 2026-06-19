from google import genai
import json
import re


def get_ai_judgment(seo_data: dict, api_key: str) -> dict:
    client = genai.Client(api_key=api_key)

    prompt = f"""あなたはSEOとLLMO（AI検索最適化）の専門家です。
以下のウェブサイト分析データをもとに、SEOとLLMOの診断を行ってください。

## 分析データ
URL: {seo_data.get('url')}

### 基本SEO情報
- タイトル: 「{seo_data.get('title')}」({seo_data.get('title_length')}文字)
- メタディスクリプション: 「{seo_data.get('meta_description')}」({seo_data.get('meta_description_length')}文字)
- H1タグ数: {seo_data.get('h1_count')}個 / 内容: {seo_data.get('h1_texts')}
- H2タグ内容: {seo_data.get('h2_texts', [])[:5]}
- SSL対応: {seo_data.get('is_ssl')}
- Canonicalタグ: {seo_data.get('has_canonical')}
- viewport(モバイル対応): {seo_data.get('has_viewport')}
- OGP設定: {seo_data.get('has_ogp')}

### コンテンツ
- テキスト量(語数): {seo_data.get('word_count')}
- 内部リンク数: {seo_data.get('internal_links_count')}
- 外部リンク数: {seo_data.get('external_links_count')}
- 画像総数: {seo_data.get('total_images')}
- alt属性なし画像数: {seo_data.get('images_without_alt')}

### LLMO関連（AI可読性）
- 構造化データ(schema.org): {seo_data.get('has_schema')} / 種類: {seo_data.get('schema_types')}
- FAQ・Q&Aコンテンツ: {seo_data.get('has_faq')}
- 連絡先情報: {seo_data.get('has_contact')}
- 会社・サービス情報: {seo_data.get('has_about')}

## 評価基準
- SEO: タイトル(30-60文字が理想)、メタ(70-120文字が理想)、H1は1つ、SSL必須
- LLMO: 構造化データ、FAQ、会社情報の明確さ、AIが読みやすい構造、テキスト量

以下のJSON形式のみで回答してください（コードブロック不要、JSONだけ）:

{{
  "seo_score": 0から100の整数,
  "llmo_score": 0から100の整数,
  "seo_status": "良好または要改善または要対応",
  "llmo_status": "良好または要改善または要対応",
  "seo_summary": "SEO状態の要約（1-2文）",
  "llmo_summary": "LLMO状態の要約（1-2文）",
  "issues": [
    {{"category": "SEOまたはLLMO", "severity": "高または中または低", "title": "課題タイトル", "detail": "詳細説明"}}
  ],
  "priority_actions": [
    {{"rank": 1, "action": "具体的な改善アクション", "expected_effect": "期待される効果", "difficulty": "簡単または普通または難しい"}}
  ]
}}

issuesは最大6件、priority_actionsは最大5件。必ずJSONのみ返してください。"""

    candidate_models = [
        'gemini-2.5-flash-lite',
        'gemini-2.5-flash',
        'gemini-2.0-flash-lite',
        'gemini-1.5-flash-8b',
        'gemini-1.5-flash',
    ]

    last_error = None
    response = None
    for model_name in candidate_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
            )
            break
        except Exception as e:
            last_error = e
            continue

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
    except json.JSONDecodeError as e:
        return {'error': f'AI応答のパースに失敗しました: {e}'}
    except Exception as e:
        return {'error': str(e)}
