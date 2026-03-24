import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import os

# --- 1. 앱 설정 및 아이콘 강제 주입 ---
st.set_page_config(page_title="Leo 주식비서", page_icon="icon.png", layout="wide")

# 아이콘을 강제로 폰에 인식시키는 메타 태그 (에러 방지용 구조 수정)
st.markdown("""
    <head>
        <link rel="apple-touch-icon" href="icon.png">
        <link rel="icon" href="icon.png">
    </head>
    """, unsafe_allow_html=True)

# CSS 스타일 정의 (에러 없이 깔끔하게 분리)
st.markdown("""
    <style>
    /* 메인 선택창 스타일 */
    .main-selector { background-color: #f1f3f5; padding: 15px; border-radius: 15px; margin-bottom: 20px; }
    
    /* 가격 표시 스타일 */
    .price-container { background-color: #ffffff; padding: 15px; border-radius: 15px; text-align: center; margin-bottom: 20px; border: 1px solid #dee2e6; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    .current-price { font-size: 2.2rem; font-weight: bold; color: #212529; margin-bottom: 5px; }
    .price-delta { font-size: 1.1rem; font-weight: 500; }
    
    /* 신호등 및 카드 스타일 */
    .signal-container { display: flex; flex-wrap: wrap; justify-content: center; gap: 8px; margin-bottom: 25px; }
    .signal-box { flex: 1 1 100px; padding: 12px 8px; border-radius: 12px; text-align: center; font-weight: bold; color: #adb5bd; background-color: #f8f9fa; border: 1px solid #e9ecef; font-size: 0.9rem; }
    .active-strong-buy { background-color: #2b8a3e !important; color: white !important; border: 2px solid #51cf66 !important; }
    .active-buy { background-color: #5c940d !important; color: white !important; border: 2px solid #94d82d !important; }
    .active-hold { background-color: #f08c00 !important; color: white !important; border: 2px solid #ffc078 !important; }
    .active-sell { background-color: #e03131 !important; color: white !important; border: 2px solid #ff8787 !important; }
    .active-strong-sell { background-color: #c92a2a !important; color: white !important; border: 2px solid #ffa8a8 !important; }
    
    .strategy-card { padding: 18px; border-radius: 15px; border-left: 6px solid #228be6; background-color: #ffffff; margin-bottom: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .indicator-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
    .indicator-label { font-weight: bold; font-size: 1.1rem; color: #343a40; }
    
    @media (max-width: 600px) { .current-price { font-size: 1.8rem; } }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 로드 (이후 로직은 동일) ---
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

st.title("🚦 Leo의 AI 주식 비서")

# 관심종목 버튼
watch_cols = st.columns(len(st.session_state.watchlist))
for i, stock in enumerate(st.session_state.watchlist):
    if watch_cols[i].button(stock.split(" ")[0], key=f"btn_{i}", use_container_width=True):
        st.session_state.current_selection = stock
        st.rerun()

all_names = df_krx['Display'].tolist()
search_stock = st.selectbox("🔍 종목 검색", options=all_names, 
                            index=all_names.index(st.session_state.current_selection) if st.session_state.current_selection in all_names else 0,
                            label_visibility="collapsed")

if search_stock != st.session_state.current_selection:
    st.session_state.current_selection = search_stock
    st.rerun()

stock_info = df_krx[df_krx['Display'] == st.session_state.current_selection].iloc[0]
ticker = f"{stock_info['Code']}.KS" if stock_info['Market'] == 'KOSPI' else f"{stock_info['Code']}.KQ"
display_name = stock_info['Name']

with st.sidebar:
    st.header("⚙️ 분석 설정")
    use_ma = st.checkbox("방법 A: 이동평균선", value=True)
    use_rsi = st.checkbox("방법 B: RSI 심리", value=True)
    use_vol = st.checkbox("방법 C: 거래량 실세", value=True)
    use_bb = st.checkbox("방법 D: 볼린저 밴드", value=True)
    expert_mode = st.toggle("🛠️ 전문가 차트 보기", value=False)
    st.divider()
    if st.button("⭐ 현재 종목 관심등록", use_container_width=True):
        if st.session_state.current_selection not in st.session_state.watchlist:
            st.session_state.watchlist.append(st.session_state.current_selection)
            st.rerun()
    if st.button("🗑️ 관심종목 삭제", use_container_width=True):
        if len(st.session_state.watchlist) > 1:
            st.session_state.watchlist.remove(st.session_state.current_selection)
            st.session_state.current_selection = st.session_state.watchlist[0]
            st.rerun()

def analyze_stock(symbol, u_ma, u_rsi, u_vol, u_bb):
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
        curr_p, prev_p = float(last['Close']), float(prev['Close'])
        delta = curr_p - prev_p
        price_info = {"curr": curr_p, "delta": delta, "percent": (delta/prev_p)*100}
        results = []
        if u_ma:
            m5, m20 = float(last['MA5']), float(last['MA20'])
            results.append(("이동평균선", "매수 추천" if m5 > m20 else "매도 추천", "상승 추세" if m5 > m20 else "하락 추세", 1 if m5 > m20 else -1))
        if u_rsi:
            rv = float(last['RSI'])
            sc = 2 if rv < 35 else (-2 if rv > 70 else 0)
            results.append(("RSI 심리", "강력 매수" if sc==2 else ("강력 매도" if sc==-2 else "안정적"), f"지수 {rv:.1f}", sc))
        if u_vol:
            r = (float(last['Volume']) / float(last['Vol_MA20'])) * 100
            sc = 2 if r > 200 and curr_p > prev_p else (-1 if r < 50 else 0)
            results.append(("거래량", "관심 집중" if sc==2 else "소외 상태", f"평균의 {r:.0f}%", sc))
        if u_bb:
            p, up, lo = curr_p, float(last['BB_Upper']), float(last['BB_Lower'])
            sc = 2 if p <= lo else (-2 if p >= up else 0)
            results.append(("볼린저밴드", "바닥권" if sc==2 else ("천장권" if sc==-2 else "안정적"), "밴드 하단", sc))
        avg = sum(r[3] for r in results) / len(results) if results else 0
        final = "강력 매수" if avg >= 1.2 else ("매수 추천" if avg >= 0.4 else ("강력 매도" if avg <= -1.2 else ("매도" if avg <= -0.4 else "관망")))
        return df, results, final, price_info
    except: return None, None, None, None

df, indicators, final_status, price = analyze_stock(ticker, use_ma, use_rsi, use_vol, use_bb)

if df is not None:
    color = "#e03131" if price['delta'] > 0 else "#1971c2"
    st.markdown(f"""
        <div class="price-container">
            <div style="font-size: 1.1rem; color: #868e96; margin-bottom: 5px;">{display_name} 현재가</div>
            <div class="current-price">{price['curr']:,.0f} 원</div>
            <div class="price-delta" style="color: {color};">
                {"▲" if price['delta'] > 0 else "▼"} {abs(price['delta']):,.0f} ({price['percent']:.2f}%)
            </div>
        </div>
        """, unsafe_allow_html=True)
    signals = ["강력 매도", "매도", "관망", "매수 추천", "강력 매수"]
    cmap = {"강력 매수":"active-strong-buy", "매수 추천":"active-buy", "관망":"active-hold", "매도":"active-sell", "강력 매도":"active-strong-sell"}
    boxes = "".join([f'<div class="signal-box {cmap[s] if s==final_status else ""}">{s}</div>' for s in signals])
    st.markdown(f'<div class="signal-container">{boxes}</div>', unsafe_allow_html=True)
    for name, opinion, reason, score in indicators:
        c = "#2b8a3e" if "매수" in opinion or "바닥" in opinion else ("#e03131" if "매도" in opinion or "천장" in opinion else "#f08c00")
        st.markdown(f"""
            <div class="strategy-card">
                <div class="indicator-header">
                    <span class="indicator-label">{name}</span>
                    <span class="indicator-opinion" style="color: {c};">[{opinion}]</span>
                </div>
                <div class="indicator-reason">{reason}</div>
            </div>
            """, unsafe_allow_html=True)
    if expert_mode:
        with st.expander("📊 기술적 차트", expanded=True):
            st.line_chart(df[['Close', 'MA5', 'MA20']])
            st.bar_chart(df['Volume'])
else:
    st.error("데이터 로딩 실패")
