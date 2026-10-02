import time
import random
import pandas as pd
import streamlit as st

# ==========================================
# 1. 페이지 레이아웃 설정
# ==========================================
st.set_page_config(
    page_title="Team Balancer Pro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. 컴팩트 미니멀 테마 CSS 적용
# ==========================================
def inject_theme_css(is_dark):
    if is_dark:
        bg_color = "#0E1117"
        card_bg = "#161B22"
        border_color = "#30363D"
        text_color = "#E6EDF3"
        sub_text = "#8B949E"
        input_bg = "#21262D"
        accent_btn = "#238636"
        accent_btn_hover = "#2ea043"
    else:
        bg_color = "#F8FAFC"
        card_bg = "#FFFFFF"
        border_color = "#E2E8F0"
        text_color = "#0F172A"
        sub_text = "#64748B"
        input_bg = "#F1F5F9"
        accent_btn = "#2563EB"
        accent_btn_hover = "#1D4ED8"

    st.markdown(f"""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        html, body, [class*="css"] {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
            background-color: {bg_color} !important;
            color: {text_color} !important;
            font-size: 14px !important;
        }}

        .stApp {{
            background-color: {bg_color};
        }}

        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 1000px;
        }}

        /* 컴팩트 헤더 카드 */
        .header-card {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 10px;
            padding: 14px 20px;
            margin-bottom: 16px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
        }}

        /* 입력창 및 버튼 컴팩트화 */
        .stTextInput input, .stNumberInput input {{
            background-color: {input_bg} !important;
            color: {text_color} !important;
            border: 1px solid {border_color} !important;
            border-radius: 6px !important;
            padding: 6px 10px !important;
            font-size: 13px !important;
        }}

        .stButton > button {{
            background-color: {accent_btn} !important;
            color: white !important;
            font-weight: 600 !important;
            border-radius: 6px !important;
            border: none !important;
            padding: 0.45rem 1rem !important;
            font-size: 13px !important;
            width: 100%;
            transition: all 0.2s ease;
        }}
        .stButton > button:hover {{
            background-color: {accent_btn_hover} !important;
        }}

        .streamlit-expanderHeader {{
            background-color: {card_bg} !important;
            border: 1px solid {border_color} !important;
            border-radius: 6px !important;
            font-size: 13px !important;
        }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 사이드바 설정 (다크모드 토글 포함)
# ==========================================
st.sidebar.markdown("### 🎨 화면 설정")
dark_mode = st.sidebar.toggle("🌙 다크 모드", value=True)

inject_theme_css(dark_mode)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ 매칭 설정")
num_teams = st.sidebar.number_input("팀 개수", min_value=2, max_value=8, value=2, step=1)
team_size = st.sidebar.number_input("팀당 인원 수", min_value=1, max_value=5, value=5, step=1)
cur_weight_pct = st.sidebar.slider("현재 티어 반영 비중 (%)", 0, 100, 60, 5)
cur_weight = cur_weight_pct / 100.0

total_required = num_teams * team_size
auto_balance = st.sidebar.checkbox("⚡ 자동 실시간 매칭", value=True)

# ==========================================
# 4. 점수 매핑 및 계산 함수
# ==========================================
RAW_TIER_SCORES = {
    "아이언 1": 100, "아이언 2": 200, "아이언 3": 300,
    "브론즈 1": 400, "브론즈 2": 500, "브론즈 3": 600,
    "실버 1": 700, "실버 2": 800, "실버 3": 900,
    "골드 1": 1000, "골드 2": 1100, "골드 3": 1200,
    "플래티넘 1": 1300, "플래티넘 2": 1400, "플래티넘 3": 1500,
    "다이아몬드 1": 1600, "다이아몬드 2": 1700, "다이아몬드 3": 1800,
    "초월자 1": 1900, "초월자 2": 2000, "초월자 3": 2100,
    "불멸 1": 2200, "불멸 2": 2300, "불멸 3": 2400,
    "레디언트": 2500,
    "플래 1": 1300, "플래 2": 1400, "플래 3": 1500,
    "다이아 1": 1600, "다이아 2": 1700, "다이아 3": 1800,
}

BASE_TIER_SCORES = {k.replace(" ", ""): v for k, v in RAW_TIER_SCORES.items()}

def get_tier_score(tier_name):
    if pd.isna(tier_name):
        return 1000
    cleaned_tier = str(tier_name).replace(" ", "").strip()
    return BASE_TIER_SCORES.get(cleaned_tier, 1000)

def calculate_player_mmr(cur_tier, cur_rr, peak_tier, peak_rr, cur_weight=0.6):
    cur_base = get_tier_score(cur_tier)
    peak_base = get_tier_score(peak_tier)
    
    cur_rr_val = int(cur_rr) if pd.notna(cur_rr) and str(cur_rr).isdigit() else 0
    peak_rr_val = int(peak_rr) if pd.notna(peak_rr) and str(peak_rr).isdigit() else 0
    
    return ((cur_base + cur_rr_val) * cur_weight) + ((peak_base + peak_rr_val) * (1 - cur_weight))

# ==========================================
# 5. 구글 시트 연동
# ==========================================
REQUIRED_HEADERS = ["닉네임", "현재티어", "현재RR", "최고티어", "최고RR"]

def load_data_from_google_sheet(url):
    try:
        sheet_id = url.split("/d/")[1].split("/")[0] if "docs.google.com/spreadsheets/d/" in url else url.strip()
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&_t={int(time.time())}"
        df = pd.read_csv(csv_url)
        df.columns = [str(col).replace(" ", "").strip() for col in df.columns]
        
        missing = [h for h in REQUIRED_HEADERS if h not in df.columns]
        if missing:
            st.error(f"❌ 시트 헤더 오류: **{', '.join(missing)}** 항목이 누락되었습니다.")
            return None
        return df
    except Exception:
        st.error("구글 시트를 불러오지 못했습니다. 링크 공유 설정(링크가 있는 모든 사용자 뷰어)을 확인해 주세요.")
        return None

# ==========================================
# 6. 밸런싱 알고리즘
# ==========================================
def balance_multi_teams(df, num_teams, team_size=5, cur_weight=0.6):
    players = df.to_dict('records')
    total_required = num_teams * team_size
    
    if len(players) < total_required:
        st.warning(f"⚠️ 인원이 부족합니다! {num_teams}개 팀({team_size}명)을 짜려면 최소 {total_required}명이 필요합니다. (현재: {len(players)}명)")
        return None, None

    for p in players:
        p['MMR'] = calculate_player_mmr(
            p.get('현재티어'), p.get('현재RR', 0),
            p.get('최고티어'), p.get('최고RR', 0),
            cur_weight
        )

    sorted_players = sorted(players[:total_required], key=lambda x: x['MMR'], reverse=True)
    teams = [[] for _ in range(num_teams)]
    
    for i, p in enumerate(sorted_players):
        round_num = i // num_teams
        team_idx = (i % num_teams) if round_num % 2 == 0 else (num_teams - 1 - (i % num_teams))
        teams[team_idx].append(p)

    def team_avg(t):
        return sum(p['MMR'] for p in t) / len(t) if t else 0

    best_var = sum((team_avg(t) - sum(team_avg(x) for x in teams)/num_teams)**2 for t in teams)
    
    for _ in range(1000):
        t1, t2 = random.sample(range(num_teams), 2)
        idx1, idx2 = random.randint(0, team_size - 1), random.randint(0, team_size - 1)
        
        teams[t1][idx1], teams[t2][idx2] = teams[t2][idx2], teams[t1][idx1]
        avgs = [team_avg(t) for t in teams]
        mean_avg = sum(avgs) / len(avgs)
        new_var = sum((a - mean_avg)**2 for a in avgs)
        
        if new_var < best_var:
            best_var = new_var
        else:
            teams[t1][idx1], teams[t2][idx2] = teams[t2][idx2], teams[t1][idx1]

    return teams, [team_avg(t) for t in teams]

# ==========================================
# 7. 메인 화면 UI 구성
# ==========================================
st.markdown("""
<div class="header-card">
    <h2 style="margin: 0; font-size: 1.3rem; font-weight: 700;">⚖️ TEAM BALANCER PRO</h2>
    <p style="margin: 3px 0 0 0; font-size: 0.8rem; opacity: 0.75;">구글 시트 기반 컴팩트 밸런스 매칭 시스템</p>
</div>
""", unsafe_allow_html=True)

# 입력 방식 선택 탭
input_tab1, input_tab2 = st.tabs(["🔗 Google Sheets 연동", "✏️ 직접 명단 입력"])

df_input = None

with input_tab1:
    sheet_url = st.text_input("구글 시트 공유 URL을 입력하세요", placeholder="https://docs.google.com/spreadsheets/d/...")
    if sheet_url:
        df_sheet = load_data_from_google_sheet(sheet_url)
        if df_sheet is not None:
            st.success(f"✅ 명단 불러오기 성공 (총 {len(df_sheet)}명)")
            with st.expander("📄 불러온 선수 명단 미리보기"):
                st.dataframe(df_sheet, use_container_width=True)
            df_input = df_sheet

with input_tab2:
    st.info("아래 표에 직접 참가자 명단과 티어를 입력하세요.")
    sample_tiers = ["레디언트", "불멸 3", "불멸 1", "초월자 2", "다이아 1", "플래티넘 3", "골드 2", "실버 1", "골드 1", "브론즈 2"]
    default_data = {
        "닉네임": [f"Player_{i+1}" for i in range(total_required)],
        "현재티어": [sample_tiers[i % len(sample_tiers)] for i in range(total_required)],
        "현재RR": [0] * total_required,
        "최고티어": [sample_tiers[i % len(sample_tiers)] for i in range(total_required)],
        "최고RR": [0] * total_required
    }
    df_input = st.data_editor(
        pd.DataFrame(default_data),
        num_rows="dynamic",
        use_container_width=True,
        key=f"editor_{total_required}"
    )

# ==========================================
# 8. 결과 출력 대시보드
# ==========================================
st.markdown("---")

run_match = False
if auto_balance and df_input is not None:
    run_match = True
else:
    if st.button("🚀 팀 밸런스 매칭 실행", type="primary"):
        run_match = True

if run_match and df_input is not None:
    teams, avgs = balance_multi_teams(df_input, num_teams, team_size, cur_weight)
    
    if teams:
        st.markdown("### 📊 밸런스 매칭 결과")
        
        # 요약 메트릭
        max_diff = max(avgs) - min(avgs)
        col1, col2, col3 = st.columns(3)
        col1.metric("총 인원", f"{total_required}명 ({num_teams}팀)")
        col2.metric("평균 평점", f"{sum(avgs)/len(avgs):.1f} pts")
        col3.metric("팀 간 격차", f"{max_diff:.1f} pts")
        
        st.write("")
        
        # 팀별 카드 출력
        cols = st.columns(num_teams)
        team_colors = ["#2563EB", "#16A34A", "#D97706", "#7C3AED", "#DB2777", "#0D9488"]
        team_names = ["A TEAM", "B TEAM", "C TEAM", "D TEAM", "E TEAM", "F TEAM"]
        
        for i, col in enumerate(cols):
            with col:
                t_color = team_colors[i % len(team_colors)]
                t_name = team_names[i] if i < len(team_names) else f"TEAM {i+1}"
                
                st.markdown(f"""
                <div style="background-color: {('#161B22' if dark_mode else '#FFFFFF')}; border-top: 3px solid {t_color}; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; border-left: 1px solid {('#30363D' if dark_mode else '#E2E8F0')}; border-right: 1px solid {('#30363D' if dark_mode else '#E2E8F0')}; border-bottom: 1px solid {('#30363D' if dark_mode else '#E2E8F0')};">
                    <span style="font-weight: 700; font-size: 0.9rem;">{t_name}</span>
                    <span style="float: right; font-weight: 600; color: {t_color}; font-size: 0.8rem;">Avg {avgs[i]:.1f}</span>
                </div>
                """, unsafe_allow_html=True)
                
                df_t = pd.DataFrame(teams[i])[['닉네임', '현재티어', '최고티어', 'MMR']]
                df_t['MMR'] = df_t['MMR'].round(1)
                st.dataframe(df_t, use_container_width=True, hide_index=True)
