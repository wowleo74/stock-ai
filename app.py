import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import os

# --- 1. 앱 설정 및 스타일 ---
st.set_page_config(page_title="Leo의 AI 주식 비서", layout="wide")

st.markdown("""
    <style>
    .signal-container { display: flex; justify-content: space-around; margin-bottom: 20px; gap: 10px; }
    .signal-box { flex: 1; padding: 15px; border-radius: 10px; text-align: center; font-weight: bold; color: #bdc3c7; background-color: #f8f9fa; border: 1px solid #dee2e6; font-size: 1.1rem; }
    .active-strong-buy { background-color: #1b5e20 !important; color: white !important; border: 3px solid #4caf50 !important; }
    .active-buy { background-color: #4caf50 !important; color: white !important; border: 3px solid #81c784 !important; }
    .active-hold { background-color: #ff9800 !important; color: white !important; border: 3px solid #ffb74d !important; }
    .active-sell { background-color: #f44336 !important; color: white !important; border: 3px solid #ef5350 !important; }
    .active-strong-sell { background-color: #b71c1c !important; color: white !important; border: 3px solid #d32f2f !important; }
    .strategy-card { padding: 15px; border-radius: 8px; border-left: 5px solid #3498db; background-color: #ffffff; margin-bottom: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); min-height: 110px; }
    .indicator-label { font-weight: bold; font-size: 1.1rem; color: #2c3e50; }
    .indicator-opinion { font-weight: bold; font-size: 1.1rem; margin-left: 5px; }
    .indicator-reason { font-size: 0.9rem; color: #7f8c8d; margin-top: 8px; line-height: 1.4; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 로드 (CSV 파일 읽기) ---
@st.cache_data
def load_stock_list():
    if os.path.exists('krx_stocks.csv'):
        df = pd.read_csv('krx_stocks.csv')
        # 코드를 6자리 문자열로 변환 (005930 등)
        df['Code'] = df['Code'].astype(str).str.zfill(6)
        # 검색용 이름 생성: "삼성전자 (005930)"
        df['Display'] = df['Name'] + " (" + df['Code'] + ")"
        return df
    else:
        # 파일이 없을 경우를 대비한 최소한의 리스트
        return pd.DataFrame({'Code':['005930'], 'Name':['삼성전자'], 'Market':['KOSPI'], 'Display':['삼성전자 (005930)']})

df_krx = load_stock_list()

# 세션 상태 초기화
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["삼성전자 (005930)", "SK하이닉스 (000660)", "현대차 (005380)"]
if 'current_selection' not in st.session_state:
    st.session_state.current_selection = "삼성전자 (005930)"

# --- 3. 사이드바 구성 ---
with st.sidebar:
    st.header("⭐ 관심종목 리스트")
    # 1. 관심종목 바로가기
    selected_watch = st.selectbox("내 관심종목 바로가기", options=st.session_state.watchlist)
    
    if st.button("🚀 바로 분석", use_container_width=True):
        st.session_state.current_selection = selected_watch
        st.rerun()

    st.divider()
    st.header("🔍 전 종목 검색")
    # 2. 모든 종목 자동완성 검색창
    all_names = df_krx['Display'].tolist()
    # 현재 선택된 종목이 리스트에 있으면 해당 인덱스, 없으면 0번
    try:
        current_idx = all_names.index(st.session_state.current_selection)
    except:
        current_idx = 0
        
    search_stock = st.selectbox("회사명 검색", options=all_names, index=current_idx)
    
    # 추가/삭제 버튼
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⭐ 추가"):
            if search_stock not in st.session_state.watchlist:
                st.session_state.watchlist.append(search_stock)
                st.rerun()
    with col2:
        if st.button("🗑️ 삭제"):
            if search_stock in st.session_state.watchlist and len(st.session_state.watchlist) > 1:
                st.session_state.watchlist.remove(search_stock)
                st.session_state.current_selection = st.session_state.watchlist[0]
                st.rerun()

    # 분석용 티커 추출
    st.session_state.current_selection = search_stock
    stock_info = df_krx[df_krx['Display'] == search_stock].iloc[0]
    raw_code = stock_info['Code']
    ticker = f"{raw_code}.KS" if stock_info['Market'] == 'KOSPI' else f"{raw_code}.KQ"
    display_name = stock_info['Name']

    st.divider()
    st.subheader("💡 분석 옵션")
    use_ma = st.checkbox("이동평균선", value=True)
    use_rsi = st.checkbox("RSI 심리", value=True)
    use_vol = st.checkbox("거래량 실세", value=True)
    use_bb = st.checkbox("볼린저 밴드", value=True)
    expert_mode = st.toggle("🛠️ 전문가 차트 보기", value=False)

# --- 4. 분석 엔진 ---
def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty: return None, None, None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 지표 계산
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['Vol_MA20'] = ta.sma(df['Volume'], length=20)
        bb = ta.bbands(df['Close'], length=20, std=2)
        df['BB_Upper'], df['BB_Lower'] = bb.iloc[:, 2], bb.iloc[:, 0]
        
        last, prev = df.iloc[-1], df.iloc[-2]
        results = [] 

        if use_ma:
            ma5, ma20 = float(last['MA5']), float(last['MA20'])
            results.append(("이동평균선", "매수 추천" if ma5 > ma20 else "매도 추천", "단기 상승세입니다." if ma5 > ma20 else "하락 추세입니다.", 1 if ma5 > ma20 else -1))
        if use_rsi:
            rsi_v = float(last['RSI'])
            sc = 2 if rsi_v < 35 else (-2 if rsi_v > 70 else 0)
            results.append(("RSI 심리", "강력 매수" if sc==2 else ("강력 매도" if sc==-2 else "관망"), f"지수 {rsi_v:.1f}", sc))
        if use_vol:
            ratio = (float(last['Volume']) / float(last['Vol_MA20'])) * 100
            sc = 2 if ratio > 200 and last['Close'] > prev['Close'] else (-1 if ratio < 50 else 0)
            results.append(("거래량 실세", "강력 매수" if sc==2 else "관망", f"평균 대비 {ratio:.0f}%", sc))
        if use_bb:
            p, up, lo = float(last['Close']), float(last['BB_Upper']), float(last['BB_Lower'])
            sc = 2 if p <= lo else (-2 if p >= up else 0)
            results.append(("볼린저 밴드", "강력 매수" if sc==2 else ("강력 매도" if sc==-2 else "관망"), "밴드 하단 이탈" if sc==2 else "안정적", sc))

        avg_score = sum(r[3] for r in results) / len(results) if results else 0
        final = "강력 매수" if avg_score >= 1.2 else ("매수 추천" if avg_score >= 0.4 else ("강력 매도" if avg_score <= -1.2 else ("매도" if avg_score <= -0.4 else "관망")))
        return df, results, final
    except: return None, None, None

# --- 5. 메인 화면 ---
st.title(f"🚦 AI 전략 리포트: {display_name}")

df, indicators, final_status = analyze_stock(ticker)

if df is not None:
    # 신호등 UI
    signals = ["강력 매도", "매도", "관망", "매수 추천", "강력 매수"]
    cmap = {"강력 매수":"active-strong-buy", "매수 추천":"active-buy", "관망":"active-hold", "매도":"active-sell", "강력 매도":"active-strong-sell"}
    boxes = "".join([f'<div class="signal-box {cmap[s] if s==final_status else ""}">{s}</div>' for s in signals])
    st.markdown(f'<div class="signal-container">{boxes}</div>', unsafe_allow_html=True)
    
    st.subheader("📝 상세 분석")
    cols = st.columns(len(indicators))
    for i, (name, opinion, reason, score) in enumerate(indicators):
        color = "#2e7d32" if "매수" in opinion else ("#c62828" if "매도" in opinion else "#ef6c00")
        with cols[i]:
            st.markdown(f'<div class="strategy-card"><span class="indicator-label">{name}</span><span class="indicator-opinion" style="color: {color};">[{opinion}]</span><div class="indicator-reason">{reason}</div></div>', unsafe_allow_html=True)

    if expert_mode:
        st.divider()
        st.subheader("📊 기술적 차트")
        st.line_chart(df[['Close', 'BB_Upper', 'BB_Lower']] if use_bb else df[['Close', 'MA5', 'MA20']])
else:
    st.error("데이터 로딩 실패. 종목 코드를 확인해 주세요.")
