import os
import json
import re
import datetime as dt
from datetime import datetime
import sqlite3
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import requests
import urllib.parse

# ==========================================
# ⚙️ CONFIGURACIÓN INICIAL
# ==========================================
# Verificación de API Key para Logs de Render
_api_key_status = os.environ.get("GOOGLE_API_KEY")
if _api_key_status:
    print("✅ API KEY DETECTADA (longitud: {})".format(len(_api_key_status)))
else:
    print("❌ API KEY NO ENCONTRADA — Configura GOOGLE_API_KEY en Render Environment")

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app, resources={r"/*": {"origins": "*"}})

# Rutas relativas (compatibles con Render)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FILE = os.path.join(BASE_DIR, "sabores_del_sur.db")
PEDIDO_FILE = os.path.join(BASE_DIR, "pedido.json")


# ==========================================
# 🗄️ HELPERS DE BASE DE DATOS
# ==========================================
def conectar_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def obtener_columnas_producto():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(productos)")
    columnas = [row[1] for row in cursor.fetchall()]
    conn.close()
    return columnas


def construir_campos_producto():
    columnas = obtener_columnas_producto()
    campos = [c for c in ["id", "nombre", "precio", "stock", "categoria"] if c in columnas]
    campos.append("imagen_url" if "imagen_url" in columnas else "'' AS imagen_url")
    return ", ".join(campos)


def obtener_productos_db(limit=50):
    campos = construir_campos_producto()
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        f"SELECT {campos} FROM productos ORDER BY categoria ASC, id ASC LIMIT ?",
        (limit,)
    )
    productos = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return productos


def obtener_producto_db(producto_id):
    campos = construir_campos_producto()
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {campos} FROM productos WHERE id = ?", (producto_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


# ==========================================
# 📦 INVENTARIO Y CARRITO
# ==========================================
carrito_actual = []


def consultar_inventario(producto: str = None):
    """Consulta el inventario real del minimarket en la base de datos."""
    conn = None
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        if producto and producto.strip():
            cursor.execute(
                "SELECT id, nombre, precio, stock, categoria FROM productos "
                "WHERE nombre LIKE ? ORDER BY nombre ASC",
                (f"%{producto.strip()}%",)
            )
            rows = [dict(r) for r in cursor.fetchall()]
            if not rows:
                return json.dumps(
                    {"encontrado": False, "mensaje": f"No se encontró '{producto}' en el inventario."},
                    ensure_ascii=False
                )
            resultados = [
                {"id": r["id"], "nombre": r["nombre"], "precio": r["precio"],
                 "stock": r["stock"], "categoria": r["categoria"]}
                for r in rows
            ]
            return json.dumps({"encontrado": True, "productos": resultados}, ensure_ascii=False)
        else:
            cursor.execute(
                "SELECT id, nombre, precio, stock, categoria FROM productos "
                "ORDER BY categoria ASC, nombre ASC"
            )
            rows = [dict(r) for r in cursor.fetchall()]
            categorias = {}
            for r in rows:
                cat = r.get("categoria") or "Otros"
                categorias.setdefault(cat, []).append(
                    {"id": r["id"], "nombre": r["nombre"], "precio": r["precio"], "stock": r["stock"]}
                )
            return json.dumps({"total_productos": len(rows), "categorias": categorias}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Error al consultar inventario: {str(e)}"}, ensure_ascii=False)
    finally:
        if conn:
            conn.close()


def agregar_producto(producto: str, cantidad: int = 1):
    """Agrega una cantidad específica de un producto al carrito."""
    global carrito_actual
    conn = None
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, nombre, precio, stock FROM productos WHERE nombre LIKE ?",
            (f"%{producto}%",)
        )
        rows = [dict(r) for r in cursor.fetchall()]
        if not rows:
            return f"Error: El producto '{producto}' no existe en el catálogo."
        prod = min(rows, key=lambda r: len(r["nombre"]))
        if prod["stock"] < cantidad:
            return f"Error de Stock: Solo quedan {prod['stock']} unidades de {prod['nombre']}."
        cursor.execute(
            "UPDATE productos SET stock = ? WHERE id = ?",
            (prod["stock"] - cantidad, prod["id"])
        )
        conn.commit()
        for item in carrito_actual:
            if item["id"] == prod["id"]:
                item["cantidad"] += cantidad
                item["subtotal"] = item["precio"] * item["cantidad"]
                return f"Éxito: Sumadas {cantidad} unidades de {prod['nombre']}. Total en carrito: {item['cantidad']}."
        carrito_actual.append({
            "id": prod["id"], "nombre": prod["nombre"], "precio": prod["precio"],
            "cantidad": cantidad, "subtotal": prod["precio"] * cantidad
        })
        return f"Éxito: Agregados {cantidad} unidades de {prod['nombre']} al carrito."
    except Exception as e:
        return f"Error al agregar producto: {str(e)}"
    finally:
        if conn:
            conn.close()


