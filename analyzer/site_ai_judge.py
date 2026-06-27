from google import genai
import json
import re


def judge_site(aggregated: dict, api_key: str) -> dict:
    """サイト全体のクロールデータをAIが総合診断"""
    client = genai.Client(api_key=api_key)

    prompt = f"""あなたはSEO専門家です。以下のWebサイト全体のSEO分析データをもとに、
サイト全体の課題と改善提案を診断してください。

## サイト情報
URL: {aggregated.get('base_url')}
クロールページ数: {aggregated.get('total_pages')}ページ
平均SEOスコア: {aggregated.get('avg_score')}点

## サイト全体の問題集計
{json.dumps(aggregated.get('issue_summary', {}), ensure_ascii=False, indent=2)}

## スコアの低いページ（要改善）
{json.dumps(aggregated.get('low_score_pages', []), ensure_ascii=False, indent=2)}

## ページサンプル（最大10件）
{json.dumps(aggregated.get('sample_pages', []), ensure_ascii=False, indent=2)}

以下のJSON形式のみで回答してください:

{{
  "site_score": 0から100の整数,
  "site_status": "良好または要改善または要対応",
  "site_summary": "サイト全体の状態を2-3文で要約",
  "top_issues": [
    {{"rank": 1, "issue": "最重要課題", "affected_pages": 件数の整数, "detail": "詳細説明", "fix": "具体的な改善方法"}}
  ],
  "priority_actions": [
    {{"rank": 1, "action": "優先改善アクション", "expected_effect": "期待効果", "difficulty": "簡単または普通または難しい"}}
  ],
  "page_type_advice": [
    {{"page_type": "トップページ/サービスページ/ブログ等", "advice": "そのページ種別向けのSEOアドバイス"}}
  ]
}}

top_issuesは最大5件、priority_actionsは最大5件、page_type_adviceは最大3件。JSONのみ返してください。"""

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
