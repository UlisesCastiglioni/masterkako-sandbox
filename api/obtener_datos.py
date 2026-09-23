import os
import psycopg2
import json
from datetime import datetime
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_GET(self):
        conn = None
        cursor = None
        try:
            connection_string = os.environ.get('POSTGRES_URL')
            if not connection_string:
                raise Exception("Falta la variable de entorno POSTGRES_URL en Vercel")

            conn = psycopg2.connect(connection_string)
            conn.autocommit = True
            cursor = conn.cursor()

            # 1. Consulta inteligente de pares con tolerancia a columnas faltantes
            tiene_columnas_extra = True
            try:
                cursor.execute("SELECT nombre, ticker_stock, ticker_bono, categoria, tipo_par FROM configuracion_pares;")
                pares_raw = cursor.fetchall()
            except Exception:
                # Si falló porque no existen 'categoria' o 'tipo_par', reintentamos con las columnas base
                conn.rollback()
                tiene_columnas_extra = False
                cursor.execute("SELECT nombre, ticker_stock, ticker_bono FROM configuracion_pares;")
                pares_raw = cursor.fetchall()

            # 2. Consulta de precios históricos filtrando fechas nulas
            cursor.execute("""
                SELECT ticker, to_char(fecha, 'DD/MM/YYYY'), precio_stock, volumen 
                FROM precios_historicos 
                WHERE fecha IS NOT NULL AND precio_stock IS NOT NULL 
                ORDER BY fecha ASC;
            """)
            precios_raw = cursor.fetchall()

            # 3. Mapeo optimizado de cotizaciones
            mapeo_precios = {}
            for row in precios_raw:
                if not row[0] or not row[1]:
                    continue
                ticker = str(row[0]).upper().strip()
                fecha = str(row[1]).strip()
                
                try:
                    precio = float(row[2]) if row[2] is not None else 0.0
                except (ValueError, TypeError):
                    precio = 0.0

                try:
                    volumen = float(row[3]) if row[3] is not None else 0.0
                except (ValueError, TypeError):
                    volumen = 0.0

                if ticker not in mapeo_precios:
                    mapeo_precios[ticker] = {}
                mapeo_precios[ticker][fecha] = {
                    'precio': precio,
                    'volumen': volumen
                }

            # 4. Función segura para ordenar fechas DD/MM/YYYY
            def parse_fecha_segura(f_str):
                try:
                    return datetime.strptime(f_str, '%d/%m/%Y')
                except Exception:
                    return datetime.min

            # 5. Ensamblado de la respuesta para el frontend
            respuesta_final = {}
            for row in pares_raw:
                if not row[0] or not row[1] or not row[2]:
                    continue
                nombre = str(row[0]).strip()
                stk = str(row[1]).upper().strip()
                bon = str(row[2]).upper().strip()

                if tiene_columnas_extra:
                    categoria = str(row[3]).strip() if len(row) > 3 and row[3] else 'Mis Pares'
                    tipo_par = str(row[4]).strip() if len(row) > 4 and row[4] else 'Defensivo'
                else:
                    categoria = 'Mis Pares'
                    tipo_par = 'Defensivo'

                dict_stk = mapeo_precios.get(stk, {})
                dict_bon = mapeo_precios.get(bon, {})

                # Fechas comunes válidas presentes en ambos activos
                claves_comunes = [f for f in set(dict_stk.keys()).intersection(dict_bon.keys()) if f and len(f) == 10]
                fechas_comunes = sorted(claves_comunes, key=parse_fecha_segura)

                respuesta_final[nombre] = {
                    "name": nombre,
                    "stock": stk,
                    "bono": bon,
                    "categoria": categoria,
                    "tipo_par": tipo_par,
                    "dates": fechas_comunes,
                    "stockPrices": [dict_stk[f]['precio'] for f in fechas_comunes],
                    "bonoPrices": [dict_bon[f]['precio'] for f in fechas_comunes],
                    "stockVolumes": [dict_stk[f]['volumen'] for f in fechas_comunes]
                }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(respuesta_final).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"error": f"Error interno en obtener_datos: {str(e)}"}).encode('utf-8'))
        finally:
            if cursor is not None:
                try: cursor.close()
                except: pass
            if conn is not None:
                try: conn.close()
                except: pass