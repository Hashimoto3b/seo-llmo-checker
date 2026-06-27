import streamlit as st
import os
from dotenv import load_dotenv
from analyzer.scraper import scrape_page
from analyzer.ai_judge import get_ai_judgment
from analyzer.keyword_rank import search_keyword, highlight_urls

from analyzer.aio_analyzer import analyze_aio
from analyzer.meo_analyzer import analyze_meo

load_dotenv()

st.set_page_config(
    page_title="SEO・LLMO診断ツール",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
.score-box {
    padding: 24px; border-radius: 12px; text-align: center; margin: 8px 0;
}
.score-good { background-color: #d4edda; border: 2px solid #28a745; color: #155724; }
.score-warn { background-color: #fff3cd; border: 2px solid #ffc107; color: #856404; }
.score-bad  { background-color: #f8d7da; border: 2px solid #dc3545; color: #721c24; }
.score-num  { font-size: 3rem; font-weight: bold; margin: 8px 0; }
.issue-card { padding: 12px 16px; border-radius: 8px; margin: 6px 0; }
.issue-high { background: #fff5f5; border-left: 5px solid #dc3545; }
.issue-mid  { background: #fffdf0; border-left: 5px solid #ffc107; }
.issue-low  { background: #f0fff4; border-left: 5px solid #28a745; }
.tag { display: inline-block; padding: 2px 8px; border-radius: 4px;
       font-size: 0.75rem; font-weight: bold; margin-right: 6px; }
.tag-seo  { background: #cce5ff; color: #004085; }
.tag-llmo { background: #e2d9f3; color: #4a235a; }
.rank-row { padding: 10px 14px; border-radius: 8px; margin: 4px 0;
            border: 1px solid #e0e0e0; }
.rank-target { background: #fff3cd; border: 2px solid #ffc107; }
.rank-other  { background: #ffffff; }
</style>
""", unsafe_allow_html=True)


def get_gemini_key() -> str:
    try:
        return st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass
    return os.getenv('GEMINI_API_KEY', st.session_state.get('gemini_key', ''))


def get_serpapi_key():
    try:
        return st.secrets.get("SERPAPI_KEY", "")
    except Exception:
        pass
    return os.getenv('SERPAPI_KEY', st.session_state.get('serpapi_key', ''))


def score_css(s):
    if s is None: return "score-warn"
    return "score-good" if s >= 70 else "score-warn" if s >= 40 else "score-bad"


def render_score_box(label, score, status, summary):
    st.markdown(f"""
    <div class="score-box {score_css(score)}">
        <div style="font-size:1.1rem;font-weight:bold;">{label}</div>
        <div class="score-num">{score if score is not None else 'N/A'}</div>
        <div style="font-size:0.85rem;margin-bottom:4px;">/ 100 &nbsp;|&nbsp; {status}</div>
        <div style="font-size:0.85rem;">{summary}</div>
    </div>
    """, unsafe_allow_html=True)


def render_issues(issues, show_fix=False):
    severity_icon = {'高': '🔴', '中': '🟡', '低': '🟢'}
    severity_css  = {'高': 'issue-high', '中': 'issue-mid', '低': 'issue-low'}
    for issue in issues:
        sev = issue.get('severity', '中')
        fix = f"<br><span style='font-size:0.82rem;color:#1a73e8;'>💡 {issue.get('fix','')}</span>" if show_fix and issue.get('fix') else ''
        st.markdown(f"""
        <div class="issue-card {severity_css.get(sev,'issue-mid')}">
            <span class="tag" style="background:#f0f0f0;color:#333;">{severity_icon.get(sev,'🟡')} {sev}</span>
            <strong>{issue.get('title','')}</strong><br>
            <span style="font-size:0.88rem;color:#555;">{issue.get('detail','')}</span>{fix}
        </div>
        """, unsafe_allow_html=True)


# ===== サイドバー =====
with st.sidebar:
    st.header("⚙️ 設定")
    gemini_key = get_gemini_key()

    if gemini_key:
        st.success("✅ AIエンジン接続済み")
    else:
        st.warning("Gemini APIキーが必要です")
        k = st.text_input("Gemini API Key", type="password")
        if st.button("設定", type="primary"):
            if k:
                st.session_state['gemini_key'] = k
                st.rerun()

    st.divider()

    serpapi_key = get_serpapi_key()
    if serpapi_key:
        st.success("✅ キーワード検索設定済み")
    else:
        with st.expander("🔑 キーワード順位設定（任意）"):
            k2 = st.text_input("SerpAPI Key", type="password")
            if st.button("キーワード設定を保存"):
                st.session_state['serpapi_key'] = k2
                st.rerun()
            st.caption("[SerpAPI無料登録 →](https://serpapi.com)")

    st.divider()
    st.caption("Powered by Google Gemini AI")

# ===== メイン =====
st.title("🔍 SEO・LLMO 無料診断ツール")
st.caption("AIが検索エンジン対策・AI検索対策・MEO対策を同時に診断します")

tab1, tab2, tab3, tab4 = st.tabs(["📊 SEO・LLMO診断", "🔎 キーワード順位", "🤖 AIO分析", "📍 MEO分析"])


# =====================
# TAB1: SEO・LLMO診断
# =====================
with tab1:
    st.subheader("URLを入力してSEO・LLMO診断")
    c1, c2 = st.columns([4, 1])
    with c1:
        url1 = st.text_input("診断URL", placeholder="https://example.com",
                             label_visibility="collapsed", key="url1")
    with c2:
        run1 = st.button("🚀 診断開始", type="primary", use_container_width=True, key="run1")

    if run1:
        if not url1 or not url1.startswith('http'):
            st.error("正しいURLを入力してください")
            st.stop()
        if not gemini_key:
            st.error("サイドバーにGemini APIキーを設定してください")
            st.stop()

        with st.status("診断中...", expanded=True) as status:
            st.write("📄 ページ情報を収集中...")
            seo_data = scrape_page(url1)
            if 'error' in seo_data:
                status.update(label="エラー", state="error")
                st.error(seo_data['error'])
                st.stop()
            st.write("🤖 AIが診断中...")
            result = get_ai_judgment(seo_data, gemini_key)
            if 'error' in result:
                status.update(label="エラー", state="error")
                st.error(result['error'])
                st.stop()
            status.update(label="診断完了！", state="complete")

        st.success("✅ 診断完了")
        st.markdown("---")
        st.caption(f"診断URL: {url1}")

        col1, col2 = st.columns(2)
        with col1:
            render_score_box("🔍 SEOスコア", result.get('seo_score'),
                             result.get('seo_status',''), result.get('seo_summary',''))
        with col2:
            render_score_box("🤖 LLMOスコア", result.get('llmo_score'),
                             result.get('llmo_status',''), result.get('llmo_summary',''))

        st.markdown("---")
        st.subheader("⚠️ 主な課題")
        issues = result.get('issues', [])
        if issues:
            severity_css = {'高': 'issue-high', '中': 'issue-mid', '低': 'issue-low'}
            severity_icon = {'高': '🔴', '中': '🟡', '低': '🟢'}
            cat_css = {'SEO': 'tag-seo', 'LLMO': 'tag-llmo'}
            for issue in issues:
                sev = issue.get('severity', '中')
                cat = issue.get('category', 'SEO')
                st.markdown(f"""
                <div class="issue-card {severity_css.get(sev,'issue-mid')}">
                    <span class="tag {cat_css.get(cat,'tag-seo')}">{cat}</span>
                    <span class="tag" style="background:#f0f0f0;color:#333;">{severity_icon.get(sev,'🟡')} {sev}</span>
                    <strong>{issue.get('title','')}</strong><br>
                    <span style="font-size:0.88rem;color:#555;">{issue.get('detail','')}</span>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("✅ 優先改善ポイント")
        diff_icon = {'簡単': '🟢', '普通': '🟡', '難しい': '🔴'}
        for action in result.get('priority_actions', []):
            diff = action.get('difficulty', '普通')
            with st.expander(f"#{action.get('rank','')}  {action.get('action','')}　{diff_icon.get(diff,'🟡')} {diff}"):
                st.write(f"**期待効果:** {action.get('expected_effect','')}")

        with st.expander("🔧 技術詳細データ"):
            st.json({k: v for k, v in seo_data.items() if k != 'url'})


# =====================
# TAB2: キーワード順位
# =====================
with tab2:
    st.subheader("🔎 キーワード検索順位確認")

    serpapi_key = get_serpapi_key()
    if not serpapi_key:
        st.info("サイドバーの「キーワード順位設定」にSerpAPI Keyを入力すると利用できます。")
        st.markdown("""
        **設定手順（無料・100回/月）**
        1. [serpapi.com](https://serpapi.com) で無料登録
        2. ダッシュボードの **API Key** をコピー
        3. サイドバーに入力して保存
        """)
    else:
        kw = st.text_input("検索キーワード", placeholder="どさんこシェフ", key="kw")

        st.markdown("**自社・競合URLを入力（何位か強調表示されます）**")
        tc1, tc2, tc3 = st.columns(3)
        with tc1:
            t_url1 = st.text_input("URL①（自社）", placeholder="https://example.com", key="t1")
        with tc2:
            t_url2 = st.text_input("URL②（競合）", placeholder="https://hotpepper.jp/...", key="t2")
        with tc3:
            t_url3 = st.text_input("URL③", placeholder="任意", key="t3")

        num_results = st.slider("取得件数", 10, 20, 10)
        run2 = st.button("🔎 検索開始", type="primary", key="run2")

        if run2:
            if not kw:
                st.error("キーワードを入力してください")
                st.stop()

            with st.spinner("検索中..."):
                data = search_keyword(kw, serpapi_key, num_results)

            if 'error' in data:
                st.error(f"検索エラー: {data['error']}")
                st.stop()

            results = data.get('results', [])
            target_urls = [t_url1, t_url2, t_url3]
            results = highlight_urls(results, target_urls)

            # 自社・競合の順位サマリー
            targets_found = [r for r in results if r.get('is_target')]
            if targets_found:
                st.markdown("#### 📌 指定サイトの順位")
                for r in targets_found:
                    st.success(f"**{r['rank']}位** — {r['domain']}　「{r['title'][:40]}」")
            else:
                st.warning(f"指定したURLは上位{num_results}件に見つかりませんでした")

            st.markdown("---")
            st.markdown(f"#### 「{kw}」の検索結果 上位{len(results)}件")

            for r in results:
                css = "rank-target" if r.get('is_target') else "rank-other"
                badge = "⭐ 自社・競合" if r.get('is_target') else ""
                st.markdown(f"""
                <div class="rank-row {css}">
                    <span style="font-size:1.3rem;font-weight:bold;color:#1a73e8;">#{r['rank']}</span>
                    &nbsp;&nbsp;{badge}
                    <strong>{r['title']}</strong><br>
                    <span style="font-size:0.8rem;color:#1a73e8;">{r['url']}</span><br>
                    <span style="font-size:0.85rem;color:#555;">{r['snippet'][:100]}...</span>
                </div>
                """, unsafe_allow_html=True)


# =====================
# TAB3: AIO分析
# =====================
with tab3:
    st.subheader("🤖 AIO（AI検索対策）分析")
    st.caption("ChatGPT・Gemini・Perplexity などのAI検索に引用されやすいかを診断します")

    c1, c2 = st.columns([4, 1])
    with c1:
        url3 = st.text_input("診断URL", placeholder="https://example.com",
                             label_visibility="collapsed", key="url3")
    with c2:
        run3 = st.button("🤖 分析開始", type="primary", use_container_width=True, key="run3")

    if run3:
        if not url3 or not url3.startswith('http'):
            st.error("正しいURLを入力してください")
            st.stop()
        if not gemini_key:
            st.error("サイドバーにGemini APIキーを設定してください")
            st.stop()

        with st.status("AIO分析中...", expanded=True) as status:
            st.write("📄 ページ情報を収集中...")
            seo_data3 = scrape_page(url3)
            if 'error' in seo_data3:
                status.update(label="エラー", state="error")
                st.error(seo_data3['error'])
                st.stop()
            st.write("🤖 AIがAIO対策度を診断中...")
            aio = analyze_aio(seo_data3, gemini_key)
            if 'error' in aio:
                status.update(label="エラー", state="error")
                st.error(aio['error'])
                st.stop()
            status.update(label="分析完了！", state="complete")

        st.success("✅ AIO分析完了")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            render_score_box("🤖 AIOスコア", aio.get('aio_score'),
                             aio.get('aio_status',''), aio.get('aio_summary',''))
        with col2:
            render_score_box("⭐ E-E-A-Tスコア", aio.get('eeat_score'),
                             '', aio.get('eeat_comment',''))

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("✅ AI検索に有利な点")
            for s in aio.get('strengths', []):
                st.success(f"✓ {s}")

        with col2:
            st.subheader("⚠️ 改善が必要な点")
            for w in aio.get('weaknesses', []):
                with st.expander(f"📌 {w.get('title','')}"):
                    st.write(w.get('detail',''))
                    if w.get('fix'):
                        st.info(f"💡 改善方法: {w.get('fix','')}")

        st.markdown("---")
        st.subheader("📝 コンテンツ改善提案")
        for i, rec in enumerate(aio.get('content_recommendations', []), 1):
            st.markdown(f"**{i}.** {rec}")


# =====================
# TAB4: MEO分析
# =====================
with tab4:
    st.subheader("📍 MEO（Googleマップ・ローカル検索）分析")
    st.caption("費用ゼロ。Webサイト上のローカルSEOシグナルを分析します")

    c1, c2 = st.columns([4, 1])
    with c1:
        url4 = st.text_input("診断URL", placeholder="https://example.com",
                             label_visibility="collapsed", key="url4")
    with c2:
        run4 = st.button("📍 分析開始", type="primary", use_container_width=True, key="run4")

    if run4:
        if not url4 or not url4.startswith('http'):
            st.error("正しいURLを入力してください")
            st.stop()
        if not gemini_key:
            st.error("サイドバーにGemini APIキーを設定してください")
            st.stop()

        with st.status("MEO分析中...", expanded=True) as status:
            st.write("📍 ローカルSEOシグナルを収集中...")
            meo = analyze_meo(url4, gemini_key)
            if 'error' in meo:
                status.update(label="エラー", state="error")
                st.error(meo['error'])
                st.stop()
            status.update(label="分析完了！", state="complete")

        st.success("✅ MEO分析完了")
        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            render_score_box("📍 MEOスコア", meo.get('meo_score'),
                             meo.get('meo_status',''), meo.get('meo_summary',''))
        with col2:
            render_score_box("📋 NAP情報スコア", meo.get('nap_score'),
                             '', meo.get('nap_comment',''))

        st.markdown("---")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("⚠️ 課題")
            render_issues(meo.get('issues', []), show_fix=True)

        with col2:
            st.subheader("☑️ Googleビジネスプロフィール確認リスト")
            status_icon = {'要確認': '🔴', '推奨': '🟡', '済み': '🟢'}
            for item in meo.get('gbp_checklist', []):
                s = item.get('status', '要確認')
                st.markdown(f"{status_icon.get(s,'🟡')} {item.get('item','')}")

        st.markdown("---")
        st.subheader("✅ 優先改善ポイント")
        diff_icon = {'簡単': '🟢', '普通': '🟡', '難しい': '🔴'}
        for action in meo.get('priority_actions', []):
            diff = action.get('difficulty', '普通')
            with st.expander(f"#{action.get('rank','')}  {action.get('action','')}　{diff_icon.get(diff,'🟡')} {diff}"):
                st.write(f"**期待効果:** {action.get('expected_effect','')}")
