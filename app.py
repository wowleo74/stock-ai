import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr

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

# --- 2. 데이터 로드 및 세션 관리 ---
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["삼성전자 (KOSPI)", "SK하이닉스 (KOSPI)", "현대차 (KOSPI)"]

@st.cache_data
def get_all_stock_data():
    df = fdr.StockListing('KRX')
    if 'Code' in df.columns: df = df.rename(columns={'Code': 'Symbol'})
    df['Display'] = df['Name'] + " (" + df['Market'] + ")"
    return df

# --- 3. 사이드바 구성 ---
with st.sidebar:
    st.header("⭐ 관심종목 리스트")
    # 관심종목 선택기
    selected_watchlist = st.selectbox("내 관심종목 바로가기", options=st.session_state.watchlist)
    
    st.divider()
    st.header("🔍 새 종목 검색")
    df_all = get_all_stock_data()
    all_names = df_all['Display'].tolist()
    
    # 관심종목에서 선택한 게 있으면 그걸 검색창 기본값으로 설정
    default_idx = all_names.index(selected_watchlist) if selected_watchlist in all_names else 0
    search_stock = st.selectbox("종목 찾기", options=all_names, index=default_idx)
    
    # 관심종목 추가/삭제 버튼
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⭐ 추가"):
            if search_stock not in st.session_state.watchlist:
                st.session_state.watchlist.append(search_stock)
                st.rerun()
    with col2:
        if st.button("🗑️ 삭제"):
            if search_stock in st.session_state.watchlist:
                st.session_state.watchlist.remove(search_stock)
                st.rerun()

    st.divider()
    st.subheader("💡 분석 옵션")
    use_ma = st.checkbox("방법 A: 이동평균선", value=True)
    use_rsi = st.checkbox("방법 B: RSI 심리", value=True)
    use_vol = st.checkbox("방법 C: 거래량 실세", value=True)
    use_bb = st.checkbox("방법 D: 볼린저 밴드", value=True)
    expert_mode = st.toggle("🛠️ 전문가 데이터 보기", value=False)

    stock_info = df_all[df_all['Display'] == search_stock].iloc[0]
    ticker = f"{stock_info['Symbol']}{'.KQ' if 'KOSDAQ' in stock_info['Market'].upper() else '.KS'}"
    display_name = stock_info['Name']

# --- 4. 분석 엔진 ---
def analyze_stock(symbol, use_ma, use_rsi, use_vol, use_bb):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty: return None, None, None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
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
            results.append(("이동평균선", "매수 추천" if ma5 > ma20 else "매도 추천", f"5일선({ma5:,.0f})이 20일선 위에 있어 상승 추세입니다." if ma5 > ma20 else "하락 추세입니다.", 1 if ma5 > ma20 else -1))
        if use_rsi:
            rsi_v = float(last['RSI'])
            sc = 2 if rsi_v < 35 else (-2 if rsi_v > 70 else 0)
            results.append(("RSI 심리", "강력 매수" if sc==2 else ("강력 매도" if sc==-2 else "관망"), f"RSI가 {rsi_v:.1f}로 {'바닥권' if sc==2 else ('과열권' if sc==-2 else '안정적')}입니다.", sc))
        if use_vol:
            ratio = (float(last['Volume']) / float(last['Vol_MA20'])) * 100
            sc = 2 if ratio > 200 and last['Close'] > prev['Close'] else (-1 if ratio < 50 else 0)
            results.append(("거래량 실세", "강력 매수" if sc==2 else "관망", f"거래량이 평소 대비 {ratio:.0f}% 수준입니다.", sc))
        if use_bb:
            p, up, lo = float(last['Close']), float(last['BB_Upper']), float(last['BB_Lower'])
            sc = 2 if p <= lo else (-2 if p >= up else 0)
            results.append(("볼린저 밴드", "강력 매수" if sc==2 else ("강력 매도" if sc==-2 else "관망"), f"주가가 밴드 {'하단' if sc==2 else ('상단' if sc==-2 else '내부')}에 위치합니다.", sc))

        avg_score = sum(r[3] for r in results) / len(results) if results else 0
        final = "강력 매수" if avg_score >= 1.2 else ("매수 추천" if avg_score >= 0.4 else ("강력 매도" if avg_score <= -1.2 else ("매도" if avg_score <= -0.4 else "관망")))
        return None, df, results, final
    except Exception as e: return str(e), None, None, None

# --- 5. 메인 화면 ---
st.title(f"🚦 AI 전략 리포트: {display_name}")

err, df, indicators, final_status = analyze_stock(ticker, use_ma, use_rsi, use_vol, use_bb)

if df is not None:
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
        st.subheader("📊 기술적 분석 차트")
        st.line_chart(df[['Close', 'BB_Upper', 'BB_Lower']] if use_bb else df[['Close', 'MA5', 'MA20']])
        if use_vol: st.bar_chart(df['Volume'])
else:
    st.error(f"분석 중 오류: {err}")