def _calcular_totales():
    global carrito_actual
    if not carrito_actual:
        return 0, 0, []
    nombres = [item["nombre"].lower() for item in carrito_actual]
    total_a_pagar = sum(item["subtotal"] for item in carrito_actual)
    descuento = 0
    promos = []
    if (any("carne" in n for n in nombres) and any("carbon" in n for n in nombres)
            and any("sal" in n for n in nombres)):
        descuento += total_a_pagar * 0.15
        promos.append("Pack Parrillero (-15%)")
    if (any("leche" in n for n in nombres)
            and any("pan" in n or "marraqueta" in n or "hallulla" in n for n in nombres)
            and any("mantequilla" in n for n in nombres)):
        descuento += total_a_pagar * 0.10
        promos.append("Desayuno Sureño (-10%)")
    if (any("tomate" in n for n in nombres) and any("lechuga" in n for n in nombres)
            and any("cebolla" in n for n in nombres)):
        descuento += total_a_pagar * 0.12
        promos.append("Pack Ensalada Fresca (-12%)")
    return total_a_pagar - descuento, descuento, promos


def calcular_total() -> str:
    """Calcula el monto total actual del carrito, incluyendo descuentos."""
    if not carrito_actual:
        return "El carrito está vacío."
    total, desc, promos = _calcular_totales()
    msg = f"El total actual es de ${total:,.0f}."
    if desc > 0:
        msg += f" (Ahorro de ${desc:,.0f} por: {', '.join(promos)})."
    return msg


# ==========================================
# 📞 INTEGRACIONES (WhatsApp)
# ==========================================
def enviar_whatsapp_confirmacion(resumen_pedido):
    telefono = "56956465104"
    apikey = "5073002"
    items_msg = ""
    for item in resumen_pedido.get("productos", []):
        items_msg += f"- {item['nombre']} x{item['cantidad']} (${item['subtotal']:,.0f})\n"
    nombre = resumen_pedido.get("cliente", "Cliente Web")
    texto = (
        f"🛒 *SABORES DEL SUR - NUEVO PEDIDO*\n\n"
        f"👤 *Cliente:* {nombre}\n"
        f"📦 *Detalle:*\n{items_msg}\n"
        f"💰 *Total a pagar:* ${resumen_pedido['total']:,.0f}\n"
        f"📍 *Retiro:* Casa Central (Calle de la Ribera 450)\n\n"
        f"¡Gracias por su compra! 🌽🥩"
    )
    texto_encoded = urllib.parse.quote(texto)
    url = f"https://api.callmebot.com/whatsapp.php?phone={telefono}&text={texto_encoded}&apikey={apikey}"
    try:
        response = requests.get(url, timeout=15)
        if response.status_code == 200 and "Message queued" in response.text:
            print("¡WhatsApp (CallMeBot) enviado con éxito!")
            return True
        print(f"Error de CallMeBot API: {response.text}")
    except Exception as e:
        print(f"Error enviando WhatsApp via CallMeBot: {e}")
    return False


