from http.server import BaseHTTPRequestHandler
import os
import requests
import psycopg2
import math
from datetime import datetime

TELEGRAM_TOKEN = "8754211087:AAE0GXwAkcnlPK8dYoMoZXew3EgrXbq26Vk"
TELEGRAM_CHAT_IDS = ["2032380151", "8757698875"]

def calc_rsi(prices, period=14):
    if len(prices) < period: return [50]*len(prices)
    rsis = []
    g, l = 0, 0
    for i in range(1, period + 1):
        d = prices[i] - prices[i-1]
        if d > 0: g += d
        else: l -= d
    ag = g / period
    al = l / period
    rsis.append(100 - (100 / (1 + (ag / (al if al != 0 else 1e-9)))))
    for i in range(period + 1, len(prices)):
        d = prices[i] - prices[i-1]
        gn = d if d > 0 else 0
        ln = -d if d < 0 else 0
        ag = (ag * 13 + gn) / 14
        al = (al * 13 + ln) / 14
        rsis.append(100 - (100 / (1 + (ag / (al if al != 0 else 1e-9)))))
    return [50]*period + rsis

def ema(data, p):
    if not data: return []
    k = 2 / (p + 1)
    r = [data[0]]
    for i in range(1, len(data)):
        r.append(data[i] * k + r[-1] * (1 - k))
    return r

def sma(data, p):
    if len(data) < p: return [data[0] if len(data)>0 else 0]*len(data)
    smas = []
    for i in range(len(data)):
        if i < p - 1:
            smas.append(data[i])
        else:
            smas.append(sum(data[i-p+1:i+1]) / p)
    return smas

def calc_macd(prices):
    if len(prices) < 26: return [0]*len(prices)
    e12 = ema(prices, 12)
    e26 = ema(prices, 26)
    macd = [e12[i] - e26[i] for i in range(len(prices))]
    sig = ema(macd, 9)
    return [macd[i] - sig[i] for i in range(len(prices))]

def calc_vol(prices, p=20):
    v = []
    for i in range(len(prices)):
        if i < p:
            v.append(1)
            continue
        s = prices[i-p:i]
        m = sum(s)/p
        va = sum((x - m)**2 for x in s)/p
        v.append((math.sqrt(va) / prices[i]) * 100 if prices[i] != 0 else 1)
    return v

# ENTRADA ASIMETRICA: Facil entrar al stock (+3), dificil salir al bono (-thr)
def eval_trade_signal(sc, thr, is_rotacion, ema_s_diff, ema_b_diff):
    if sc >= 3: return 'STOCK'
    elif sc <= -thr: return 'BONO'
    elif ema_s_diff > 0: return 'STOCK'
    elif is_rotacion and ema_b_diff > 0: return 'BONO'
    return 'CASH'

