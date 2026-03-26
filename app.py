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
    .market-badge { display: inline-block; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 0.95rem; margin-top: 10px; margin-right: 5px; border: 1px solid #ced4da; }
    .weight-badge { display: inline-block; background-color: #e6fcf5; color: #08a081; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 0.95rem; border: 1px solid #63e6be; margin-top: 10px; margin-right: 5px;}
    
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

# --- 3. 글로벌 시장 필터 ---
@st.cache_data(ttl=3600)
def get_kospi_filter():
    try:
        kospi = yf.download("^KS11", period="3y", interval="1d", progress=False)
        if isinstance(kospi.columns, pd.MultiIndex): kospi.columns = kospi.columns.get_level_values(0)
        
        kospi['MA60'] = ta.sma(kospi['Close'], length=60)
        kospi['ATR'] = ta.atr(kospi['High'], kospi['Low'], kospi['Close'], length=14)
        kospi['Volatility'] = kospi['ATR'] / kospi['Close']
        kospi['MA60_Slope'] = kospi['MA60'].diff(5)
        
        cond_up = (kospi['Close'] > kospi['MA60']) & (kospi['MA60_Slope'] > 0)
        cond_down = kospi['Close'] < kospi['MA60']
        
        kospi['Global_Mode'] = np.select([cond_up, cond_down], ["UPTREND", "DOWNTREND"], default="SIDEWAYS")
        return kospi[['Global_Mode']]
    except: return pd.DataFrame()

# 화면 이동 콜백
def move_to_detail(stock_display):
    st.session_state.current_selection = stock_display
    st.session_state.page_selection = "📊 단일 종목 분석"

def move_to_portfolio():
    st.session_state.page_selection = "💼 내 계좌 관리 (실전 포트폴리오)"

if 'current_selection' not in st.session_state: st.session_state.current_selection = df_krx['Display'].iloc[0]
if 'page_selection' not in st.session_state: st.session_state.page_selection = "📊 단일 종목 분석"
if 'search_results' not in st.session_state: st.session_state.search_results = []

# --- 4. 사이드바 ---
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
    st.header("🤖 리스크 관리 통합 시스템")
    
    kospi_df_global = get_kospi_filter()
    global_mode = kospi_df_global['Global_Mode'].iloc[-1] if not kospi_df_global.empty else "SIDEWAYS"
    
    global_mode_map = {
        "UPTREND": "🌍 코스피: 대세 상승장",
        "SIDEWAYS": "🌍 코스피: 혼조세 (박스권)",
        "DOWNTREND": "🌍 코스피: 대세 하락장 (매수 차단)"
    }
    st.info(f"**{global_mode_map.get(global_mode)}**")
    if global_mode == "DOWNTREND": st.error("⚠️ 코스피 하락장으로 신규 매수 신호가 차단됩니다.")
    
    st.divider()
    trading_fee_rate = st.number_input("왕복 수수료+세금 (%)", value=0.2, step=0.05) / 100


# --- 5. 실전 매매 분석 엔진 ---
def analyze_sniper_backtest(symbol, fee_rate):
    try:
        df = yf.download(symbol, period="3y", interval="1d", progress=False) 
        if df.empty or len(df) < 60: return None, "에러", 0, 0, 0, 0, None, 0, 0, 0, None, 0
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        df = df.ffill().dropna()

        kospi_df = get_kospi_filter()
        if not kospi_df.empty:
            df = df.join(kospi_df, how='left')
            df['Global_Mode'] = df['Global_Mode'].ffill().fillna("SIDEWAYS")
        else:
            df['Global_Mode'] = "SIDEWAYS"

        df['MA_S'] = ta.sma(df['Close'], length=5)
        df['MA_L'] = ta.sma(df['Close'], length=20)
        df['MA_20'] = df['MA_L']
        df['MA60'] = ta.sma(df['Close'], length=60)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['Volatility'] = df['ATR'] / df['Close']
        df['MA60_Slope'] = df['MA60'].diff(5)
        
        cond_up = (df['Close'] > df['MA60']) & (df['MA60_Slope'] > 0) & (df['Volatility'] < 0.03)
        cond_vol_up = (df['Close'] > df['MA60']) & (df['MA60_Slope'] > 0) & (df['Volatility'] >= 0.03)
        cond_side = (abs(df['Close'] - df['MA60']) / df['MA60'] < 0.02)
        cond_down = ~(cond_up | cond_vol_up | cond_side)

        df['Market_Mode'] = np.select(
            [cond_up, cond_vol_up, cond_side, cond_down], 
            ["UPTREND", "VOLATILE_UP", "SIDEWAYS", "DOWNTREND"], 
            default="DOWNTREND"
        )
        
        df['Target_Score'] = np.select(
            [df['Market_Mode'] == "UPTREND", df['Market_Mode'] == "SIDEWAYS", df['Market_Mode'] == "VOLATILE_UP", df['Market_Mode'] == "DOWNTREND"],
            [4, 5, 6, 6], default=6
        )
        df['ATR_SL_Mult'] = np.select(
            [df['Market_Mode'] == "UPTREND", df['Market_Mode'] == "SIDEWAYS", df['Market_Mode'] == "VOLATILE_UP", df['Market_Mode'] == "DOWNTREND"],
            [2.5, 1.5, 2.0, 1.2], default=1.5
        )
        df['ATR_TP_Mult'] = np.select(
            [df['Market_Mode'] == "UPTREND", df['Market_Mode'] == "SIDEWAYS", df['Market_Mode'] == "VOLATILE_UP", df['Market_Mode'] == "DOWNTREND"],
            [4.0, 2.0, 3.0, 2.0], default=2.5
        )

        df['Vol_MA'] = ta.sma(df['Volume'], length=20)
        df['Value'] = df['Close'] * df['Volume']
        df['Value_MA'] = df['Value'].rolling(20).mean()
        
        macd_calc = ta.macd(df['Close'])
        df['MACD_Line'], df['MACD_Signal'] = macd_calc.iloc[:, 0], macd_calc.iloc[:, 2]
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        
        score_ma = np.where(df['MA_S'] > df['MA_L'], 3, 0)
        score_macd = np.where(df['MACD_Line'] > df['MACD_Signal'], 2, 0)
        score_vol = np.where((df['Volume'] > df['Vol_MA'] * 1.5) & (df['Close'] > df['Open']), 2, 0)
        score_mfi = np.where(df['MFI'] > 50, 2, 0)
        df['Total_Score'] = score_ma + score_macd + score_vol + score_mfi
        
        cond_score = df['Total_Score'] >= df['Target_Score']
        cond_pullback = df['Close'] < (df['MA_S'] * 1.03)
        cond_overheat = df['Close'].pct_change(10) < 0.30
        cond_trigger = df['Close'] > df['High'].shift(1)
        cond_value = df['Value'] > (df['Value_MA'] * 1.5)
        
        cond_allow_local = df['Market_Mode'] != "VOLATILE_UP"
        cond_allow_global = df['Global_Mode'] != "DOWNTREND" 
        
        df['Buy_Signal'] = cond_score & cond_pullback & cond_overheat & cond_trigger & cond_value & cond_allow_local & cond_allow_global

        positions = np.zeros(len(df))
        trade_actions = np.zeros(len(df))
        strategy_returns = np.zeros(len(df))
        
        in_position = False
        entry_price = 0.0
        sl_price = 0.0
        tp_price = 0.0
        current_position_size = 0.0 
        
        total_trades = 0
        winning_trades = 0
        
        closes = df['Close'].values
        opens = df['Open'].values
        highs = df['High'].values
        lows = df['Low'].values
        ma20s = df['MA_20'].values
        atrs = df['ATR'].values
        buy_signals = df['Buy_Signal'].values
        
        sl_mults = df['ATR_SL_Mult'].values
        tp_mults = df['ATR_TP_Mult'].values
        
        risk_per_trade = 0.01 
        
        for i in range(1, len(df)):
            if not in_position:
                if buy_signals[i-1]: 
                    prev_close = closes[i-1]
                    gap = (opens[i] / prev_close) - 1 if prev_close > 0 else 0
                    
                    if -0.03 <= gap <= 0.03:
                        in_position = True
                        entry_price = opens[i] 
                        
                        sl_price = entry_price - (atrs[i-1] * sl_mults[i-1])
                        tp_price = entry_price + (atrs[i-1] * tp_mults[i-1])
                        
                        risk_per_share = entry_price - sl_price
                        if risk_per_share > 0:
                            calc_size = risk_per_trade / (risk_per_share / entry_price)
                            current_position_size = min(calc_size, 1.0) 
                        else:
                            current_position_size = 1.0
                            
                        positions[i] = 1
                        trade_actions[i] = 1 
                        total_trades += 1
                    else:
                        positions[i] = 0
                        trade_actions[i] = 0
            else:
                exit_price = None
                
                if lows[i] <= sl_price: exit_price = sl_price
                elif highs[i] >= tp_price: exit_price = tp_price
                elif closes[i] < ma20s[i-1]: exit_price = closes[i]
                    
                if exit_price is not None:
                    in_position = False
                    positions[i] = 0
                    trade_actions[i] = -1 
                    if exit_price > entry_price: winning_trades += 1
                else:
                    positions[i] = 1
                    trade_actions[i] = 0
            
            if closes[i-1] > 0:
                if trade_actions[i] == -1 and exit_price is not None:
                    strategy_returns[i] = current_position_size * ((exit_price - closes[i-1]) / closes[i-1])
                else:
                    strategy_returns[i] = current_position_size * (positions[i-1] * (closes[i] - closes[i-1]) / closes[i-1])
                    
            if trade_actions[i] == 1: strategy_returns[i] = 0
            if trade_actions[i] != 0: strategy_returns[i] -= (fee_rate / 2) * current_position_size
                
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
        
        if df['Buy_Signal'].iloc[-1]: status = "🔥 강력 매수 대기"
        elif last['Position'] == 1: status = "🛡️ 보유자 영역 (Hold)"
        else: status = "👀 관망"
        
        curr_risk_pct = (last['ATR'] * last['ATR_SL_Mult']) / df['Close'].iloc[-1]
        rec_weight = min(0.01 / curr_risk_pct, 1.0) if curr_risk_pct > 0 else 1.0
        
        mode_results = []
        for mode in ["UPTREND", "SIDEWAYS", "VOLATILE_UP", "DOWNTREND"]:
            temp = df_1y[df_1y['Market_Mode'] == mode]
            if len(temp) > 0:
                trades_only = temp[temp['Trade_Action'] != 0]
                win_pct = (trades_only['Strategy_Return'] > 0).mean() * 100 if len(trades_only) > 0 else 0
                days_in_mode = len(temp)
                mode_results.append({"시장상태": mode, "출현 일수": days_in_mode, "청산 승률": round(win_pct, 1)})

        mode_df = pd.DataFrame(mode_results) if mode_results else None
        
        return df_1y, status, cagr, mdd, win_rate, b_profit, last['Total_Score'], last['Target_Score'], last['Market_Mode'], last['ATR'], mode_df, rec_weight
    except: return None, "에러", 0, 0, 0, 0, None, 0, 0, 0, None, 0


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

    df, status, cagr, mdd, win_rate, b_profit, total_score, target_score, current_mode, current_atr, mode_df, rec_weight = analyze_sniper_backtest(ticker_sym, trading_fee_rate)
    details = get_detailed_info(ticker_sym)

    if df is not None:
        curr_p = df['Close'].iloc[-1]
        prev_p = details.get('regularMarketPreviousClose')
        if not prev_p or prev_p == 0:
            prev_p = df['Close'].iloc[-2] if len(df) > 1 else curr_p
            
        diff = curr_p - prev_p
        rate = (diff / prev_p) * 100 if prev_p > 0 else 0
        price_color = "#e03131" if diff > 0 else ("#1971c2" if diff < 0 else "#212529")
        
        sl_mult = df['ATR_SL_Mult'].iloc[-1]
        tp_mult = df['ATR_TP_Mult'].iloc[-1]
        stop_loss_price = curr_p - (current_atr * sl_mult) if current_atr > 0 else 0
        take_profit_price = curr_p + (current_atr * tp_mult) if current_atr > 0 else 0

        mode_map = {
            "UPTREND": "🚀 상승 추세장",
            "SIDEWAYS": "⚖️ 박스 횡보장",
            "VOLATILE_UP": "🔥 변동성 장세",
            "DOWNTREND": "📉 하락장"
        }
        
        mode_colors = {
            "UPTREND": "background-color: #e3fafc; color: #0c8599;",
            "SIDEWAYS": "background-color: #f3f0ff; color: #6741d9;",
            "VOLATILE_UP": "background-color: #fff0f6; color: #a61e4d;",
            "DOWNTREND": "background-color: #f8f9fa; color: #495057;"
        }

        st.markdown(f"""
            <div style='background-color:#ffffff; padding:25px; border-radius:15px; border:2px solid #e9ecef; margin-bottom:20px;'>
                <div>
                    <span class='market-badge' style='{mode_colors.get(current_mode, "")}'>
                        현재 종목 상태: {mode_map.get(current_mode, "알 수 없음")}
                    </span>
                    {f"<span class='weight-badge'>⚖️ 권장 투자 비중: {rec_weight*100:.0f}% (리스크 1% 기준)</span>" if rec_weight > 0 else ""}
                    {f"<span class='stop-loss-badge'>🛡️ 자동 손절: {stop_loss_price:,.0f}원</span>" if stop_loss_price > 0 else ""}
                    {f"<span class='take-profit-badge'>🚀 자동 익절: {take_profit_price:,.0f}원</span>" if take_profit_price > 0 else ""}
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

        st.markdown("### 🏆 AI 퀀트 전략 성과 리포트 (최근 1년, 비중 조절 반영)")
        r1, r2, r3, r4 = st.columns(4)
        with r1: st.metric("포트폴리오 CAGR", f"{cagr*100:.2f}%")
        with r2: st.metric("계좌 MDD", f"{mdd*100:.2f}%")
        with r3: st.metric("전략 승률 (Win Rate)", f"{win_rate:.1f}%")
        with r4: st.metric("단순 존버 수익률", f"{b_profit*100:.2f}%")

        if "강력 매수" in status:
            min_entry = curr_p * 0.97
            max_entry = curr_p * 1.03
            status_html = f"""
                <div class="signal-box status-buy" style="font-size:1.4rem;">
                    🔥 강력 매수 (점수: {total_score:.0f}점 / 진입선: {target_score}점)<br>
                    <span style='font-size:1.1rem; color:#f8f9fa; font-weight:normal;'>
                        👉 내일 시가 진입 허용 구간: <b>{min_entry:,.0f}원 ~ {max_entry:,.0f}원</b> (±3% 이내)<br>
                        ⚠️ 이 가격을 벗어나서 출발하면 절대 매수 금지 (갭 리스크)
                    </span>
                </div>
            """
        elif df['Global_Mode'].iloc[-1] == "DOWNTREND":
             status_html = f'<div class="signal-box status-wait" style="font-size:1.5rem;">🌍 글로벌 하락장 (신규 진입 전면 차단)</div>'
        elif current_mode == "VOLATILE_UP":
             status_html = f'<div class="signal-box status-wait" style="font-size:1.5rem;">🔥 개별 변동성 심화 (신규 진입 제한)</div>'
        else:
            status_class = "status-hold" if "보유자 영역" in status else "status-wait"
            status_html = f'<div class="signal-box {status_class}" style="font-size:1.5rem;">{status} (점수: {total_score:.0f}점 / 진입선: {target_score}점)</div>'
            
        st.markdown(f'<div class="signal-container">{status_html}</div>', unsafe_allow_html=True)
        
        if mode_df is not None and not mode_df.empty:
            with st.expander("📊 최근 1년 국면(Regime)별 분석 결과 보기"):
                st.dataframe(mode_df, use_container_width=True, hide_index=True)
                
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
    st.title(f"🕸️ 실전 타점 스캐너 (통합 리스크 관리 모드)")
    scan_mode = st.radio("검색 대상", ["📈 시가총액 우량주 스캔", "📝 내 관심종목 폴더 스캔"], horizontal=True)
    
    target_stocks = pd.DataFrame() 
    if scan_mode == "📈 시가총액 우량주 스캔":
        col_range, col_count = st.columns(2)
        
        # [🔥 신규 확장] 50개 단위로 최대 500위까지 선택 가능하게 확장!
        ranges = [f"{i*50 + 1}위 ~ {(i+1)*50}위" for i in range(10)]
        with col_range: scan_range = st.selectbox("검색 범위", ranges)
        
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
                res = analyze_sniper_backtest(t_code, trading_fee_rate)
                if res[0] is not None:
                    df_res, status, cagr, mdd, win_rate, _, t_score, _, _, _, _, rec_w = res
                    temp_results.append({'종목명': row['Name'], '종목코드': row['Code'], 'Display': row['Display'], '상태': status, '타점점수': t_score, '비중': round(rec_w * 100), '승률': round(win_rate, 1)})
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
                            {item['상태']} (획득 점수: {item['타점점수']:.0f}점) | 권장 비중: {item['비중']}% | 승률: {item['승률']}%
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            with c_btn:
                st.write("") 
                st.button("📈 상세 분석", key=f"go_{item['종목코드']}", on_click=move_to_detail, args=(item['Display'],), use_container_width=True)


# ====== [화면 3: 내 계좌(포트폴리오) 관리] ======
elif st.session_state.page_selection == "💼 내 계좌 관리 (실전 포트폴리오)":
    st.title("💼 내 실제 계좌 (포트폴리오) 관리")
    st.markdown("**종목의 실시간 변동성 및 시장 4단계 국면**에 맞춰 AI가 최적의 손/익절 타이밍을 감시합니다.")
    
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
        st.subheader("📊 보유 종목 실시간 진단 (국면 연동 자동 대응)")
        total_invested = 0
        total_current_value = 0
        
        for code, data in pf.items():
            t_code = f"{code}.KS" if not df_krx[df_krx['Code']==code].empty and df_krx[df_krx['Code']==code]['Market'].iloc[0] == 'KOSPI' else f"{code}.KQ"
            
            res = analyze_sniper_backtest(t_code, trading_fee_rate)
            if res[0] is not None:
                df_res = res[0]
                curr_price = df_res['Close'].iloc[-1]
                c_atr = df_res['ATR'].iloc[-1]
                sl_mult = df_res['ATR_SL_Mult'].iloc[-1]
                tp_mult = df_res['ATR_TP_Mult'].iloc[-1]
            else:
                curr_price = data['BuyPrice']
                c_atr = 0
                sl_mult, tp_mult = 1.5, 2.5
            
            my_sl = data['BuyPrice'] - (c_atr * sl_mult) if c_atr > 0 else data['BuyPrice'] * 0.95
            my_tp = data['BuyPrice'] + (c_atr * tp_mult) if c_atr > 0 else data['BuyPrice'] * 1.10
            
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
                        목표 익절가: {my_tp:,.0f}원 (+{tp_mult}ATR) | 한계 손절가: {my_sl:,.0f}원 (-{sl_mult}ATR)
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
    
    st.header("1. ⚖️ 포지션 사이징 (자금 관리의 핵심)")
    st.success("""
    * **1% 리스크 관리법:** 주가가 아무리 요동쳐도, 한 번 손절할 때 **내 전체 계좌 자산의 딱 1%만 잃도록** 투자 비중을 AI가 계산해 줍니다. 
    * 변동성이 큰 주식(위험)은 비중을 적게, 변동성이 작은 주식(안전)은 비중을 크게 실어 전체 포트폴리오의 생존 확률을 극대화합니다.
    """)
    
    st.header("2. 🤖 시장 상황 기반 AI 4국면 스위칭 (Dynamic Regime)")
    st.warning("""
    **개별 종목의 주가 흐름, 60일선 이격도, 변동성(ATR)을 종합하여 4가지 국면으로 나누고 타점 난이도를 조절합니다.**
    * **🚀 상승 추세장 (UPTREND):** 변동성이 낮고 추세가 뚜렷함. (점수 4점 커트라인 / 익절폭 극대화)
    * **⚖️ 박스 횡보장 (SIDEWAYS):** 주가가 60일선 근처에서 횡보함. (점수 5점 커트라인 / 짧게 치고 빠지기)
    * **📉 하락장 (DOWNTREND):** 역배열. (점수 6점 극상향 / 칼손절 대응)
    * **🔥 변동성 장세 (VOLATILE_UP):** 위아래 꼬리가 길고 급등락이 심함. (리스크 관리 차원에서 **신규 진입 원천 차단**)
    """)
    
    st.header("3. 🌍 글로벌 마켓 통합 필터")
    st.info("""
    * 개별 종목이 아무리 좋아 보여도, **코스피 시장 전체가 하락장(DOWNTREND)이면 모든 신규 매수를 원천 차단**합니다. 계좌를 지키는 최후의 보루입니다.
    """)