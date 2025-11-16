import paho.mqtt.client as mqtt
import json
import time
import random
import math
from datetime import datetime

# --- CONFIGURACIÓN FLESPI MQTT ---
MQTT_SERVER = "mqtt.flespi.io"
MQTT_PORT = 1883
MQTT_USERNAME = "FlespiToken dKRZlZsrolEy8ddgG9JD9WY0TgTCpAtrUZReOBwWYuvfuVfrDIM4M7nf4GQEIWcV"
MQTT_TOPIC = "satnet/agrodrone/telemetry"

# --- Configuración del Dron ---
CLIENT_ID = "AgroDrone_01"

# Parámetros de simulación GPS
base_lat = -34.6123
base_lon = -58.3772
base_alt = 234.2

# Variables de estado
current_lat = base_lat
current_lon = base_lon
current_alt = base_alt
battery_level = 100.0

# Contador para anomalías
reading_count = 0

# Variables para nuevas funciones
flight_time = 0.0
gps_loss_count = 0

# Variables para cálculo de velocidad
prev_lat = base_lat
prev_lon = base_lon

# Cliente MQTT
mqtt_client = None
connected = False

def on_connect(client, userdata, flags, rc):
    """Callback cuando se conecta al broker MQTT"""
    global connected
    if rc == 0:
        print("✓ CONECTADO a MQTT")
        print(f"Cliente: {CLIENT_ID}")
        print(f"Tópico: {MQTT_TOPIC}\n")
        connected = True
    else:
        print(f"✗ Error de conexión. Código: {rc}")
        connected = False

def on_disconnect(client, userdata, rc):
    """Callback cuando se desconecta del broker"""
    global connected
    connected = False
    if rc != 0:
        print(f"⚠ Desconexión inesperada. Código: {rc}")

def on_publish(client, userdata, mid):
    """Callback cuando se publica un mensaje"""
    pass

# ===== FUNCIONES DEL PROYECTO =====

def calculate_remaining_autonomy():
    """Función 1: Calcular autonomía restante del dron (minutos)"""
    return battery_level

def calculate_covered_area():
    """Función 2: Calcular área cubierta por el dron (m²)"""
    distance_km = (flight_time * 0.5) / 60.0
    area_m2 = distance_km * 1000.0 * 10.0
    return area_m2

def evaluate_spray_conditions(temp, humidity):
    """Función 3: Evaluar condiciones ambientales para fumigación"""
    if temp < 10 or temp > 35:
        return "NO_APTO_TEMP"
    if humidity < 30 or humidity > 90:
        return "NO_APTO_HUMEDAD"
    return "APTO"

def calculate_drone_speed():
    """Función 4: Calcular velocidad del dron (m/s)"""
    global prev_lat, prev_lon
    
    lat_diff = (current_lat - prev_lat) * 111139.0
    lon_diff = (current_lon - prev_lon) * 111139.0
    distance = math.sqrt(lat_diff * lat_diff + lon_diff * lon_diff)
    
    prev_lat = current_lat
    prev_lon = current_lon
    
    return distance

def get_solar_intensity():
    """Función 5: Simular intensidad de luz solar según hora del día (lux)"""
    hours = datetime.now().hour
    
    if 6 <= hours <= 18:
        # Día: 6 AM a 6 PM
        hour_factor = math.sin((hours - 6) * 3.14159 / 12.0)
        return 50000.0 * hour_factor + random.randint(-5000, 5000)
    else:
        # Noche
        return random.randint(0, 100)

def detect_rain_condition(humidity):
    """Función 6: Detectar probabilidad de lluvia y retornar estado"""
    rain_prob = random.randint(0, 100)
    
    if humidity > 80 and rain_prob > 70:
        return "LLUVIA_DETECTADA"
    elif humidity > 70 and rain_prob > 50:
        return "RIESGO_LLUVIA"
    else:
        return "SIN_LLUVIA"

def simulate_drone_movement():
    """Simular movimiento del dron"""
    global current_lat, current_lon, current_alt
    
    current_lat += random.randint(-100, 100) / 1000000.0
    current_lon += random.randint(-100, 100) / 1000000.0
    current_alt = base_alt + random.randint(-50, 50) / 10.0
    
    # Mantener dentro de límites
    if abs(current_lat - base_lat) > 0.005:
        current_lat = base_lat + random.randint(-50, 50) / 10000.0
    if abs(current_lon - base_lon) > 0.005:
        current_lon = base_lon + random.randint(-50, 50) / 10000.0