def calc_optimal_thr(sp, bp, scores, is_rotacion, ema20_s, ema20_b):
    best_ret = -float('inf')
    best_v = 20
    last = len(scores) - 1
    lookback = min(60, last) # Ajuste a 60 días
    if lookback < 10: return 20
    
    for v in range(10, 26): # Tope en 25
        cumul = 1.0
        for i in range(last - lookback + 1, last + 1):
            rS = (sp[i] - sp[i-1]) / sp[i-1] if sp[i-1] != 0 else 0
            rB = (bp[i] - bp[i-1]) / bp[i-1] if bp[i-1] != 0 else 0
            ema_s_diff = sp[i-1] - ema20_s[i-1]
            ema_b_diff = bp[i-1] - ema20_b[i-1]
            sig = eval_trade_signal(scores[i-1], v, is_rotacion, ema_s_diff, ema_b_diff)
            ret = rS if sig == 'STOCK' else (rB if sig == 'BONO' else 0)
            cumul *= (1 + ret)
        if cumul > best_ret:
            best_ret = cumul
            best_v = v
    return best_v

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        connection_string = os.environ.get('POSTGRES_URL')
        if not connection_string:
            self.send_response(500)
            self.end_headers()
            self.wfile.write("Falta Base de Datos".encode('utf-8'))
            return

        conn = None
        try:
            conn = psycopg2.connect(connection_string)
            cursor = conn.cursor()
            
            cursor.execute("SELECT nombre, ticker_stock, ticker_bono, categoria, tipo_par FROM configuracion_pares;")
            pares = cursor.fetchall()
            
            cursor.execute("SELECT ticker, to_char(fecha, 'DD/MM/YYYY'), precio_stock, volumen FROM precios_historicos ORDER BY fecha ASC;")
            precios_raw = cursor.fetchall()
            
            mapeo_precios = {}
            for ticker, fecha, precio, volumen in precios_raw:
                t_key = ticker.upper().strip()
                if t_key not in mapeo_precios: mapeo_precios[t_key] = {}
                mapeo_precios[t_key][fecha] = {'p': float(precio), 'v': float(volumen) if volumen else 0.0}
            
            resultados = []
            
            for row in pares:
                nombre = row[0]
                stk = row[1].upper().strip()
                bon = row[2].upper().strip()
                tipo_par = row[4] if len(row) > 4 and row[4] else 'Defensivo'
                is_rotacion = (tipo_par == 'Rotación')
                
                dict_stk = mapeo_precios.get(stk, {})
                dict_bon = mapeo_precios.get(bon, {})
                
                fechas_comunes = sorted(list(set(dict_stk.keys()).intersection(dict_bon.keys())), key=lambda x: datetime.strptime(x, '%d/%m/%Y'))
                if len(fechas_comunes) < 32: continue
                
                sp = [dict_stk[f]['p'] for f in fechas_comunes]
                bp = [dict_bon[f]['p'] for f in fechas_comunes]
                sV = [dict_stk[f]['v'] for f in fechas_comunes]
                
                calcPrices = [sp[i] / bp[i] if bp[i] != 0 else 1 for i in range(len(sp))] if is_rotacion else sp
                
                rsi = calc_rsi(calcPrices)
                macd = calc_macd(calcPrices)
                volDev = calc_vol(calcPrices)
                ema20_s = ema(sp, 20)
                ema20_b = ema(bp, 20)
                sma50_s = sma(sp, 50)
                sma50_b = sma(bp, 50)
                
                scores = []
                for i in range(len(sp)):
                    volToday = sV[i]
                    volBoost = 1.0
                    if i >= 20:
                        volMA20 = sum(sV[i-20:i]) / 20
                        if volMA20 > 0 and volToday > 0:
                            ratioVol = volToday / volMA20
                            if ratioVol >= 1.3: volBoost = 1.35
                            elif ratioVol <= 0.7: volBoost = 0.85
                            
                    pr = calcPrices[i] if calcPrices[i] != 0 else 1
                    vd = volDev[i] if volDev[i] != 0 else 1
                    
                    rawScore = ((rsi[i] or 50) - 50) * 1.2 + ((macd[i] / pr) * 1000 * 3 * max(0.5, min(2, 2 / vd)))
                    if math.isnan(rawScore) or math.isinf(rawScore): rawScore = 0
                    rawScore *= volBoost
                    
                    # TRAMPA DE APRENDIZAJE SMA50 (Omniscient)
                    if i >= 49:
                        if sp[i] > sma50_s[i]:
                            if rawScore > 0: rawScore *= 1.5
                        else:
                            if rawScore > 0: rawScore /= 3.0
                            
                        if is_rotacion and bp[i] < sma50_b[i] and rawScore < 0:
                            rawScore /= 3.0
                            
                    scores.append(rawScore)
                
                thr = calc_optimal_thr(sp, bp, scores, is_rotacion, ema20_s, ema20_b)
                
                # Tracking de Flips
                last = len(scores) - 1
                limit = max(1, last - 120)
                flips = 0
                last_sig = None
                days_since = 0
                
                for i in range(limit, last + 1):
                    sc = scores[i]
                    e_s_d = sp[i] - ema20_s[i]
                    e_b_d = bp[i] - ema20_b[i]
                    
                    sig = eval_trade_signal(sc, thr, is_rotacion, e_s_d, e_b_d)
                    
                    if last_sig is not None and sig != last_sig:
                        flips += 1
                        days_since = 0
                    else:
                        days_since += 1
                    last_sig = sig
                
                avg_flip = round(120 / flips) if flips > 0 else 120
                
                sc_curr = scores[-1]
                sc_prev = scores[-2]
                
                estado = eval_trade_signal(sc_curr, thr, is_rotacion, sp[-1] - ema20_s[-1], bp[-1] - ema20_b[-1])
                
                if estado == 'STOCK':
                    accion = f"COMPRAR {stk}"
                elif estado == 'BONO':
                    accion = f"COMPRAR {bon}" if is_rotacion else f"COBERTURA ({bon})"
                else:
                    accion = "MANTENER CASH"

                resultados.append({
                    'name': nombre,
                    'tipo': tipo_par,
                    'stk': stk,
                    'bon': bon,
                    'score': round(sc_curr, 2),
                    'prev': round(sc_prev, 2),
                    'thr': thr,
                    'estado': estado,
                    'accion': accion,
                    'flip_avg': avg_flip,
                    'flip_cur': days_since
                })
            
            # --- ARMADO DEL MENSAJE DE TELEGRAM V8 OMNISCIENT ---
            mensaje = f"🏛 <b>MASTERKAKO QUANT V8.0 OMNISCIENT</b>\n"
            mensaje += f"📅 <i>Reporte: {datetime.now().strftime('%d/%m/%Y')}</i>\n"
            mensaje += f"───────────────────\n\n"
            
            grupos = {"STOCK": [], "BONO": [], "CASH": []}
            for r in resultados: grupos[r['estado']].append(r)
            
            def form_card(r):
                return f"Nombre del par: ({r['name']})\nTipo de Par: ({r['tipo']})\nStock: ({r['stk']})\nBono: ({r['bon']})\nUmbral: (±{r['thr']})\nScore actual: ({'+' if r['score']>0 else ''}{r['score']})\nScore del día anterior: ({'+' if r['prev']>0 else ''}{r['prev']})\nPromedio flip / Día del ciclo: ({r['flip_avg']} días / Día {r['flip_cur']})\nSeñal: (<b>{r['accion']}</b>)\n───────────────\n"

            if grupos['STOCK']:
                mensaje += "🟢 <b>COMPRAS (STOCK)</b>\n\n"
                for r in grupos['STOCK']: mensaje += form_card(r)
            
            if grupos['BONO']:
                mensaje += "🔵 <b>COBERTURAS / ROTACIONES</b>\n\n"
                for r in grupos['BONO']: mensaje += form_card(r)

            if grupos['CASH']:
                mensaje += "⚪ <b>ZONAS NEUTRAS (CASH)</b>\n\n"
                for r in grupos['CASH']: mensaje += form_card(r)

            url_tg = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            for chat_id in TELEGRAM_CHAT_IDS:
                requests.post(url_tg, data={"chat_id": chat_id, "text": mensaje, "parse_mode": "HTML"}, timeout=5)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/plain; charset=utf-8')
            self.end_headers()
            self.wfile.write(f"✅ ¡Éxito! Reporte V8.0 enviado.".encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(f"Error critico V8: {str(e)}".encode('utf-8'))
        finally:
            if conn is not None:
                try: cursor.close()
                except: pass
                conn.close()