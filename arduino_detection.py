"""
Script para enviar datos del Arduino a Flespi vía MQTT
Captura imágenes cada 15 segundos y detecta anomalías (humo)
"""

import serial
import serial.tools.list_ports
import time
import json
import random
from datetime import datetime
import paho.mqtt.client as mqtt

class ArduinoFlespiMQTT:
    def __init__(self, flespi_token, baudrate=115200):
        """
        Inicializa el enviador de datos a Flespi vía MQTT
        
        Args:
            flespi_token: Tu token de Flespi
            baudrate: Velocidad del serial (default 115200)
        """
        self.baudrate = baudrate
        self.serial_port = None
        self.is_connected_arduino = False
        self.is_connected_mqtt = False
        
        # Configuración MQTT Flespi
        self.flespi_token = flespi_token
        self.mqtt_host = "mqtt.flespi.io"
        self.mqtt_port = 1883  # Puerto sin SSL, usar 8883 para SSL
        self.mqtt_topic = "arduino/anomalias"  # Puedes cambiarlo
        
        # Cliente MQTT
        self.mqtt_client = mqtt.Client(
            client_id=f"arduino-detector-{int(time.time())}",
            protocol=mqtt.MQTTv5
        )
        self.mqtt_client.username_pw_set(f"FlespiToken {flespi_token}", "")
        
        # Callbacks MQTT
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        self.mqtt_client.on_publish = self.on_mqtt_publish
        
        # Estadísticas
        self.total_envios = 0
        self.envios_humo = 0
        self.envios_normal = 0
        self.errores = 0
    
    def on_mqtt_connect(self, client, userdata, flags, rc, properties=None):
        """Callback cuando se conecta a MQTT"""
        if rc == 0:
            print("✅ Conectado a Flespi MQTT!")
            self.is_connected_mqtt = True
        else:
            print(f"❌ Error de conexión MQTT. Código: {rc}")
            self.is_connected_mqtt = False
    
    def on_mqtt_disconnect(self, client, userdata, rc, properties=None):
        """Callback cuando se desconecta de MQTT"""
        print("⚠️  Desconectado de MQTT")
        self.is_connected_mqtt = False
    
    def on_mqtt_publish(self, client, userdata, mid):
        """Callback cuando se publica un mensaje"""
        pass  # Silencioso para no saturar la consola
    
    def conectar_mqtt(self):
        """Conecta al broker MQTT de Flespi"""
        print(f"\n🔌 Conectando a Flespi MQTT ({self.mqtt_host})...")
        
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, keepalive=60)
            self.mqtt_client.loop_start()
            
            # Esperar conexión
            timeout = time.time() + 5
            while not self.is_connected_mqtt and time.time() < timeout:
                time.sleep(0.1)
            
            if self.is_connected_mqtt:
                print(f"✅ MQTT conectado! Topic: {self.mqtt_topic}")
                return True
            else:
                print("❌ Timeout conectando a MQTT")
                return False
                
        except Exception as e:
            print(f"❌ Error conectando MQTT: {e}")
            return False
    
    def listar_puertos(self):
        """Lista todos los puertos seriales disponibles"""
        puertos = serial.tools.list_ports.comports()
        print("\n" + "="*60)
        print("PUERTOS SERIALES DISPONIBLES:")
        print("="*60)
        
        if not puertos:
            print("❌ No se encontraron puertos seriales")
            return []
        
        for i, puerto in enumerate(puertos, 1):
            print(f"{i}. {puerto.device} - {puerto.description}")
        
        return puertos
    
    def conectar_arduino(self, puerto=None):
        """Conecta al Arduino"""
        if puerto is None:
            puertos = self.listar_puertos()
            if not puertos:
                return False
            
            try:
                seleccion = int(input("\nSelecciona el número de puerto: ")) - 1
                puerto = puertos[seleccion].device
            except (ValueError, IndexError):
                print("❌ Selección inválida")
                return False
        
        try:
            print(f"\n🔌 Conectando a Arduino ({puerto})...")
            self.serial_port = serial.Serial(puerto, self.baudrate, timeout=1)
            time.sleep(2)
            self.is_connected_arduino = True
            print("✅ Arduino conectado!")
            return True
        except serial.SerialException as e:
            print(f"❌ Error al conectar: {e}")
            return False
    
    def leer_linea(self):
        """Lee una línea del serial"""
        if not self.is_connected_arduino:
            return None
        
        try:
            if self.serial_port.in_waiting > 0:
                linea = self.serial_port.readline().decode('utf-8', errors='ignore').strip()
                return linea
        except Exception as e:
            print(f"⚠️  Error al leer: {e}")
        
        return None
    
    def enviar_comando(self, comando):
        """Envía un comando al Arduino"""
        if not self.is_connected_arduino:
            return False
        
        try:
            self.serial_port.write(f"{comando}\n".encode())
            return True
        except Exception as e:
            print(f"❌ Error al enviar comando: {e}")
            return False
    
    def capturar_datos_csv(self):
        """Captura datos CSV de la imagen del Arduino"""
        print("\n📸 Capturando imagen del Arduino...")
        
        # Limpiar buffer serial
        while self.serial_port.in_waiting > 0:
            self.serial_port.read()
        
        # Enviar comando para captura ML
        if not self.enviar_comando('3'):
            return None
        
        time.sleep(0.5)
        
        datos_csv = []
        capturando = False
        timeout = time.time() + 10
        
        while time.time() < timeout:
            linea = self.leer_linea()
            
            if linea:
                # Detectar inicio de datos CSV
                if "INICIO DATOS CSV" in linea or "===" in linea:
                    capturando = True
                    continue
                
                # Detectar fin de datos CSV
                if "FIN DATOS CSV" in linea or "Copia estos datos" in linea:
                    break
                
                # Capturar líneas con datos
                if capturando and ',' in linea and not linea.startswith('#'):
                    datos_csv.append(linea)
            
            time.sleep(0.01)
        
        if datos_csv:
            print(f"✅ Captura completada: {len(datos_csv)} líneas")
            return datos_csv
        else:
            print("❌ No se capturaron datos")
            return None
    
    def convertir_csv_a_array(self, datos_csv):
        """Convierte las líneas CSV en un array de valores"""
        valores = []
        for linea in datos_csv:
            fila = [int(val.strip()) for val in linea.split(',') if val.strip()]
            valores.extend(fila)
        return valores
    
    def generar_anomalia(self, datos_imagen):
        """
        Determina si hay humo basándose en el análisis estadístico de la imagen.
        Evalúa brillo promedio y rango dinámico (contraste).
        """
        if not datos_imagen:
            return "normal"

        brillo_promedio = sum(datos_imagen) / len(datos_imagen)
        brillo_min = min(datos_imagen)
        brillo_max = max(datos_imagen)
        rango = brillo_max - brillo_min  
        if brillo_promedio < 60 and rango < 25:
            return "humo"
        elif brillo_promedio < 80 and rango < 20:
            return "humo"
        else:
            return "normal"

    def enviar_a_flespi(self, datos_imagen, anomalia):
        """Envía los datos a Flespi vía MQTT"""
        if not self.is_connected_mqtt:
            print("❌ No conectado a MQTT")
            self.errores += 1
            return False
        
        timestamp = int(time.time())
        
        # Crear payload JSON
        payload = {
            "ts": timestamp,
            "anomalia": anomalia,
            "imagen_datos": datos_imagen,
            "total_pixeles": len(datos_imagen),
            "timestamp_legible": datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Agregar estadísticas de la imagen
        if datos_imagen:
            payload["brillo_promedio"] = round(sum(datos_imagen) / len(datos_imagen), 2)
            payload["brillo_minimo"] = min(datos_imagen)
            payload["brillo_maximo"] = max(datos_imagen)
        
        print(f"\n📤 Enviando a Flespi MQTT...")
        print(f"   Topic: {self.mqtt_topic}")
        print(f"   Anomalía: {anomalia.upper()}")
        print(f"   Píxeles: {len(datos_imagen)}")
        print(f"   Timestamp: {payload['timestamp_legible']}")
        
        try:
            # Convertir a JSON
            mensaje_json = json.dumps(payload)
            
            # Publicar en MQTT
            result = self.mqtt_client.publish(
                self.mqtt_topic,
                mensaje_json,
                qos=1
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f"✅ Enviado exitosamente a Flespi MQTT!")
                self.total_envios += 1
                
                if anomalia == "humo":
                    self.envios_humo += 1
                    print("🔥 ALERTA: Anomalía detectada - HUMO")
                else:
                    self.envios_normal += 1
                
                return True
            else:
                print(f"❌ Error al publicar MQTT. Código: {result.rc}")
                self.errores += 1
                return False
                
        except Exception as e:
            print(f"❌ Error al enviar: {e}")
            self.errores += 1
            return False
    
    def mostrar_estadisticas(self):
        """Muestra estadísticas de envíos"""
        print("\n" + "="*60)
        print("📊 ESTADÍSTICAS")
        print("="*60)
        print(f"Total envíos: {self.total_envios}")
        if self.total_envios > 0:
            print(f"  ✅ Normal: {self.envios_normal} ({self.envios_normal/self.total_envios*100:.1f}%)")
            print(f"  🔥 Humo: {self.envios_humo} ({self.envios_humo/self.total_envios*100:.1f}%)")
        else:
            print(f"  ✅ Normal: 0")
            print(f"  🔥 Humo: 0")
        print(f"  ❌ Errores: {self.errores}")
        print("="*60)
    
    def iniciar_monitoreo(self, intervalo=15):
        """
        Inicia el monitoreo continuo
        
        Args:
            intervalo: Segundos entre capturas (default 15)
        """
        print("\n" + "="*60)
        print("🚀 INICIANDO MONITOREO CONTINUO")
        print("="*60)
        print(f"📷 Captura cada {intervalo} segundos")
        print(f"🔥 30% de probabilidad de detectar humo")
        print(f"📡 Publicando en topic: {self.mqtt_topic}")
        print("\nPresiona Ctrl+C para detener\n")
        print("="*60)
        
        try:
            contador = 0
            while True:
                inicio = time.time()
                contador += 1
                
                print(f"\n{'='*60}")
                print(f"CAPTURA #{contador}")
                print(f"{'='*60}")
                
                # Capturar datos del Arduino
                datos_csv = self.capturar_datos_csv()
                
                if datos_csv:
                    # Convertir a array
                    datos_imagen = self.convertir_csv_a_array(datos_csv)
                    
                    # Determinar anomalía
                    anomalia = self.generar_anomalia(datos_imagen)

                    
                    # Enviar a Flespi
                    self.enviar_a_flespi(datos_imagen, anomalia)
                    
                    # Mostrar estadísticas cada 5 envíos
                    if self.total_envios % 5 == 0 and self.total_envios > 0:
                        self.mostrar_estadisticas()
                else:
                    print("⚠️  No se pudieron capturar datos, reintentando...")
                    self.errores += 1
                
                # Esperar hasta completar el intervalo
                tiempo_transcurrido = time.time() - inicio
                tiempo_espera = max(0, intervalo - tiempo_transcurrido)
                
                if tiempo_espera > 0:
                    print(f"\n⏳ Esperando {tiempo_espera:.1f} segundos hasta próxima captura...")
                    time.sleep(tiempo_espera)
        
        except KeyboardInterrupt:
            print("\n\n✋ Monitoreo detenido por el usuario")
            self.mostrar_estadisticas()
    
    def cerrar(self):
        """Cierra las conexiones"""
        if self.mqtt_client:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
            print("🔌 Desconectado de MQTT")
        
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            print("🔌 Conexión con Arduino cerrada")


def main():
    print("╔════════════════════════════════════════════════════════╗")
    print("║   ARDUINO → FLESPI MQTT - DETECTOR DE ANOMALÍAS      ║")
    print("║   Monitoreo continuo con detección de humo            ║")
    print("╚════════════════════════════════════════════════════════╝")
    
    # Token de Flespi (el que proporcionaste)
    FLESPI_TOKEN = "64cOnWYf9Me5yFj6VWX1y0UZFqpdWv3yXmfHj4xGk82MsubrWCA6q4eM2qopRNeG"
    
    print(f"\n🔑 Usando token: {FLESPI_TOKEN[:20]}...")
    
    # Crear instancia
    sender = ArduinoFlespiMQTT(FLESPI_TOKEN)
    
    # Conectar a MQTT
    if not sender.conectar_mqtt():
        print("❌ No se pudo conectar a Flespi MQTT")
        return
    
    # Conectar Arduino
    if sender.conectar_arduino():
        try:
            # Preguntar intervalo
            intervalo_str = input("\n⏱️  Intervalo entre capturas en segundos (default 15): ").strip()
            intervalo = int(intervalo_str) if intervalo_str else 15
            
            # Preguntar topic personalizado
            topic_custom = input(f"📡 Topic MQTT (default: {sender.mqtt_topic}): ").strip()
            if topic_custom:
                sender.mqtt_topic = topic_custom
            
            # Iniciar monitoreo
            sender.iniciar_monitoreo(intervalo)
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Programa interrumpido")
        except Exception as e:
            print(f"\n❌ Error: {e}")
        finally:
            sender.cerrar()
    else:
        print("❌ No se pudo conectar al Arduino")
        sender.cerrar()


if __name__ == "__main__":
    main()