def confirmar_compra(nombre_cliente: str = None):
    """Confirma el pedido actual, guarda el resumen y envía notificación por WhatsApp."""
    global carrito_actual
    if not carrito_actual:
        return "Error: No puedo confirmar la compra porque el carrito está vacío."
    total, desc, promos = _calcular_totales()
    resumen_pedido = {
        "fecha_pedido": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "productos": carrito_actual, "total": total,
        "descuento": desc, "promos_aplicadas": promos, "estado": "Confirmado"
    }
    try:
        with open(PEDIDO_FILE, "w", encoding="utf-8") as f:
            json.dump(resumen_pedido, f, indent=4, ensure_ascii=False)
        resumen_pedido["cliente"] = nombre_cliente or "Cliente Web"
        wsp_enviado = enviar_whatsapp_confirmacion(resumen_pedido)
        carrito_actual = []
        msg = f"¡Compra confirmada! Total a pagar: ${total:,.0f}."
        if nombre_cliente:
            msg = f"¡Excelente {nombre_cliente}! Compra confirmada por ${total:,.0f}."
        if promos:
            msg += f" Se aplicaron promos: {', '.join(promos)}."
        msg += " Te enviamos el detalle por WhatsApp." if wsp_enviado else " (Aviso: No se pudo enviar el WhatsApp)."
        return msg
    except Exception as e:
        return f"Error crítico al guardar el pedido: {str(e)}"




# ==========================================
# 🌐 ENDPOINTS DE LA API
# ==========================================


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/catalogo')
def catalogo():
    return render_template('catalogo.html')


@app.route('/carrito')
def carrito_page():
    return render_template('carrito.html')


@app.route('/inventario_page')
def inventario_page():
    return render_template('inventario.html')


@app.route('/cuenta')
def cuenta():
    return render_template('cuenta.html')


@app.route('/recetas')
def recetas():
    return render_template('recetas.html')


@app.route("/api/productos", methods=["GET"])
def api_productos():
    return jsonify(obtener_productos_db(limit=50))


@app.route("/api/carrito/add", methods=["POST"])
def api_carrito_add():
    global carrito_actual
    data = request.get_json() or {}
    producto_id = data.get("id")
    cantidad = int(data.get("cantidad", 1))
    if not producto_id:
        return jsonify({"error": "Falta el id del producto."}), 400
    if cantidad < 1:
        return jsonify({"error": "La cantidad debe ser al menos 1."}), 400
    producto = obtener_producto_db(producto_id)
    if not producto:
        return jsonify({"error": "Producto no encontrado."}), 404
    if producto["stock"] < cantidad:
        return jsonify({"error": "Stock insuficiente.", "stock": producto["stock"]}), 409
    existente = next((item for item in carrito_actual if item["id"] == producto_id), None)
    if existente:
        existente["cantidad"] += cantidad
        existente["subtotal"] = existente["cantidad"] * existente["precio"]
    else:
        carrito_actual.append({
            "id": producto["id"], "nombre": producto["nombre"],
            "precio": producto["precio"], "cantidad": cantidad,
            "subtotal": producto["precio"] * cantidad
        })
    total, desc, promos = _calcular_totales()
    return jsonify({"productos": carrito_actual, "total": total, "descuento": desc, "promos_aplicadas": promos})


@app.route("/inventario", methods=["GET"])
def obtener_inventario():
    return jsonify(obtener_productos_db(limit=1000))


