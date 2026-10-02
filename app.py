import time
import random
import pandas as pd
import streamlit as st

# ==========================================
# 1. 페이지 및 티어 점수 설정
# ==========================================
st.set_page_config(
    page_title="발로란트 내전 팀 밸런서",
    page_icon="⚔️",
    layout="wide"
)

# 기본 티어 점수 매핑
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
    # 약어 표현 지원
    "플래 1": 1300, "플래 2": 1400, "플래 3": 1500,
    "다이아 1": 1600, "다이아 2": 1700, "다이아 3": 1800,
}

# 띄어쓰기 무시 정규화
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
    
    cur_total = cur_base + cur_rr_val
    peak_total = peak_base + peak_rr_val
    
    return (cur_total * cur_weight) + (peak_total * (1 - cur_weight))

# ==========================================
# 2. 구글 시트 연동
# ==========================================
REQUIRED_HEADERS = ["닉네임", "현재티어", "현재RR", "최고티어", "최고RR"]

def load_data_from_google_sheet(url):
    try:
        if "docs.google.com/spreadsheets/d/" in url:
            sheet_id = url.split("/d/")[1].split("/")[0]
        else:
            sheet_id = url.strip()
            
        csv_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&_t={int(time.time())}"
        df = pd.read_csv(csv_url)
        
        # 헤더 띄어쓰기 정규화
        df.columns = [str(col).replace(" ", "").strip() for col in df.columns]
        
        missing_headers = [h for h in REQUIRED_HEADERS if h not in df.columns]
        if missing_headers:
            st.error("❌ 구글 시트 1행 헤더 규칙이 맞지 않습니다!")
            st.warning(f"누락/오타 항목: **{', '.join(missing_headers)}**")
            st.info("💡 1행 헤더 규칙: `닉네임 | 현재티어 | 현재RR | 최고티어 | 최고RR` 순서대로 입력했는지 확인해주세요.")
            return None
            
        return df
    except Exception as e:
        st.error("구글 시트를 불러오지 못했습니다. 공유 설정('링크가 있는 모든 사용자')을 확인해 주세요.")
        return None

# ==========================================
# 3. 팀 밸런싱 알고리즘
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

    def team_avg(team):
        return sum(p['MMR'] for p in team) / len(team) if team else 0

    def calc_variance(teams_list):
        avgs = [team_avg(t) for t in teams_list]
        mean_avg = sum(avgs) / len(avgs)
        return sum((a - mean_avg) ** 2 for a in avgs)

    best_variance = calc_variance(teams)
    
    for _ in range(1000):
        t1, t2 = random.sample(range(num_teams), 2)
        idx1, idx2 = random.randint(0, team_size - 1), random.randint(0, team_size - 1)
        
        teams[t1][idx1], teams[t2][idx2] = teams[t2][idx2], teams[t1][idx1]
        new_var = calc_variance(teams)
        
        if new_var < best_variance:
            best_variance = new_var
        else:
            teams[t1][idx1], teams[t2][idx2] = teams[t2][idx2], teams[t1][idx1]

    return teams, [team_avg(t) for t in teams]

# ==========================================
# 4. UI 구성 및 자동 로드 처리
# ==========================================
st.title("⚔️ 발로란트 내전 팀 밸런서")
st.caption("구글 시트 URL 연동 또는 직접 입력으로 발로란트 팀 밸런스를 맞춥니다.")

# 사이드바 설정
st.sidebar.header("⚙️ 내전 옵션")
num_teams = st.sidebar.number_input("팀 개수", min_value=2, max_value=8, value=2, step=1)
team_size = st.sidebar.number_input("팀당 인원 수", min_value=1, max_value=5, value=5, step=1)
cur_weight_pct = st.sidebar.slider("현재 티어 반영 비중 (%)", 0, 100, 60, 5)
cur_weight = cur_weight_pct / 100.0

total_required = num_teams * team_size

auto_balance = st.sidebar.checkbox("⚡ 옵션/데이터 변경 시 팀 자동 다시 짜기", value=True)

st.sidebar.info(f"📌 **필요 총 인원**: **{total_required}명** ({num_teams}개 팀 × {team_size}명)\n📌 **1행 헤더**: 닉네임 | 현재티어 | 현재RR | 최고티어 | 최고RR")

# 입력 방식 선택
input_mode = st.radio("데이터 입력 방식을 선택하세요:", ["🔗 구글 시트 URL 연동 (자동 반영)", "✏️ 직접 입력하기"], horizontal=True)

df_input = None

if "🔗 구글 시트 URL" in input_mode:
    col_url, col_btn = st.columns([4, 1])
    with col_url:
        sheet_url = st.text_input("구글 시트 URL을 입력하세요", placeholder="https://docs.google.com/spreadsheets/d/...")
    with col_btn:
        st.write("")
        st.write("")
        refresh = st.button("🔄 시트 새로고침")

    if sheet_url:
        df_sheet = load_data_from_google_sheet(sheet_url)
        if df_sheet is not None:
            st.success(f"✅ 구글 시트 자동 연동 성공! (총 {len(df_sheet)}명 수신)")
            st.dataframe(df_sheet, use_container_width=True)
            df_input = df_sheet

else:
    # 💡 동적 행 자동 생성 (팀 수가 변경되면 인원수만큼 표 행이 자동으로 확장됩니다)
    sample_tiers = ["레디언트", "불멸 3", "불멸 1", "초월자 2", "다이아 1", "플래티넘 3", "골드 2", "실버 1", "골드 1", "브론즈 2"]
    
    dynamic_players = {
        "닉네임": [f"선수_{i+1}" for i in range(total_required)],
        "현재티어": [sample_tiers[i % len(sample_tiers)] for i in range(total_required)],
        "현재RR": [0] * total_required,
        "최고티어": [sample_tiers[i % len(sample_tiers)] for i in range(total_required)],
        "최고RR": [0] * total_required
    }
    
    st.caption(f"💡 현재 설정된 팀 수에 따라 **총 {total_required}명**의 입력칸이 자동으로 준비되었습니다.")
    
    # key=f"editor_{total_required}" 로 설정하여 팀 수/인원 변경 시 표 크기가 자동 재설정됨
    df_input = st.data_editor(
        pd.DataFrame(dynamic_players),
        num_rows="dynamic",
        use_container_width=True,
        key=f"editor_{total_required}"
    )

# ==========================================
# 5. 팀 밸런스 생성 및 출력
# ==========================================
st.markdown("---")

run_balance = False
if auto_balance and df_input is not None:
    run_balance = True
else:
    if st.button("🔥 팀 밸런스 맞추기", type="primary"):
        run_balance = True

if run_balance and df_input is not None:
    teams, avgs = balance_multi_teams(df_input, num_teams, team_size, cur_weight)
    if teams:
        st.subheader("📊 팀 배정 결과")
        
        cols = st.columns(num_teams)
        team_names = ["A팀", "B팀", "C팀", "D팀", "E팀", "F팀", "G팀", "H팀"]
        
        for i, col in enumerate(cols):
            with col:
                t_name = team_names[i] if i < len(team_names) else f"팀 {i+1}"
                st.markdown(f"### 🛡️ **{t_name}**")
                st.caption(f"평균 MMR: **{avgs[i]:.1f}점**")
                
                df_t = pd.DataFrame(teams[i])[['닉네임', '현재티어', '현재RR', '최고티어', 'MMR']]
                st.dataframe(df_t, use_container_width=True)
