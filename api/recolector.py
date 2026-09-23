from http.server import BaseHTTPRequestHandler
import os
import requests
import psycopg2
from datetime import datetime

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        connection_string = os.environ.get('POSTGRES_URL')
        if not connection_string:
            self.send_response(500)
            self.end_headers()
            return

        logs = []
        conn = None
        try:
            conn = psycopg2.connect(connection_string)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # --- CREAR TABLAS SI NO EXISTEN EN SUPABASE ---
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion_pares (
                id SERIAL PRIMARY KEY,
                nombre VARCHAR(100) UNIQUE,
                ticker_stock VARCHAR(50),
                ticker_bono VARCHAR(50),
                categoria VARCHAR(50) DEFAULT 'Mis Pares',
                tipo_par VARCHAR(20) DEFAULT 'Defensivo'
            );
            """)
            
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS precios_historicos (
                ticker VARCHAR(50),
                fecha DATE,
                precio_stock NUMERIC,
                precio_bono NUMERIC,
                volumen NUMERIC DEFAULT 0,
                PRIMARY KEY (ticker, fecha)
            );
            """)
            # -----------------------------------------------
            
            cursor.execute("SELECT ticker_stock, ticker_bono FROM configuracion_pares;")
            filas = cursor.fetchall()
            
            tickers_unicos = set()
            for f in filas:
                tickers_unicos.add(f[0].upper().strip())
                tickers_unicos.add(f[1].upper().strip())
            
            headers_nav = {'User-Agent': 'Mozilla/5.0'}
            
            for ticker in tickers_unicos:
                try:
                    url_api = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1y&interval=1d"
                    res = requests.get(url_api, headers=headers_nav, timeout=5)
                    
                    if res.status_code != 200:
                        continue
                    
                    data_json = res.json()
                    if not data_json.get('chart') or not data_json['chart'].get('result') or data_json['chart']['result'][0] is None:
                        logs.append(f"⚠️ {ticker}: No existe en Yahoo.")
                        continue
                        
                    res_m = data_json['chart']['result'][0]
                    timestamps = res_m.get('timestamp', [])
                    indicadores = res_m.get('indicators', {}).get('quote', [{}])[0]
                    precios_cierre = indicadores.get('close', [])
                    volumenes = indicadores.get('volume', []) 
                    
                    contador = 0
                    for i in range(len(timestamps)):
                        ts = timestamps[i]
                        val = precios_cierre[i]
                        vol = volumenes[i] if i < len(volumenes) and volumenes[i] is not None else 0
                        
                        if ts is None or val is None: continue
                        fecha_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                        
                        query_upsert = """
                        INSERT INTO precios_historicos (ticker, fecha, precio_stock, precio_bono, volumen)
                        VALUES (%s, %s, %s, %s, %s)
                        ON CONFLICT (ticker, fecha) DO UPDATE SET precio_stock = EXCLUDED.precio_stock, volumen = EXCLUDED.volumen;
                        """
                        cursor.execute(query_upsert, (ticker, fecha_str, float(val), 0, float(vol)))
                        contador += 1
                        
                    logs.append(f"✅ {ticker}: Sincronizados {contador} días (1 Año).")
                    
                except Exception as e_t:
                    logs.append(f"❌ Error en {ticker}: {str(e_t)}")
            
            if len(logs) == 0:
                logs.append("✅ La base de datos está vacía. Ve a la Terminal (Almacén) para agregar tus primeros pares.")

            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write("\n".join(logs).encode('utf-8'))
            
        except Exception as e_g:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e_g).encode('utf-8'))
        finally:
            if conn is not None:
                try: cursor.close()
                except Exception: pass
                conn.close()