def publish_telemetry():
    """Publicar telemetría al servidor MQTT"""
    global reading_count, battery_level, flight_time, gps_loss_count
    
    if not connected:
        print("⚠ No conectado a MQTT")
        return
    
    reading_count += 1
    has_anomaly = (reading_count % 5 == 0)
    anomaly_type = 0
    
    if has_anomaly:
        anomaly_type = random.randint(1, 3)
    
    # Simular movimiento o pérdida GPS
    if anomaly_type != 2:
        simulate_drone_movement()
    else:
        gps_loss_count += 1
    
    # Decrementar batería
    battery_level -= 0.1
    if battery_level < 0:
        battery_level = 100.0
    
    # Crear timestamp
    timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Temperatura con posible anomalía
    if anomaly_type == 1:
        temperature = 45.0 + random.randint(50, 200) / 10.0
        print("🔥 ANOMALÍA: Temperatura crítica!")
    else:
        temperature = 25.0 + random.randint(0, 150) / 10.0
    
    humidity = 40.0 + random.randint(0, 400) / 10.0
    
    # Altitud con posible anomalía
    if anomaly_type == 3:
        altitude = random.randint(-500, -100) / 10.0
        print("⬇  ANOMALÍA: Altitud negativa - CAÍDA!")
    else:
        altitude = current_alt
    
    # Crear payload JSON
    data = {
        "timestamp": timestamp,
        "temperature": round(temperature, 1),
        "humidity": round(humidity, 1),
        "altitude": round(altitude, 1),
        "battery": int(battery_level)
    }
    
    # GPS con posible anomalía
    if anomaly_type == 2:
        data["gps"] = {"lat": None, "lon": None}
        print("📡 ANOMALÍA: Pérdida de señal GPS!")
    else:
        data["gps"] = {"lat": current_lat, "lon": current_lon}
    
    # Publicar a MQTT
    try:
        json_str = json.dumps(data)
        result = mqtt_client.publish(MQTT_TOPIC, json_str, qos=0)
        
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            # Mostrar información
            if has_anomaly:
                print(f"⚠  LECTURA #{reading_count} - CON ANOMALÍA")
            else:
                print(f"✓ Lectura #{reading_count} - Normal")
            
            print(f"  📍 GPS: ", end="")
            if anomaly_type == 2:
                print("NULL (sin señal)")
            else:
                print(f"{current_lat:.6f}, {current_lon:.6f}")
            
            print(f"  🌡  Temp: {temperature:.1f}°C")
            print(f"  📏 Alt: {altitude:.1f}m")
            print(f"  🔋 Batería: {int(battery_level)}% (Autonomía: {calculate_remaining_autonomy():.0f} min)")
            
            # Mostrar datos de luz solar y lluvia
            solar = get_solar_intensity()
            rain = detect_rain_condition(humidity)
            
            print(f"  ☀  Luz solar: {solar:.0f} lux")
            print(f"  🌧  Estado lluvia: {rain}")
            print(f"  📊 JSON: {json_str}")
            
            # Estadísticas cada 5 lecturas
            if reading_count % 5 == 0:
                print("\n--- ESTADÍSTICAS DE VUELO ---")
                print(f"⏱  Tiempo de vuelo: {flight_time/60.0:.1f} min")
                print(f"📐 Área cubierta: {calculate_covered_area():.0f} m²")
                print(f"💨 Velocidad: {calculate_drone_speed():.2f} m/s")
                print(f"🌿 Condiciones fumigación: {evaluate_spray_conditions(temperature, humidity)}")
                print(f"📡 Pérdidas GPS totales: {gps_loss_count}")
                print(f"☀  Intensidad solar: {solar:.0f} lux")
                print(f"🌧  Condición climática: {rain}")
                print("-----------------------------\n")
            
            print()
        else:
            print(f"✗ Error al publicar. Código: {result.rc}")
            
    except Exception as e:
        print(f"✗ Error al publicar: {e}")

def main():
    """Función principal"""
    global mqtt_client, flight_time
    
    print("\n" + "="*40)
    print("🚁 AgroDrone Telemetry Simulator")
    print("⚠  Con anomalías cada 5 lecturas")
    print("="*40)
    print("\nConectando a MQTT Flespi...\n")
    
    # Configurar cliente MQTT
    mqtt_client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    mqtt_client.username_pw_set(MQTT_USERNAME, "")
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_publish = on_publish
    
    # Conectar al broker
    try:
        mqtt_client.connect(MQTT_SERVER, MQTT_PORT, keepalive=60)
        mqtt_client.loop_start()
        
        # Esperar conexión
        timeout = 10
        while not connected and timeout > 0:
            time.sleep(0.5)
            timeout -= 0.5
        
        if not connected:
            print("⚠ No se pudo conectar a MQTT")
            return
        
        print("="*40)
        print("\nIniciando publicación de telemetría...\n")
        
        # Loop principal
        while True:
            try:
                publish_telemetry()
                flight_time += 1.0
                time.sleep(1)  # Publicar cada 1 segundo
                
            except KeyboardInterrupt:
                print("\n\n⚠ Deteniendo AgroDrone...")
                mqtt_client.loop_stop()
                mqtt_client.disconnect()
                print("✓ Desconectado correctamente")
                break
            except Exception as e:
                print(f"Error inesperado: {e}")
                time.sleep(1)
                
    except Exception as e:
        print(f"Error de conexión MQTT: {e}")

# Iniciar el programa
if __name__ == "__main__":
    main()