@app.route("/ultimo-pedido", methods=["GET"])
def ultimo_pedido():
    try:
        if os.path.exists(PEDIDO_FILE):
            with open(PEDIDO_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify(data)
        return jsonify({"error": "No hay pedidos previos"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/test", methods=["GET"])
def test_server():
    return jsonify({"status": "ok", "message": "Servidor Flask activo y funcionando correctamente"})


@app.route("/api/carrito", methods=["GET"])
def obtener_carrito():
    total, desc, promos = _calcular_totales()
    return jsonify({"productos": carrito_actual, "total": total, "descuento": desc, "promos_aplicadas": promos})


# ==========================================
# 🤖 ENDPOINT PRINCIPAL DEL CHAT
# ==========================================
@app.route("/chat", methods=["POST"])
def chat():
    global carrito_actual
    try:
        data = request.get_json()
        mensaje_usuario = data.get("mensaje", "").strip()
        modo_ia_real = data.get("modoIAReal", False)

        if not mensaje_usuario:
            return jsonify({"respuesta": "Mensaje vacío", "carrito": carrito_actual}), 400

        mensaje_sistema_res = None
        contexto_extra = ""
        msg_lower = mensaje_usuario.lower()

        # --- DETECCIÓN DE INTENCIÓN MANUAL (Igual para MODO DEMO y MODO IA) ---
        if any(kw in msg_lower for kw in ["pagar", "confirmar", "listo", "comprar"]):
            nombre_demo = None
            nombre_match = re.search(r'(?:soy|me llamo|mi nombre es)\s+([a-záéíóúñ]+)', msg_lower)
            if nombre_match:
                nombre_demo = nombre_match.group(1).capitalize()
            mensaje_sistema_res = confirmar_compra(nombre_cliente=nombre_demo)
            contexto_extra = f"{mensaje_sistema_res}"

        elif any(kw in msg_lower for kw in ["precio", "cuesta", "vale", "cuánto", "cuanto"]):
            busqueda = msg_lower
            for pc in ["precio", "cuesta", "vale", "cuánto", "cuanto", "del", "de", "la", "el", "un", "una", "?", "¿"]:
                busqueda = busqueda.replace(pc, "")
            busqueda = busqueda.strip().strip("?¿")
            if busqueda:
                resultado = consultar_inventario(busqueda)
                datos = json.loads(resultado)
                if datos.get("encontrado"):
                    prods = datos["productos"]
                    info = [f"{p['nombre']}: ${p['precio']:,} ({p['stock']} uds)" for p in prods[:3]]
                    contexto_extra = " | ".join(info)
                else:
                    contexto_extra = f"No encontré '{busqueda}' en el catálogo."
            else:
                contexto_extra = "Dime qué producto te interesa y te doy el precio."

        elif any(kw in msg_lower for kw in ["total", "boleta", "carrito"]):
            mensaje_sistema_res = calcular_total()
            contexto_extra = f"{mensaje_sistema_res}"

        elif any(kw in msg_lower for kw in ["qué tienen", "que tienen", "catálogo", "catalogo", "productos", "disponible"]):
            resultado = consultar_inventario()
            datos = json.loads(resultado)
            cats = datos.get("categorias", {})
            resumen = []
            for cat, prods in cats.items():
                nombres_p = [f"{p['nombre']} (${p['precio']:,})" for p in prods[:3]]
                resumen.append(f"{cat}: {', '.join(nombres_p)}{'...' if len(prods) > 3 else ''}")
            contexto_extra = f"Tenemos {datos.get('total_productos', 0)} productos. " + " | ".join(resumen[:3])

        elif any(kw in msg_lower for kw in ["agrega", "quiero", "llevar", "dame", "añade", "ponme"]):
            num_match = re.search(r'\b(\d+)\b', msg_lower)
            cantidad = int(num_match.group(1)) if num_match else 1
            conn = conectar_db()
            cursor = conn.cursor()
            cursor.execute("SELECT nombre FROM productos ORDER BY LENGTH(nombre) DESC")
            all_prods = [dict(r) for r in cursor.fetchall()]
            conn.close()
            msg_norm = msg_lower.replace("-", " ")
            producto_detectado = None
            for prod in all_prods:
                nombre_norm = prod["nombre"].lower().replace("-", " ")
                keywords = [w for w in re.split(r'[\s\-/()]+', nombre_norm) if len(w) > 3]
                if any(kw in msg_norm for kw in keywords):
                    producto_detectado = prod["nombre"]
                    break
            if producto_detectado:
                mensaje_sistema_res = agregar_producto(producto_detectado, cantidad)
                contexto_extra = f"{mensaje_sistema_res}"
            else:
                contexto_extra = "No encontré ese producto en el catálogo. Intenta con un nombre más específico."

        # --- RESPUESTA FINAL SEGÚN MODO ---
        if modo_ia_real:
            # --- MODO IA (con SDK moderno google-genai) ---
            historial = "No hay pedidos anteriores."
            if os.path.exists(PEDIDO_FILE):
                try:
                    with open(PEDIDO_FILE, "r", encoding="utf-8") as f:
                        pedido_data = json.load(f)
                        prods = [p["nombre"] for p in pedido_data.get("productos", [])]
                        if prods:
                            historial = f"Último pedido: {', '.join(prods)}."
                except Exception:
                    historial = "No se pudo leer el historial de pedidos."

            sys_instruction = (
                "Actúa como Robot.ia, el asistente virtual experto de 'Sabores del Sur'. "
                "Tu objetivo es gestionar ventas y consultas de inventario con máxima eficiencia y cordialidad chilena.\n\n"
                "Directrices: Solo saluda al inicio. Recuerda el nombre del cliente. Mantén hilo lógico. "
                "Prioridad: cerrar la venta. Tono profesional pero cercano, modismos chilenos sutiles.\n\n"
                "Si un producto no tiene stock, ofrece alternativas similares disponibles.\n\n"
                f"Contexto: {historial}\n\n"
                "Promos (Sugerir el 3ro si tienen 2):\n"
                "- Parrillero: Carbón + Sal + alguna carne.\n"
                "- Desayuno Sureño: Pan + Café/Té + Mantequilla/Margarina.\n"
                "- Ensalada Fresca: Tomate + Lechuga + Cebolla.\n\n"
                "Reglas de formato:\n"
                "1. Responde conciso (máximo 2-3 frases), texto plano (sin asteriscos ni markdown).\n"
                "2. Formatea precios como $X.XXX (ej: $1.500).\n"
                "3. Sé amigable y natural, como un vecino del barrio."
            )

            prompt = f"{sys_instruction}\n\nMensaje del usuario: {mensaje_usuario}"
            if contexto_extra:
                prompt += f"\n\nContexto adicional del sistema (usa esta información para responder con precisión): {contexto_extra}"

            try:
                from google import genai
                
                GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
                if not GOOGLE_API_KEY:
                    return jsonify({
                        "respuesta": "El servicio de IA no está disponible. Configura GOOGLE_API_KEY en el servidor.",
                        "carrito": carrito_actual
                    }), 500

                gemini_client = genai.Client(
                    api_key=GOOGLE_API_KEY
                )

                response = gemini_client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )

                texto = getattr(response, "text", "")

                if not texto:
                    texto = "No pude generar una respuesta ahora mismo."

                mensaje_respuesta = texto.strip()

            except Exception as e:
                mensaje_respuesta = f"Error en la IA: {str(e)}"

        else:
            # --- MODO DEMO (Texto crudo) ---
            if contexto_extra:
                mensaje_respuesta = contexto_extra
            else:
                mensaje_respuesta = (
                    "¡Hola! Soy Robot.ia. Puedo mostrarte el catálogo, decirte precios, "
                    "agregar al carrito o confirmar tu compra. ¿En qué te ayudo?"
                )

        return jsonify({
            "respuesta": mensaje_respuesta,
            "sistema": mensaje_sistema_res,
            "carrito": carrito_actual
        })

    except Exception as e:
        print(f"❌ Error en /chat: {e}")
        return jsonify({
            "respuesta": f"Error en el servidor: {str(e)}",
            "carrito": carrito_actual
        }), 500


# ==========================================
# 🚀 ARRANQUE DEL SERVIDOR
# ==========================================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)