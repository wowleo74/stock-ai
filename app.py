import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from datetime import datetime, timedelta

# --- 1. 앱 설정 및 스타일 (기존 디자인 유지) ---
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

# --- 2. 세션 및 데이터 관리 ---
# 초기 관심종목 설정
if 'watchlist' not in st.session_state:
    st.session_state.watchlist = {"삼성전자": "005930", "SK하이닉스": "000660", "현대차": "005380", "애플": "AAPL", "테슬라": "TSLA"}

if 'target_ticker' not in st.session_state:
    st.session_state.target_ticker = "005930"

# --- 3. 사이드바 구성 ---
with st.sidebar:
    st.header("⭐ 관심종목")
    # 버튼 형태로 관심종목 리스트 표시
    for name, code in st.session_state.watchlist.items():
        if st.button(f"{name} ({code})", use_container_width=True):
            st.session_state.target_ticker = code
            st.rerun()
    
    st.divider()
    st.header("🔍 종목 검색")
    # 직접 입력창 추가 (KRX 서버 에러 방지용)
    new_ticker = st.text_input("종목코드 6자리 또는 티커 입력", value=st.session_state.target_ticker)
    if new_ticker != st.session_state.target_ticker:
        st.session_state.target_ticker = new_ticker
        st.rerun()

    st.divider()
    st.subheader("💡 분석 옵션")
    use_ma = st.checkbox("방법 A: 이동평균선", value=True)
    use_rsi = st.checkbox("방법 B: RSI 심리", value=True)
    use_vol = st.checkbox("방법 C: 거래량 실세", value=True)
    use_bb = st.checkbox("방법 D: 볼린저 밴드", value=True)
    expert_mode = st.toggle("🛠️ 전문가 데이터 보기", value=False)

# 티커 정제 (한국 주식 자동 처리)
raw_ticker = st.session_state.target_ticker.strip()
if raw_ticker.isdigit() and len(raw_ticker) == 6:
    ticker = f"{raw_ticker}.KS"  # 기본 KOSPI로 시도
else:
    ticker = raw_ticker

# --- 4. 분석 엔진 ---
def analyze_stock(symbol, use_ma, use_rsi, use_vol, use_bb):
    try:
        df = yf.download(symbol, period="1y", interval="1d", progress=False)
        
        # KOSPI에서 못 찾으면 KOSDAQ(.KQ)으로 재시도
        if df.empty and ".KS" in symbol:
            symbol = symbol.replace(".KS", ".KQ")
            df = yf.download(symbol, period="1y", interval="1d", progress=False)
            
        if df.empty: return "데이터를 찾을 수 없습니다.", None, None, None
        
        # 컬럼 정리
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
            opinion = "매수 추천" if ma5 > ma20 else "매도 추천"
            reason = "5일선이 20일선 위에 있어 상승 추세입니다." if ma5 > ma20 else "하락 추세입니다."
            results.append(("이동평균선", opinion, reason, 1 if ma5 > ma20 else -1))
        
        if use_rsi:
            rsi_v = float(last['RSI'])
            sc = 2 if rsi_v < 35 else (-2 if rsi_v > 70 else 0)
            opinion = "강력 매수" if sc==2 else ("강력 매도" if sc==-2 else "관망")
            results.append(("RSI 심리", opinion, f"RSI가 {rsi_v:.1f}로 {'바닥권' if sc==2 else ('과열권' if sc==-2 else '안정적')}입니다.", sc))
            
        if use_vol:
            vol_ratio = (float(last['Volume']) / float(last['Vol_MA20'])) * 100
            sc = 2 if vol_ratio > 200 and last['Close'] > prev['Close'] else (-1 if vol_ratio < 50 else 0)
            results.append(("거래량 실세", "강력 매수" if sc==2 else "관망", f"거래량이 평소 대비 {vol_ratio:.0f}% 수준입니다.", sc))
            
        if use_bb:
            p, up, lo = float(last['Close']), float(last['BB_Upper']), float(last['BB_Lower'])
            sc = 2 if p <= lo else (-2 if p >= up else 0)
            opinion = "강력 매수" if sc==2 else ("강력 매도" if sc==-2 else "관망")
            results.append(("볼린저 밴드", opinion, f"주가가 밴드 {'하단' if sc==2 else ('상단' if sc==-2 else '내부')}에 위치합니다.", sc))

        avg_score = sum(r[3] for r in results) / len(results) if results else 0
        final = "강력 매수" if avg_score >= 1.2 else ("매수 추천" if avg_score >= 0.4 else ("강력 매도" if avg_score <= -1.2 else ("매도" if avg_score <= -0.4 else "관망")))
        
        return None, df, results, final
    except Exception as e: 
        return str(e), None, None, None

# --- 5. 메인 화면 ---
st.title(f"🚦 AI 전략 리포트: {raw_ticker}")

err, df, indicators, final_status = analyze_stock(ticker, use_ma, use_rsi, use_vol, use_bb)

if df is not None:
    # 신호등 UI
    signals = ["강력 매도", "매도", "관망", "매수 추천", "강력 매수"]
    cmap = {"강력 매수":"active-strong-buy", "매수 추천":"active-buy", "관망":"active-hold", "매도":"active-sell", "강력 매도":"active-strong-sell"}
    boxes = "".join([f'<div class="signal-box {cmap[s] if s==final_status else ""}">{s}</div>' for s in signals])
    st.markdown(f'<div class="signal-container">{boxes}</div>', unsafe_allow_html=True)
    
    # 상세 분석 카드
    st.subheader("📝 상세 분석")
    cols = st.columns(len(indicators))
    for i, (name, opinion, reason, score) in enumerate(indicators):
        color = "#2e7d32" if "매수" in opinion else ("#c62828" if "매도" in opinion else "#ef6c00")
        with cols[i]:
            st.markdown(f'<div class="strategy-card"><span class="indicator-label">{name}</span><span class="indicator-opinion" style="color: {color};">[{opinion}]</span><div class="indicator-reason">{reason}</div></div>', unsafe_allow_html=True)

    # 전문가 모드 차트
    if expert_mode:
        st.divider()
        st.subheader("📊 기술적 분석 차트")
        st.line_chart(df[['Close', 'BB_Upper', 'BB_Lower']] if use_bb else df[['Close', 'MA5', 'MA20']])
        if use_vol: st.bar_chart(df['Volume'])
else:
    st.error(f"분석 중 오류: {err}")
    st.info("💡 팁: 한국 주식은 6자리 숫자(예: 005930)를, 미국 주식은 티커(예: AAPL)를 입력하세요.")
