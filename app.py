import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import os
import json

# --- 1. PC 광폭 레이아웃 및 스타일 ---
st.set_page_config(page_title="Leo 실전 퀀트 스나이퍼", layout="wide")

st.markdown("""
    <style>
    .index-card { background-color: #f8f9fa; padding: 15px; border-radius: 12px; text-align: center; border: 1px solid #dee2e6; box-shadow: 0 2px 4px rgba(0,0,0,0.02); }
    .index-name { font-size: 0.95rem; color: #495057; font-weight: bold; margin-bottom: 5px; }
    .index-value { font-size: 1.4rem; font-weight: bold; }
    .index-change { font-size: 0.95rem; font-weight: bold; margin-top: 3px; }
    .report-card { padding: 20px; border-radius: 15px; background-color: #ffffff; border-left: 8px solid #228be6; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); }
    .signal-box { flex: 1; padding: 18px; border-radius: 12px; text-align: center; font-weight: bold; color: #adb5bd; background-color: #f8f9fa; border: 1px solid #e9ecef; font-size: 1.1rem; }
    .status-buy { background-color: #2b8a3e !important; color: white !important; border: 2px solid #51cf66 !important; }
    .status-hold { background-color: #f08c00 !important; color: white !important; border: 2px solid #ffc078 !important; }
    .status-wait { background-color: #868e96 !important; color: white !important; border: 2px solid #adb5bd !important; }
    .rank-card { padding: 15px; border-radius: 12px; border: 1px solid #dee2e6; margin-bottom: 8px; background-color: #ffffff; display: flex; flex-direction: column; justify-content: center; transition: 0.2s; }
    .rank-card:hover { border-color: #228be6; box-shadow: 0 4px 12px rgba(0,0,0,0.05); }
    .stop-loss-badge { display: inline-block; background-color: #fff5f5; color: #e03131; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 0.95rem; border: 1px solid #ffc9c9; margin-top: 10px; margin-right: 5px;}
    .take-profit-badge { display: inline-block; background-color: #f4fce3; color: #5c940d; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 0.95rem; border: 1px solid #d8f5a2; margin-top: 10px;}
    .market-badge { display: inline-block; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 0.95rem; margin-top: 10px; margin-right: 5px; border: 1px solid #ced4da; }
    .weight-badge { display: inline-block; background-color: #e6fcf5; color: #08a081; padding: 5px 12px; border-radius: 20px; font-weight: bold; font-size: 0.95rem; border: 1px solid #63e6be; margin-top: 10px; margin-right: 5px;}
    .portfolio-card { padding: 20px; border-radius: 12px; border: 1px solid #ced4da; background-color: #ffffff; box-shadow: 0 2px 4px rgba(0,0,0,0.05); margin-bottom: 15px; border-left: 6px solid #495057; }
    .pf-profit { border-left-color: #e03131 !important; }
    .pf-loss { border-left-color: #1971c2 !important; }
    .pf-title { font-size: 1.4rem; font-weight: bold; margin-bottom: 10px; }
    .pf-detail { font-size: 1.1rem; color: #495057; }
    .folder-box { border: 1px solid #ced4da; border-radius: 12px; padding: 20px; background-color: #f8f9fa; height: 100%; min-height: 300px; box-shadow: inset 0 2px 4px rgba(0,0,0,0.02); }
    </style>
    """, unsafe_allow_html=True)

# --- 5대 시장 지수 ---
def display_market_indices():
    try:
        tickers = {
            "🇰🇷 KOSPI": "^KS11", 
            "🇰🇷 KOSDAQ": "^KQ11", 
            "🇺🇸 S&P 500": "^GSPC", 
            "🇺🇸 나스닥": "^IXIC", 
            "🇺🇸 다우존스": "^DJI"
        }
        indices = yf.download(list(tickers.values()), period="5d", interval="1d", progress=False)['Close']
        cols = st.columns(5)
        
        for i, (name, ticker) in enumerate(tickers.items()):
            s = indices[ticker].dropna()
            if len(s) >= 2:
                curr = s.iloc[-1]
                prev = s.iloc[-2]
                diff = curr - prev
                rate = (diff / prev) * 100
                
                if diff > 0:
                    color = "#e03131"
                    arrow = "▲"
                elif diff < 0:
                    color = "#1971c2"
                    arrow = "▼"
                else:
                    color = "#495057"
                    arrow = "-"
                
                with cols[i]:
                    st.markdown(f"""
                        <div class="index-card">
                            <div class="index-name">{name}</div>
                            <div class="index-value" style="color:{color};">{curr:,.2f}</div>
                            <div class="index-change" style="color:{color};">{arrow} {abs(diff):,.2f} ({rate:+.2f}%)</div>
                        </div>
                    """, unsafe_allow_html=True)
    except Exception:
        st.caption("시장 지수 데이터를 불러오고 있습니다...")

