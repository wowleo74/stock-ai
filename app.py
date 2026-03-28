import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import numpy as np
import os
import json
from datetime import datetime, timedelta

# ==========================================================
# --- [섹션 0] 시스템 초기화 및 세션 상태 설정 (에러 방지) ---
# ==========================================================

# 프로그램이 처음 실행될 때 메뉴와 상태를 미리 정의합니다.
# 이렇게 해야 'page_selection' 에러가 나지 않습니다.

if 'page_selection' not in st.session_state:
    st.session_state['page_selection'] = "📊 단일 종목 분석"

if 'current_selection' not in st.session_state:
    st.session_state['current_selection'] = "삼성전자 (005930)"

if 'search_results' not in st.session_state:
    st.session_state['search_results'] = []

# ==========================================================
# --- [섹션 1] 전체 페이지 레이아웃 및 스타일 정의 ---
# ==========================================================

st.set_page_config(
    page_title="Leo 퀀트 스나이퍼 v4.4 (최종)",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 커스텀 CSS 정의 (화면을 예쁘게 만들기 위한 코드)
st.markdown("""
    <style>
    /* 전체 배경색상 설정 */
    .main {
        background-color: #f8f9fa;
    }

    /* 상단 지수 카드 디자인 */
    .index-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        text-align: center;
        border: 1px solid #e9ecef;
        box-shadow: 0 4px 6px rgba(0,0,0,0.02);
    }
    .index-name {
        font-size: 1.0rem;
        color: #495057;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .index-value {
        font-size: 1.6rem;
        font-weight: bold;
    }
    .index-change {
        font-size: 1.0rem;
        font-weight: bold;
        margin-top: 5px;
    }

    /* 종목 상태 표시 배지 */
    .market-badge {
        display: inline-block;
        padding: 6px 15px;
        border-radius: 25px;
        font-weight: bold;
        font-size: 0.95rem;
        margin-right: 8px;
        border: 1px solid #dee2e6;
        background-color: #f1f3f5;
    }
    .stop-loss-badge {
        display: inline-block;
        background-color: #fff5f5;
        color: #e03131;
        padding: 6px 15px;
        border-radius: 25px;
        font-weight: bold;
        font-size: 0.95rem;
        border: 1px solid #ffc9c9;
        margin-right: 8px;
    }
    .take-profit-badge {
        display: inline-block;
        background-color: #f4fce3;
        color: #5c940d;
        padding: 6px 15px;
        border-radius: 25px;
        font-weight: bold;
        font-size: 0.95rem;
        border: 1px solid #d8f5a2;
        margin-right: 8px;
    }
    .weight-badge {
        display: inline-block;
        background-color: #e6fcf5;
        color: #08a081;
        padding: 6px 15px;
        border-radius: 25px;
        font-weight: bold;
        font-size: 0.95rem;
        border: 1px solid #63e6be;
    }

    /* 백테스팅 성적표 박스 */
    .stat-box {
        background-color: #ffffff;
        border: 1px solid #e9ecef;
        padding: 20px;
        border-radius: 12px;
        text-align: center;
        flex: 1;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    .stat-label {
        font-size: 0.9rem;
        color: #868e96;
        margin-bottom: 8px;
    }
    .stat-value {
        font-size: 1.4rem;
        font-weight: bold;
        color: #212529;
    }

    /* 시그널 알림 상자 */
    .signal-box {
        padding: 25px;
        border-radius: 15px;
        text-align: center;
        font-weight: bold;
        font-size: 1.3rem;
        margin-bottom: 25px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
    }
    .status-buy { background-color: #2b8a3e !important; color: white !important; border: 2px solid #51cf66 !important; }
    .status-hold { background-color: #f08c00 !important; color: white !important; border: 2px solid #ffc078 !important; }
    .status-wait { background-color: #868e96 !important; color: white !important; border: 2px solid #adb5bd !important; }

    /* 포트폴리오 관리 카드 */
    .portfolio-card {
        padding: 25px;
        border-radius: 15px;
        background-color: #ffffff;
        border: 1px solid #dee2e6;
        margin-bottom: 20px;
        border-left: 10px solid #495057;
        box-shadow: 0 4px 6px rgba(0,0,0,0.03);
    }

    /* 스크리너 내 랭킹 카드 */
    .rank-card {
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #dee2e6;
        margin-bottom: 12px;
        background-color: #ffffff;
        transition: 0.3s;
    }
    .rank-card:hover {
        border-color: #228be6;
        box-shadow: 0 6px 15px rgba(0,0,0,0.1);
    }

    /* 관심종목 폴더 섹션 */
    .folder-box {
        border: 1px solid #dee2e6;
        border-radius: 15px;
        padding: 25px;
        background-color: #ffffff;
        min-height: 450px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.02);
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================================
# --- [섹션 2] 데이터 유틸리티 함수 정의 ---
# ==========================================================

def display_market_header():
    """상단에 실시간 시장 지수 띠를 출력하는 함수입니다."""
    try:
        # 주요 지수 티커 정의
        ticker_list = {
            "🇰🇷 KOSPI": "^KS11", 
            "🇰🇷 KOSDAQ": "^KQ11", 
            "🇺🇸 S&P 500": "^GSPC", 
            "🇺🇸 나스닥": "^IXIC", 
            "🇺🇸 다우존스": "^DJI"
        }
        
        # 야후 파이낸스에서 데이터 로드
        data = yf.download(list(ticker_list.values()), period="5d", interval="1d", progress=False)['Close']
        
        # 5칸 레이아웃 생성
        market_cols = st.columns(5)
        
        for i, (name, symbol) in enumerate(ticker_list.items()):
            series = data[symbol].dropna()
            
            if len(series) >= 2:
                current_val = series.iloc[-1]
                previous_val = series.iloc[-2]
                change_val = current_val - previous_val
                change_pct = (change_val / previous_val) * 100
                
                # 상승/하락에 따른 색상 설정
                if change_val > 0:
                    text_clr = "#e03131" # 빨간색
                    icon = "▲"
                elif change_val < 0:
                    text_clr = "#1971c2" # 파란색
                    icon = "▼"
                else:
                    text_clr = "#495057" # 회색
                    icon = "-"
                
                with market_cols[i]:
                    st.markdown(f"""
                        <div class="index-card">
                            <div class="index-name">{name}</div>
                            <div class="index-value" style="color:{text_clr};">{current_val:,.2f}</div>
                            <div class="index-change" style="color:{text_clr};">
                                {icon} {abs(change_val):,.2f} ({change_pct:+.2f}%)
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
    except Exception as e:
        st.caption(f"시장 데이터 로드 오류: {e}")

# --- 파일 관리 시스템 ---
# 사용자 데이터를 로컬 파일에 저장하고 불러오는 함수들입니다.

WATCHLIST_PATH = "leo_user_watchlist.json"
PORTFOLIO_PATH = "leo_user_portfolio.json"
JOURNAL_PATH = "leo_user_journal.csv"

def get_watchlist():
    """저장된 관심종목 폴더를 불러옵니다."""
    if os.path.exists(WATCHLIST_PATH):
        try:
            with open(WATCHLIST_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {"관심종목1": [], "관심종목2": [], "관심종목3": []}
    return {"관심종목1": [], "관심종목2": [], "관심종목3": []}

def save_watchlist_to_file(data):
    """관심종목 폴더를 파일에 저장합니다."""
    with open(WATCHLIST_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_portfolio():
    """보유 종목 리스트를 불러옵니다."""
    if os.path.exists(PORTFOLIO_PATH):
        try:
            with open(PORTFOLIO_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_portfolio_to_file(data):
    """보유 종목 리스트를 파일에 저장합니다."""
    with open(PORTFOLIO_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def get_journal_data():
    """매매 일지 데이터를 불러옵니다."""
    if os.path.exists(JOURNAL_PATH):
        try:
            return pd.read_csv(JOURNAL_PATH)
        except:
            pass
    
    # 파일이 없거나 오류 시 빈 데이터프레임 생성
    cols = ["발굴일자", "종목명", "시장국면", "비중", "허용진입가", "실제진입일", "실제매수가", "손절가", "익절가", "청산사유", "수익률(%)"]
    return pd.DataFrame(columns=cols)

# --- 종목 마스터 데이터 관리 ---

@st.cache_data
def get_krx_stock_master():
    """KRX 전체 종목 리스트를 캐시하여 로드합니다."""
    if os.path.exists('krx_stocks.csv'):
        master_df = pd.read_csv('krx_stocks.csv')
        master_df['Code'] = master_df['Code'].astype(str).str.zfill(6)
        master_df['Display'] = master_df['Name'] + " (" + master_df['Code'] + ")"
        return master_df
    # 파일이 없을 경우 최소한의 샘플 데이터 반환
    return pd.DataFrame([{'Code': '005930', 'Name': '삼성전자', 'Market': 'KOSPI', 'Display': '삼성전자 (005930)'}])

df_krx_master = get_krx_stock_master()

@st.cache_data(ttl=3600)
def fetch_stock_meta_info(stock_symbol):
    """야후 파이낸스에서 종목의 상세 정보(시총, PER 등)를 가져옵니다."""
    try:
        ticker_obj = yf.Ticker(stock_symbol)
        meta = ticker_obj.info
        
        # 일반적인 info 데이터가 비어있을 경우 대비
        if not meta or 'marketCap' not in meta:
            fast = ticker_obj.fast_info
            meta = {
                'marketCap': getattr(fast, 'market_cap', 0),
                'regularMarketPreviousClose': getattr(fast, 'previous_close', 0),
                'fiftyTwoWeekHigh': getattr(fast, 'year_high', 0),
                'fiftyTwoWeekLow': getattr(fast, 'year_low', 0),
                'trailingPE': getattr(ticker_obj.info, 'trailingPE', None),
                'priceToBook': getattr(ticker_obj.info, 'priceToBook', None)
            }
        return meta
    except:
        return {}

@st.cache_data(ttl=3600)
def check_global_market_regime():
    """코스피 지수를 분석하여 현재 시장이 대세 하락장인지 판별합니다."""
    try:
        # 코스피 데이터 3년치 분석
        kospi_history = yf.download("^KS11", period="3y", interval="1d", progress=False)
        if isinstance(kospi_history.columns, pd.MultiIndex):
            kospi_history.columns = kospi_history.columns.get_level_values(0)
            
        # 60일 이동평균선(MA60) 및 기울기
        kospi_history['MA60'] = ta.sma(kospi_history['Close'], length=60)
        kospi_history['Slope'] = kospi_history['MA60'].diff(5)
        
        last_price = kospi_history['Close'].iloc[-1]
        last_ma60 = kospi_history['MA60'].iloc[-1]
        last_slope = kospi_history['Slope'].iloc[-1]
        
        # 상태 판별 로직
        if (last_price > last_ma60) and (last_slope > 0):
            return "UPTREND"
        elif last_price < last_ma60:
            return "DOWNTREND"
        else:
            return "SIDEWAYS"
    except:
        return "SIDEWAYS"

# ==========================================================
# --- [섹션 3] 퀀트 분석 핵심 엔진 (V3.1 로직 정석 구현) ---
# ==========================================================

def execute_quant_logic(symbol_string, fee_rate=0.002):
    """
    특정 종목에 대해 3년 백테스팅 및 현재 타점을 계산합니다.
    입력: 종목 티커 (예: 005930.KS)
    출력: 성적표(CAGR, MDD, 승률, 존버 등), 현재 상태, 권장 비중 등
    """
    try:
        # 1. 역사 데이터 수집 (3년 일봉)
        stock_df = yf.download(symbol_string, period="3y", interval="1d", progress=False)
        
        # 데이터가 너무 적으면 분석 불가
        if stock_df.empty or len(stock_df) < 120:
            return None, "데이터 부족", 0, 0, 0, 0, 0, 0, "NONE", 0, 0, 0
            
        # 멀티인덱스 컬럼 정리
        if isinstance(stock_df.columns, pd.MultiIndex):
            stock_df.columns = stock_df.columns.get_level_values(0)
        
        # 결측치 처리
        stock_df = stock_df.ffill().dropna()

        # 2. 기술적 지표 산출
        # 단기(5일), 중기(20일), 장기(60일) 이평선
        stock_df['MA5'] = ta.sma(stock_df['Close'], length=5)
        stock_df['MA20'] = ta.sma(stock_df['Close'], length=20)
        stock_df['MA60'] = ta.sma(stock_df['Close'], length=60)
        stock_df['MA60_Slope'] = stock_df['MA60'].diff(5)
        
        # 변동성 및 자금 지표
        stock_df['ATR'] = ta.atr(stock_df['High'], stock_df['Low'], stock_df['Close'], length=14)
        stock_df['Vol_MA20'] = ta.sma(stock_df['Volume'], length=20)
        
        # MACD 및 MFI
        macd_output = ta.macd(stock_df['Close'])
        stock_df['MACD_Line'] = macd_output.iloc[:, 0]
        stock_df['MACD_Signal'] = macd_output.iloc[:, 2]
        stock_df['MFI_Index'] = ta.mfi(stock_df['High'], stock_df['Low'], stock_df['Close'], stock_df['Volume'], length=14)
        
        # 3. 개별 종목 국면 정의 (Regime Detection)
        stock_df['Volatility_Rate'] = stock_df['ATR'] / stock_df['Close']
        
        # 상승, 변동성상승, 횡보, 하락 판별
        cond_up = (stock_df['Close'] > stock_df['MA60']) & (stock_df['MA60_Slope'] > 0) & (stock_df['Volatility_Rate'] < 0.03)
        cond_vol = (stock_df['Close'] > stock_df['MA60']) & (stock_df['MA60_Slope'] > 0) & (stock_df['Volatility_Rate'] >= 0.03)
        cond_side = (abs(stock_df['Close'] - stock_df['MA60']) / stock_df['MA60'] < 0.02)
        
        stock_df['Local_Mode'] = np.select(
            [cond_up, cond_vol, cond_side], 
            ["UPTREND", "VOLATILE_UP", "SIDEWAYS"], 
            default="DOWNTREND"
        )

        # 4. 타점 점수(Total Score) 계산 (9점 만점)
        # 이평선 정배열(3점) + MACD 반전(2점) + 거래량 폭증(2점) + 자금유입(2점)
        sc_ma = np.where(stock_df['MA5'] > stock_df['MA20'], 3, 0)
        sc_macd = np.where(stock_df['MACD_Line'] > stock_df['MACD_Signal'], 2, 0)
        sc_vol = np.where((stock_df['Volume'] > stock_df['Vol_MA20'] * 1.2) & (stock_df['Close'] > stock_df['Open']), 2, 0)
        sc_mfi = np.where(stock_df['MFI_Index'] > 50, 2, 0)
        
        stock_df['Final_Score'] = sc_ma + sc_macd + sc_vol + sc_mfi
        
        # 국면별 진입 커트라인 점수 설정
        stock_df['Cutline_Score'] = np.select(
            [stock_df['Local_Mode'] == "UPTREND", stock_df['Local_Mode'] == "SIDEWAYS"], 
            [3, 4], 
            default=6
        )

        # 5. 매수 신호(Buy Signal) 결정 로직
        # 시장 국면 필터 적용 (하락장 시 매수 금지)
        global_market_mode = check_global_market_regime()

        stock_df['Buy_Signal'] = (stock_df['Final_Score'] >= stock_df['Cutline_Score']) & \
                                 (stock_df['Close'] < stock_df['MA5'] * 1.05) & \
                                 (stock_df['Local_Mode'] != "VOLATILE_UP") & \
                                 (global_market_mode != "DOWNTREND")

        # 6. 백테스팅(Backtesting) 시뮬레이션
        # 3년 전체가 아닌 최근 1년(250거래일)을 집중 분석
        
        pos_array = np.zeros(len(stock_df))
        strategy_return_array = np.zeros(len(stock_df))
        is_in_position = False
        trade_count = 0
        win_count = 0
        entry_price_val = 0
        stop_loss_val = 0
        take_profit_val = 0
        pos_size = 0
        
        # 루프를 돌며 가상 매매 시뮬레이션
        close_vals = stock_df['Close'].values
        open_vals = stock_df['Open'].values
        high_vals = stock_df['High'].values
        low_vals = stock_df['Low'].values
        
        for i in range(1, len(stock_df)):
            if not is_in_position:
                # 매수 신호 포착 (전일 신호 발생 시 금일 시가 진입)
                if stock_df['Buy_Signal'].iloc[i-1]:
                    # 갭 통과 확인 (±3% 이내)
                    gap_pct = (open_vals[i] / close_vals[i-1]) - 1
                    if -0.03 <= gap_pct <= 0.03:
                        is_in_position = True
                        entry_price_val = open_vals[i]
                        trade_count += 1
                        
                        # ATR 기반 손절/익절가 세팅
                        current_atr = stock_df['ATR'].iloc[i-1]
                        stop_loss_val = entry_price_val - (current_atr * 2.0)
                        take_profit_val = entry_price_val + (current_atr * 3.5)
                        
                        # 리스크 기반 비중 조절
                        unit_risk = (entry_price_val - stop_loss_val) / entry_price_val
                        pos_size = min(0.01 / unit_risk, 1.0) if unit_risk > 0 else 1.0
                        pos_array[i] = 1
            else:
                # 매도 조건 확인
                final_exit_price = None
                
                # 시나리오 1: 손절가 터치
                if low_vals[i] <= stop_loss_val:
                    final_exit_price = stop_loss_val
                    is_in_position = False
                # 시나리오 2: 익절가 터치
                elif high_vals[i] >= take_profit_val:
                    final_exit_price = take_profit_val
                    is_in_position = False
                    win_count += 1
                # 시나리오 3: 20일 이평선 이탈 (추세 이탈)
                elif close_vals[i] < stock_df['MA20'].iloc[i-1]:
                    final_exit_price = close_vals[i]
                    is_in_position = False
                    if final_exit_price > entry_price_val:
                        win_count += 1
                else:
                    pos_array[i] = 1
                
                # 수익률 기록
                if not is_in_position:
                    # 매도 시점 수익률 (수수료 차감)
                    strategy_return_array[i] = pos_size * ((final_exit_price / close_vals[i-1]) - 1 - fee_rate)
                else:
                    # 보유 시점 수익률
                    strategy_return_array[i] = pos_size * ((close_vals[i] / close_vals[i-1]) - 1)

        # 7. 성적표 도출 (최근 1년 기준)
        stock_df_1y = stock_df.iloc[-250:].copy()
        strat_returns_1y = strategy_return_array[-250:]
        
        # 누적 수익률 계산
        stock_df_1y['Strat_Cumulative'] = (1 + strat_returns_1y).cumprod()
        
        # 최종 지표 계산
        final_cum_val = stock_df_1y['Strat_Cumulative'].iloc[-1] if not stock_df_1y.empty else 1.0
        cagr_val = (final_cum_val ** (252/250)) - 1
        
        # MDD 계산
        running_max_vals = stock_df_1y['Strat_Cumulative'].cummax()
        drawdown_vals = (stock_df_1y['Strat_Cumulative'] - running_max_vals) / running_max_vals
        mdd_val = drawdown_vals.min()
        
        # 승률 및 존버 수익률
        win_rate_val = (win_count / trade_count * 100) if trade_count > 0 else 0
        buy_and_hold_val = (close_vals[-1] / close_vals[-250]) - 1 if len(close_vals) >= 250 else 0
        
        # 현재 상태 정보
        last_row = stock_df.iloc[-1]
        current_status_text = "🔥 강력 매수 대기" if last_row['Buy_Signal'] else ("🛡️ 보유중 (Hold)" if is_in_position else "👀 관망")
        
        # 권장 투자 비중
        last_atr = last_row['ATR']
        recommended_weight_val = min(0.01 / ((last_atr * 2.0) / last_row['Close']), 1.0) if last_row['Close'] > 0 else 0
        
        return (
            stock_df_1y,           # 1년 데이터프레임
            current_status_text,   # 현재 상태
            cagr_val,             # 연복리 수익률
            mdd_val,              # 최대 낙폭
            win_rate_val,         # 승률
            buy_and_hold_val,     # 존버 수익률
            last_row['Final_Score'], # 현재 점수
            last_row['Cutline_Score'], # 기준 점수
            last_row['Local_Mode'],   # 국면
            last_atr,             # 변동성
            is_in_position,       # 보유 여부
            recommended_weight_val # 권장 비중
        )
    except Exception as general_error:
        print(f"Error in execution: {general_error}")
        return None, f"오류 발생: {general_error}", 0, 0, 0, 0, 0, 0, "NONE", 0, False, 0

# ==========================================================
# --- [섹션 4] 메뉴별 화면 렌더링 함수 (1~6번 메뉴 풀버전) ---
# ==========================================================

# --- 메뉴 1: 단일 종목 분석 화면 ---

def render_page_stock_detail():
    st.markdown("### 📊 종목 정밀 타점 분석기")
    
    # 1. 종목 선택
    stock_names = df_krx_master['Display'].tolist()
    user_choice = st.selectbox(
        "분석할 특정 종목을 입력하거나 선택하세요", 
        options=stock_names, 
        index=stock_names.index(st.session_state.current_selection) if st.session_state.current_selection in stock_names else 0
    )
    
    # 선택 변경 시 화면 갱신
    if user_choice != st.session_state.current_selection:
        st.session_state.current_selection = user_choice
        st.rerun()

    # 종목 코드 추출
    selected_row = df_krx_master[df_krx_master['Display'] == user_choice].iloc[0]
    full_ticker = f"{selected_row['Code']}.KS" if selected_row['Market'] == 'KOSPI' else f"{selected_row['Code']}.KQ"

    # 2. 퀀트 분석 실행
    with st.spinner(f"[{selected_row['Name']}] 3년치 빅데이터 분석 및 시뮬레이션 가동 중..."):
        df_1y, status, cagr, mdd, win, hold, score, cut, mode, atr, _, weight = execute_quant_logic(full_ticker)
        meta_info = fetch_stock_meta_info(full_ticker)

    # 3. 화면 UI 구성
    if df_1y is not None:
        curr_price = df_1y['Close'].iloc[-1]
        prev_price = meta_info.get('regularMarketPreviousClose', df_1y['Close'].iloc[-2])
        diff_val = curr_price - prev_price
        diff_pct = (diff_val / prev_price) * 100
        
        # 가격 색상 및 아이콘
        text_clr = "#e03131" if diff_val > 0 else ("#1971c2" if diff_val < 0 else "#212529")
        icon_mark = "▲" if diff_val > 0 else ("▼" if diff_val < 0 else "-")

        # [메인 종목 카드]
        st.markdown(f"""
        <div style='background-color:#ffffff; padding:25px; border-radius:18px; border:2px solid #e9ecef; margin-bottom:20px;'>
            <div style='margin-bottom:15px;'>
                <span class='market-badge'>종목 국면: {mode}</span>
                <span class='weight-badge'>⚖️ 권장 투자 비중: {weight*100:.0f}%</span>
                <span class='stop-loss-badge'>🛡️ 자동 손절 가격: {curr_price - (atr*2.0):,.0f}원</span>
                <span class='take-profit-badge'>🚀 자동 익절 가격: {curr_price + (atr*3.5):,.0f}원</span>
            </div>
            <div style='display:flex; align-items:baseline; gap:20px;'>
                <span style='font-size:2.3rem; font-weight:bold;'>{selected_row['Name']}</span>
                <span style='font-size:3.8rem; font-weight:bold; color:{text_clr};'>{curr_price:,.0f}원</span>
                <span style='font-size:1.8rem; font-weight:bold; color:{text_clr};'>{icon_mark} {abs(diff_val):,.0f} ({diff_pct:+.2f}%)</span>
            </div>
            <div style='margin-top:20px; border-top:1px solid #eee; padding-top:15px; display:flex; gap:40px; color:#495057;'>
                <div><small>시가총액</small><br><b>{meta_info.get('marketCap',0)/1e12:.2f}조원</b></div>
                <div><small>52주 최고</small><br><b style='color:#e03131;'>{meta_info.get('fiftyTwoWeekHigh',0):,.0f}원</b></div>
                <div><small>52주 최저</small><br><b style='color:#1971c2;'>{meta_info.get('fiftyTwoWeekLow',0):,.0f}원</b></div>
                <div><small>PER</small><br><b>{meta_info.get('trailingPE',0) if meta_info.get('trailingPE') else 0:.1f}배</b></div>
                <div><small>PBR</small><br><b>{meta_info.get('priceToBook',0) if meta_info.get('priceToBook') else 0:.1f}배</b></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # [최근 1년 백테스팅 성적표 - 복구 완료]
        st.markdown(f"""
        <div style='display:flex; gap:15px; margin-bottom:20px;'>
            <div class='stat-box'><div class='stat-label'>연복리 수익률(CAGR)</div><div class='stat-value' style='color:#e03131;'>{cagr*100:+.1f}%</div></div>
            <div class='stat-box'><div class='stat-label'>최대 낙폭(MDD)</div><div class='stat-value' style='color:#1971c2;'>{mdd*100:.1f}%</div></div>
            <div class='stat-box'><div class='stat-label'>전략 승률</div><div class='stat-value'>{win:.1f}%</div></div>
            <div class='stat-box'><div class='stat-label'>존버 수익률(1년)</div><div class='stat-value' style='color:{"#e03131" if hold > 0 else "#1971c2"};'>{hold*100:+.1f}%</div></div>
        </div>
        """, unsafe_allow_html=True)

        # [현재 시그널 판정]
        box_style = "status-buy" if "매수" in status else ("status-hold" if "보유" in status else "status-wait")
        final_msg = f"{status} (알고리즘 점수: {score}점 / 진입 기준: {cut}점)"
        
        if "매수" in status:
            final_msg += f"<br><small style='font-weight:normal;'>👉 내일 시가 진입 허용 구간: <b>{curr_price*0.97:,.0f}원 ~ {curr_price*1.03:,.0f}원</b> (±3% 이내)</small>"
        
        st.markdown(f"<div class='signal-box {box_style}'>{final_msg}</div>", unsafe_allow_html=True)
        
        # 차트 출력
        st.line_chart(df_1y[['Close', 'MA5', 'MA20']], height=450)

        # 관심종목 저장 기능
        st.divider()
        col_folder, col_btn = st.columns([3, 1])
        target_folder = col_folder.selectbox("이 종목을 관심 폴더에 저장할까요?", ["관심종목1", "관심종목2", "관심종목3"], label_visibility="collapsed")
        if col_btn.button("⭐ 현재 종목 폴더 저장", use_container_width=True):
            current_wl = get_watchlist()
            if selected_row['Code'] not in current_wl[target_folder]:
                current_wl[target_folder].append(selected_row['Code'])
                save_watchlist_to_file(current_wl)
                st.toast(f"✅ {selected_row['Name']}이 {target_folder}에 추가되었습니다!")

# --- 메뉴 2: 조건 검색기 (스크리너) 화면 ---

def render_page_screener():
    st.title("🔍 실전 퀀트 종목 스캐너")
    st.info("시장에 등록된 전 종목을 실시간 퀀트 알고리즘으로 스캔하여 '강력 매수' 타점 종목을 찾아냅니다.")
    
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        scan_mode = st.radio("검색 대상 설정", ["전체 시장 (순위별 100개)", "⭐ 관심종목 폴더 스캔"], horizontal=True)
    with c2:
        if scan_mode == "전체 시장 (순위별 100개)":
            rank_range = st.selectbox("시가총액 순위 범위", [f"{i*100 + 1}위 ~ {(i+1)*100}위" for i in range(15)])
    
    if st.button("🚀 알고리즘 스캔 시작 (300년 치 데이터 연산)", type="primary", use_container_width=True):
        if scan_mode == "전체 시장 (순위별 100개)":
            start_num = int(rank_range.split("위")[0].strip()) - 1
            target_list = df_krx_master.iloc[start_num : start_num + 100]
        else:
            wl_data = get_watchlist()
            merged_codes = list(set(wl_data["관심종목1"] + wl_data["관심종목2"] + wl_data["관심종목3"]))
            target_list = df_krx_master[df_krx_master['Code'].isin(merged_codes)]
            
        if target_list.empty:
            st.warning("검색할 종목이 없습니다. 폴더에 종목을 먼저 추가해 주세요.")
        else:
            prog_bar = st.progress(0, text="대규모 퀀트 데이터 연산 중...")
            screener_results = []
            
            for index_num, (idx, row) in enumerate(target_list.iterrows()):
                ticker_full = f"{row['Code']}.KS" if row['Market'] == 'KOSPI' else f"{row['Code']}.KQ"
                res_data = execute_quant_logic(ticker_full)
                
                if res_data[0] is not None:
                    screener_results.append({
                        'Name': row['Name'],
                        'Code': row['Code'],
                        'Display': row['Display'],
                        'Status': res_data[1],
                        'Score': res_data[6],
                        'Weight': round(res_data[11] * 100),
                        'CAGR': res_data[2]
                    })
                prog_bar.progress((index_num + 1) / len(target_list))
            
            prog_bar.empty()
            # 정렬 로직: 매수 신호 우선 -> 점수 순 -> 수익률 순
            st.session_state.search_results = sorted(
                screener_results, 
                key=lambda x: (0 if "강력" in x['Status'] else 1, -x['Score'], -x['CAGR'])
            )[:12]

    # 결과 리스트 출력
    if st.session_state.search_results:
        st.subheader("🏆 금일의 알고리즘 TOP 픽")
        for item in st.session_state.search_results:
            card_col, btn_col, add_col = st.columns([4, 1, 1.5])
            
            with card_col:
                st.markdown(f"""
                <div class='rank-card'>
                    <div style='display:flex; justify-content:space-between; align-items:center;'>
                        <span style='font-size:1.1rem;'><b>{item['Name']} ({item['Code']})</b></span>
                        <span style='color:#2b8a3e; font-weight:bold;'>{item['Status']}</span>
                    </div>
                    <div style='font-size:0.9rem; color:#666; margin-top:8px;'>
                        알고리즘 점수: {item['Score']}점 | 권장 투자 비중: {item['Weight']}% | 예상 연수익률: {item['CAGR']*100:+.1f}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with btn_col:
                st.write("") # 패딩용
                if st.button("상세분석", key=f"scr_det_{item['Code']}", use_container_width=True):
                    st.session_state.current_selection = item['Display']
                    st.session_state.page_selection = "📊 단일 종목 분석"
                    st.rerun()
            
            with add_col:
                st.write("")
                sc1, sc2 = st.columns([1, 1])
                f_box = sc1.selectbox("폴더", ["관심종목1", "관심종목2", "관심종목3"], key=f"scr_f_{item['Code']}", label_visibility="collapsed")
                if sc2.button("⭐", key=f"scr_a_{item['Code']}", use_container_width=True):
                    wl_save = get_watchlist()
                    if item['Code'] not in wl_save[f_box]:
                        wl_save[f_box].append(item['Code'])
                        save_watchlist_to_file(wl_save)
                        st.toast(f"{item['Name']} 저장!")

# --- 메뉴 3: 내 계좌 관리 (포트폴리오) 화면 ---

def render_page_portfolio():
    st.title("💼 실전 보유 종목 관리")
    st.write("현재 계좌에 담긴 종목들을 퀀트 모델로 추적하여 매도 타이밍을 잡습니다.")
    
    my_pf = get_portfolio()
    
    # 신규 등록 섹션
    with st.expander("➕ 보유 종목 수동 등록", expanded=True):
        p_c1, p_c2, p_c3, p_c4 = st.columns([3, 2, 2, 1])
        stk_choice = p_c1.selectbox("매수한 종목 선택", options=df_krx_master['Display'].tolist())
        stk_price = p_c2.number_input("나의 매입 단가(원)", min_value=1, value=50000, step=100)
        stk_qty = p_c3.number_input("매수 수량(주)", min_value=1, value=10, step=1)
        
        if p_c4.button("등록하기", use_container_width=True):
            stk_code = stk_choice.split("(")[-1].replace(")", "")
            my_pf[stk_code] = {
                "Name": stk_choice.split("(")[0].strip(),
                "BuyPrice": stk_price,
                "Quantity": stk_qty
            }
            save_portfolio_to_file(my_pf)
            st.success("포트폴리오에 성공적으로 등록되었습니다.")
            st.rerun()

    st.divider()
    
    if not my_pf:
        st.info("등록된 보유 종목이 없습니다. 위에서 종목을 추가해 주세요.")
    else:
        for code_key, p_data in my_pf.items():
            # 시장 구분 확인
            full_code = f"{code_key}.KS" if not df_krx_master[df_krx_master['Code']==code_key].empty and df_krx_master[df_krx_master['Code']==code_key]['Market'].iloc[0] == 'KOSPI' else f"{code_key}.KQ"
            
            # 분석 데이터 로드
            p_res = execute_quant_logic(full_code)
            
            if p_res[0] is not None:
                now_price = p_res[0]['Close'].iloc[-1]
                p_atr = p_res[9]
                target_tp = p_data['BuyPrice'] + (p_atr * 3.5)
                target_sl = p_data['BuyPrice'] - (p_atr * 2.0)
            else:
                now_price = p_data['BuyPrice']
                target_tp, target_sl = now_price * 1.15, now_price * 0.95
                
            total_profit = (now_price - p_data['BuyPrice']) * p_data['Quantity']
            profit_rate = (total_profit / (p_data['BuyPrice'] * p_data['Quantity'])) * 100
            
            # AI 가이드 메시지
            if now_price >= target_tp:
                p_action, p_clr = "🚀 수익 실현 권장", "#5c940d"
            elif now_price <= target_sl:
                p_action, p_clr = "⚠️ 리스크 위험! 칼손절 필요", "#e03131"
            else:
                p_action, p_clr = "✅ 원칙 홀딩 (관망)", "#2b8a3e"
            
            st.markdown(f"""
            <div class='portfolio-card'>
                <div style='display:flex; justify-content:space-between; align-items:center;'>
                    <span style='font-size:1.6rem; font-weight:bold;'>{p_data['Name']} ({code_key})</span>
                    <span style='color:{p_clr}; font-weight:bold; font-size:1.3rem;'>{p_action}</span>
                </div>
                <div style='display:flex; gap:35px; margin-top:18px;'>
                    <div><small>매입단가</small><br><b>{p_data['BuyPrice']:,.0f}원</b></div>
                    <div><small>현재가</small><br><b>{now_price:,.0f}원</b></div>
                    <div><small>평가손익</small><br><b style='color:{"#e03131" if total_profit > 0 else "#1971c2"};'>{total_profit:+,.0f}원 ({profit_rate:+.2f}%)</b></div>
                    <div><small>목표 익절가</small><br><b style='color:#5c940d;'>{target_tp:,.0f}원</b></div>
                    <div><small>방어 손절가</small><br><b style='color:#e03131;'>{target_sl:,.0f}원</b></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("이 종목을 목록에서 제거", key=f"pf_rm_{code_key}"):
                del my_pf[code_key]
                save_portfolio_to_file(my_pf)
                st.rerun()

# --- 메뉴 4: 실전 매매 일지 (저널) 화면 ---

def render_page_journal():
    st.title("📓 Leo의 실전 매매 기록장")
    st.write("성공적인 퀀트는 철저한 기록에서 시작됩니다. 감정을 배제하고 원칙 준수 여부를 남기세요.")
    
    j_df = get_journal_data()
    
    # 스트림릿 데이터 에디터 활용
    edited_j_df = st.data_editor(
        j_df,
        num_rows="dynamic",
        use_container_width=True,
        height=600,
        column_config={
            "시장국면": st.column_config.SelectboxColumn("📈 국면", options=["상승장", "횡보장", "하락장"]),
            "청산사유": st.column_config.SelectboxColumn("매도결과", options=["보유중", "목표가 익절", "손절가 손절", "추세이탈 매도", "뇌동매매"])
        }
    )
    
    if st.button("💾 매매 일지 파일로 저장하기", use_container_width=True, type="primary"):
        edited_j_df.to_csv(JOURNAL_PATH, index=False, encoding='utf-8-sig')
        st.success("매매 일지가 CSV 파일로 성공적으로 저장되었습니다.")

# --- 메뉴 5: 관심종목 관리 폴더 화면 ---

def render_page_watchlist():
    st.title("📂 내 관심종목 폴더 관리")
    w_data = get_watchlist()
    
    fold_col1, fold_col2, fold_col3 = st.columns(3)
    folder_names = ["관심종목1", "관심종목2", "관심종목3"]
    cols_list = [fold_col1, fold_col2, fold_col3]
    
    for idx_f in range(3):
        cur_f_name = folder_names[idx_f]
        with cols_list[idx_f]:
            st.markdown(f"<div class='folder-box'>", unsafe_allow_html=True)
            st.subheader(f"📁 {cur_f_name}")
            saved_codes = w_data.get(cur_f_name, [])
            
            if not saved_codes:
                st.caption("비어 있음 (스캐너에서 추가하세요)")
            else:
                for c_item in saved_codes:
                    # 이름 찾기
                    found_name = df_krx_master[df_krx_master['Code'] == c_item]['Name'].iloc[0] if not df_krx_master[df_krx_master['Code'] == c_item].empty else c_item
                    
                    row_c1, row_c2 = st.columns([4, 1])
                    row_c1.write(f"**{found_name}** ({c_item})")
                    if row_c2.button("❌", key=f"wl_del_{cur_f_name}_{c_item}"):
                        w_data[cur_f_name].remove(c_item)
                        save_watchlist_to_file(w_data)
                        st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# --- 메뉴 6: 퀀트 백과사전 & 매뉴얼 화면 ---

def render_page_manual():
    st.title("📖 Leo의 퀀트 투자 백과사전")
    
    tab_theory, tab_kiwoom = st.tabs(["🧠 퀀트 투자 원칙", "📱 영웅문 실전 매뉴얼"])
    
    with tab_theory:
        st.header("1. ⚖️ 1% 리스크 관리법")
        st.info("어떤 종목을 사든, '손절가'에 도달했을 때 잃는 돈이 내 전체 투자금의 딱 1%가 되도록 수량을 조절하는 법입니다.")
        
        st.header("2. 🤖 시장 국면(Regime) 필터")
        st.success("코스피가 60일선 아래에 있는 '대세 하락장'에서는 어떤 천재적인 알고리즘 신호가 와도 매수를 쉬는 것이 퀀트의 첫 번째 원칙입니다.")
        
        st.header("3. 🧪 백테스팅(Backtesting) 성적표 보는 법")
        st.markdown("""
        * **CAGR (연복리 수익률):** 전략이 매년 평균적으로 벌어다 준 수익입니다.
        * **MDD (최대 낙폭):** 고점 대비 계좌가 가장 많이 깎였던 순간입니다. 이 숫자가 적을수록 맘 편한 투자입니다.
        * **존버 수익률:** 전략 없이 그냥 1년 전 사서 들고만 있었을 때의 결과입니다. 우리 전략이 이보다 좋아야 합니다.
        """)

    with tab_kiwoom:
        st.header("📱 영웅문S# 100% 자동 매매 가이드")
        
        st.subheader("☀️ 1단계: 매수 시 (🚨 지정가 함정 매수법)")
        st.warning("레오님이 발견하신 이 방법은 아침 9시 폭락장을 걸러내는 가장 스마트한 방패입니다.")
        st.markdown("""
        1. **메뉴:** [주식] → [주문] → [자동감시주문] → [신규종목]
        2. **감시 조건:** 현재가 **>=** (이상) 선택 후 프로그램이 준 **'최저가'** 입력
        3. **주문 설정:** 종류를 반드시 **'보통(지정가)'**로 선택 ★★★
        4. **주문 가격:** 프로그램이 준 **'최고가'** 입력
        5. **결과:** 주가가 우리가 원하는 '허용 구간'에 있을 때만 주문이 나갑니다.
        """)
        
        st.subheader("🛡️ 2단계: 매도 시 (잔고편입 스탑로스)")
        st.markdown("""
        1. **메뉴:** [자동감시주문] → [잔고편입] 탭 선택
        2. **대상:** 방금 매수한 종목 선택
        3. **감시 조건:** 현재가 **'도달 시'** (절대 가격) 선택
        4. **가격 입력:** 프로그램이 준 **'목표 익절가'**와 **'방어 손절가'** 입력
        5. **주문 설정:** 매도 종류는 무조건 **'시장가'** 선택 ★★★
        6. **유효기간:** **90일**로 설정 후 감시 시작 버튼 누르기
        """)

# ==========================================================
# --- [섹션 5] 메인 컨트롤러 및 실행부 (최종 마무리) ---
# ==========================================================

# 상단 지수 띠 출력
display_market_header()
st.markdown("<br>", unsafe_allow_html=True)

# 사이드바 메뉴 구성
with st.sidebar:
    st.header("📌 시스템 메뉴")
    # key="page_selection"을 사용하여 위에서 초기화한 세션 상태와 연동
    st.radio(
        "이동할 페이지 선택", 
        [
            "📊 단일 종목 분석", 
            "🔍 조건 검색기 (스크리너)", 
            "💼 내 계좌 관리 (실전 포트폴리오)", 
            "📓 실전 매매 일지", 
            "📂 관심종목 관리", 
            "📖 주식 & 전략 백과사전"
        ], 
        key="page_selection"
    )
    
    st.divider()
    
    # 리스크 관리 대시보드
    st.header("🤖 리스크 관리 통합 시스템")
    current_regime = check_global_market_regime()
    regime_display = {
        "UPTREND": "🇰🇷 코스피: 대세 상승장 (적극 매수)", 
        "DOWNTREND": "🇰🇷 코스피: 대세 하락장 (신규 매수 금지)", 
        "SIDEWAYS": "🇰🇷 코스피: 혼조세 (비중 축소)"
    }.get(current_regime, "알 수 없음")
    
    st.info(f"**{regime_display}**")
    
    st.divider()
    
    # 수수료 설정
    user_fee = st.number_input("왕복 수수료+세금 (%)", value=0.2, step=0.05) / 100

# 최종 화면 렌더링 (에러 없이 실행되는 핵심 로직)
current_page = st.session_state.get('page_selection', "📊 단일 종목 분석")

if current_page == "📊 단일 종목 분석":
    render_page_stock_detail()
elif current_page == "🔍 조건 검색기 (스크리너)":
    render_page_screener()
elif current_page == "💼 내 계좌 관리 (실전 포트폴리오)":
    render_page_portfolio()
elif current_page == "📓 실전 매매 일지":
    render_page_journal()
elif current_page == "📂 관심종목 관리":
    render_page_watchlist()
elif current_page == "📖 주식 & 전략 백과사전":
    render_page_manual()

# 하단 정보 표시
st.sidebar.markdown("---")
st.sidebar.caption(f"Leo Quant Sniper v4.4 Final Version")
st.sidebar.caption(f"시스템 최종 갱신: {datetime.now().strftime('%Y-%m-%d %H:%M')}")