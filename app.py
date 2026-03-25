import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import os
import json

# --- 1. PC 광폭 레이아웃 및 원본 스타일 설정 (전체 복구 및 유지) ---
st.set_page_config(page_title="Leo 실전 퀀트 스나이퍼", layout="wide")

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
    
    /* 신규 실전 매매 상태 컬러 */
    .status-buy { background-color: #2b8a3e !important; color: white !important; border: 2px solid #51cf66 !important; }
    .status-hold { background-color: #f08c00 !important; color: white !important; border: 2px solid #ffc078 !important; }
    .status-wait { background-color: #868e96 !important; color: white !important; border: 2px solid #adb5bd !important; }
    
    .rank-card { padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 12px; background-color: #f8f9fa; display: flex; flex-direction: column; justify-content: center; transition: 0.2s; }
    .rank-card:hover { border-color: #228be6; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .rank-number { font-size: 1.6rem; font-weight: bold; color: #228be6; width: 45px; }
    .rank-name { font-size: 1.3rem; font-weight: bold; color: #212529; }
    .folder-box { border: 1px solid #ced4da; border-radius: 12px; padding: 20px; background-color: #f8f9fa; height: 100%; min-height: 300px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02); }
    .stop-loss-badge { display: inline-block; background-color: #fff5f5; color: #e03131; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 1rem; border: 1px solid #ffc9c9; margin-top: 10px; }
    .market-good { display: inline-block; background-color: #e3fafc; color: #0c8599; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 1rem; border: 1px solid #99e9f2; margin-top: 10px; margin-right: 10px;}
    .market-bad { display: inline-block; background-color: #fff0f6; color: #a61e4d; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 1rem; border: 1px solid #fcc2d7; margin-top: 10px; margin-right: 10px;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 관리 및 유틸리티 함수 ---
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
        if info is None: info = {}
        if not info or 'marketCap' not in info:
            f_info = ticker.fast_info
            info['marketCap'] = getattr(f_info, 'market_cap', 0)
            info['fiftyTwoWeekHigh'] = getattr(f_info, 'year_high', 0)
            info['fiftyTwoWeekLow'] = getattr(f_info, 'year_low', 0)
            info['regularMarketPreviousClose'] = getattr(f_info, 'previous_close', 0)
        return info
    except: return {}

def move_to_detail(stock_display):
    st.session_state.current_selection = stock_display
    st.session_state.page_selection = "📊 단일 종목 분석"

if 'current_selection' not in st.session_state: st.session_state.current_selection = df_krx['Display'].iloc[0]
if 'page_selection' not in st.session_state: st.session_state.page_selection = "📊 단일 종목 분석"
if 'search_results' not in st.session_state: st.session_state.search_results = []

# --- 3. 사이드바 메뉴 (불필요한 지표 선택 제거, 실전 변수만 남김) ---
with st.sidebar:
    st.header("📌 메뉴 이동")
    page = st.radio("원하는 작업을 선택하세요", ["📊 단일 종목 분석", "🔍 조건 검색기 (스크리너)", "📂 관심종목 관리"], key="page_selection")
    
    st.divider()
    st.header("⚙️ 실전 스나이퍼 설정")
    st.info("💡 전략: 추세 + 눌림 + 수급 + 돌파")
    
    ma_s = st.slider("단기 이평선 (눌림목 기준)", 3, 20, 5)
    ma_l = st.slider("장기 이평선 (추세 기준)", 20, 120, 20)
    trading_fee_rate = st.number_input("왕복 수수료+세금 (%)", value=0.2, step=0.05) / 100

# --- 4. 코스피 시장 필터 로드 ---
@st.cache_data(ttl=3600)
def get_kospi_filter():
    try:
        kospi = yf.download("^KS11", period="2y", interval="1d", progress=False)
        if isinstance(kospi.columns, pd.MultiIndex): kospi.columns = kospi.columns.get_level_values(0)
        kospi['KOSPI_MA60'] = ta.sma(kospi['Close'], length=60)
        kospi['Market_Good'] = kospi['Close'] > kospi['KOSPI_MA60']
        return kospi[['Market_Good']]
    except:
        # 에러 시 기본적으로 매수 허용 (오프라인/에러 방어)
        return pd.DataFrame()

# --- 5. 실전 매매 분석 엔진 (대공사 완료) ---
def analyze_sniper_backtest(symbol, fee_rate):
    try:
        df = yf.download(symbol, period="2y", interval="1d", progress=False)
        if df.empty or len(df) < 60: return None, "에러", 0, 0, 0, False, 0
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        # 1. 코스피 시장 필터 적용
        kospi_df = get_kospi_filter()
        if not kospi_df.empty:
            df = df.join(kospi_df, how='left')
            df['Market_Good'] = df['Market_Good'].ffill().fillna(True)
        else:
            df['Market_Good'] = True

        # 2. 필수 지표 계산
        df['MA_S'] = ta.sma(df['Close'], length=ma_s)
        df['MA_L'] = ta.sma(df['Close'], length=ma_l)
        df['MA_20'] = ta.sma(df['Close'], length=20) # 20일선 (청산용)
        df['Vol_MA'] = ta.sma(df['Volume'], length=20)
        macd_calc = ta.macd(df['Close'])
        df['MACD_Line'], df['MACD_Signal'] = macd_calc.iloc[:, 0], macd_calc.iloc[:, 2]
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14) # UI 표시용
        
        # 3. 가중치 점수 계산 (Total_Score)
        score_ma = np.where(df['MA_S'] > df['MA_L'], 3, 0)
        score_macd = np.where(df['MACD_Line'] > df['MACD_Signal'], 2, 0)
        score_vol = np.where((df['Volume'] > df['Vol_MA'] * 1.5) & (df['Close'] > df['Open']), 2, 0)
        score_mfi = np.where(df['MFI'] > 50, 2, 0)
        df['Total_Score'] = score_ma + score_macd + score_vol + score_mfi
        
        # 4. 세부 진입 조건 설정
        cond_score = df['Total_Score'] >= 5
        cond_pullback = df['Close'] < (df['MA_S'] * 1.03)
        cond_overheat = df['Close'].pct_change(10) < 0.30
        cond_trigger = df['Close'] > df['High'].shift(1)
        
        # 5. 최종 매수 신호 (모든 조건 AND)
        df['Buy_Signal'] = df['Market_Good'] & cond_score & cond_pullback & cond_overheat & cond_trigger

        # 6. 실전 State-Based 백테스트 루프 (손절/익절 기계적 적용)
        positions = np.zeros(len(df))
        trade_actions = np.zeros(len(df))
        in_position = False
        entry_price = 0.0
        
        closes = df['Close'].values
        ma20s = df['MA_20'].values
        buy_signals = df['Buy_Signal'].values
        
        for i in range(1, len(df)):
            if not in_position:
                if buy_signals[i]:
                    in_position = True
                    entry_price = closes[i]
                    positions[i] = 1
                    trade_actions[i] = 1 # 매수
            else:
                # 이미 보유 중일 때 출구 전략 (손절 -5%, 익절 +10%, 또는 20일선 이탈)
                if closes[i] <= entry_price * 0.95 or closes[i] >= entry_price * 1.10 or closes[i] < ma20s[i]:
                    in_position = False
                    positions[i] = 0
                    trade_actions[i] = -1 # 매도
                else:
                    positions[i] = 1
                    trade_actions[i] = 0 # 홀딩
                    
        df['Position'] = positions
        df['Trade_Action'] = trade_actions
        
        # 수익률 계산 (최근 1년만 집중)
        df_1y = df.iloc[-250:].copy()
        df_1y['Daily_Return'] = df_1y['Close'].pct_change()
        df_1y['Strategy_Return'] = (df_1y['Position'].shift(1) * df_1y['Daily_Return']) - np.where(df_1y['Trade_Action'] != 0, fee_rate / 2, 0)
        
        s_profit = (1 + df_1y['Strategy_Return']).cumprod().iloc[-1] - 1
        b_profit = (df_1y['Close'].iloc[-1] / df_1y['Close'].iloc[0]) - 1
        
        # 현재 상태 판단
        last = df_1y.iloc[-1]
        if last['Position'] == 1 and last['Trade_Action'] == 1: status = "🎯 매수 타점 포착!"
        elif last['Position'] == 1: status = "🟢 수익 극대화 (보유중)"
        else: status = "⚪ 관망 대기"
        
        return df_1y, status, s_profit, b_profit, last['Total_Score'], last['Market_Good'], last['ATR']
    except: return None, "에러", 0, 0, 0, False, 0


# ====== [화면 1: 단일 종목 분석] ======
if st.session_state.page_selection == "📊 단일 종목 분석":
    all_names = df_krx['Display'].tolist()
    current_index = all_names.index(st.session_state.current_selection) if st.session_state.current_selection in all_names else 0
    search_stock = st.selectbox("🎯 분석할 특정 종목을 고르세요", options=all_names, index=current_index)
    
    if search_stock != st.session_state.current_selection:
        st.session_state.current_selection = search_stock
        st.rerun()

    stock_info = df_krx[df_krx['Display'] == search_stock].iloc[0]
    ticker_sym = f"{stock_info['Code']}.KS" if stock_info['Market'] == 'KOSPI' else f"{stock_info['Code']}.KQ"

    df, status, s_profit, b_profit, total_score, market_good, current_atr = analyze_sniper_backtest(ticker_sym, trading_fee_rate)
    details = get_detailed_info(ticker_sym)

    if df is not None:
        curr_p = df['Close'].iloc[-1]
        prev_p = details.get('regularMarketPreviousClose')
        if not prev_p or prev_p == 0:
            prev_p = df['Close'].iloc[-2] if len(df) > 1 else curr_p
            
        diff = curr_p - prev_p
        rate = (diff / prev_p) * 100 if prev_p > 0 else 0
        price_color = "#e03131" if diff > 0 else ("#1971c2" if diff < 0 else "#212529")
        
        # UI 전용 ATR 기반 권장 손절가
        stop_loss_price = curr_p - (current_atr * 2) if current_atr > 0 else 0

        st.markdown(f"""
            <div style='background-color:#ffffff; padding:25px; border-radius:15px; border:2px solid #e9ecef; margin-bottom:20px;'>
                <div>
                    <span class='{"market-good" if market_good else "market-bad"}'>
                        {"📈 시장: 매수 허용 (코스피 60일선 위)" if market_good else "📉 시장: 매수 금지 (코스피 60일선 아래)"}
                    </span>
                    {f"<span class='stop-loss-badge'>🛡️ 권장 손절가: {stop_loss_price:,.0f}원 (2ATR)</span>" if stop_loss_price > 0 else ""}
                </div>
                <div style='display:flex; align-items:baseline; gap:20px; margin-top:15px;'>
                    <span style='font-size:3.8rem; font-weight:bold; color:{price_color};'>{curr_p:,.0f}원</span>
                    <span style='font-size:2rem; font-weight:bold; color:{price_color};'>{"▲" if diff > 0 else "▼"} {abs(diff):,.0f} ({rate:+.2f}%)</span>
                </div>
                <div style='color:#868e96; font-size:1.1rem; margin-top:5px;'>
                    전일종가: {prev_p:,.0f} | <b>금일 고가: {df['High'].iloc[-1]:,.0f} | 금일 저가: {df['Low'].iloc[-1]:,.0f}</b>
                </div>
            </div>
        """, unsafe_allow_html=True)

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

        st.write("")
        st.markdown("<div style='background-color:#f8f9fa; padding:25px; border-radius:15px; margin-bottom:20px;'>", unsafe_allow_html=True)
        r1, r2, r3 = st.columns(3)
        with r1: st.metric("스나이퍼 전략 수익률 (1년)", f"{s_profit*100:.2f}%")
        with r2: st.metric("단순 보유 수익률 (1년)", f"{b_profit*100:.2f}%")
        with r3: st.metric("타점 가중치 점수 (9점 만점)", f"{total_score:.0f}점")
        st.markdown("</div>", unsafe_allow_html=True)

        status_class = "status-buy" if "매수 타점" in status else ("status-hold" if "보유중" in status else "status-wait")
        st.markdown(f'<div class="signal-container"><div class="signal-box {status_class}" style="font-size:1.5rem;">{status}</div></div>', unsafe_allow_html=True)
        
        st.subheader("📊 스나이퍼 매매 차트 (진입/청산 20일선 표시)")
        st.line_chart(df[['Close', 'MA_S', 'MA_20']], height=480)

        # 🌟 4. [변경 완료] 스나이퍼 매매 전략 설명
        st.divider()
        with st.expander("📖 Leo의 스나이퍼 실전 매매 로직 가이드 (필독!)", expanded=True):
            st.markdown("""
            #### 1️⃣ 시장 필터 (비 올 때는 쉰다)
            * **코스피 60일선 판단:** 코스피 지수가 60일선 아래로 무너지면, 개별 종목 점수가 아무리 좋아도 **절대 매수하지 않습니다.** 하락장에서 계좌를 지키는 핵심 방패입니다.
            
            #### 2️⃣ 가중치 타점 점수 (Total Score: 5점 이상 합격)
            * **이동평균선 추세 (3점):** 단기 이평선이 장기 이평선 위에 있는가?
            * **MACD 돌파 (2점):** MACD가 시그널선을 골든크로스 했는가?
            * **거래량 실세 (2점):** 거래량이 평소의 1.5배 이상 터지며 양봉인가?
            * **MFI 수급 (2점):** 돈(수급)이 확실히 들어오고 있는가 (MFI > 50)?
            
            #### 3️⃣ 3대 정밀 사격 조건 (스나이퍼 룰)
            * **눌림목 포착:** 주가가 단기 이평선 대비 너무 붕 떠있지 않고 3% 이내로 눌려있을 때만 진입합니다.
            * **과열 방지:** 최근 10일간 30% 이상 급등한 종목은 피합니다. (고점 물림 방지)
            * **돌파 트리거:** 전일 고가를 시원하게 뚫어버리는 순간 방아쇠를 당깁니다.
            
            #### 4️⃣ 기계적 청산 로직 (출구 전략)
            * **익절 (+10%):** 매수가 대비 10% 상승 시 미련 없이 수익을 챙깁니다.
            * **손절 (-5%):** 매수가 대비 5% 하락 시 기계적으로 손절하여 시드를 보호합니다.
            * **추세 이탈:** 수익권이더라도 주가가 20일선을 깨고 내려오면 전량 매도합니다.
            """)

        # 관심종목 저장
        st.divider()
        col_f, col_b = st.columns([3, 1])
        f_name = col_f.selectbox("저장할 폴더를 선택하세요", ["관심종목1", "관심종목2", "관심종목3"], label_visibility="collapsed")
        if col_b.button("⭐ 관심종목에 추가", use_container_width=True):
            wl = load_watchlist()
            if stock_info['Code'] not in wl[f_name]:
                wl[f_name].append(stock_info['Code'])
                save_watchlist(wl)
                st.toast(f"✅ {stock_info['Name']} 저장 완료!")


# ====== [화면 2: 조건 검색기 - 실전 매매 우선 정렬 적용] ======
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
            my_bar = st.progress(0, text="정밀 타점 스캔 중...")
            temp_results = []
            for idx, (i, row) in enumerate(target_stocks.iterrows()):
                t_code = f"{row['Code']}.KS" if row['Market'] == 'KOSPI' else f"{row['Code']}.KQ"
                df_res, status, s_prof, _, t_score, m_good, _ = analyze_sniper_backtest(t_code, trading_fee_rate)
                if df_res is not None:
                    temp_results.append({'종목명': row['Name'], '종목코드': row['Code'], 'Display': row['Display'], '상태': status, '타점점수': t_score, '1년전략수익률(%)': round(s_prof * 100, 2)})
                my_bar.progress((idx + 1) / len(target_stocks))
            my_bar.empty()
            
            # [🔥 핵심 업데이트] 타점 1순위, 점수 2순위로 정렬 로직 변경
            def sort_priority(item):
                if "매수 타점" in item['상태']: p = 1
                elif "보유중" in item['상태']: p = 2
                else: p = 3
                return (p, -item['타점점수']) # p가 낮을수록(1) 상위, 타점점수는 높을수록 상위
                
            st.session_state.search_results = sorted(temp_results, key=sort_priority)[:top_n]

    if st.session_state.search_results:
        st.subheader("🏆 실전 매매 타점 랭킹 TOP (매수발생 우선)")
        df_csv = pd.DataFrame(st.session_state.search_results).drop(columns=['Display'])
        st.download_button("💾 엑셀(CSV) 저장", data=df_csv.to_csv(index=False).encode('utf-8-sig'), file_name="Leo_스나이퍼검색.csv", mime="text/csv", use_container_width=True)
        st.divider()
        for rank, item in enumerate(st.session_state.search_results):
            score_color = "#2b8a3e" if "매수 타점" in item['상태'] else ("#f08c00" if "보유중" in item['상태'] else "#868e96")
            c_info, c_btn = st.columns([4, 1])
            with c_info:
                st.markdown(f"""
                    <div class='rank-card'>
                        <div style='display:flex; align-items:center;'>
                            <span class='rank-number'>{rank + 1}</span>
                            <span class='rank-name'>{item['종목명']} <small style='color:#868e96;'>({item['종목코드']})</small></span>
                        </div>
                        <div style='margin-top: 10px; font-weight:bold; color:{score_color}; font-size:1.1rem;'>
                            {item['상태']} (점수: {item['타점점수']}점) | 1년 전략수익률: {item['1년전략수익률(%)']}%
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with c_btn:
                st.write("") 
                st.button("📈 타점 분석", key=f"go_{item['종목코드']}", on_click=move_to_detail, args=(item['Display'],), use_container_width=True)


# ====== [화면 3: 관심종목 관리] ======
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