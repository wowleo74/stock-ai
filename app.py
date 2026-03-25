import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import os
import time
import json

# --- 1. PC 광폭 레이아웃 및 원본 스타일 설정 (전체 복구) ---
st.set_page_config(page_title="Leo 주식 수익 검증 시스템", layout="wide")

st.markdown("""
    <style>
    .report-card { padding: 20px; border-radius: 15px; background-color: #ffffff; border-left: 8px solid #228be6; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .price-large { font-size: 3.2rem; font-weight: bold; }
    .metric-title { font-size: 1rem; color: #868e96; font-weight: bold; margin-bottom: 5px; }
    .metric-value { font-size: 1.8rem; font-weight: bold; }
    .metric-container-box { background-color: #f8f9fa; padding: 15px; border-radius: 12px; border: 1px solid #e9ecef; text-align: center; margin-bottom: 10px; min-height: 80px; display: flex; flex-direction: column; justify-content: center; }
    .info-label { color: #868e96; font-size: 0.85rem; font-weight: bold; margin-bottom: 2px; }
    .info-value { color: #212529; font-size: 1.15rem; font-weight: bold; }
    .guide-box { background-color: #f8f9fa; border-radius: 10px; padding: 15px; border-left: 5px solid #adb5bd; margin-bottom: 12px; line-height: 1.6; }
    .signal-container { display: flex; justify-content: center; gap: 10px; margin: 25px 0; }
    .signal-box { flex: 1; padding: 18px; border-radius: 12px; text-align: center; font-weight: bold; color: #adb5bd; background-color: #f8f9fa; border: 1px solid #e9ecef; font-size: 1.1rem; }
    .active-strong-buy { background-color: #2b8a3e !important; color: white !important; border: 2px solid #51cf66 !important; }
    .active-buy { background-color: #5c940d !important; color: white !important; border: 2px solid #94d82d !important; }
    .active-hold { background-color: #f08c00 !important; color: white !important; border: 2px solid #ffc078 !important; }
    .active-sell { background-color: #e03131 !important; color: white !important; border: 2px solid #ff8787 !important; }
    .active-strong-sell { background-color: #c92a2a !important; color: white !important; border: 2px solid #ffa8a8 !important; }
    .rank-card { padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 12px; background-color: #f8f9fa; display: flex; flex-direction: column; justify-content: center; transition: 0.2s; }
    .rank-card:hover { border-color: #228be6; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .rank-number { font-size: 1.6rem; font-weight: bold; color: #228be6; width: 45px; }
    .rank-name { font-size: 1.3rem; font-weight: bold; color: #212529; }
    .folder-box { border: 1px solid #ced4da; border-radius: 12px; padding: 20px; background-color: #f8f9fa; height: 100%; min-height: 300px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 관리 및 유틸리티 함수 (원본 보존) ---
WATCHLIST_FILE = "watchlist.json"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except: pass
    return {"관심종목1": [], "관심종목2": [], "관심종목3": []}

def save_watchlist(data):
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

@st.cache_data
def load_stock_list():
    if os.path.exists('krx_stocks.csv'):
        df = pd.read_csv('krx_stocks.csv')
        df['Code'] = df['Code'].astype(str).str.zfill(6)
        df['Display'] = df['Name'] + " (" + df['Code'] + ")"
        return df
    return pd.DataFrame([{'Code': '005930', 'Name': '삼성전자', 'Market': 'KOSPI', 'Display': '삼성전자 (005930)'}])

df_krx = load_stock_list()

@st.cache_data(ttl=3600)
def get_detailed_info(symbol):
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        if not info or 'marketCap' not in info:
            # 보완 로직
            f_info = ticker.fast_info
            info['marketCap'] = getattr(f_info, 'market_cap', 0)
            info['fiftyTwoWeekHigh'] = getattr(f_info, 'year_high', 0)
            info['fiftyTwoWeekLow'] = getattr(f_info, 'year_low', 0)
            info['regularMarketPreviousClose'] = getattr(f_info, 'last_price', 0)
        return info
    except: return {}

# 화면 이동을 위한 콜백 (원본 핵심 로직)
def move_to_detail(stock_display):
    st.session_state.current_selection = stock_display
    st.session_state.page_selection = "📊 단일 종목 분석"

if 'current_selection' not in st.session_state:
    st.session_state.current_selection = df_krx['Display'].iloc[0]
if 'page_selection' not in st.session_state:
    st.session_state.page_selection = "📊 단일 종목 분석"
if 'search_results' not in st.session_state:
    st.session_state.search_results = []

# --- 3. 사이드바 메뉴 (원본 디자인 보존) ---
with st.sidebar:
    st.header("📌 메뉴 이동")
    page = st.radio("원하는 작업을 선택하세요", ["📊 단일 종목 분석", "🔍 조건 검색기 (스크리너)", "📂 관심종목 관리"], key="page_selection")
    
    st.divider()
    st.header("⚙️ 분석 조건 설정")
    st.subheader("🛠️ 지표 선택")
    use_ma = st.checkbox("방법 A: 이동평균선", value=True)
    use_rsi = st.checkbox("방법 B: RSI 심리", value=True)
    use_vol = st.checkbox("방법 C: 거래량 실세", value=True)
    use_bb = st.checkbox("방법 D: 볼린저 밴드", value=True)
    use_macd = st.checkbox("방법 E: MACD 추세", value=True) 
    
    st.divider()
    ma_s = st.slider("단기 이평선 기간", 3, 20, 5)
    ma_l = st.slider("장기 이평선 기간", 20, 120, 20)
    trading_fee_rate = st.number_input("왕복 수수료+세금 (%)", value=0.2, step=0.05) / 100

# --- 4. 분석 엔진 (심장부 - 원본 로직 100% 무삭제) ---
def analyze_reality_backtest(symbol, u_ma, u_rsi, u_vol, u_bb, u_macd, fee_rate):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        if df.empty or len(df) < 50: return None, None, None, 0, 0, 0, 0
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 지표 계산 로직
        df['MA_S'] = ta.sma(df['Close'], length=ma_s)
        df['MA_L'] = ta.sma(df['Close'], length=ma_l)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['Vol_MA'] = ta.sma(df['Volume'], length=20)
        bb = ta.bbands(df['Close'], length=20, std=2)
        df['BB_U'], df['BB_M'], df['BB_L'] = bb.iloc[:, 2], bb.iloc[:, 1], bb.iloc[:, 0]
        macd_calc = ta.macd(df['Close'])
        df['MACD_Line'], df['MACD_Hist'], df['MACD_Signal'] = macd_calc.iloc[:, 0], macd_calc.iloc[:, 1], macd_calc.iloc[:, 2]

        # 점수 산정 (원본 무삭제 복구)
        df['Score_MA'], df['Score_RSI'], df['Score_Vol'], df['Score_BB'], df['Score_MACD'] = 0, 0, 0, 0, 0
        active_tools = 0
        if u_ma:
            active_tools += 1
            spread = df['MA_S'] - df['MA_L']
            df['Score_MA'] = np.select([(spread > 0) & (spread > spread.shift(1)), (spread > 0), (spread < 0) & (spread < spread.shift(1)), (spread < 0)], [2, 1, -2, -1], default=0)
        if u_rsi:
            active_tools += 1
            df['Score_RSI'] = np.select([(df['RSI'] < 30), (df['RSI'] >= 30) & (df['RSI'] < 45), (df['RSI'] > 70), (df['RSI'] <= 70) & (df['RSI'] > 55)], [2, 1, -2, -1], default=0)
        if u_vol:
            active_tools += 1
            v_ratio = df['Volume'] / df['Vol_MA']
            pc = df['Close'].pct_change()
            df['Score_Vol'] = np.select([(v_ratio > 2.0) & (pc > 0), (v_ratio > 1.5) & (pc > 0), (v_ratio > 2.0) & (pc < 0), (v_ratio > 1.5) & (pc < 0)], [2, 1, -2, -1], default=0)
        if u_bb:
            active_tools += 1
            df['Score_BB'] = np.select([(df['Close'] <= df['BB_L']), (df['Close'] > df['BB_L']) & (df['Close'] < df['BB_M']), (df['Close'] >= df['BB_U']), (df['Close'] < df['BB_U']) & (df['Close'] > df['BB_M'])], [2, 1, -2, -1], default=0)
        if u_macd:
            active_tools += 1
            df['Score_MACD'] = np.select([(df['MACD_Line'] > df['MACD_Signal']) & (df['MACD_Hist'] > 0), (df['MACD_Line'] > df['MACD_Signal']), (df['MACD_Line'] < df['MACD_Signal']) & (df['MACD_Hist'] < 0), (df['MACD_Line'] < df['MACD_Signal'])], [2, 1, -2, -1], default=0)

        df['Avg_Score'] = (df['Score_MA'] + df['Score_RSI'] + df['Score_Vol'] + df['Score_BB'] + df['Score_MACD']) / active_tools if active_tools > 0 else 0
        df['Position'] = np.where(df['Avg_Score'] >= 0.4, 1, 0)
        df['Trade_Action'] = df['Position'].diff().fillna(0)
        df['Daily_Return'] = df['Close'].pct_change()
        df['Strategy_Return'] = (df['Position'].shift(1) * df['Daily_Return']) - np.where(df['Trade_Action'] != 0, fee_rate / 2, 0)
        
        s_profit = (1 + df['Strategy_Return']).cumprod().iloc[-1] - 1
        b_profit = (df['Close'].iloc[-1] / df['Close'].iloc[0]) - 1
        last = df.iloc[-1]
        status = "강력 매수" if last['Avg_Score'] >= 1.5 else ("매수 추천" if last['Avg_Score'] >= 0.5 else ("강력 매도" if last['Avg_Score'] <= -1.5 else ("매도" if last['Avg_Score'] <= -0.5 else "관망")))
        
        return df, status, s_profit, b_profit, last['Avg_Score']
    except: return None, "에러", 0, 0, 0


# ====== [화면 1: 단일 종목 분석] ======
if st.session_state.page_selection == "📊 단일 종목 분석":
    all_names = df_krx['Display'].tolist()
    current_index = all_names.index(st.session_state.current_selection) if st.session_state.current_selection in all_names else 0
    search_stock = st.selectbox("🎯 분석할 종목 선택", options=all_names, index=current_index)
    
    if search_stock != st.session_state.current_selection:
        st.session_state.current_selection = search_stock
        st.rerun()

    stock_info = df_krx[df_krx['Display'] == search_stock].iloc[0]
    ticker_sym = f"{stock_info['Code']}.KS" if stock_info['Market'] == 'KOSPI' else f"{stock_info['Code']}.KQ"

    df, status, s_profit, b_profit, f_score = analyze_reality_backtest(ticker_sym, use_ma, use_rsi, use_vol, use_bb, use_macd, trading_fee_rate)
    details = get_detailed_info(ticker_sym)

    if df is not None:
        # 🌟 1. 등락 정보 및 현재가 (색상 연동 + 콤마 적용)
        curr_p = df['Close'].iloc[-1]
        prev_p = details.get('regularMarketPreviousClose', df['Close'].iloc[-2])
        diff = curr_p - prev_p
        rate = (diff / prev_p) * 100
        # 상승 빨강, 하락 파랑 결정
        price_color = "#e03131" if diff > 0 else ("#1971c2" if diff < 0 else "#212529")

        st.markdown(f"""
            <div style='background-color:#ffffff; padding:25px; border-radius:15px; border:2px solid #e9ecef; margin-bottom:20px;'>
                <div style='display:flex; align-items:baseline; gap:20px;'>
                    <span style='font-size:3.8rem; font-weight:bold; color:{price_color};'>{curr_p:,.0f}원</span>
                    <span style='font-size:2rem; font-weight:bold; color:{price_color};'>{"▲" if diff > 0 else "▼"} {abs(diff):,.0f} ({rate:+.2f}%)</span>
                </div>
                <div style='color:#868e96; font-size:1.1rem; margin-top:5px;'>
                    전일종가: {prev_p:,.0f} | <b>금일 고가: {df['High'].iloc[-1]:,.0f} | 금일 저가: {df['Low'].iloc[-1]:,.0f}</b>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # 🌟 2. 기업 펀더멘털 (콤마 적용 + 데이터 보강)
        def fmt(val, unit="", d=0): 
            if val is None or val == 0 or np.isnan(val): return "데이터 준비중"
            return f"{val:,.{d}f}{unit}"
        
        st.write("### 🏢 기업 상세 정보 및 펀더멘털")
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"<div class='metric-container-box'><span class='info-label'>시가총액</span><br><b class='info-value'>{fmt(details.get('marketCap',0)/100000000, '억')}</b></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-container-box'><span class='info-label'>52주 최고</span><br><b class='info-value'>{fmt(details.get('fiftyTwoWeekHigh',0), '원')}</b></div>", unsafe_allow_html=True)
        with c2:
            st.markdown(f"<div class='metric-container-box'><span class='info-label'>PER (주가수익비율)</span><br><b class='info-value'>{fmt(details.get('trailingPE') or details.get('forwardPE'), '배', 2)}</b></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-container-box'><span class='info-label'>EPS (주당이익)</span><br><b class='info-value'>{fmt(details.get('trailingEps'), '원')}</b></div>", unsafe_allow_html=True)
        with c3:
            st.markdown(f"<div class='metric-container-box'><span class='info-label'>PBR (주가순자산비율)</span><br><b class='info-value'>{fmt(details.get('priceToBook'), '배', 2)}</b></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-container-box'><span class='info-label'>BPS (주당순자산)</span><br><b class='info-value'>{fmt(details.get('bookValue'), '원')}</b></div>", unsafe_allow_html=True)
        with c4:
            st.markdown(f"<div class='metric-container-box'><span class='info-label'>배당수익률</span><br><b class='info-value'>{fmt(details.get('dividendYield',0)*100, '%', 2)}</b></div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-container-box'><span class='info-label'>52주 최저</span><br><b class='info-value'>{fmt(details.get('fiftyTwoWeekLow',0), '원')}</b></div>", unsafe_allow_html=True)

        # 🌟 3. 분석 결과 요약 카드
        st.write("")
        st.markdown("<div style='background-color:#f8f9fa; padding:25px; border-radius:15px; margin-bottom:20px;'>", unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        with r1: st.metric("AI 전략 수익률 (1년)", f"{s_profit*100:.2f}%")
        with r2: st.metric("단순 보유 수익률 (1년)", f"{b_profit*100:.2f}%")
        with r3: st.metric("AI 종합 점수", f"{f_score:.2f}점")
        st.markdown("</div>", unsafe_allow_html=True)

        # 시그널 박스 (원본 디자인)
        signals = ["강력 매도", "매도", "관망", "매수 추천", "강력 매수"]
        cmap = {"강력 매수":"active-strong-buy", "매수 추천":"active-buy", "관망":"active-hold", "매도":"active-sell", "강력 매도":"active-strong-sell"}
        boxes = "".join([f'<div class="signal-box {cmap[s] if s==status else ""}">{s}</div>' for s in signals])
        st.markdown(f'<div class="signal-container">{boxes}</div>', unsafe_allow_html=True)
        
        st.subheader("📊 기술적 분석 차트")
        st.line_chart(df[['Close', 'MA_S', 'MA_L']], height=480)

        # 🌟 4. [완벽 복구] 상세 분석 지표 설명 가이드 (레오님 요청)
        st.divider()
        with st.expander("📖 Leo의 주식 투자 백과사전 (용어 설명 및 상세 분석 로직)", expanded=True):
            st.markdown("#### 1️⃣ 핵심 투자 용어 설명")
            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.markdown("""
                <div class='guide-box'>
                <b>PER (Price Earnings Ratio):</b> 주가를 주당순이익(EPS)으로 나눈 값입니다. 기업이 버는 돈에 비해 주가가 얼마나 비싼지/싼지 판단합니다. 낮을수록 '저평가'입니다.
                <br><br><b>PBR (Price Book-value Ratio):</b> 주가를 주당순자산(BPS)으로 나눈 값입니다. 1배 미만이면 기업의 자산가치보다 주가가 싸다는 뜻입니다.
                </div>
                """, unsafe_allow_html=True)
            with col_t2:
                st.markdown("""
                <div class='guide-box'>
                <b>EPS (Earnings Per Share):</b> 주식 1주가 1년 동안 벌어들인 순이익입니다.
                <br><br><b>배당수익률:</b> 주가 대비 배당금이 몇 %인지 나타냅니다. 고배당주는 하락장에서 훌륭한 방어막이 됩니다.
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("#### 2️⃣ Leo AI 엔진의 5단계 분석 로직")
            st.markdown(f"""
            <div class='guide-box'>
            <b>📍 방법 A: 이동평균선 ({ma_s}일 & {ma_l}일)</b><br>
            - 단기선이 장기선 위에 있고 간격이 넓어지면 <b>상승 동력 강력(+2점)</b><br>
            - 단기선이 장기선 아래에 있으면 <b>하락 주의(-2점)</b>
            </div>
            <div class='guide-box'>
            <b>📍 방법 B: RSI 심리 지표</b><br>
            - 30 이하: 시장이 공포에 질려 과도하게 팔린 상태. <b>매수 기회(+2점)</b><br>
            - 70 이상: 시장이 지나치게 열광한 과열 상태. <b>매도 고려(-2점)</b>
            </div>
            <div class='guide-box'>
            <b>📍 방법 C: 거래량 실세</b><br>
            - 평소 거래량의 1.5배~2배 이상 터지며 주가가 오르면 <b>진짜 세력 등장(+2점)</b><br>
            - 거래량은 터지는데 주가가 내리면 <b>탈출 신호(-2점)</b>
            </div>
            <div class='guide-box'>
            <b>📍 방법 D: 볼린저 밴드</b><br>
            - 주가가 밴드 하단선에 닿거나 뚫고 내려가면 <b>통계적 저점(+2점)</b><br>
            - 밴드 상단선에 닿으면 <b>단기 고점(-2점)</b>
            </div>
            <div class='guide-box'>
            <b>📍 방법 E: MACD 추세 변곡점</b><br>
            - MACD선이 시그널선을 골든크로스하고 히스토그램이 양수면 <b>추세 전환 성공(+2점)</b>
            </div>
            """, unsafe_allow_html=True)

        # 관심종목 저장 (원본 유지)
        st.divider()
        col_f, col_b = st.columns([3, 1])
        f_name = col_f.selectbox("저장할 폴더를 선택하세요", ["관심종목1", "관심종목2", "관심종목3"], label_visibility="collapsed")
        if col_b.button("⭐ 관심종목에 추가", use_container_width=True):
            wl = load_watchlist()
            if stock_info['Code'] not in wl[f_name]:
                wl[f_name].append(stock_info['Code'])
                save_watchlist(wl)
                st.toast(f"✅ {stock_info['Name']} 저장 완료!")


# ====== [화면 2: 조건 검색기 - 원본 로직 무삭제 복구] ======
elif st.session_state.page_selection == "🔍 조건 검색기 (스크리너)":
    st.title("🕸️ 나만의 조건 검색기")
    scan_mode = st.radio("어떤 종목들을 검색해볼까요?", ["📈 시가총액 우량주 스캔", "📝 내 관심종목 폴더 스캔"], horizontal=True)
    
    target_stocks = pd.DataFrame() 
    if scan_mode == "📈 시가총액 우량주 스캔":
        col_range, col_count = st.columns(2)
        with col_range: scan_range = st.selectbox("검색 범위", ["1위 ~ 50위", "51위 ~ 100위", "101위 ~ 150위", "151위 ~ 200위"])
        with col_count: top_n = st.selectbox("표시 개수", [5, 10, 15])
        start_idx = int(scan_range.split("위")[0].strip()) - 1
        target_stocks = df_krx.iloc[start_idx:start_idx+50]
    else: 
        col_folder, col_count = st.columns(2)
        with col_folder: selected_scan_folder = st.selectbox("스캔할 폴더 선택", ["관심종목1", "관심종목2", "관심종목3"])
        with col_count: top_n = st.selectbox("표시 개수", [5, 10, 20])
        wl = load_watchlist()
        target_stocks = df_krx[df_krx['Code'].isin(wl.get(selected_scan_folder, []))]

    if st.button("🚀 조건 검색 실행", type="primary", use_container_width=True):
        if target_stocks.empty: st.error("스캔할 종목이 없습니다.")
        else:
            my_bar = st.progress(0, text="정밀 분석 중...")
            temp_results = []
            for idx, (i, row) in enumerate(target_stocks.iterrows()):
                t_code = f"{row['Code']}.KS" if row['Market'] == 'KOSPI' else f"{row['Code']}.KQ"
                df_res, status, s_prof, _, f_score = analyze_reality_backtest(t_code, use_ma, use_rsi, use_vol, use_bb, use_macd, trading_fee_rate)
                if df_res is not None:
                    temp_results.append({'종목명': row['Name'], '종목코드': row['Code'], 'Display': row['Display'], 'AI추천상태': status, '종합점수': round(f_score, 2), '1년AI수익률(%)': round(s_prof * 100, 2)})
                my_bar.progress((idx + 1) / len(target_stocks))
            my_bar.empty()
            st.session_state.search_results = sorted(temp_results, key=lambda x: x['종합점수'], reverse=True)[:top_n]

    if st.session_state.search_results:
        st.subheader("🏆 현재 조건 종합 랭킹 TOP")
        df_csv = pd.DataFrame(st.session_state.search_results).drop(columns=['Display'])
        st.download_button("💾 엑셀(CSV) 저장", data=df_csv.to_csv(index=False).encode('utf-8-sig'), file_name="Leo_퀀트검색.csv", mime="text/csv", use_container_width=True)
        st.divider()
        for rank, item in enumerate(st.session_state.search_results):
            score_color = "#2b8a3e" if item['종합점수'] > 0 else "#e03131"
            c_info, c_btn = st.columns([4, 1])
            with c_info:
                st.markdown(f"""
                    <div class='rank-card'>
                        <div style='display:flex; align-items:center;'>
                            <span class='rank-number'>{rank + 1}</span>
                            <span class='rank-name'>{item['종목명']} <small style='color:#868e96;'>({item['종목코드']})</small></span>
                        </div>
                        <div style='margin-top: 10px; font-weight:bold; color:{score_color}; font-size:1.1rem;'>
                            {item['AI추천상태']} (점수: {item['종합점수']}) | 1년 AI수익률: {item['1년AI수익률(%)']}%
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with c_btn:
                st.write("") 
                st.button("📈 상세 분석", key=f"go_{item['종목코드']}", on_click=move_to_detail, args=(item['Display'],), use_container_width=True)


# ====== [화면 3: 관심종목 관리 - 원본 로직 무삭제 복구] ======
elif st.session_state.page_selection == "📂 관심종목 관리":
    st.title("📂 내 관심종목 관리")
    wl = load_watchlist()
    st.divider()
    cols = st.columns(3)
    for i, f_name in enumerate(["관심종목1", "관심종목2", "관심종목3"]):
        with cols[i]:
            st.markdown(f"<div class='folder-box'>", unsafe_allow_html=True)
            st.subheader(f"📁 {f_name}")
            codes = wl.get(f_name, [])
            if not codes:
                st.info("비어 있습니다.")
            else:
                for code in codes:
                    name_row = df_krx[df_krx['Code'] == code]
                    name = name_row['Name'].iloc[0] if not name_row.empty else "알수없음"
                    c_n, c_b = st.columns([4, 1])
                    with c_n: st.markdown(f"**{name}**<br><span style='color:#adb5bd; font-size:0.9rem;'>{code}</span>", unsafe_allow_html=True)
                    with c_b:
                        if st.button("❌", key=f"del_{f_name}_{code}"):
                            wl[f_name].remove(code); save_watchlist(wl); st.rerun()
                    st.markdown("<hr style='margin: 12px 0; border:0.5px solid #eee;'>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)