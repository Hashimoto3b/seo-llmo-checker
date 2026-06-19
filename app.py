import streamlit as st
import os
from dotenv import load_dotenv, set_key
from analyzer.scraper import scrape_page
from analyzer.ai_judge import get_ai_judgment

load_dotenv()

ENV_PATH = os.path.join(os.path.dirname(__file__), '.env')

st.set_page_config(
    page_title="SEO・LLMO診断ツール",
    page_icon="🔍",
    layout="wide"
)

st.markdown("""
<style>
.score-box {
    padding: 24px;
    border-radius: 12px;
    text-align: center;
    margin: 8px 0;
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
</style>
""", unsafe_allow_html=True)

# ===== APIキー管理 =====
saved_key = os.getenv('GEMINI_API_KEY', '')

with st.sidebar:
    st.header("⚙️ 設定")

    if saved_key:
        st.success("✅ Gemini APIキー設定済み")
        gemini_key = saved_key
        if st.button("🔑 APIキーを変更"):
            st.session_state['change_key'] = True
    else:
        st.session_state['change_key'] = True

    if st.session_state.get('change_key'):
        new_key = st.text_input("Gemini API Key", type="password",
                                placeholder="AIza...")
        if st.button("💾 保存", type="primary"):
            if new_key:
                if not os.path.exists(ENV_PATH):
                    open(ENV_PATH, 'w').close()
                set_key(ENV_PATH, 'GEMINI_API_KEY', new_key)
                os.environ['GEMINI_API_KEY'] = new_key
                st.session_state['change_key'] = False
                st.rerun()
            else:
                st.error("APIキーを入力してください")
        gemini_key = new_key

    st.divider()
    st.markdown("**Gemini APIキーの取得**")
    st.markdown("1. [Google AI Studio](https://aistudio.google.com/) にアクセス")
    st.markdown("2. 「Get API key」をクリック")
    st.markdown("3. 上の欄に貼り付けて保存")

# ===== メイン =====
st.title("🔍 SEO・LLMO 無料診断ツール")
st.caption("AIが検索エンジン対策とAI検索対策を同時に診断します")
st.markdown("---")

col_input, col_btn = st.columns([4, 1])
with col_input:
    url = st.text_input("診断するURLを入力", placeholder="https://example.com",
                        label_visibility="collapsed")
with col_btn:
    run = st.button("🚀 診断開始", type="primary", use_container_width=True)

# ===== 診断実行 =====
if run:
    if not url:
        st.error("URLを入力してください")
        st.stop()
    if not url.startswith(('http://', 'https://')):
        st.error("URLは http:// または https:// から始めてください")
        st.stop()
    if not gemini_key:
        st.error("サイドバーから Gemini API Key を保存してください")
        st.stop()

    with st.status("診断中...", expanded=True) as status:
        st.write("📄 ページ情報を収集中...")
        seo_data = scrape_page(url)

        if 'error' in seo_data:
            status.update(label="エラー", state="error")
            st.error(f"ページ取得エラー: {seo_data['error']}")
            st.stop()

        st.write("🤖 AIが診断中...")
        result = get_ai_judgment(seo_data, gemini_key)

        if 'error' in result:
            status.update(label="エラー", state="error")
            st.error(f"AI診断エラー: {result['error']}")
            st.stop()

        status.update(label="診断完了！", state="complete")

    st.success("✅ 診断が完了しました")
    st.markdown("---")

    # ===== スコア表示 =====
    st.subheader("📊 総合スコア")
    st.caption(f"診断URL: {url}")

    seo_score = result.get('seo_score', 0)
    llmo_score = result.get('llmo_score', 0)

    def score_css(s):
        return "score-good" if s >= 70 else "score-warn" if s >= 40 else "score-bad"

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div class="score-box {score_css(seo_score)}">
            <div style="font-size:1.1rem;font-weight:bold;">🔍 SEOスコア</div>
            <div class="score-num">{seo_score}</div>
            <div style="font-size:0.85rem;margin-bottom:4px;">/ 100 &nbsp;|&nbsp; {result.get('seo_status', '')}</div>
            <div style="font-size:0.85rem;">{result.get('seo_summary', '')}</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="score-box {score_css(llmo_score)}">
            <div style="font-size:1.1rem;font-weight:bold;">🤖 LLMOスコア</div>
            <div class="score-num">{llmo_score}</div>
            <div style="font-size:0.85rem;margin-bottom:4px;">/ 100 &nbsp;|&nbsp; {result.get('llmo_status', '')}</div>
            <div style="font-size:0.85rem;">{result.get('llmo_summary', '')}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # ===== 課題 =====
    st.subheader("⚠️ 主な課題")

    severity_icon = {'高': '🔴', '中': '🟡', '低': '🟢'}
    severity_css  = {'高': 'issue-high', '中': 'issue-mid', '低': 'issue-low'}
    cat_css       = {'SEO': 'tag-seo', 'LLMO': 'tag-llmo'}

    issues = result.get('issues', [])
    if issues:
        for issue in issues:
            sev = issue.get('severity', '中')
            cat = issue.get('category', 'SEO')
            st.markdown(f"""
            <div class="issue-card {severity_css.get(sev, 'issue-mid')}">
                <span class="tag {cat_css.get(cat, 'tag-seo')}">{cat}</span>
                <span class="tag" style="background:#f0f0f0;color:#333;">{severity_icon.get(sev, '🟡')} {sev}</span>
                <strong>{issue.get('title', '')}</strong><br>
                <span style="font-size:0.88rem;color:#555;">{issue.get('detail', '')}</span>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("課題は見つかりませんでした")

    st.markdown("---")

    # ===== 優先改善ポイント =====
    st.subheader("✅ 優先改善ポイント")

    diff_icon = {'簡単': '🟢', '普通': '🟡', '難しい': '🔴'}
    actions = result.get('priority_actions', [])

    if actions:
        for action in actions:
            diff = action.get('difficulty', '普通')
            with st.expander(f"#{action.get('rank', '')}  {action.get('action', '')}　{diff_icon.get(diff, '🟡')} {diff}"):
                st.write(f"**期待効果:** {action.get('expected_effect', '')}")
    else:
        st.info("改善ポイントはありません")

    st.markdown("---")

    # ===== 詳細データ =====
    with st.expander("🔧 技術詳細データ"):
        st.json({k: v for k, v in seo_data.items() if k != 'url'})
