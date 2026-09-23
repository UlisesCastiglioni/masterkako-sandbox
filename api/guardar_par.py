# api/guardar_par.py
from http.server import BaseHTTPRequestHandler
import json
import os
import urllib.request
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        data = json.loads(body.decode('utf-8')) if body else {}

        nombre = data.get('nombre', '').strip()
        stock = data.get('stock', '').strip().upper()
        bono = data.get('bono', '').strip().upper()
        categoria = data.get('categoria', 'Mis Pares').strip()
        tipo_par = data.get('tipo_par', 'Defensivo').strip()

        if not nombre or not stock or not bono:
            self.send_response(400)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Faltan campos obligatorios'}).encode('utf-8'))
            return

        supabase_url = os.environ.get('SUPABASE_URL') or os.environ.get('NEXT_PUBLIC_SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_SERVICE_ROLE_KEY') or os.environ.get('SUPABASE_KEY') or os.environ.get('SUPABASE_ANON_KEY')

        if not supabase_url or not supabase_key:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({'error': 'Faltan credenciales de Supabase'}).encode('utf-8'))
            return

        # 1. Guardar par en Supabase
        payload_par = json.dumps({
            'nombre': nombre,
            'stock': stock,
            'bono': bono,
            'categoria': categoria,
            'tipo_par': tipo_par
        }).encode('utf-8')

        req_par = urllib.request.Request(
            f"{supabase_url}/rest/v1/pares",
            data=payload_par,
            headers={
                'apikey': supabase_key,
                'Authorization': f'Bearer {supabase_key}',
                'Content-Type': 'application/json',
                'Prefer': 'resolution=merge-duplicates'
            },
            method='POST'
        )

        try:
            with urllib.request.urlopen(req_par) as response:
                pass
        except Exception:
            # Reintento con estructura básica si no existen las columnas nuevas
            payload_base = json.dumps({'nombre': nombre, 'stock': stock, 'bono': bono}).encode('utf-8')
            req_base = urllib.request.Request(
                f"{supabase_url}/rest/v1/pares",
                data=payload_base,
                headers={
                    'apikey': supabase_key,
                    'Authorization': f'Bearer {supabase_key}',
                    'Content-Type': 'application/json',
                    'Prefer': 'resolution=merge-duplicates'
                },
                method='POST'
            )
            try:
                with urllib.request.urlopen(req_base) as response:
                    pass
            except Exception:
                pass

        # 2. Descargar histórico de Yahoo Finance para stock y bono
        def sync_ticker(ticker):
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp:
                    yf_data = json.loads(resp.read().decode('utf-8'))

                res = yf_data.get('chart', {}).get('result', [{}])[0]
                timestamps = res.get('timestamp', [])
                closes = res.get('indicators', {}).get('quote', [{}])[0].get('close', [])
                volumes = res.get('indicators', {}).get('quote', [{}])[0].get('volume', [])

                rows = []
                for ts, c, v in zip(timestamps, closes, volumes):
                    if c is None:
                        continue
                    fecha_str = datetime.utcfromtimestamp(ts).strftime('%d/%m/%Y')
                    rows.append({
                        'ticker': ticker,
                        'fecha': fecha_str,
                        'precio': round(float(c), 4),
                        'volumen': int(v or 0)
                    })

                if rows:
                    p_data = json.dumps(rows).encode('utf-8')
                    req_p = urllib.request.Request(
                        f"{supabase_url}/rest/v1/precios",
                        data=p_data,
                        headers={
                            'apikey': supabase_key,
                            'Authorization': f'Bearer {supabase_key}',
                            'Content-Type': 'application/json',
                            'Prefer': 'resolution=merge-duplicates'
                        },
                        method='POST'
                    )
                    with urllib.request.urlopen(req_p) as r:
                        pass
            except Exception as e:
                print(f"Error sincronizando {ticker}: {e}")

        sync_ticker(stock)
        sync_ticker(bono)

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps({'success': True, 'message': 'Par guardado'}).encode('utf-8'))