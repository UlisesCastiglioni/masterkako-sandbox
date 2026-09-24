# api/sensibilidad.py
# Masterkako MKX - Diagnóstico de Sensibilidad y Exposición Macro
from http.server import BaseHTTPRequestHandler
import json
import urllib.parse
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        ticker = params.get('ticker', ['SPY'])[0].upper().strip()

        tech = ['NVDA', 'AAPL', 'MSFT', 'AMD', 'TSLA', 'QQQ', 'MU', 'GOOGL', 'META', 'AVGO', 'AMZN', 'INTC', 'CRM', 'ORCL', 'ARM', 'TSM', 'PLTR']
        energy = ['XLE', 'VIST', 'YPF', 'CVX', 'XOM', 'PBR', 'SLB', 'HAL']
        gold = ['GLD', 'GOLD', 'HMY', 'AU', 'NEM', 'PAAS', 'SLV']
        finance = ['JPM', 'BAC', 'WFC', 'C', 'XLF', 'GS', 'MS', 'BMA', 'GGAL', 'BBAR']
        defensive = ['XLP', 'KO', 'PEP', 'PG', 'MCD', 'WMT', 'JNJ', 'COST', 'CL']

        if ticker in tech:
            sector = "Tecnología & Crecimiento"
            beta = "Alto (Beta > 1.3)"
            exposicion = "ALTA"
            rates = "Muy Alta (Negativa)"
            dxy = "Moderada"
            wti = "Indirecta"
            vix = "Alta"
            explicacion = f"{ticker} posee alta sensibilidad a las tasas del Tesoro (US10Y). Desviaciones alcistas en inflación o tasas comprimen de inmediato sus múltiplos de valuación."
        elif ticker in energy:
            sector = "Energía & Petróleo"
            beta = "Medio-Alto"
            exposicion = "ALTA A COMMODITY"
            rates = "Baja"
            dxy = "Inversa (DXY frena)"
            wti = "Directa Máxima (+90%)"
            vix = "Media"
            explicacion = f"{ticker} depende directamente de la cotización internacional del crudo WTI/Brent y las decisiones de cuota de la OPEP+."
        elif ticker in gold:
            sector = "Metales Preciosos & Refugio"
            beta = "Descorrelacionado"
            exposicion = "AUTÓNOMO / REFUGIO"
            rates = "Inversa con tasas reales"
            dxy = "Inversa Máxima"
            wti = "Baja"
            vix = "Positiva (Sube con pánico)"
            explicacion = f"{ticker} opera como activo de cobertura contra depreciación monetaria e incertidumbre geopolítica mundial."
        elif ticker in finance:
            sector = "Financiero & Bancos"
            beta = "Medio"
            exposicion = "MEDIA"
            rates = "Positiva (Márgenes)"
            dxy = "Neutral"
            wti = "Baja"
            vix = "Media"
            explicacion = f"{ticker} reacciona a la curva de rendimientos soberana y al ritmo de actividad económica."
        elif ticker in defensive:
            sector = "Consumo Básico / Defensivo"
            beta = "Bajo"
            exposicion = "BAJA"
            rates = "Baja"
            dxy = "Baja"
            wti = "Costos de logística"
            vix = "Baja (Escudo)"
            explicacion = f"{ticker} ofrece flujos estables y predecibles con baja vulnerabilidad a shocks de tasas o materias primas."
        else:
            sector = "Renta Variable General"
            beta = "Medio"
            exposicion = "MEDIA"
            rates = "Moderada"
            dxy = "Moderada"
            wti = "Indirecta"
            vix = "Media"
            explicacion = f"{ticker} responde a las condiciones generales de liquidez del S&P 500."

        res = {
            "status": "success",
            "ticker": ticker,
            "sector": sector,
            "beta": beta,
            "exposicion": exposicion,
            "sensibilidad": {
                "tasas": rates,
                "dolar": dxy,
                "petroleo": wti,
                "vix": vix
            },
            "explicacion": explicacion,
            "timestamp": datetime.now().strftime('%H:%M:%S')
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(res).encode('utf-8'))