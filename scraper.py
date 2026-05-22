"""
Options Signal Data Scraper v3.0
Yahoo Finance에서 미국 옵션 시그널 6개 지표 수집
GitHub Actions cron으로 매일 미국 마감 후 자동 실행

출력: options-data.json (HTML 대시보드가 fetch)
의존: yfinance>=0.2.30
"""
import json
import sys
from datetime import datetime, timezone, timedelta

import yfinance as yf

KST = timezone(timedelta(hours=9))
UTC = timezone.utc


def fetch_yahoo(symbol, retries=3):
    """야후에서 종가/전일종가/변동률 가져옴 (재시도 포함)"""
    last_err = None
    for attempt in range(retries):
        try:
            t = yf.Ticker(symbol).history(period='5d')
            if t.empty:
                last_err = "empty result"
                continue
            closes = t['Close'].dropna()
            if len(closes) == 0:
                last_err = "no valid close"
                continue
            price = float(closes.iloc[-1])
            prev = float(closes.iloc[-2]) if len(closes) >= 2 else price
            change = price - prev
            change_pct = (change / prev * 100) if prev != 0 else 0
            return {
                'price': round(price, 4),
                'prev_close': round(prev, 4),
                'change': round(change, 4),
                'change_pct': round(change_pct, 4),
                'date': str(t.index[-1].date()),
            }
        except Exception as e:
            last_err = str(e)
            continue
    print(f'  X {symbol} failed after {retries} retries: {last_err}', file=sys.stderr)
    return None


def main():
    print(f'[{datetime.now(KST).isoformat()}] Options scraper start')
    
    symbols = {
        'vix':   '^VIX',
        'vix9d': '^VIX9D',
        'vix3m': '^VIX3M',
        'vvix':  '^VVIX',
        'skew':  '^SKEW',
        'spx':   '^GSPC',
    }
    
    data = {
        'generated_at_kst': datetime.now(KST).isoformat(),
        'generated_at_utc': datetime.now(UTC).isoformat(),
        'source': 'yfinance via GitHub Actions',
        'version': '3.0',
        'metrics': {},
        'computed': {},
        'errors': [],
    }
    
    for key, symbol in symbols.items():
        print(f'  fetching {key} ({symbol})...')
        result = fetch_yahoo(symbol)
        if result:
            data['metrics'][key] = result
            print(f'  OK {key}: {result["price"]:.2f} ({result["change_pct"]:+.2f}%)')
        else:
            data['metrics'][key] = None
            data['errors'].append(f'{key} ({symbol}) failed')
    
    # 파생 비율 계산
    m = data['metrics']
    if m.get('vix') and m.get('vix9d'):
        data['computed']['vix9d_vix_ratio'] = round(
            m['vix9d']['price'] / m['vix']['price'], 4
        )
    if m.get('vix') and m.get('vix3m'):
        data['computed']['vix_vix3m_ratio'] = round(
            m['vix']['price'] / m['vix3m']['price'], 4
        )
    
    success_count = sum(1 for v in m.values() if v is not None)
    data['success_count'] = success_count
    data['total_count'] = len(symbols)
    
    with open('options-data.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print(f'OK Saved options-data.json ({success_count}/{len(symbols)} success)')
    
    if success_count == 0:
        print('X All symbols failed - exiting with error', file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
