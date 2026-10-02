import time
import random
import pandas as pd
import streamlit as st

# ==========================================
# 1. 페이지 레이아웃 설정 (기본 화이트 모드)
# ==========================================
st.set_page_config(
    page_title="Team Balancer Pro",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==========================================
# 2. VCT 레퍼런스 스타일 대진표 & 테마 CSS
# ==========================================
def inject_theme_css(is_dark):
    if is_dark:
        bg_color = "#0E1117"
        sidebar_bg = "#161B22"
        card_bg = "#161B22"
        border_color = "#30363D"
        text_color = "#E6EDF3"
        input_bg = "#21262D"
        accent_btn = "#238636"
        accent_btn_hover = "#2ea043"
        vct_box_bg = "#111620"
        team_box_bg = "#21262D"
    else:
        bg_color = "#F8FAFC"
        sidebar_bg = "#F1F5F9"
        card_bg = "#FFFFFF"
        border_color = "#E2E8F0"
        text_color = "#0F172A"
        input_bg = "#FFFFFF"
        accent_btn = "#2563EB"
        accent_btn_hover = "#1D4ED8"
        vct_box_bg = "#F1F5F9"
        team_box_bg = "#E2D929"  # VCT 참고 이미지 골드/베이지 톤

    st.markdown(f"""
    <style>
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        
        html, body, [class*="css"] {{
            font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
            background-color: {bg_color} !important;
            color: {text_color} !important;
            font-size: 13.5px !important;
        }}

        .stApp {{
            background-color: {bg_color} !important;
        }}

        [data-testid="stSidebar"] {{
            background-color: {sidebar_bg} !important;
            border-right: 1px solid {border_color};
        }}
        [data-testid="stSidebar"] * {{
            color: {text_color} !important;
        }}

        .main .block-container {{
            padding-top: 1rem;
            padding-bottom: 2rem;
            max-width: 1100px;
        }}

        .header-card {{
            background-color: {card_bg};
            border: 1px solid {border_color};
            border-radius: 10px;
            padding: 14px 20px;
            margin-bottom: 16px;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
        }}

        .vct-bracket-container {{
            background-color: {vct_box_bg};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 20px;
        }}

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
        }}
        .stButton > button:hover {{
            background-color: {accent_btn_hover} !important;
        }}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 3. 사이드바 설정 (기본 화이트모드)
# ==========================================
st.sidebar.markdown("### 🎨 화면 설정")
dark_mode = st.sidebar.toggle("🌙 다크 모드", value=False)
inject_theme_css(dark_mode)

st.sidebar.markdown("---")
st.sidebar.markdown("### ⚙️ 매칭 설정")
num_teams = st.sidebar.number_input("팀 개수 (3팀~8팀 지원)", min_value=2, max_value=8, value=4, step=1)
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
        st.error("구글 시트를 불러오지 못했습니다. 링크 공유 설정(뷰어 접근)을 확인하세요.")
        return None

# ==========================================
# 6. 밸런싱 알고리즘
# ==========================================
def balance_multi_teams(df, num_teams, team_size=5, cur_weight=0.6):
    players = df.to_dict('records')
    total_required = num_teams * team_size
    
    if len(players) < total_required:
        st.warning(f"⚠️ 인원이 부족합니다! 최소 {total_required}명이 필요합니다. (현재: {len(players)}명)")
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
    <h2 style="margin: 0; font-size: 1.3rem; font-weight: 700;">🏆 VCT STYLE TOURNAMENT & BALANCER</h2>
    <p style="margin: 3px 0 0 0; font-size: 0.8rem; opacity: 0.75;">다단계 토너먼트 자동 연동 브래킷 • 부전승(BYE) 지원 • 포인트 자동 정산</p>
</div>
""", unsafe_allow_html=True)

input_tab1, input_tab2 = st.tabs(["🔗 Google Sheets 연동", "✏️ 직접 명단 입력"])
df_input = None

with input_tab1:
    sheet_url = st.text_input("구글 시트 공유 URL 입력", placeholder="https://docs.google.com/spreadsheets/d/...")
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
# 8. 팀 매칭 및 멀티 라운드 토너먼트 브래킷
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
        team_names_list = [f"TEAM {chr(65+i)}" for i in range(num_teams)]
        
        st.markdown("### 📊 밸런스 매칭 결과 및 팀원 구성")
        cols = st.columns(num_teams)
        team_colors = ["#2563EB", "#16A34A", "#D97706", "#7C3AED", "#DB2777", "#0D9488", "#2563EB", "#16A34A"]
        
        for i, col in enumerate(cols):
            with col:
                t_color = team_colors[i % len(team_colors)]
                st.markdown(f"""
                <div style="background-color: {('#161B22' if dark_mode else '#FFFFFF')}; border-top: 3px solid {t_color}; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; border-left: 1px solid {('#30363D' if dark_mode else '#E2E8F0')}; border-right: 1px solid {('#30363D' if dark_mode else '#E2E8F0')}; border-bottom: 1px solid {('#30363D' if dark_mode else '#E2E8F0')};">
                    <span style="font-weight: 700; font-size: 0.9rem;">{team_names_list[i]}</span>
                    <span style="float: right; font-weight: 600; color: {t_color}; font-size: 0.8rem;">Avg {avgs[i]:.1f}</span>
                </div>
                """, unsafe_allow_html=True)
                
                df_t = pd.DataFrame(teams[i])[['닉네임', '현재티어', '최고티어', 'MMR']]
                df_t['MMR'] = df_t['MMR'].round(1)
                st.dataframe(df_t, use_container_width=True, hide_index=True)

        # ==========================================
        # 9. 동적 토너먼트 브래킷 (팀 수에 따른 자동 라운드 확장)
        # ==========================================
        st.markdown("---")
        st.markdown("### 🏆 다단계 토너먼트 대진표 (자동 승자 연동)")
        st.info("💡 각 라운드 경기 스코어를 입력하면, 승리한 팀들이 자동으로 다음 라운드(준결승 및 결승) 매치업으로 진출합니다[cite: 14].")

        all_match_records = []
        
        st.markdown('<div class="vct-bracket-container">', unsafe_allow_html=True)
        
        # [단계 1] 8팀 / 6팀 / 5팀 등의 1라운드(Quarterfinals 또는 Prelims) 생성
        current_round_teams = list(team_names_list)
        
        # 홀수 팀일 경우 첫 번째 팀 부전승 처리 안내
        round_idx = 1
        r_results = []
        
        while len(current_round_teams) > 2:
            st.markdown(f"<h4 style='margin-top:10px; font-size:1rem; font-weight:700;'>🔹 Round {round_idx} (예선 / 준준결승)</h4>", unsafe_allow_html=True)
            
            next_round_winners = []
            matches_in_this_round = []
            
            i = 0
            while i < len(current_round_teams) - 1:
                t1 = current_round_teams[i]
                t2 = current_round_teams[i+1]
                match_name = f"R{round_idx} - MATCH {i//2 + 1}"
                
                st.markdown(f"<p style='font-size: 0.75rem; font-weight: 700; color: #888; margin-bottom: 2px;'>{match_name}</p>", unsafe_allow_html=True)
                c1, c2, c3 = st.columns([5, 1.5, 1.5])
                with c1:
                    st.markdown(f"""
                    <div style="background-color: {'#21262D' if dark_mode else '#E2D929'}; color: {'#E6EDF3' if dark_mode else '#111111'}; padding: 6px 10px; border-radius: 6px; font-weight: 700; margin-bottom: 3px; font-size:12px;">
                        1P: {t1}
                    </div>
                    <div style="background-color: {'#21262D' if dark_mode else '#E2D929'}; color: {'#E6EDF3' if dark_mode else '#111111'}; padding: 6px 10px; border-radius: 6px; font-weight: 700; font-size:12px;">
                        2P: {t2}
                    </div>
                    """, unsafe_allow_html=True)
                with c2:
                    s1 = st.number_input("1P 승수", min_value=0, max_value=5, value=0, key=f"r{round_idx}_s1_{i}")
                    s2 = st.number_input("2P 승수", min_value=0, max_value=5, value=0, key=f"r{round_idx}_s2_{i}")
                with c3:
                    t_games = st.number_input("총 경기", min_value=0, max_value=7, value=1, key=f"r{round_idx}_tg_{i}")
                
                st.markdown("<hr style='margin: 8px 0; border-color: rgba(150,150,150,0.15);'>", unsafe_allow_html=True)
                
                winner = t1 if s1 >= s2 else t2
                next_round_winners.append(winner)
                
                matches_in_this_round.append({
                    "match_id": match_name,
                    "team1": t1, "s1": s1,
                    "team2": t2, "s2": s2,
                    "total_games": t_games
                })
                i += 2

            # 홀수 남은 팀 처리 (자동 부전승 진출)
            if i < len(current_round_teams):
                loner = current_round_teams[i]
                next_round_winners.append(loner)
                st.info(f"⭐ **{loner}** 팀은 이번 라운드 부전승으로 다음 라운드에 직행합니다!")

            all_match_records.extend(matches_in_this_round)
            current_round_teams = next_round_winners
            round_idx += 1

        # [단계 2] 최종 결승전(Finals) 매치 생성 (남은 2팀 대결)
        st.markdown(f"<h4 style='margin-top:20px; font-size:1rem; font-weight:700;'>🔥 FINALS (결승전 - 이전 라운드 승자 자동 연동)</h4>", unsafe_allow_html=True)
        
        final_matches = []
        if len(current_round_teams) == 2:
            ft1 = current_round_teams[0]
            ft2 = current_round_teams[1]
            match_name = "MATCH FINAL"
            
            st.markdown(f"<p style='font-size: 0.75rem; font-weight: 700; color: #888; margin-bottom: 2px;'>{match_name}</p>", unsafe_allow_html=True)
            fc1, fc2, fc3 = st.columns([5, 1.5, 1.5])
            with fc1:
                st.markdown(f"""
                <div style="background-color: {'#21262D' if dark_mode else '#E2D929'}; color: {'#E6EDF3' if dark_mode else '#111111'}; padding: 6px 10px; border-radius: 6px; font-weight: 700; margin-bottom: 3px; font-size:12px;">
                    1P (승자 진출): {ft1}
                </div>
                <div style="background-color: {'#21262D' if dark_mode else '#E2D929'}; color: {'#E6EDF3' if dark_mode else '#111111'}; padding: 6px 10px; border-radius: 6px; font-weight: 700; font-size:12px;">
                    2P (승자 진출): {ft2}
                </div>
                """, unsafe_allow_html=True)
            with fc2:
                fs1 = st.number_input("결승 1P 승수", min_value=0, max_value=5, value=0, key="final_s1")
                fs2 = st.number_input("결승 2P 승수", min_value=0, max_value=5, value=0, key="final_s2")
            with fc3:
                ft_games = st.number_input("결승 총 경기", min_value=0, max_value=7, value=1, key="final_tg")
            
            final_matches.append({
                "match_id": match_name,
                "team1": ft1, "s1": fs1,
                "team2": ft2, "s2": fs2,
                "total_games": ft_games
            })
        elif len(current_round_teams) == 1:
            st.success(f"🏆 최종 우승 팀: **{current_round_teams[0]}** (추가 매치업 없음)")
        
        all_match_records.extend(final_matches)
        st.markdown('</div>', unsafe_allow_html=True)

        # ==========================================
        # 10. 포인트 정산 시스템 (모든 라운드 전적 누적)
        # ==========================================
        st.markdown("---")
        st.markdown("### 💰 포인트 지급 정산 결과")
        st.markdown("규정: **참여한 경기 수(전) × 150 포인트 + 승리 횟수(승) × 70 포인트** 자동 계산")

        if st.button("🎁 포인트 계산 및 정산 실행", type="primary"):
            player_stats = {}
            for p_list in teams:
                for p in p_list:
                    player_stats[p['닉네임']] = {"total_games": 0, "total_wins": 0}

            team_map = {team_names_list[i]: teams[i] for i in range(num_teams)}

            for r in all_match_records:
                b_team, b_wins = r["team1"], int(r["s1"])
                r_team, r_wins = r["team2"], int(r["s2"])
                tg = int(r["total_games"])

                if b_team in team_map:
                    for p in team_map[b_team]:
                        player_stats[p['닉네임']]["total_games"] += tg
                        player_stats[p['닉네임']]["total_wins"] += b_wins
                if r_team in team_map:
                    for p in team_map[r_team]:
                        player_stats[p['닉네임']]["total_games"] += tg
                        player_stats[p['닉네임']]["total_wins"] += r_wins

            result_data = []
            for nick, stat in player_stats.items():
                earned_pts = (stat["total_games"] * 150) + (stat["total_wins"] * 70)
                result_data.append({
                    "닉네임": nick,
                    "총 참여 경기 (전)": stat["total_games"],
                    "총 승리 횟수 (승)": stat["total_wins"],
                    "지급 포인트 (PT)": earned_pts
                })

            df_points = pd.DataFrame(result_data)
            st.success("✅ 토너먼트 전체 라운드 연동 및 포인트 정산이 완료되었습니다!")
            st.dataframe(df_points, use_container_width=True, hide_index=True)
