import sys
import os
import json
import re
import datetime as dt
from datetime import datetime
import sqlite3
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from functools import wraps
# Comentado para permitir que el servidor inicie sin google-generativeai
# from google import genai
# from google.genai import types
import requests
import urllib.parse

# ==========================================
# ⚙️ CONFIGURACIÓN INICIAL
# ==========================================
# Configuramos la app para usar la estructura estándar de Flask (/templates y /static)
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app, resources={r"/*": {"origins": "*"}})

# CONFIGURACIÓN DE SEGURIDAD
# En producción, usa variables de entorno para esto
API_TOKEN_ESPIRITU = "ESPIRITU_SUR_2026_SEGURIDAD_MAXIMA"

def proteger_con_token(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token_cliente = request.headers.get('x-api-token')
        if token_cliente != API_TOKEN_ESPIRITU:
            return jsonify({"error": "Acceso no autorizado. Token inválido o ausente."}), 403
        return f(*args, **kwargs)
    return decorated_function

# El cliente se inicializará perezosamente para evitar bloqueos en el arranque
client = None
def get_genai_client():
    global client
    if client is None:
        try:
            from google import genai
            api_key = os.environ.get("GOOGLE_API_KEY", "AIzaSyAkS1aND4le5-E8nHuvcPWkU_FXBkYQk10")
            client = genai.Client(api_key=api_key)
        except ImportError:
            print("Advertencia: google-generativeai no está instalado. Las funciones IA no estarán disponibles.")
            return None
    return client

# Helper para fechas
hoy = datetime.now()
def d_str(days=0):
    return (hoy + dt.timedelta(days=days)).strftime("%Y-%m-%d")

# Configuración de Rutas
# BASE_DIR será la carpeta donde se encuentre este archivo app.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Ruta relativa a la base de datos para funcionar en local y en Render
DB_FILE = os.path.join(BASE_DIR, "sabores_del_sur.db")
PEDIDO_FILE = os.path.join(BASE_DIR, "pedido.json")

# Helpers de base de datos
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
    campos = [col for col in ["id", "nombre", "precio", "stock", "categoria"] if col in columnas]
    if "imagen_url" in columnas:
        campos.append("imagen_url")
    else:
        campos.append("'' AS imagen_url")
    return ", ".join(campos)

def obtener_productos_db(limit=50):
    campos = construir_campos_producto()
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(f"SELECT {campos} FROM productos ORDER BY categoria ASC, id ASC LIMIT ?", (limit,))
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

def actualizar_stock_db(producto_id, cantidad):
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT stock FROM productos WHERE id = ?", (producto_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise ValueError(f"Producto con id {producto_id} no existe")
    stock_actual = row["stock"]
    if stock_actual < cantidad:
        conn.close()
        raise ValueError(f"Stock insuficiente para el producto id {producto_id}")
    nuevo_stock = stock_actual - cantidad
    cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (nuevo_stock, producto_id))
    conn.commit()
    conn.close()
    return nuevo_stock

# ==========================================
# 📦 INVENTARIO DINÁMICO (SQLite en tiempo real)
# ==========================================
carrito_actual = []

def consultar_inventario(producto: str = None):
    """Consulta el inventario real del minimarket en la base de datos.
    Si se proporciona un nombre de producto, busca ese producto específico.
    Si no se proporciona nombre, devuelve la lista completa por categorías."""
    conn = None
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        if producto and producto.strip():
            # Búsqueda por nombre parcial (case-insensitive)
            cursor.execute(
                "SELECT id, nombre, precio, stock, categoria FROM productos WHERE nombre LIKE ? ORDER BY nombre ASC",
                (f"%{producto.strip()}%",)
            )
            rows = [dict(r) for r in cursor.fetchall()]
            if not rows:
                return json.dumps({"encontrado": False, "mensaje": f"No se encontró '{producto}' en el inventario."}, ensure_ascii=False)
            resultados = [{"id": r["id"], "nombre": r["nombre"], "precio": r["precio"], "stock": r["stock"], "categoria": r["categoria"]} for r in rows]
            return json.dumps({"encontrado": True, "productos": resultados}, ensure_ascii=False)
        else:
            # Lista completa agrupada por categoría
            cursor.execute("SELECT id, nombre, precio, stock, categoria FROM productos ORDER BY categoria ASC, nombre ASC")
            rows = [dict(r) for r in cursor.fetchall()]
            categorias = {}
            for r in rows:
                cat = r.get("categoria") or "Otros"
                if cat not in categorias:
                    categorias[cat] = []
                categorias[cat].append({"id": r["id"], "nombre": r["nombre"], "precio": r["precio"], "stock": r["stock"]})
            return json.dumps({"total_productos": len(rows), "categorias": categorias}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"Error al consultar inventario: {str(e)}"}, ensure_ascii=False)
    finally:
        if conn:
            conn.close()

