import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import os

# --- 1. 앱 설정 및 모바일 최적화 스타일 ---
st.set_page_config(page_title="Leo의 AI 주식 비서", layout="wide")

st.markdown("""
    <style>
    /* 신호등 컨테이너: 모바일에서 자동 줄바꿈 */
    .signal-container { 
        display: flex; 
        flex-wrap: wrap; 
        justify-content: center; 
        gap: 8px; 
        margin-bottom: 25px; 
    }
    .signal-box { 
        flex: 1 1 100px; /* 화면 좁으면 줄바꿈, 최소 100px 유지 */
        padding: 12px 8px; 
        border-radius: 12px; 
        text-align: center; 
        font-weight: bold; 
        color: #95a5a6; 
        background-color: #f1f3f5; 
        border: 1px solid #e9ecef; 
        font-size: 0.9rem; 
    }
    .active-strong-buy { background-color: #2b8a3e !important; color: white !important; border: 2px solid #51cf66 !important; }
    .active-buy { background-color: #5c940d !important; color: white !important; border: 2px solid #94d82d !important; }
    .active-hold { background-color: #f08c00 !important; color: white !important; border: 2px solid #ffc078 !important; }
    .active-sell { background-color: #e03131 !important; color: white !important; border: 2px solid #ff8787 !important; }
    .active-strong-sell { background-color: #c92a2a !important; color: white !important; border: 2px solid #ffa8a8 !important; }

    /* 상세 분석 카드: 세로 정렬 최적화 */
    .strategy-card { 
        padding: 18px; 
        border-radius: 15px; 
        border-left: 6px solid #228be6; 
        background-color: #ffffff; 
        margin-bottom: 15px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); 
    }
    .indicator-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .indicator-label { font-weight: bold; font-size: 1.1rem; color: #343a40; }
    .indicator-opinion { font-weight: bold; font-size: 1rem; }
    .indicator-reason { font-size: 0.95rem; color: #495057; line-height: 1.5; }
    
    /* 모바일에서 폰트 크기 조정 */
    @media (max-width: 600px) {
        .stTitle { font-size: 1.5rem !important; }
        .indicator-label { font-size: 1rem; }
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 로드 (기존 CSV 로직 유지) ---
@st.cache_data
def load_stock_list():
    if os.path.exists('krx_stocks.csv'):
        df = pd.read_csv('krx_stocks.csv')
        df['Code'] = df['Code'].astype(str).str.zfill(6)
        df['Display'] = df['Name'] + " (" + df['Code'] + ")"
        return df
    return pd.DataFrame({'Code':['005930'], 'Name':['삼성전자'], 'Market':['KOSPI'], 'Display':['삼성전자 (005930)']})

df_krx = load_stock_list()

if 'watchlist' not in st.session_state:
    st.session_state.watchlist = ["삼성전자 (005930)", "SK하이닉스 (000660)", "현대차 (005380)"]
if 'current_selection' not in st.session_state:
    st.session_state.current_selection = "삼성전자 (005930)"

# --- 3. 사이드바 ---
with st.sidebar:
    st.header("⭐ 관심종목")
    selected_watch = st.selectbox("리스트에서 선택", options=st.session_state.watchlist)
    
    if st.button("🚀 분석 실행", use_container_width=True):
        st.session_state.current_selection = selected_watch
        st.rerun()

    st.divider()
    st.header("🔍 종목 검색")
    all_names = df_krx['Display'].tolist()
    search_stock = st.selectbox("이름으로 검색", options=all_names, 
                                index=all_names.index(st.session_state.current_selection) if st.session_state.current_selection in all_names else 0)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("⭐ 추가", use_container_width=True):
            if search_stock not in st.session_state.watchlist:
                st.session_state.watchlist.append(search_stock)
                st.rerun()
    with col2:
        if st.button("🗑️ 삭제", use_container_width=True):
            if search_stock in st.session_state.watchlist and len(st.session_state.watchlist) > 1:
                st.session_state.watchlist.remove(search_stock)
                st.session_state.current_selection = st.session_state.watchlist[0]
                st.rerun()

    st.session_state.current_selection = search_stock
    stock_info = df_krx[df_krx['Display'] == search_stock].iloc[0]
    ticker = f"{stock_info['Code']}.KS" if stock_info['Market'] == 'KOSPI' else f"{stock_info['Code']}.KQ"
    display_name = stock_info['Name']

# --- 4. 분석 엔진 ---
def analyze_stock(symbol):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty: return None, None, None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA20'] = ta.sma(df['Close'], length=20)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['Vol_MA20'] = ta.sma(df['Volume'], length=20)
        bb = ta.bbands(df['Close'], length=20, std=2)
        df['BB_Upper'], df['BB_Lower'] = bb.iloc[:, 2], bb.iloc[:, 0]
        
        last, prev = df.iloc[-1], df.iloc[-2]
        results = [] 
        
        # 지표별 점수 계산
        ma5, ma20 = float(last['MA5']), float(last['MA20'])
        results.append(("이동평균선", "매수 추천" if ma5 > ma20 else "매도 추천", "단기 상승세입니다." if ma5 > ma20 else "하강 추세입니다.", 1 if ma5 > ma20 else -1))
        
        rsi_v = float(last['RSI'])
        sc_rsi = 2 if rsi_v < 35 else (-2 if rsi_v > 70 else 0)
        results.append(("RSI 심리", "강력 매수" if sc_rsi==2 else ("강력 매도" if sc_rsi==-2 else "안정적"), f"지수 {rsi_v:.1f}로 {'저평가' if sc_rsi==2 else ('과열' if sc_rsi==-2 else '안정')} 상태", sc_rsi))
        
        ratio = (float(last['Volume']) / float(last['Vol_MA20'])) * 100
        sc_vol = 2 if ratio > 200 and last['Close'] > prev['Close'] else (-1 if ratio < 50 else 0)
        results.append(("거래량", "관심 집중" if sc_vol==2 else "소외 상태", f"평소 대비 {ratio:.0f}% 수준", sc_vol))
        
        p, up, lo = float(last['Close']), float(last['BB_Upper']), float(last['BB_Lower'])
        sc_bb = 2 if p <= lo else (-2 if p >= up else 0)
        results.append(("볼린저밴드", "바닥권" if sc_bb==2 else ("천장권" if sc_bb==-2 else "정상범위"), "밴드 하단 근접" if sc_bb==2 else "안정적", sc_bb))

        avg_score = sum(r[3] for r in results) / len(results)
        final = "강력 매수" if avg_score >= 1.2 else ("매수 추천" if avg_score >= 0.4 else ("강력 매도" if avg_score <= -1.2 else ("매도" if avg_score <= -0.4 else "관망")))
        return df, results, final
    except: return None, None, None

# --- 5. 메인 화면 ---
st.title(f"🚦 AI 전략: {display_name}")

df, indicators, final_status = analyze_stock(ticker)

if df is not None:
    # 1. 신호등 섹션
    signals = ["강력 매도", "매도", "관망", "매수 추천", "강력 매수"]
    cmap = {"강력 매수":"active-strong-buy", "매수 추천":"active-buy", "관망":"active-hold", "매도":"active-sell", "강력 매도":"active-strong-sell"}
    boxes = "".join([f'<div class="signal-box {cmap[s] if s==final_status else ""}">{s}</div>' for s in signals])
    st.markdown(f'<div class="signal-container">{boxes}</div>', unsafe_allow_html=True)
    
    # 2. 상세 카드 섹션 (모바일 최적화 세로 배치)
    st.subheader("📝 AI 분석 코멘트")
    for name, opinion, reason, score in indicators:
        color = "#2b8a3e" if "매수" in opinion or "바닥" in opinion else ("#e03131" if "매도" in opinion or "천장" in opinion else "#f08c00")
        st.markdown(f"""
            <div class="strategy-card">
                <div class="indicator-header">
                    <span class="indicator-label">{name}</span>
                    <span class="indicator-opinion" style="color: {color};">[{opinion}]</span>
                </div>
                <div class="indicator-reason">{reason}</div>
            </div>
            """, unsafe_allow_html=True)

    # 3. 차트 섹션
    with st.expander("📊 기술적 차트 보기"):
        st.line_chart(df[['Close', 'MA5', 'MA20']])
        st.bar_chart(df['Volume'])
else:
    st.error("데이터를 불러오지 못했습니다.")