# --- 데이터 관리 ---
WATCHLIST_FILE = "watchlist.json"
PORTFOLIO_FILE = "portfolio.json"
JOURNAL_FILE = "trading_journal.csv"

def load_watchlist():
    if os.path.exists(WATCHLIST_FILE):
        try:
            with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {"관심종목1": [], "관심종목2": [], "관심종목3": []}

def save_watchlist(data):
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            pass
    return {} 

def save_portfolio(data):
    with open(PORTFOLIO_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def load_journal():
    if os.path.exists(JOURNAL_FILE):
        try:
            return pd.read_csv(JOURNAL_FILE)
        except:
            pass
    cols = [
        "발굴일자", "종목명", "시장국면", "비중", "허용진입가", 
        "실제진입일", "실제매수가", "갭통과", "손절가", "익절가", 
        "매도일자", "실제매도가", "청산사유", "수익률(%)", "실현손익", 
        "원칙준수", "복기_피드백"
    ]
    return pd.DataFrame(columns=cols)

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
        info = ticker.info if ticker.info else {}
        if not info or 'marketCap' not in info:
            f_info = ticker.fast_info
            info['marketCap'] = getattr(f_info, 'market_cap', 0)
            info['regularMarketPreviousClose'] = getattr(f_info, 'previous_close', 0)
            info['fiftyTwoWeekHigh'] = getattr(f_info, 'year_high', None)
            info['fiftyTwoWeekLow'] = getattr(f_info, 'year_low', None)
        return info
    except:
        return {}

@st.cache_data(ttl=3600)
def get_kospi_filter():
    try:
        kospi = yf.download("^KS11", period="3y", interval="1d", progress=False)
        if isinstance(kospi.columns, pd.MultiIndex):
            kospi.columns = kospi.columns.get_level_values(0)
            
        kospi['MA60'] = ta.sma(kospi['Close'], length=60)
        kospi['ATR'] = ta.atr(kospi['High'], kospi['Low'], kospi['Close'], length=14)
        kospi['Volatility'] = kospi['ATR'] / kospi['Close']
        kospi['MA60_Slope'] = kospi['MA60'].diff(5)
        
        cond_up = (kospi['Close'] > kospi['MA60']) & (kospi['MA60_Slope'] > 0)
        cond_down = kospi['Close'] < kospi['MA60']
        
        kospi['Global_Mode'] = np.select(
            [cond_up, cond_down], 
            ["UPTREND", "DOWNTREND"], 
            default="SIDEWAYS"
        )
        return kospi[['Global_Mode']]
    except:
        return pd.DataFrame()

def move_to_detail(stock_display):
    st.session_state.current_selection = stock_display
    st.session_state.page_selection = "📊 단일 종목 분석"

if 'current_selection' not in st.session_state: 
    st.session_state.current_selection = df_krx['Display'].iloc[0]
if 'page_selection' not in st.session_state: 
    st.session_state.page_selection = "📊 단일 종목 분석"
if 'search_results' not in st.session_state: 
    st.session_state.search_results = []

# --- V3.1 타점 엔진 (로직 완화 버전) ---
def analyze_sniper_backtest(symbol, fee_rate):
    try:
        df = yf.download(symbol, period="3y", interval="1d", progress=False) 
        if df.empty or len(df) < 60: 
            return None, "에러", 0, 0, 0, 0, None, 0, 0, 0, None, 0
            
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
        df = df.ffill().dropna()

        kospi_df = get_kospi_filter()
        if not kospi_df.empty:
            df['Global_Mode'] = df.join(kospi_df, how='left')['Global_Mode'].ffill().fillna("SIDEWAYS")
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
            [3, 4, 6, 6], 
            default=6
        )
        
        df['ATR_SL_Mult'] = np.select(
            [df['Market_Mode'] == "UPTREND", df['Market_Mode'] == "SIDEWAYS", df['Market_Mode'] == "VOLATILE_UP", df['Market_Mode'] == "DOWNTREND"], 
            [2.5, 1.5, 2.0, 1.2], 
            default=1.5
        )
        
        df['ATR_TP_Mult'] = np.select(
            [df['Market_Mode'] == "UPTREND", df['Market_Mode'] == "SIDEWAYS", df['Market_Mode'] == "VOLATILE_UP", df['Market_Mode'] == "DOWNTREND"], 
            [4.0, 2.0, 3.0, 2.0], 
            default=2.5
        )

        df['Vol_MA'] = ta.sma(df['Volume'], length=20)
        macd_calc = ta.macd(df['Close'])
        df['MACD_Line'] = macd_calc.iloc[:, 0]
        df['MACD_Signal'] = macd_calc.iloc[:, 2]
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        
        score_ma = np.where(df['MA_S'] > df['MA_L'], 3, 0)
        score_macd = np.where(df['MACD_Line'] > df['MACD_Signal'], 2, 0)
        score_vol = np.where((df['Volume'] > df['Vol_MA'] * 1.2) & (df['Close'] > df['Open']), 2, 0) 
        score_mfi = np.where(df['MFI'] > 50, 2, 0)
        
        df['Total_Score'] = score_ma + score_macd + score_vol + score_mfi
        
        cond_score = df['Total_Score'] >= df['Target_Score']
        cond_pullback = df['Close'] < (df['MA_S'] * 1.05)
        cond_overheat = df['Close'].pct_change(10) < 0.30
        cond_trigger = (df['Close'] > df['Close'].shift(1)) | (df['Close'] > df['Open']) 
        cond_allow_local = df['Market_Mode'] != "VOLATILE_UP"
        cond_allow_global = df['Global_Mode'] != "DOWNTREND" 
        
        df['Buy_Signal'] = cond_score & cond_pullback & cond_overheat & cond_trigger & cond_allow_local & cond_allow_global

        positions = np.zeros(len(df))
        trade_actions = np.zeros(len(df))
        strategy_returns = np.zeros(len(df))
        
        in_position = False
        total_trades = 0
        winning_trades = 0
        entry_price = 0.0
        sl_price = 0.0
        tp_price = 0.0
        current_position_size = 0.0
        
        closes = df['Close'].values
        opens = df['Open'].values
        highs = df['High'].values
        lows = df['Low'].values
        ma20s = df['MA_20'].values
        atrs = df['ATR'].values
        buy_signals = df['Buy_Signal'].values
        sl_mults = df['ATR_SL_Mult'].values
        tp_mults = df['ATR_TP_Mult'].values
        
        for i in range(1, len(df)):
            if not in_position:
                if buy_signals[i-1]: 
                    gap = (opens[i] / closes[i-1]) - 1 if closes[i-1] > 0 else 0
                    if -0.03 <= gap <= 0.03:
                        in_position = True
                        entry_price = opens[i] 
                        sl_price = entry_price - (atrs[i-1] * sl_mults[i-1])
                        tp_price = entry_price + (atrs[i-1] * tp_mults[i-1])
                        risk_per_share = entry_price - sl_price
                        
                        if risk_per_share > 0:
                            current_position_size = min(0.01 / (risk_per_share / entry_price), 1.0)
                        else:
                            current_position_size = 1.0
                            
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
                    strategy_returns[i] = current_position_size * ((exit_price - closes[i-1]) / closes[i-1])
                else:
                    strategy_returns[i] = current_position_size * (positions[i-1] * (closes[i] - closes[i-1]) / closes[i-1])
                    
            if trade_actions[i] == 1:
                strategy_returns[i] = 0
                
            if trade_actions[i] != 0:
                strategy_returns[i] -= (fee_rate / 2) * current_position_size
                
        df['Position'] = positions
        df['Trade_Action'] = trade_actions
        df['Strategy_Return'] = strategy_returns
        
        df_1y = df.iloc[-250:].copy()
        
        cum_ret = (1 + df_1y['Strategy_Return']).cumprod()
        running_max = cum_ret.cummax()
        mdd = ((cum_ret - running_max) / running_max).min()
        cagr = (cum_ret.iloc[-1] ** (252 / len(df_1y))) - 1 if cum_ret.iloc[-1] > 0 and len(df_1y) > 0 else 0
        win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
        b_profit = (df_1y['Close'].iloc[-1] / df_1y['Close'].iloc[0]) - 1 if len(df_1y) > 0 else 0
        
        last = df.iloc[-1]
        
        if df['Buy_Signal'].iloc[-1]:
            status = "🔥 강력 매수 대기"
        elif last['Position'] == 1:
            status = "🛡️ 보유자 영역 (Hold)"
        else:
            status = "👀 관망"
            
        curr_risk_pct = (last['ATR'] * last['ATR_SL_Mult']) / df['Close'].iloc[-1]
        rec_weight = min(0.01 / curr_risk_pct, 1.0) if curr_risk_pct > 0 else 1.0
        
        return df_1y, status, cagr, mdd, win_rate, b_profit, last['Total_Score'], last['Target_Score'], last['Market_Mode'], last['ATR'], None, rec_weight
    except:
        return None, "에러", 0, 0, 0, 0, None, 0, 0, 0, None, 0

