from http.server import BaseHTTPRequestHandler
import os
import json
import psycopg2

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        connection_string = os.environ.get('POSTGRES_URL')
        if not connection_string:
            self.send_response(500)
            self.end_headers()
            return

        content_length = int(self.headers['Content-Length'])
        body_recibido = self.rfile.read(content_length)
        datos = json.loads(body_recibido.decode('utf-8'))
        
        nombre = datos.get('nombre', '').strip()
        nueva_categoria = datos.get('categoria', 'Mis Pares').strip()

        if not nombre or not nueva_categoria:
            self.send_response(400)
            self.end_headers()
            return

        try:
            conn = psycopg2.connect(connection_string)
            cursor = conn.cursor()
            
            # Actualizamos únicamente la columna categoría
            query = "UPDATE configuracion_pares SET categoria = %s WHERE nombre = %s;"
            cursor.execute(query, (nueva_categoria, nombre))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "success"}).encode('utf-8'))
            
        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(str(e).encode('utf-8'))

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()