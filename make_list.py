import FinanceDataReader as fdr
import pandas as pd

print("🚀 종목 리스트를 가져오는 중입니다. 잠시만 기다려주세요...")

try:
    # 한국 거래소 전 종목 가져오기
    df = fdr.StockListing('KRX')

    # 필요한 정보만 추리기 (코드, 이름, 시장)
    df = df[['Code', 'Name', 'Market']]

    # CSV 파일로 저장
    df.to_csv('krx_stocks.csv', index=False, encoding='utf-8-sig')

    print("✅ 파일 생성 완료! 'krx_stocks.csv' 파일이 생겼습니다.")
except Exception as e:
    print(f"❌ 에러 발생: {e}")