# ====== [메인 화면 UI] ======
display_market_indices() 
st.markdown("<br>", unsafe_allow_html=True)

with st.sidebar:
    st.header("📌 시스템 메뉴")
    st.radio(
        "이동할 페이지 선택", 
        ["📊 단일 종목 분석", "🔍 조건 검색기 (스크리너)", "💼 내 계좌 관리 (실전 포트폴리오)", "📓 실전 매매 일지", "📂 관심종목 관리", "📖 주식 & 전략 백과사전"], 
        key="page_selection"
    )
    
    st.divider()
    st.header("🤖 리스크 관리 통합 시스템")
    
    kospi_df_global = get_kospi_filter()
    global_mode = kospi_df_global['Global_Mode'].iloc[-1] if not kospi_df_global.empty else "SIDEWAYS"
    
    mode_map = {
        "UPTREND": "🇰🇷 코스피 종합: 대세 상승장", 
        "SIDEWAYS": "🇰🇷 코스피 종합: 혼조세 (박스권)", 
        "DOWNTREND": "🇰🇷 코스피 종합: 대세 하락장 (신규 매수 차단)"
    }
    mode_text = mode_map.get(global_mode, "알 수 없음")
    st.info(f"**{mode_text}**")
    
    st.divider()
    trading_fee_rate = st.number_input("왕복 수수료+세금 (%)", value=0.2, step=0.05) / 100

