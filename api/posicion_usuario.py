import os
import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from supabase import create_client, Client

class handler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200):
        self.send_response(status)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def do_OPTIONS(self):
        self._set_headers()

    def do_GET(self):
        query = parse_qs(urlparse(self.path).query)
        pair_name = query.get('pair_name', [None])[0]

        if not pair_name:
            self._set_headers(400)
            self.wfile.write(json.dumps({"error": "Falta el nombre del par"}).encode())
            return

        try:
            # Conexión a Supabase usando las variables de entorno de Vercel
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_KEY")
            supabase: Client = create_client(url, key)

            # Traer los últimos 15 registros de este par
            response = supabase.table("user_trades").select("*").eq("pair_name", pair_name).order("trade_date", desc=True).limit(15).execute()
            
            self._set_headers(200)
            self.wfile.write(json.dumps(response.data).encode())
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_POST(self):
        try:
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            data = json.loads(post_data)

            pair_name = data.get('pair_name')
            trade_date = data.get('trade_date')
            executed_position = data.get('executed_position')
            note = data.get('note', '')

            if not all([pair_name, trade_date, executed_position]):
                self._set_headers(400)
                self.wfile.write(json.dumps({"error": "Faltan datos requeridos"}).encode())
                return

            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_KEY")
            supabase: Client = create_client(url, key)

            # Upsert: Inserta el registro o lo actualiza si ya existe uno ese mismo día
            response = supabase.table("user_trades").upsert({
                "pair_name": pair_name,
                "trade_date": trade_date,
                "executed_position": executed_position,
                "note": note
            }, on_conflict="pair_name,trade_date").execute()

            self._set_headers(200)
            self.wfile.write(json.dumps({"status": "ok", "data": response.data}).encode())
        except Exception as e:
            self._set_headers(500)
            self.wfile.write(json.dumps({"error": str(e)}).encode())