# ==========================================
# 📞 INTEGRACIONES (WhatsApp)
# ==========================================
def enviar_whatsapp_confirmacion(resumen_pedido):
    import requests
    import urllib.parse
    
    # Credenciales de CallMeBot (IMPORTANTE: La APIKey está vinculada al número)
    # Si cambias el número, debes solicitar una nueva APIKey a CallMeBot
    telefono = "56928117627"
    apikey = "4211824"
    
    # Construir el mensaje detallado
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
        # Usamos un timeout mayor para evitar cortes
        response = requests.get(url, timeout=15)
        if response.status_code == 200 and "Message queued" in response.text:
            print("¡WhatsApp (CallMeBot) enviado con éxito!")
            return True
        print(f"Error de CallMeBot API: {response.text}")
    except Exception as e:
        print(f"Error enviando WhatsApp via CallMeBot: {e}")
    return False

# ==========================================
# 🛠️ HERRAMIENTAS (TOOLS)
# ==========================================
def agregar_producto(producto: str, cantidad: int = 1):
    """Agrega una cantidad específica de un producto al carrito."""
    global carrito_actual
    conn = None
    try:
        conn = conectar_db()
        cursor = conn.cursor()
        # Búsqueda exacta primero, luego parcial
        cursor.execute("SELECT id, nombre, precio, stock FROM productos WHERE nombre LIKE ?", (f"%{producto}%",))
        rows = [dict(r) for r in cursor.fetchall()]
        if not rows:
            return f"Error: El producto '{producto}' no existe en el catálogo."
        # Elegir la coincidencia más corta (más específica)
        prod = min(rows, key=lambda r: len(r["nombre"]))
        if prod["stock"] < cantidad:
            return f"Error de Stock: Solo quedan {prod['stock']} unidades de {prod['nombre']}."
        # Descontar stock en DB
        cursor.execute("UPDATE productos SET stock = ? WHERE id = ?", (prod["stock"] - cantidad, prod["id"]))
        conn.commit()
        # Agregar o sumar en carrito local
        for item in carrito_actual:
            if item["id"] == prod["id"]:
                item["cantidad"] += cantidad
                item["subtotal"] = item["precio"] * item["cantidad"]
                return f"Éxito: Sumadas {cantidad} unidades de {prod['nombre']}. Total en carrito: {item['cantidad']}."
        carrito_actual.append({
            "id": prod["id"],
            "nombre": prod["nombre"],
            "precio": prod["precio"],
            "cantidad": cantidad,
            "subtotal": prod["precio"] * cantidad
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

    # Validaciones de Promos
    if any("carne" in n for n in nombres) and any("carbon" in n for n in nombres) and any("sal" in n for n in nombres):
        descuento += total_a_pagar * 0.15
        promos.append("Pack Parrillero (-15%)")
        
    if any("leche" in n for n in nombres) and any("pan" in n or "marraqueta" in n or "hallulla" in n for n in nombres) and any("mantequilla" in n for n in nombres):
        descuento += total_a_pagar * 0.10
        promos.append("Desayuno Sureño (-10%)")
        
    if any("tomate" in n for n in nombres) and any("lechuga" in n for n in nombres) and any("cebolla" in n for n in nombres):
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

def confirmar_compra(nombre_cliente: str = None):
    """Confirma el pedido actual, guarda el resumen y envía una notificación por WhatsApp.
    Si se proporciona el nombre del cliente, se incluye en la notificación."""
    global carrito_actual
    if not carrito_actual:
        return "Error: No puedo confirmar la compra porque el carrito está vacío."
    
    total, desc, promos = _calcular_totales()
    resumen_pedido = {
        "fecha_pedido": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "productos": carrito_actual,
        "total": total,
        "descuento": desc,
        "promos_aplicadas": promos,
        "estado": "Confirmado"
    }
    
    try:
        if not os.path.exists(BASE_DIR):
            os.makedirs(BASE_DIR, exist_ok=True)
        # El stock ya fue descontado en agregar_producto, solo guardamos el pedido
        with open(PEDIDO_FILE, "w", encoding="utf-8") as f:
            json.dump(resumen_pedido, f, indent=4, ensure_ascii=False)
            
        resumen_pedido["cliente"] = nombre_cliente or "Cliente Web"
        wsp_enviado = enviar_whatsapp_confirmacion(resumen_pedido)
        carrito_actual = []
        
        msg = f"¡Compra confirmada! Total a pagar: ${total:,.0f}."
        if nombre_cliente: msg = f"¡Excelente {nombre_cliente}! Compra confirmada por ${total:,.0f}."
        if promos: msg += f" Se aplicaron promos: {', '.join(promos)}."
        msg += " Te enviamos el detalle por WhatsApp." if wsp_enviado else " (Aviso: No se pudo enviar el WhatsApp)."
        return msg
    except PermissionError:
        return "Error: Problema con los permisos para guardar el pedido."
    except Exception as e:
        return f"Error crítico al guardar el pedido: {str(e)}"

tools_list = [consultar_inventario, agregar_producto, confirmar_compra, calcular_total]

# ==========================================
# 🌐 ENDPOINTS DE LA API
# ==========================================

@app.route('/')
def index():
    # Renderiza la plantilla principal para evitar el error 404/127
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
    productos = obtener_productos_db(limit=50)
    return jsonify(productos)

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
            "id": producto["id"],
            "nombre": producto["nombre"],
            "precio": producto["precio"],
            "cantidad": cantidad,
            "subtotal": producto["precio"] * cantidad
        })

    total, desc, promos = _calcular_totales()
    return jsonify({
        "productos": carrito_actual,
        "total": total,
        "descuento": desc,
        "promos_aplicadas": promos
    })

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
        else:
            return jsonify({"error": "No hay pedidos previos"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/test", methods=["GET"])
def test_server():
    return jsonify({"status": "ok", "message": "Servidor Flask activo y funcionando correctamente"})

@app.route("/carrito", methods=["GET"])
def obtener_carrito():
    total, desc, promos = _calcular_totales()
    return jsonify({
        "productos": carrito_actual,
        "total": total,
        "descuento": desc,
        "promos_aplicadas": promos
    })

@app.route("/chat", methods=["POST"])
def chat():
    global carrito_actual
    try:
        data = request.get_json()
        mensaje_usuario = data.get("mensaje", "").strip()
        modo_ia_real = data.get("modoIAReal", False)

        if not mensaje_usuario:
            return jsonify({"error": "Mensaje vacío"}), 400

        mensaje_sistema_res = None
        
        if modo_ia_real:
            # --- MODO IA (GEMINI con Tools en tiempo real) ---
            historial = "No hay pedidos anteriores."
            if os.path.exists(PEDIDO_FILE):
                try:
                    with open(PEDIDO_FILE, "r", encoding="utf-8") as f:
                        pedido_data = json.load(f)
                        prods = [p["nombre"] for p in pedido_data.get("productos", [])]
                        if prods: historial = f"Último pedido: {', '.join(prods)}."
                except Exception:
                    historial = "No se pudo leer el historial de pedidos."

            sys_instruction = f"""Actúa como Robot.ia, el asistente virtual experto de 'Sabores del Sur'. Tu objetivo es gestionar ventas y consultas de inventario con máxima eficiencia y cordialidad chilena.

Directrices Críticas de Comportamiento:

Gestión de Saludos (Antirrepetitivo): Solo saludarás al inicio de la conversación o si ha pasado un tiempo prolongado de inactividad. En el flujo continuo de mensajes, ve directo al grano. Está prohibido decir 'Hola', 'Buenos días' o '¿En qué puedo ayudarte?' en cada respuesta.

Memoria de Identidad: Debes recordar y utilizar el nombre del cliente una vez que te lo proporcione para generar cercanía, pero hazlo de forma natural (ej: 'Perfecto, Cristian, ya agregué el pan').

Manejo de Historial y Coherencia: Mantén un hilo lógico estricto. Si el usuario dice 'agrega dos más', debes saber perfectamente a qué producto se refiere basándote en los últimos 5 mensajes. No hagas preguntas de las que ya tienes la respuesta en el historial.

Marco de Servicio de Venta: Tu prioridad es cerrar la venta. Si el cliente se desvía del tema, redirige sutilmente la conversación hacia el catálogo o el proceso de pago.

Tono de Voz: Profesional, ejecutivo, pero cercano. Usa modismos chilenos sutiles y amigables propios de un minimarket de barrio moderno.

Cada vez que te pidan un producto que no hay en stock, respondele la verdad, pero ofrece alternativs similares que sí estén disponibles.


Configuración de Memoria Técnica:

Utiliza el historial de mensajes (chat_history) para contextualizar tus respuestas antes de generar una nueva.

Si el stock de un producto cambia durante la conversación (vía function calling), prioriza siempre el dato más reciente de la base de datos.

Contexto: {historial}

Promos (Sugerir el 3ro si tienen 2):
- Parrillero: Carbón + Sal + alguna carne.
- Desayuno Sureño: Pan + Café/Té + Mantequilla/Margarina.
- Ensalada Fresca: Tomate + Lechuga + Cebolla.

Reglas de formato:
1. Responde de forma concisa (máximo 2-3 frases), texto plano (sin asteriscos ni markdown).
2. Formatea precios como $X.XXX (ej: $1.500).
3. Sé amigable y natural, como un vecino del barrio."""

            c = get_genai_client()
            if c is None:
                return jsonify({
                    "error": "El servicio de IA no está disponible.",
                    "mensaje": "Por favor, instala google-generativeai con: pip install google-generativeai"
                }), 503
            
            from google.genai import types

            config = types.GenerateContentConfig(
                system_instruction=sys_instruction,
                tools=tools_list,
                temperature=0.3
            )

            # Primera llamada al modelo
            try:
                response = c.models.generate_content(
                    model='gemini-1.5-flash',
                    contents=mensaje_usuario,
                    config=config
                )
            except Exception as e:
                if "429" in str(e):
                    return jsonify({
                        "respuesta": "Lo siento, Robot.ia ha alcanzado su límite de consultas gratuitas en este modelo por hoy. Por favor, intenta de nuevo en unos minutos o cambia a Modo Demo.",
                        "carrito": carrito_actual
                    }), 429
                raise e

            # Mapa de funciones disponibles
            funciones_disponibles = {
                "consultar_inventario": consultar_inventario,
                "agregar_producto": agregar_producto,
                "calcular_total": calcular_total,
                "confirmar_compra": confirmar_compra,
            }

            # Bucle de function calling (máximo 5 turnos)
            mensaje_respuesta = ""
            current_history = [types.Content(role='user', parts=[types.Part.from_text(text=mensaje_usuario)])]
            
            for _turno in range(5):
                if not response.function_calls:
                    mensaje_respuesta = response.text or ""
                    break

                model_parts = []
                for fc in response.function_calls:
                    model_parts.append(types.Part.from_function_call(name=fc.name, args=fc.args))
                current_history.append(types.Content(role='model', parts=model_parts))

                response_parts = []
                for fc in response.function_calls:
                    fn = funciones_disponibles.get(fc.name)
                    try:
                        if fn:
                            resultado = fn(**fc.args) if fc.args else fn()
                            if fc.name != "consultar_inventario":
                                mensaje_sistema_res = resultado
                            response_parts.append(types.Part.from_function_response(
                                name=fc.name,
                                response={"result": resultado}
                            ))
                        else:
                            response_parts.append(types.Part.from_function_response(
                                name=fc.name,
                                response={"result": "Error: Función no encontrada"}
                            ))
                    except Exception as e:
                        response_parts.append(types.Part.from_function_response(
                            name=fc.name,
                            response={"result": f"Error: {str(e)}"}
                        ))

                current_history.append(types.Content(role='user', parts=response_parts))

                mensaje_respuesta = response.text or "Lo siento, la consulta tomó demasiados pasos."

        else:
            # --- MODO DEMO (con DB en tiempo real) ---
            msg_lower = mensaje_usuario.lower()
            
            if any(kw in msg_lower for kw in ["pagar", "confirmar", "listo", "comprar"]):
                # Intentar capturar nombre en modo demo
                nombre_demo = None
                nombre_match = re.search(r'(?:soy|me llamo|mi nombre es)\s+([a-záéíóúñ]+)', msg_lower)
                if nombre_match:
                    nombre_demo = nombre_match.group(1).capitalize()
                
                mensaje_sistema_res = confirmar_compra(nombre_cliente=nombre_demo)
                mensaje_respuesta = f"{mensaje_sistema_res}"
                
            elif any(kw in msg_lower for kw in ["precio", "cuesta", "vale", "cuánto", "cuanto"]):
                # Consulta de precio específico
                busqueda = msg_lower
                for palabra_clave in ["precio", "cuesta", "vale", "cuánto", "cuanto", "del", "de", "la", "el", "un", "una", "?", "¿"]:
                    busqueda = busqueda.replace(palabra_clave, "")
                busqueda = busqueda.strip().strip("?¿")
                if busqueda:
                    resultado = consultar_inventario(busqueda)
                    datos = json.loads(resultado)
                    if datos.get("encontrado"):
                        prods = datos["productos"]
                        info = [f"{p['nombre']}: ${p['precio']:,} ({p['stock']} unidades)" for p in prods[:3]]
                        mensaje_respuesta = " | ".join(info)
                    else:
                        mensaje_respuesta = f"No encontré '{busqueda}' en el catálogo. Pregúntame qué tenemos disponible."
                else:
                    mensaje_respuesta = "Dime qué producto te interesa y te doy el precio."
                
            elif any(kw in msg_lower for kw in ["total", "boleta", "carrito"]):
                mensaje_sistema_res = calcular_total()
                mensaje_respuesta = f"{mensaje_sistema_res}"
                
            elif any(kw in msg_lower for kw in ["qué tienen", "que tienen", "catálogo", "catalogo", "productos", "disponible"]):
                resultado = consultar_inventario()
                datos = json.loads(resultado)
                cats = datos.get("categorias", {})
                resumen = []
                for cat, prods in cats.items():
                    nombres = [f"{p['nombre']} (${p['precio']:,})" for p in prods[:3]]
                    resumen.append(f"{cat}: {', '.join(nombres)}{'...' if len(prods) > 3 else ''}")
                mensaje_respuesta = f"Tenemos {datos.get('total_productos', 0)} productos. " + " | ".join(resumen[:3])
                
            elif any(kw in msg_lower for kw in ["agrega", "quiero", "llevar", "dame", "añade", "ponme"]):
                num_match = re.search(r'\b(\d+)\b', msg_lower)
                cantidad = int(num_match.group(1)) if num_match else 1
                
                # Buscar producto en la DB con matching flexible
                conn = conectar_db()
                cursor = conn.cursor()
                cursor.execute("SELECT nombre FROM productos ORDER BY LENGTH(nombre) DESC")
                all_prods = [dict(r) for r in cursor.fetchall()]
                conn.close()
                
                msg_norm = msg_lower.replace("-", " ")
                producto_detectado = None
                for prod in all_prods:
                    nombre_norm = prod["nombre"].lower().replace("-", " ")
                    # Dividir en palabras clave (ignorando palabras cortas)
                    keywords = [w for w in re.split(r'[\s\-/()]+', nombre_norm) if len(w) > 3]
                    if any(kw in msg_norm for kw in keywords):
                        producto_detectado = prod["nombre"]
                        break
                
                if producto_detectado:
                    mensaje_sistema_res = agregar_producto(producto_detectado, cantidad)
                    mensaje_respuesta = f"{mensaje_sistema_res}"
                else:
                    mensaje_respuesta = "No encontré ese producto en el catálogo. Intenta con un nombre más específico."
            else:
                mensaje_respuesta = "¡Hola! Soy Robot.ia. Puedo mostrarte el catálogo, decirte precios, agregar al carrito o confirmar tu compra. ¿En qué te ayudo?"

        return jsonify({
            "respuesta": mensaje_respuesta.strip(),
            "sistema": mensaje_sistema_res,
            "carrito": carrito_actual
        })

    except Exception as e:
        return jsonify({"respuesta": f"Error en el servidor: {str(e)}", "carrito": carrito_actual}), 500

# ==========================================
# 🔐 RUTAS PROTEGIDAS CON TOKEN
# ==========================================
@app.route('/confirmar-pedido', methods=['POST'])
@proteger_con_token
def confirmar_pedido():
    datos = request.json
    # Aquí llamarías a la función procesar_compra_segura(...)
    return jsonify({"status": "recibido", "mensaje": "Token validado correctamente"})

if __name__ == "__main__":
    # Configuración de puerto dinámico requerida por Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)