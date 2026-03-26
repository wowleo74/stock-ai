import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import os
import json

# --- 1. PC 광폭 레이아웃 및 원본 스타일 설정 ---
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
    
    .status-buy { background-color: #2b8a3e !important; color: white !important; border: 2px solid #51cf66 !important; }
    .status-hold { background-color: #f08c00 !important; color: white !important; border: 2px solid #ffc078 !important; }
    .status-wait { background-color: #868e96 !important; color: white !important; border: 2px solid #adb5bd !important; }
    
    .rank-card { padding: 20px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 12px; background-color: #f8f9fa; display: flex; flex-direction: column; justify-content: center; transition: 0.2s; }
    .rank-card:hover { border-color: #228be6; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .rank-number { font-size: 1.6rem; font-weight: bold; color: #228be6; width: 45px; }
    .rank-name { font-size: 1.3rem; font-weight: bold; color: #212529; }
    .folder-box { border: 1px solid #ced4da; border-radius: 12px; padding: 20px; background-color: #f8f9fa; height: 100%; min-height: 300px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02); }
    .stop-loss-badge { display: inline-block; background-color: #fff5f5; color: #e03131; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 0.95rem; border: 1px solid #ffc9c9; margin-top: 10px; margin-right: 5px;}
    .take-profit-badge { display: inline-block; background-color: #f4fce3; color: #5c940d; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 0.95rem; border: 1px solid #d8f5a2; margin-top: 10px;}
    .market-good { display: inline-block; background-color: #e3fafc; color: #0c8599; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 0.95rem; border: 1px solid #99e9f2; margin-top: 10px; margin-right: 5px;}
    .market-bad { display: inline-block; background-color: #fff0f6; color: #a61e4d; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 0.95rem; border: 1px solid #fcc2d7; margin-top: 10px; margin-right: 5px;}
    
    .portfolio-card { padding: 20px; border-radius: 12px; border: 1px solid #ced4da; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 6px solid #495057; }
    .pf-profit { border-left-color: #e03131 !important; }
    .pf-loss { border-left-color: #1971c2 !important; }
    .pf-title { font-size: 1.4rem; font-weight: bold; margin-bottom: 10px; }
    .pf-detail { font-size: 1.1rem; color: #495057; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 데이터 관리 함수 ---
WATCHLIST_FILE = "watchlist.json"
PORTFOLIO_FILE = "portfolio.json"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {"관심종목1": [], "관심종목2": [], "관심종목3": []}

def save_watchlist(data):
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f: return json.load(f)
        except: pass
    return {} 

def save_portfolio(data):
    with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f: json.dump(data, f, ensure_ascii=False, indent=4)

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

@st.cache_data(ttl=3600)
def get_current_atr(symbol):
    try:
        df = yf.download(symbol, period="1mo", progress=False)
        if len(df) > 14:
            if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
            atr = ta.atr(df['High'], df['Low'], df['Close'], length=14)
            return atr.iloc[-1]
    except: pass
    return 0

# 화면 이동 콜백
def move_to_detail(stock_display):
    st.session_state.current_selection = stock_display
    st.session_state.page_selection = "📊 단일 종목 분석"

def move_to_portfolio():
    st.session_state.page_selection = "💼 내 계좌 관리 (실전 포트폴리오)"

if 'current_selection' not in st.session_state: st.session_state.current_selection = df_krx['Display'].iloc[0]
if 'page_selection' not in st.session_state: st.session_state.page_selection = "📊 단일 종목 분석"
if 'search_results' not in st.session_state: st.session_state.search_results = []

# --- 3. 코스피 시장 필터 ---
@st.cache_data(ttl=3600)
def get_kospi_filter():
    try:
        kospi = yf.download("^KS11", period="2y", interval="1d", progress=False)
        if isinstance(kospi.columns, pd.MultiIndex): kospi.columns = kospi.columns.get_level_values(0)
        kospi['KOSPI_MA60'] = ta.sma(kospi['Close'], length=60)
        kospi['Market_Good'] = kospi['Close'] > kospi['KOSPI_MA60']
        return kospi[['Market_Good']]
    except: return pd.DataFrame()

# --- 4. 사이드바 (시장 상황 기반 전략 자동 스위칭) ---
with st.sidebar:
    st.header("📌 시스템 메뉴")
    page = st.radio("이동할 페이지 선택", [
        "📊 단일 종목 분석", 
        "🔍 조건 검색기 (스크리너)", 
        "💼 내 계좌 관리 (실전 포트폴리오)", 
        "📂 관심종목 관리", 
        "📖 주식 & 전략 백과사전"
    ], key="page_selection")
    
    st.divider()
    st.header("🤖 AI 오토 트레이딩 전략")
    
    kospi_df_global = get_kospi_filter()
    global_market_good = kospi_df_global['Market_Good'].iloc[-1] if not kospi_df_global.empty else True
    
    if global_market_good:
        auto_mode_label = "🚀 자동: 공격형 (상승장)"
        ma_s, ma_l = 5, 20
        w_ma, w_macd, w_vol, w_mfi = 2, 2, 2, 1
        target_score = 4
        atr_sl, atr_tp = 2.5, 4.0
        st.success(f"📈 대세 상승장 감지됨\n현재 전략: **{auto_mode_label}**")
        st.caption("진입 기준을 낮춰 적극적으로 타점을 포착합니다.")
    else:
        auto_mode_label = "🛡️ 자동: 안정형 (하락/조정장)"
        ma_s, ma_l = 5, 20
        w_ma, w_macd, w_vol, w_mfi = 4, 2, 2, 2
        target_score = 6
        atr_sl, atr_tp = 1.5, 2.5
        st.error(f"📉 하락/조정장 감지됨\n현재 전략: **{auto_mode_label}**")
        st.caption("진입 기준을 극도로 높여 가장 안전한 자리만 노립니다.")

    st.divider()
    trading_fee_rate = st.number_input("왕복 수수료+세금 (%)", value=0.2, step=0.05) / 100


# --- 5. 실전 매매 분석 엔진 (소프트 시장 필터 완벽 적용) ---
def analyze_sniper_backtest(symbol, fee_rate, w_ma, w_macd, w_vol, w_mfi, target_score, atr_sl, atr_tp):
    try:
        df = yf.download(symbol, period="3y", interval="1d", progress=False) 
        if df.empty or len(df) < 60: return None, "에러", 0, 0, 0, 0, 0, False, 0
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        
        df = df.ffill().dropna()
        
        kospi_df = get_kospi_filter()
        if not kospi_df.empty:
            df = df.join(kospi_df, how='left')
            df['Market_Good'] = df['Market_Good'].ffill().fillna(True)
        else:
            df['Market_Good'] = True

        df['MA_S'] = ta.sma(df['Close'], length=ma_s)
        df['MA_L'] = ta.sma(df['Close'], length=ma_l)
        df['MA_20'] = ta.sma(df['Close'], length=20)
        df['Vol_MA'] = ta.sma(df['Volume'], length=20)
        
        df['Value'] = df['Close'] * df['Volume']
        df['Value_MA'] = df['Value'].rolling(20).mean()
        
        macd_calc = ta.macd(df['Close'])
        df['MACD_Line'], df['MACD_Signal'] = macd_calc.iloc[:, 0], macd_calc.iloc[:, 2]
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        
        score_ma = np.where(df['MA_S'] > df['MA_L'], w_ma, 0)
        score_macd = np.where(df['MACD_Line'] > df['MACD_Signal'], w_macd, 0)
        score_vol = np.where((df['Volume'] > df['Vol_MA'] * 1.5) & (df['Close'] > df['Open']), w_vol, 0)
        score_mfi = np.where(df['MFI'] > 50, w_mfi, 0)
        
        # [🔥 신규 1] 기본 점수 산출
        df['Total_Score'] = score_ma + score_macd + score_vol + score_mfi
        
        # [🔥 신규 2] 소프트 시장 필터 적용 (미래참조 방지를 위해 shift 1 적용 유지)
        cond_market_soft = np.where(df['Market_Good'].shift(1).fillna(True), 1.0, 0.5)
        df['Final_Score'] = df['Total_Score'] * cond_market_soft
        
        # [🔥 신규 3] 최종 점수로 커트라인 판별 (하락장 진입을 원천 차단하는 마법의 수식)
        cond_score = df['Final_Score'] >= target_score
        
        cond_pullback = df['Close'] < (df['MA_S'] * 1.03)
        cond_overheat = df['Close'].pct_change(10) < 0.30
        cond_trigger = df['Close'] > df['High'].shift(1)
        cond_value = df['Value'] > (df['Value_MA'] * 1.5)
        
        df['Buy_Signal'] = cond_score & cond_pullback & cond_overheat & cond_trigger & cond_value

        positions = np.zeros(len(df))
        trade_actions = np.zeros(len(df))
        strategy_returns = np.zeros(len(df))
        
        in_position = False
        entry_price = 0.0
        sl_price = 0.0
        tp_price = 0.0
        
        total_trades = 0
        winning_trades = 0
        
        closes = df['Close'].values
        opens = df['Open'].values
        highs = df['High'].values
        lows = df['Low'].values
        ma20s = df['MA_20'].values
        atrs = df['ATR'].values
        buy_signals = df['Buy_Signal'].values
        
        for i in range(1, len(df)):
            if not in_position:
                if buy_signals[i-1]: 
                    in_position = True
                    entry_price = opens[i] 
                    
                    sl_price = entry_price - (atrs[i-1] * atr_sl)
                    tp_price = entry_price + (atrs[i-1] * atr_tp)
                    
                    positions[i] = 1
                    trade_actions[i] = 1 
                    total_trades += 1
            else:
                exit_price = None
                
                if lows[i] <= sl_price:
                    exit_price = sl_price
                elif highs[i] >= tp_price:
                    exit_price = tp_price
                elif closes[i] < ma20s[i-1]:
                    exit_price = closes[i]
                    
                if exit_price is not None:
                    in_position = False
                    positions[i] = 0
                    trade_actions[i] = -1 
                    
                    if exit_price > entry_price:
                        winning_trades += 1
                else:
                    positions[i] = 1
                    trade_actions[i] = 0
            
            if closes[i-1] > 0:
                if trade_actions[i] == -1 and exit_price is not None:
                    strategy_returns[i] = (exit_price - closes[i-1]) / closes[i-1]
                else:
                    strategy_returns[i] = positions[i-1] * (closes[i] - closes[i-1]) / closes[i-1]
                    
            if trade_actions[i] == 1:
                strategy_returns[i] = 0
                
            if trade_actions[i] != 0:
                strategy_returns[i] -= fee_rate / 2
                
        df['Position'] = positions
        df['Trade_Action'] = trade_actions
        df['Strategy_Return'] = strategy_returns
        
        df_1y = df.iloc[-250:].copy()
        s_profit = (1 + df_1y['Strategy_Return']).cumprod().iloc[-1] - 1 if len(df_1y) > 0 else 0
        b_profit = (df_1y['Close'].iloc[-1] / df_1y['Close'].iloc[0]) - 1 if len(df_1y) > 0 else 0
        
        cum_ret = (1 + df_1y['Strategy_Return']).cumprod()
        running_max = cum_ret.cummax()
        drawdown = (cum_ret - running_max) / running_max
        mdd = drawdown.min()
        
        days = len(df_1y)
        cagr = (cum_ret.iloc[-1] ** (252 / days)) - 1 if cum_ret.iloc[-1] > 0 and days > 0 else 0
        
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        
        last = df.iloc[-1]
        
        if df['Buy_Signal'].iloc[-1]: status = "🔥 강력 매수 (내일 아침 진입)"
        elif last['Position'] == 1: status = "🛡️ 보유자 영역 (Hold)"
        else: status = "👀 관망"
        
        # 화면의 "현재 점수"가 헷갈리지 않게 0.5가 곱해진 Final_Score를 반환합니다.
        return df_1y, status, cagr, mdd, win_rate, b_profit, last['Final_Score'], last['Market_Good'], last['ATR']
    except: return None, "에러", 0, 0, 0, 0, 0, False, 0


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

    df, status, cagr, mdd, win_rate, b_profit, total_score, market_good, current_atr = analyze_sniper_backtest(ticker_sym, trading_fee_rate, w_ma, w_macd, w_vol, w_mfi, target_score, atr_sl, atr_tp)
    details = get_detailed_info(ticker_sym)

    if df is not None:
        curr_p = df['Close'].iloc[-1]
        prev_p = details.get('regularMarketPreviousClose')
        if not prev_p or prev_p == 0:
            prev_p = df['Close'].iloc[-2] if len(df) > 1 else curr_p
            
        diff = curr_p - prev_p
        rate = (diff / prev_p) * 100 if prev_p > 0 else 0
        price_color = "#e03131" if diff > 0 else ("#1971c2" if diff < 0 else "#212529")
        
        stop_loss_price = curr_p - (current_atr * atr_sl) if current_atr > 0 else 0
        take_profit_price = curr_p + (current_atr * atr_tp) if current_atr > 0 else 0

        st.markdown(f"""
            <div style='background-color:#ffffff; padding:25px; border-radius:15px; border:2px solid #e9ecef; margin-bottom:20px;'>
                <div>
                    <span class='{"market-good" if market_good else "market-bad"}'>
                        {"📈 상승장: 공격형 전략 가동 중" if market_good else "📉 하락장: 안정형 방어막 가동 중 (점수 50% 차감)"}
                    </span>
                    {f"<span class='stop-loss-badge'>🛡️ 손절: {stop_loss_price:,.0f}원 (-{atr_sl}ATR)</span>" if stop_loss_price > 0 else ""}
                    {f"<span class='take-profit-badge'>🚀 익절: {take_profit_price:,.0f}원 (+{atr_tp}ATR)</span>" if take_profit_price > 0 else ""}
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

        st.markdown("### 🏆 AI 퀀트 전략 성과 리포트 (최근 1년)")
        r1, r2, r3, r4 = st.columns(4)
        with r1: st.metric("CAGR (연평균 수익률)", f"{cagr*100:.2f}%")
        with r2: st.metric("MDD (최대 낙폭)", f"{mdd*100:.2f}%")
        with r3: st.metric("전략 승률 (Win Rate)", f"{win_rate:.1f}%")
        with r4: st.metric("단순 존버 수익률", f"{b_profit*100:.2f}%")

        status_class = "status-buy" if "강력 매수" in status else ("status-hold" if "보유자 영역" in status else "status-wait")
        st.markdown(f'<div class="signal-container"><div class="signal-box {status_class}" style="font-size:1.5rem;">{status} (최종 점수: {total_score:.1f}점 / 진입선: {target_score}점)</div></div>', unsafe_allow_html=True)
        
        st.subheader("📊 스나이퍼 매매 차트 (진입/청산 20일선 표시)")
        st.line_chart(df[['Close', 'MA_S', 'MA_20']], height=450)

        st.divider()
        col_f, col_b, col_p = st.columns([2, 1, 1])
        f_name = col_f.selectbox("폴더 선택", ["관심종목1", "관심종목2", "관심종목3"], label_visibility="collapsed")
        
        if col_b.button("⭐ 관심종목 추가", use_container_width=True):
            wl = load_watchlist()
            if stock_info['Code'] not in wl[f_name]:
                wl[f_name].append(stock_info['Code'])
                save_watchlist(wl); st.toast(f"✅ {stock_info['Name']} 저장 완료!")
        
        col_p.button("💼 내 계좌(포트폴리오)로 이동", use_container_width=True, on_click=move_to_portfolio)


# ====== [화면 2: 조건 검색기] ======
elif st.session_state.page_selection == "🔍 조건 검색기 (스크리너)":
    st.title(f"🕸️ 실전 타점 스캐너 ({auto_mode_label})")
    scan_mode = st.radio("검색 대상", ["📈 시가총액 우량주 스캔", "📝 내 관심종목 폴더 스캔"], horizontal=True)
    
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

    if st.button("🚀 타점 검색 실행", type="primary", use_container_width=True):
        if target_stocks.empty: st.error("스캔할 종목이 없습니다.")
        else:
            my_bar = st.progress(0, text="정밀 타점 스캔 중...")
            temp_results = []
            for idx, (i, row) in enumerate(target_stocks.iterrows()):
                t_code = f"{row['Code']}.KS" if row['Market'] == 'KOSPI' else f"{row['Code']}.KQ"
                df_res, status, cagr, mdd, win_rate, _, t_score, _, _ = analyze_sniper_backtest(t_code, trading_fee_rate, w_ma, w_macd, w_vol, w_mfi, target_score, atr_sl, atr_tp)
                if df_res is not None:
                    temp_results.append({'종목명': row['Name'], '종목코드': row['Code'], 'Display': row['Display'], '상태': status, '타점점수': t_score, 'CAGR': round(cagr * 100, 2), '승률': round(win_rate, 1)})
                my_bar.progress((idx + 1) / len(target_stocks))
            my_bar.empty()
            
            def sort_priority(item):
                if "강력 매수" in item['상태']: p = 1
                elif "보유자 영역" in item['상태']: p = 2 
                else: p = 3
                return (p, -item['타점점수']) 
                
            st.session_state.search_results = sorted(temp_results, key=sort_priority)[:top_n]

    if st.session_state.search_results:
        st.subheader("🏆 실전 매매 타점 랭킹 TOP (당일 매수 우선)")
        for rank, item in enumerate(st.session_state.search_results):
            score_color = "#2b8a3e" if "강력 매수" in item['상태'] else ("#f08c00" if "보유자 영역" in item['상태'] else "#868e96")
            c_info, c_btn = st.columns([4, 1])
            with c_info:
                st.markdown(f"""
                    <div class='rank-card'>
                        <div style='display:flex; align-items:center;'>
                            <span class='rank-number'>{rank + 1}</span>
                            <span class='rank-name'>{item['종목명']} <small style='color:#868e96;'>({item['종목코드']})</small></span>
                        </div>
                        <div style='margin-top: 10px; font-weight:bold; color:{score_color}; font-size:1.1rem;'>
                            {item['상태']} (최종 점수: {item['타점점수']:.1f}점) | CAGR: {item['CAGR']}% | 승률: {item['승률']}%
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with c_btn:
                st.write("") 
                st.button("📈 상세 분석", key=f"go_{item['종목코드']}", on_click=move_to_detail, args=(item['Display'],), use_container_width=True)


# ====== [화면 3: 내 계좌(포트폴리오) 관리] ======
elif st.session_state.page_selection == "💼 내 계좌 관리 (실전 포트폴리오)":
    st.title("💼 내 실제 계좌 (포트폴리오) 관리")
    st.markdown(f"**현재 시장 상황({auto_mode_label})**에 맞춰 AI가 종목별 최적의 손/익절 타이밍을 감시합니다.")
    
    pf = load_portfolio()
    
    with st.expander("➕ 내 계좌에 주식 추가하기", expanded=True):
        col_s, col_p, col_q, col_b = st.columns([3, 2, 2, 1])
        all_names = df_krx['Display'].tolist()
        add_stock = col_s.selectbox("매수한 종목", options=all_names, label_visibility="collapsed")
        buy_price = col_p.number_input("매입 단가 (원)", min_value=1, value=50000, step=100)
        quantity = col_q.number_input("보유 수량 (주)", min_value=1, value=10, step=1)
        
        if col_b.button("저장"):
            code = add_stock.split("(")[-1].replace(")", "")
            name = add_stock.split("(")[0].strip()
            pf[code] = {"Name": name, "BuyPrice": buy_price, "Quantity": quantity}
            save_portfolio(pf)
            st.success(f"{name}이(가) 포트폴리오에 추가되었습니다!")
            st.rerun()

    st.divider()
    
    if not pf:
        st.info("현재 계좌에 등록된 주식이 없습니다. 위에서 매수한 종목을 추가해 보세요.")
    else:
        st.subheader("📊 보유 종목 실시간 진단 (ATR 적용)")
        total_invested = 0
        total_current_value = 0
        
        for code, data in pf.items():
            t_code = f"{code}.KS" if not df_krx[df_krx['Code']==code].empty and df_krx[df_krx['Code']==code]['Market'].iloc[0] == 'KOSPI' else f"{code}.KQ"
            info = get_detailed_info(t_code)
            curr_price = info.get('regularMarketPreviousClose', data['BuyPrice'])
            
            c_atr = get_current_atr(t_code)
            my_sl = data['BuyPrice'] - (c_atr * atr_sl) if c_atr > 0 else data['BuyPrice'] * 0.95
            my_tp = data['BuyPrice'] + (c_atr * atr_tp) if c_atr > 0 else data['BuyPrice'] * 1.10
            
            invested = data['BuyPrice'] * data['Quantity']
            curr_value = curr_price * data['Quantity']
            profit_amt = curr_value - invested
            profit_rate = (profit_amt / invested) * 100
            
            total_invested += invested
            total_current_value += curr_value
            
            if curr_price >= my_tp:
                ai_action = "🚀 수익 실현 권장 (목표가 도달)"
                card_class = "pf-profit"
                act_color = "#5c940d"
            elif curr_price <= my_sl:
                ai_action = "⚠️ 칼손절 필요 (위험 이탈가 도달)"
                card_class = "pf-loss"
                act_color = "#e03131"
            else:
                ai_action = "✅ 홀딩 (추세 관망 중)"
                card_class = "portfolio-card"
                act_color = "#2b8a3e"
                
            color = "#e03131" if profit_rate > 0 else ("#1971c2" if profit_rate < 0 else "#495057")
            
            st.markdown(f"""
                <div class='portfolio-card {card_class}'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <div class='pf-title'>{data['Name']} <small style='color:#adb5bd;'>({code})</small></div>
                        <div style='font-size:1.2rem; font-weight:bold; color:{act_color};'>{ai_action}</div>
                    </div>
                    <div style='display:flex; justify-content:space-between; margin-top:10px;'>
                        <div class='pf-detail'>매입단가: <b>{data['BuyPrice']:,.0f}원</b> ({data['Quantity']}주)</div>
                        <div class='pf-detail'>현재가: <b>{curr_price:,.0f}원</b></div>
                        <div class='pf-detail' style='color:{color}; font-weight:bold;'>수익률: {profit_rate:+.2f}% ({profit_amt:+,.0f}원)</div>
                    </div>
                    <div style='margin-top:10px; font-size:0.9rem; color:#868e96;'>
                        목표 익절가: {my_tp:,.0f}원 | 한계 손절가: {my_sl:,.0f}원 (자동 계산)
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("목록에서 삭제 (매도 완료)", key=f"sell_{code}"):
                del pf[code]; save_portfolio(pf); st.rerun()

        st.divider()
        total_profit = total_current_value - total_invested
        total_rate = (total_profit / total_invested) * 100 if total_invested > 0 else 0
        total_color = "#e03131" if total_profit > 0 else "#1971c2"
        st.markdown(f"### 💰 총 계좌 수익률: <span style='color:{total_color}'>{total_rate:+.2f}% ({total_profit:+,.0f}원)</span>", unsafe_allow_html=True)


# ====== [화면 4: 관심종목 관리] ======
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


# ====== [화면 5: 백과사전 및 로직 산출식] ======
elif st.session_state.page_selection == "📖 주식 & 전략 백과사전":
    st.title("📖 Leo의 퀀트 투자 백과사전")
    st.markdown("프로그램에 적용된 **실전 타점 엔진의 정확한 수학적 산출식과 작동 원리**를 투명하게 공개합니다.")
    
    st.header("1. 📉 신규 성과 지표 (퀀트 필수)")
    st.success("""
    * **CAGR (연평균 복리 수익률):** 1년 동안 내 돈이 복리로 얼마나 불어났는지 보여주는 가장 정확한 수익률 지표.
    * **MDD (최대 낙폭):** 고점 대비 계좌가 가장 많이 깨졌을 때의 비율. (예: MDD 30%면 100만 원이 70만 원까지 떨어지는 고통을 견뎠다는 뜻)
    * **승률 (Win Rate):** 전체 매매 횟수 중 수익을 내고 나온 매매의 비율.
    """)
    
    st.header("2. 🎯 스나이퍼 트리거 (거래대금 필터 추가)")
    st.info("""
    * **① 눌림목 (Pullback):** `현재가 < 단기 이평선(MA_S) * 1.03`
    * **② 과열 방지:** `10일 수익률 < 30%`
    * **③ 돌파 (Breakout):** `현재가 > 전일 고가`
    * **④ 거래대금 필터 (핵심):** `오늘 거래대금 > 20일 평균 거래대금 * 1.5` (단순 거래량이 아닌, 실제 돈이 몰려야만 합격)
    """)
    
    st.header("3. 🛡️ 소프트 시장 필터 & AI 오토 스위칭")
    st.warning("""
    **코스피 60일선(대세 이평선)을 기준으로 프로그램이 자동으로 태세를 전환합니다.**
    * **상승장 감지 시 (공격형 자동 전환):** 기준 점수를 4점으로 낮추고, 획득한 점수를 100% 인정해 적극적으로 타점을 포착합니다.
    * **하락장 감지 시 (안정형 절대 방어):** 획득한 점수를 **강제로 절반(0.5배)** 깎아버립니다. 아무리 좋은 종목도 만점(5점)을 넘어 진입선(6점)에 도달할 수 없게 만들어, **하락장에서는 100% 현금 관망**을 하도록 설계된 궁극의 킬 스위치입니다.
    """)