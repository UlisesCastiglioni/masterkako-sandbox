# api/sensibilidad.py
# Masterkako MKX - Diagnóstico Cuantitativo de Sensibilidad Macro y Exposición Externa

from http.server import BaseHTTPRequestHandler
import json
import urllib.parse

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed_path.query)
        ticker = params.get('ticker', [''])[0].strip().toUpperCase() if hasattr(str, 'toUpperCase') else params.get('ticker', [''])[0].strip().upper()

        if not ticker:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Ticker no especificado'}).encode('utf-8'))
            return

        tech_list = ['NVDA', 'AMD', 'AAPL', 'MSFT', 'TSLA', 'QQQ', 'MU', 'GOOGL', 'META', 'AVGO', 'AMZN', 'INTC', 'CRM', 'ORCL']
        energy_list = ['XLE', 'VIST', 'YPF', 'CVX', 'XOM', 'PBR', 'SLB', 'HAL']
        gold_list = ['GLD', 'GOLD', 'HMY', 'AU', 'NEM', 'PAAS']
        finance_list = ['JPM', 'BAC', 'WFC', 'C', 'XLF', 'GS', 'MS', 'BMA', 'GGAL']
        defensive_list = ['XLP', 'KO', 'PEP', 'PG', 'MCD', 'WMT', 'JNJ']

        if ticker in tech_list:
            sector = "Tecnología & Crecimiento (High Beta)"
            beta = "Alto (1.35x)"
            s_tasas = "Muy Alta (Inversa)"
            s_dxy = "Moderada (Presiona ventas globales)"
            s_wti = "Baja / Indirecta"
            s_vix = "Alta (Sufre en pánico)"
            expo = "ALTA EXPOSICIÓN EXTERNA"
            expo_color = "var(--err)"
            calendario_focus = ["cpi", "fomc"]
            explicacion = f"<strong>Vulnerabilidad a Tasas:</strong> {ticker} descuenta flujos futuros a largo plazo. Si el Bono US10Y sube, comprime múltiplos y frena compras. Requiere VIX bajo y tasas calmas para sostener rupturas."
        elif ticker in energy_list:
            sector = "Energía, Petróleo & Gas"
            beta = "Medio-Alto (1.15x)"
            s_tasas = "Baja"
            s_dxy = "Inversa Fuerte"
            s_wti = "Directa Extrema (+90%)"
            s_vix = "Media"
            expo = "ALTA EXPOSICIÓN A COMMODITIES"
            expo_color = "var(--err)"
            calendario_focus = ["eia", "opec"]
            explicacion = f"<strong>Atado al Crudo:</strong> El catalizador rector de {ticker} es el Petróleo WTI. Un barril subiendo expande márgenes directos. DXY débil despeja el rally de energía."
        elif ticker in gold_list:
            sector = "Metales Preciosos & Cobertura"
            beta = "Descorrelacionado (0.25x)"
            s_tasas = "Inversa con Tasas Reales"
            s_dxy = "Inversa Máxima (-85%)"
            s_wti = "Baja"
            s_vix = "Positiva (Actúa como refugio)"
            expo = "BAJA EXPOSICIÓN AL MERCADO"
            expo_color = "var(--green)"
            calendario_focus = ["fomc", "cpi"]
            explicacion = f"<strong>Escudo de Valor:</strong> {ticker} se beneficia en escenarios de desconfianza macro, debilidad del dólar DXY o escalada inflacionaria."
        elif ticker in finance_list:
            sector = "Finanzas & Banca"
            beta = "Medio (1.05x)"
            s_tasas = "Positiva (Margen de intermediación)"
            s_dxy = "Neutral"
            s_wti = "Baja"
            s_vix = "Media-Alta"
            expo = "EXPOSICIÓN MEDIA"
            expo_color = "var(--blue)"
            calendario_focus = ["fomc", "nfp"]
            explicacion = f"<strong>Sensible a Curva de Rendimientos:</strong> Tasas firmes permiten a {ticker} cobrar más por crédito, pero una curva invertida alerta sobre riesgo de mora crediticia."
        elif ticker in defensive_list:
            sector = "Consumo Básico / Defensivo"
            beta = "Bajo (0.65x)"
            s_tasas = "Baja"
            s_dxy = "Baja"
            s_wti = "Costos logísticos"
            s_vix = "Baja (Refugio de cartera)"
            expo = "MÍNIMA EXPOSICIÓN EXTERNA"
            expo_color = "var(--green)"
            calendario_focus = ["cpi"]
            explicacion = f"<strong>Autonomía Operativa:</strong> Flujos de caja inelásticos. {ticker} no depende del humor diario de Wall Street y ofrece contrapeso ante caídas de índices."
        else:
            sector = "Índice / Fondo Diversificado"
            beta = "Mercado (1.00x)"
            s_tasas = "Moderada"
            s_dxy = "Moderada"
            s_wti = "Equilibrada"
            s_vix = "Directa con el sentimiento general"
            expo = "EXPOSICIÓN DE MERCADO"
            expo_color = "var(--blue)"
            calendario_focus = ["cpi", "fomc", "nfp"]
            explicacion = f"<strong>Comportamiento Sistémico:</strong> {ticker} refleja el equilibrio global entre liquidez de la Reserva Federal y expectativas de crecimiento económico."

        respuesta = {
            'status': 'success',
            'ticker': ticker,
            'sector': sector,
            'beta': beta,
            'expo': expo,
            'expo_color': expo_color,
            'sensibilidad_tasas': s_tasas,
            'sensibilidad_dxy': s_dxy,
            'sensibilidad_petroleo': s_wti,
            'sensibilidad_vix': s_vix,
            'explicacion': explicacion,
            'calendario_focus': calendario_focus
        }

        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(respuesta).encode('utf-8'))