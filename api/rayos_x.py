from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import urllib.request
import datetime

SECTOR_MAP = {
    'NVDA': ('Technology', 'XLK'), 'PLTR': ('Technology', 'XLK'), 'AAPL': ('Technology', 'XLK'),
    'MSFT': ('Technology', 'XLK'), 'AMD': ('Technology', 'XLK'), 'INTC': ('Technology', 'XLK'),
    'TSM': ('Technology', 'XLK'), 'AVGO': ('Technology', 'XLK'), 'CRM': ('Technology', 'XLK'),
    'ORCL': ('Technology', 'XLK'), 'GOOGL': ('Communication Services', 'XLC'), 'GOOG': ('Communication Services', 'XLC'),
    'META': ('Communication Services', 'XLC'), 'NFLX': ('Communication Services', 'XLC'),
    'AMZN': ('Consumer Cyclical', 'XLY'), 'TSLA': ('Consumer Cyclical', 'XLY'),
    'JPM': ('Financial Services', 'XLF'), 'BAC': ('Financial Services', 'XLF'), 'V': ('Financial Services', 'XLF'),
    'XOM': ('Energy', 'XLE'), 'CVX': ('Energy', 'XLE'), 'PFE': ('Healthcare', 'XLV'),
    'JNJ': ('Healthcare', 'XLV'), 'LLY': ('Healthcare', 'XLV'), 'UNH': ('Healthcare', 'XLV'),
    'SPY': ('Broad Market Index', 'SPY'), 'QQQ': ('Broad Market Index', 'QQQ'),
    'GLD': ('Precious Metals / Refugio', 'GLD'), 'DIA': ('Broad Market Index', 'DIA'),
    'IWM': ('Small Caps', 'IWM'), 'EDV': ('Bonds / Refugio', 'EDV'), 'TLT': ('Bonds / Refugio', 'TLT')
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_url = urlparse(self.path)
        query_params = parse_qs(parsed_url.query)
        ticker_symbol = query_params.get('ticker', [''])[0].strip().upper()

        if not ticker_symbol:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Ticker no proporcionado'}).encode('utf-8'))
            return

        prices = []
        dates = []
        volumes = []
        current_price = 0.0
        p_high_52w = 0.0
        p_low_52w = 0.0
        name = ticker_symbol
        sector = 'Acción / Empresa'
        industry = 'Mercado General'
        sector_benchmark = 'SPY'
        desc = 'Sin descripción detallada disponible.'
        expense_str = 'N/A'
        earnings_str = 'N/A (Fondo / ETF)'

        if ticker_symbol in SECTOR_MAP:
            sector, sector_benchmark = SECTOR_MAP[ticker_symbol]

        # 1. Descarga directa de alta velocidad (Yahoo Chart API v8)
        try:
            url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker_symbol}?range=1y&interval=1d"
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=5) as response:
                chart_data = json.loads(response.read().decode('utf-8'))
                result = chart_data.get('chart', {}).get('result', [{}])[0]
                meta = result.get('meta', {})
                
                name = meta.get('longName') or meta.get('shortName') or ticker_symbol
                instrument_type = meta.get('instrumentType', '')
                if instrument_type == 'ETF':
                    sector = 'ETF / Fondo'
                
                timestamps = result.get('timestamp', [])
                indicators = result.get('indicators', {}).get('quote', [{}])[0]
                closes = indicators.get('close', [])
                vols = indicators.get('volume', [])

                for i in range(len(timestamps)):
                    c = closes[i]
                    if c is not None and not (isinstance(c, float) and (c != c)):
                        val = round(float(c), 2)
                        dt = datetime.datetime.fromtimestamp(timestamps[i]).strftime('%d/%m/%Y')
                        prices.append(val)
                        dates.append(dt)
                        if vols and i < len(vols) and vols[i] is not None:
                            volumes.append(int(vols[i]))

                if prices:
                    current_price = prices[-1]
                    p_high_52w = meta.get('fiftyTwoWeekHigh') or max(prices)
                    p_low_52w = meta.get('fiftyTwoWeekLow') or min(prices)

        except Exception:
            pass

        # 2. Respaldo secundario via yfinance si la API directa no trajo datos
        if not prices:
            try:
                import yfinance as yf
                t = yf.Ticker(ticker_symbol)
                hist = t.history(period="6mo", interval="1d")
                if not hist.empty:
                    for ts, val in hist['Close'].dropna().items():
                        prices.append(round(float(val), 2))
                        dates.append(ts.strftime('%d/%m/%Y'))
                    if prices:
                        current_price = prices[-1]
                        p_high_52w = max(prices)
                        p_low_52w = min(prices)
            except Exception:
                pass

        # 3. Metadatos de sector y balances
        if sector != 'ETF / Fondo':
            try:
                import yfinance as yf
                t = yf.Ticker(ticker_symbol)
                cal = t.calendar
                if cal is not None and not cal.empty:
                    if 'Earnings Date' in cal.index:
                        ed = cal.loc['Earnings Date'].dropna()
                        if len(ed) > 0:
                            earnings_str = str(ed.iloc[0]).split(' ')[0]
                    elif isinstance(cal, dict) and 'Earnings Date' in cal:
                        ed = cal['Earnings Date']
                        if ed:
                            earnings_str = str(ed[0]).split(' ')[0]
                else:
                    earnings_str = "Consultar reporte"
            except Exception:
                earnings_str = "No fijado"

        sec_lower = sector.lower()
        if 'tech' in sec_lower: sector_benchmark = 'XLK'
        elif 'finan' in sec_lower: sector_benchmark = 'XLF'
        elif 'energy' in sec_lower or 'energ' in sec_lower: sector_benchmark = 'XLE'
        elif 'health' in sec_lower: sector_benchmark = 'XLV'
        elif 'consumer' in sec_lower: sector_benchmark = 'XLY'
        elif 'comm' in sec_lower: sector_benchmark = 'XLC'
        elif 'gold' in sec_lower: sector_benchmark = 'GLD'

        data = {
            'symbol': ticker_symbol,
            'name': name,
            'sector': sector,
            'industry': industry,
            'sectorBenchmark': sector_benchmark,
            'desc': desc,
            'expense': expense_str,
            'earnings': earnings_str,
            'currentPrice': current_price,
            'high52w': p_high_52w,
            'low52w': p_low_52w,
            'prices': prices,
            'dates': dates
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))