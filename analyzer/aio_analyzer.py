from google import genai
import json
import re


def analyze_aio(seo_data: dict, api_key: str) -> dict:
    """AIO（AI検索・AI Overview）対策度を分析"""
    client = genai.Client(api_key=api_key)

    prompt = f"""あなたはAI検索最適化（AIO: AI Overview対策）の専門家です。
以下のウェブサイトデータをもとに、GoogleのAI Overview・ChatGPT・Perplexityなどの
AI検索に引用・掲載されやすいかを診断してください。

## サイトデータ
URL: {seo_data.get('url')}
タイトル: {seo_data.get('title')}
H1: {seo_data.get('h1_texts')}
H2: {seo_data.get('h2_texts', [])[:8]}
テキスト量: {seo_data.get('word_count')}語
FAQ・Q&A: {seo_data.get('has_faq')}
構造化データ: {seo_data.get('has_schema')} / 種類: {seo_data.get('schema_types')}
連絡先情報: {seo_data.get('has_contact')}
会社・サービス情報: {seo_data.get('has_about')}
SSL: {seo_data.get('is_ssl')}

## AIO評価観点
1. E-E-A-T（経験・専門性・権威性・信頼性）シグナルの有無
2. 質問形式のコンテンツ（FAQ・Q&A）があるか
3. 明確で具体的な回答・情報があるか
4. 構造化データ（schema.org）でAIが読みやすいか
5. 会社・サービス情報が明確に記載されているか
6. テキスト量が十分か（AIが参照できる情報量）
7. 信頼性シグナル（SSL・会社情報・実績等）

以下のJSON形式のみで回答してください:

{{
  "aio_score": 0から100の整数,
  "aio_status": "良好または要改善または要対応",
  "aio_summary": "AIO対策状況の要約（2-3文）",
  "eeat_score": 0から100の整数,
  "eeat_comment": "E-E-A-Tの評価コメント",
  "strengths": ["AI検索に有利な点を3つまで"],
  "weaknesses": [
    {{"title": "弱点タイトル", "detail": "詳細", "fix": "具体的な改善方法"}}
  ],
  "content_recommendations": ["AIに引用されやすくなるコンテンツ改善案を3つ"]
}}

weaknessesは最大5件。JSONのみ返してください。"""

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