# ====== 화면 1: 단일 종목 ======
if st.session_state.page_selection == "📊 단일 종목 분석":
    all_names = df_krx['Display'].tolist()
    
    search_stock = st.selectbox(
        "🎯 분석할 특정 종목을 고르세요", 
        options=all_names, 
        index=all_names.index(st.session_state.current_selection) if st.session_state.current_selection in all_names else 0
    )
    
    if search_stock != st.session_state.current_selection: 
        st.session_state.current_selection = search_stock
        st.rerun()

    stock_info = df_krx[df_krx['Display'] == search_stock].iloc[0]
    ticker_sym = f"{stock_info['Code']}.KS" if stock_info['Market'] == 'KOSPI' else f"{stock_info['Code']}.KQ"

    df, status, cagr, mdd, win_rate, b_profit, total_score, target_score, current_mode, current_atr, _, rec_weight = analyze_sniper_backtest(ticker_sym, trading_fee_rate)
    details = get_detailed_info(ticker_sym)

    if df is not None:
        curr_p = df['Close'].iloc[-1]
        prev_p = details.get('regularMarketPreviousClose', df['Close'].iloc[-2] if len(df) > 1 else curr_p)
        
        diff = curr_p - prev_p
        rate = ((curr_p - prev_p) / prev_p) * 100 if prev_p > 0 else 0
        
        if diff > 0:
            price_color = "#e03131"
            arrow_icon = "▲"
        elif diff < 0:
            price_color = "#1971c2"
            arrow_icon = "▼"
        else:
            price_color = "#212529"
            arrow_icon = "-"
            
        sl_mult = df['ATR_SL_Mult'].iloc[-1]
        tp_mult = df['ATR_TP_Mult'].iloc[-1]
        
        stop_loss_price = curr_p - (current_atr * sl_mult) if current_atr > 0 else 0
        take_profit_price = curr_p + (current_atr * tp_mult) if current_atr > 0 else 0
        
        # 재무 및 52주 지표 포맷팅
        mcap = details.get('marketCap', 0)
        if mcap > 0:
            mcap_str = f"{int(mcap // 1000000000000)}조 {int((mcap % 1000000000000) // 100000000)}억"
        else:
            mcap_str = "N/A"
            
        high52 = details.get('fiftyTwoWeekHigh')
        low52 = details.get('fiftyTwoWeekLow')
        per = details.get('trailingPE')
        pbr = details.get('priceToBook')
        
        h52_str = f"{high52:,.0f}원" if high52 else "N/A"
        l52_str = f"{low52:,.0f}원" if low52 else "N/A"
        per_str = f"{per:.2f}배" if per else "N/A"
        pbr_str = f"{pbr:.2f}배" if pbr else "N/A"
        
        mode_label_map = {
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

        weight_badge_html = f"<span class='weight-badge'>⚖️ 권장 투자 비중: {rec_weight*100:.0f}%</span>" if rec_weight > 0 else ""
        stop_badge_html = f"<span class='stop-loss-badge'>🛡️ 자동 손절: {stop_loss_price:,.0f}원</span>" if stop_loss_price > 0 else ""
        profit_badge_html = f"<span class='take-profit-badge'>🚀 자동 익절: {take_profit_price:,.0f}원</span>" if take_profit_price > 0 else ""

        # [버그 수정 완료] 들여쓰기를 제거하여 HTML이 깨지지 않게 보호합니다.
        st.markdown(f"""
<div style='background-color:#ffffff; padding:25px; border-radius:15px; border:2px solid #e9ecef; margin-bottom:20px;'>
<div style='margin-bottom:15px;'>
<span class='market-badge' style='{mode_colors.get(current_mode, "")}'>현재 종목 상태: {mode_label_map.get(current_mode, "알 수 없음")}</span>
{weight_badge_html}
{stop_badge_html}
{profit_badge_html}
</div>
<div style='display:flex; align-items:baseline; gap:20px;'>
<span style='font-size:2.2rem; font-weight:bold; color:#343a40;'>{stock_info['Name']}</span>
<span style='font-size:3.8rem; font-weight:bold; color:{price_color};'>{curr_p:,.0f}원</span>
<span style='font-size:2rem; font-weight:bold; color:{price_color};'>{arrow_icon} {abs(diff):,.0f} ({rate:+.2f}%)</span>
</div>
<div style='margin-top:20px; padding-top:15px; border-top:1px solid #f1f3f5; display:flex; gap:40px; color:#495057;'>
<div><span style='font-size:0.95rem; color:#868e96;'>시가총액</span><br><b style='font-size:1.1rem;'>{mcap_str}</b></div>
<div><span style='font-size:0.95rem; color:#868e96;'>52주 최고</span><br><b style='font-size:1.1rem; color:#e03131;'>{h52_str}</b></div>
<div><span style='font-size:0.95rem; color:#868e96;'>52주 최저</span><br><b style='font-size:1.1rem; color:#1971c2;'>{l52_str}</b></div>
<div><span style='font-size:0.95rem; color:#868e96;'>PER</span><br><b style='font-size:1.1rem;'>{per_str}</b></div>
<div><span style='font-size:0.95rem; color:#868e96;'>PBR</span><br><b style='font-size:1.1rem;'>{pbr_str}</b></div>
</div>
</div>
""", unsafe_allow_html=True)

        if "강력 매수" in status:
            min_entry = curr_p * 0.97
            max_entry = curr_p * 1.03
            status_html = f"""
            <div class="signal-box status-buy" style="font-size:1.4rem;">
                🔥 강력 매수 (점수: {total_score:.0f}점 / 진입선: {target_score}점)<br>
                <span style='font-size:1.1rem; color:#f8f9fa; font-weight:normal;'>👉 내일 시가 진입 허용 구간: <b>{min_entry:,.0f}원 ~ {max_entry:,.0f}원</b> (±3% 이내)</span>
            </div>
            """
        elif df['Global_Mode'].iloc[-1] == "DOWNTREND": 
            status_html = f'<div class="signal-box status-wait" style="font-size:1.5rem;">🇰🇷 종합 하락장 (신규 진입 차단)</div>'
        elif current_mode == "VOLATILE_UP": 
            status_html = f'<div class="signal-box status-wait" style="font-size:1.5rem;">🔥 개별 변동성 심화 (진입 제한)</div>'
        else: 
            status_class = "status-hold" if "보유자 영역" in status else "status-wait"
            status_html = f'<div class="signal-box {status_class}" style="font-size:1.5rem;">{status} (점수: {total_score:.0f}점 / 진입선: {target_score}점)</div>'
            
        st.markdown(f'<div class="signal-container">{status_html}</div>', unsafe_allow_html=True)
        st.line_chart(df[['Close', 'MA_S', 'MA_20']], height=450)

        st.divider()
        col_f, col_b = st.columns([2, 1])
        f_name = col_f.selectbox("폴더 선택", ["관심종목1", "관심종목2", "관심종목3"], label_visibility="collapsed")
        
        if col_b.button("⭐ 현재 종목 추가", use_container_width=True):
            wl = load_watchlist()
            if stock_info['Code'] not in wl[f_name]: 
                wl[f_name].append(stock_info['Code'])
                save_watchlist(wl)
                st.toast(f"✅ {stock_info['Name']} 저장 완료!")

# ====== 화면 2: 스캐너 (관심종목 10개 출력) ======
elif st.session_state.page_selection == "🔍 조건 검색기 (스크리너)":
    st.title("🔍 실전 타점 스캐너")
    
    scan_target = st.radio("검색 대상 선택", ["전체 시장 (순위별 100개)", "⭐ 내 관심종목 전체 스캔"], horizontal=True)
    
    if scan_target == "전체 시장 (순위별 100개)":
        scan_range = st.selectbox("검색 범위", [f"{i*100 + 1}위 ~ {(i+1)*100}위" for i in range(10)])
    else:
        scan_range = None
        st.info("폴더 1, 2, 3에 등록된 모든 관심종목을 한 번에 스캔합니다.")
    
    if st.button("🚀 타점 검색 실행", type="primary", use_container_width=True):
        if scan_target == "전체 시장 (순위별 100개)":
            start_idx = int(scan_range.split("위")[0].strip()) - 1
            target_stocks = df_krx.iloc[start_idx:start_idx+100] 
        else:
            wl = load_watchlist()
            all_wl_codes = list(set(wl["관심종목1"] + wl["관심종목2"] + wl["관심종목3"]))
            target_stocks = df_krx[df_krx['Code'].isin(all_wl_codes)]
            
        if target_stocks.empty:
            st.warning("스캔할 종목이 없습니다. (관심종목이 비어있을 수 있습니다)")
        else:
            my_bar = st.progress(0, text=f"{len(target_stocks)}개 종목 스캔 중...")
            temp_results = []
            
            for idx, (i, row) in enumerate(target_stocks.iterrows()):
                t_code = f"{row['Code']}.KS" if row['Market'] == 'KOSPI' else f"{row['Code']}.KQ"
                res = analyze_sniper_backtest(t_code, trading_fee_rate)
                if res[0] is not None: 
                    temp_results.append({
                        'Name': row['Name'], 
                        'Code': row['Code'], 
                        'Display': row['Display'], 
                        'Status': res[1], 
                        'Score': res[6], 
                        'Weight': round(res[11]*100)
                    })
                my_bar.progress((idx + 1) / len(target_stocks))
                
            my_bar.empty()
            st.session_state.search_results = sorted(temp_results, key=lambda x: (0 if "강력" in x['Status'] else 1, -x['Score']))[:10]
    
    if st.session_state.search_results:
        st.subheader("🏆 스캔 결과 (상위 10개)")
        for item in st.session_state.search_results:
            c_info, c_btn, c_wl = st.columns([3, 1, 1.5])
            with c_info: 
                st.markdown(f"""
                    <div class='rank-card'>
                        <b>{item['Name']}</b> ({item['Code']}) <br> 
                        {item['Status']} | 점수: {item['Score']} | 비중: {item['Weight']}%
                    </div>
                """, unsafe_allow_html=True)
            with c_btn:
                st.write("")
                st.button("상세분석", key=f"go_{item['Code']}", on_click=move_to_detail, args=(item['Display'],), use_container_width=True)
            with c_wl:
                st.write("")
                sub_c1, sub_c2 = st.columns([1, 1])
                with sub_c1: 
                    wl_folder = st.selectbox("폴더", ["관심종목1", "관심종목2", "관심종목3"], key=f"sel_{item['Code']}", label_visibility="collapsed")
                with sub_c2:
                    if st.button("⭐추가", key=f"add_{item['Code']}", use_container_width=True):
                        wl = load_watchlist()
                        if item['Code'] not in wl[wl_folder]: 
                            wl[wl_folder].append(item['Code'])
                            save_watchlist(wl)
                            st.toast(f"✅ 저장 완료!")

# ====== 화면 3: 내 계좌 ======
elif st.session_state.page_selection == "💼 내 계좌 관리 (실전 포트폴리오)":
    st.title("💼 내 실제 계좌 (포트폴리오) 관리")
    pf = load_portfolio()
    
    with st.expander("➕ 내 계좌에 주식 추가하기", expanded=True):
        col_s, col_p, col_q, col_b = st.columns([3, 2, 2, 1])
        add_stock = col_s.selectbox("매수한 종목", options=df_krx['Display'].tolist(), label_visibility="collapsed")
        buy_price = col_p.number_input("매입 단가 (원)", min_value=1, value=50000, step=100)
        quantity = col_q.number_input("보유 수량 (주)", min_value=1, value=10, step=1)
        
        if col_b.button("저장"):
            code = add_stock.split("(")[-1].replace(")", "")
            pf[code] = {
                "Name": add_stock.split("(")[0].strip(), 
                "BuyPrice": buy_price, 
                "Quantity": quantity
            }
            save_portfolio(pf)
            st.rerun()
            
    st.divider()
    if not pf: 
        st.info("등록된 주식이 없습니다.")
    else:
        for code, data in pf.items():
            t_code = f"{code}.KS" if not df_krx[df_krx['Code']==code].empty and df_krx[df_krx['Code']==code]['Market'].iloc[0] == 'KOSPI' else f"{code}.KQ"
            res = analyze_sniper_backtest(t_code, trading_fee_rate)
            
            if res[0] is not None: 
                curr_price = res[0]['Close'].iloc[-1]
                c_atr = res[0]['ATR'].iloc[-1]
                sl_mult = res[0]['ATR_SL_Mult'].iloc[-1]
                tp_mult = res[0]['ATR_TP_Mult'].iloc[-1]
            else: 
                curr_price = data['BuyPrice']
                c_atr = 0
                sl_mult = 1.5
                tp_mult = 2.5
                
            my_sl = (data['BuyPrice'] - (c_atr * sl_mult) if c_atr > 0 else data['BuyPrice'] * 0.95)
            my_tp = (data['BuyPrice'] + (c_atr * tp_mult) if c_atr > 0 else data['BuyPrice'] * 1.10)
            
            profit_amt = (curr_price * data['Quantity']) - (data['BuyPrice'] * data['Quantity'])
            profit_rate = (profit_amt / (data['BuyPrice'] * data['Quantity'])) * 100
            
            if curr_price >= my_tp: 
                ai_action = "🚀 수익 실현 권장"
                card_class = "pf-profit"
                act_color = "#5c940d"
            elif curr_price <= my_sl: 
                ai_action = "⚠️ 칼손절 필요"
                card_class = "pf-loss"
                act_color = "#e03131"
            else: 
                ai_action = "✅ 홀딩 (관망)"
                card_class = "portfolio-card"
                act_color = "#2b8a3e"
                
            color = "#e03131" if profit_rate > 0 else ("#1971c2" if profit_rate < 0 else "#495057")
            
            st.markdown(f"""
                <div class='portfolio-card {card_class}'>
                    <div style='display:flex; justify-content:space-between;'>
                        <div class='pf-title'>{data['Name']}</div>
                        <div style='color:{act_color}; font-weight:bold;'>{ai_action}</div>
                    </div>
                    <div style='display:flex; justify-content:space-between; margin-top:10px;'>
                        <div class='pf-detail'>매입: {data['BuyPrice']:,.0f}원</div>
                        <div class='pf-detail'>현재가: {curr_price:,.0f}원</div>
                        <div class='pf-detail' style='color:{color}; font-weight:bold;'>수익률: {profit_rate:+.2f}% ({profit_amt:+,.0f}원)</div>
                    </div>
                    <div style='margin-top:10px; font-size:0.9rem; color:#868e96;'>
                        목표가: {my_tp:,.0f}원 | 손절가: {my_sl:,.0f}원
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
            if st.button("목록에서 삭제", key=f"sell_{code}"): 
                del pf[code]
                save_portfolio(pf)
                st.rerun()

# ====== 화면 4: 매매 일지 ======
elif st.session_state.page_selection == "📓 실전 매매 일지":
    st.title("📓 포워드 테스팅 (실전 매매 일지)")
    journal_df = load_journal()
    
    edited_df = st.data_editor(
        journal_df, 
        num_rows="dynamic", 
        use_container_width=True, 
        height=500, 
        column_config={
            "시장국면": st.column_config.SelectboxColumn("📈 시장국면", options=["상승장", "횡보장", "하락장"]), 
            "갭통과": st.column_config.SelectboxColumn("🚪 갭통과", options=["O", "X"]), 
            "원칙준수": st.column_config.SelectboxColumn("🤖 원칙준수", options=["O", "X"]), 
            "청산사유": st.column_config.SelectboxColumn("결과", options=["- (보유중)", "목표가 익절", "손절가 손절", "추세 이탈 방어", "뇌동매매"])
        }
    )
    
    if st.button("💾 일지 파일 저장하기", use_container_width=True, type="primary"): 
        edited_df.to_csv(JOURNAL_FILE, index=False, encoding='utf-8-sig')
        st.success("✅ 저장 완료!")

# ====== 화면 5: 관심종목 관리 ======
elif st.session_state.page_selection == "📂 관심종목 관리":
    st.title("📂 내 관심종목 관리")
    wl = load_watchlist()
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
                    
                    with c_n: 
                        st.markdown(f"**{name}** ({code})", unsafe_allow_html=True)
                    with c_b: 
                        if st.button("❌", key=f"del_{f_name}_{code}"): 
                            wl[f_name].remove(code)
                            save_watchlist(wl)
                            st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ===== 화면 6: 백과사전 & 실전 매뉴얼 =====
elif st.session_state.page_selection == "📖 주식 & 전략 백과사전":
    st.title("📖 Leo의 퀀트 투자 백과사전 & 실전 매뉴얼")
    
    tab1, tab2 = st.tabs(["🧠 퀀트 전략 핵심 원리", "📱 키움증권 실전 자동매매 가이드"])
    
    with tab1:
        st.header("1. ⚖️ 포지션 사이징 (자금 관리의 핵심)")
        st.success("""
        * **1% 리스크 관리법:** 주가가 요동쳐도, 한 번 손절할 때 전체 계좌의 딱 1%만 잃도록 비중을 조절합니다.
        * 변동성이 큰 주식은 비중을 적게, 얌전한 주식은 비중을 크게 실어 생존 확률을 극대화합니다.
        """)
        st.header("2. 🤖 4국면 스위칭 (Dynamic Regime)")
        st.warning("""
        * **🚀 상승장:** 타점 3점 커트라인 / 익절폭 극대화
        * **⚖️ 횡보장:** 타점 4점 커트라인 / 짧게 단타 (박스권 하단 매수, 상단 매도)
        * **📉 하락장:** 역배열 방어 최우선
        * **🔥 변동성장:** 꼬리가 길고 급등락이 심한 경우, 신규 진입 원천 차단
        """)
        st.header("3. 🇰🇷 종합 마켓 통합 필터")
        st.info("* 코스피 시장 전체가 하락장(Downtrend)이면, 숲이 불타고 있다고 판단하여 모든 신규 매수를 원천 차단합니다.")
        
    with tab2:
        st.header("📱 영웅문S# 100% 자동매매 세팅법 (직장인 퀀트 필수)")
        
        with st.expander("☀️ 1단계: 살 때 (신규종목 시가 자동매수)", expanded=True):
            st.markdown("""
            **언제?** 전날 밤 ~ 당일 오전 8시 30분 사이 (출근 전)
            **목적:** 아침 9시 시가가 '진입 허용 구간' 안에 들어올 때만 기계적으로 매수
            
            1. **경로:** 앱 하단 [메뉴] ➔ [주식] ➔ [주문] ➔ **[자동감시주문]**
            2. 상단 탭에서 **[신규종목]** 선택 ➔ **[조건추가]** 클릭 ➔ 스캔한 타겟 종목 검색
            3. **감시 조건:** '현재가'가 프로그램이 알려준 **[진입 허용 구간]의 최저가 이상 ~ 최고가 이하**일 때로 설정
            4. **주문 설정:** 종류는 무조건 **[시장가]**, 수량은 권장 비중에 맞춰 입력
            5. **실행:** [조건저장] 후 반드시 **[▶ 감시시작]** 버튼 누르기 (유효기간: 1일)
            """)
            
        with st.expander("🛡️ 2단계: 팔 때 (잔고편입 스탑로스)", expanded=True):
            st.markdown("""
            **언제?** 주식이 매수 체결된 것을 확인한 직후 (업무 중 잠깐)
            **목적:** 장중 폭락(손절)과 급등(익절)에 대비해 인간의 감정을 배제하고 방어막 치기
            
            1. **경로:** [메뉴] ➔ [주식] ➔ [주문] ➔ **[자동감시주문]**
            2. 상단 탭에서 **[잔고편입]** 선택 ➔ 방금 체결된 내 주식 클릭
            3. **감시 조건:** - **이익실현 (익절):** 체크 후, 프로그램의 **[목표 익절가]** 입력
               - **이익보존/손실제한 (손절):** 체크 후, 프로그램의 **[한계 손절가]** 입력 (★제일 중요)
            4. **주문 설정:** 종류는 무조건 **[시장가]**, 수량은 **[100%]** (전량 매도)
            5. **실행:** [조건저장] 후 **[▶ 감시시작]** 버튼 누르기 (유효기간: 최장 90일)
            """)