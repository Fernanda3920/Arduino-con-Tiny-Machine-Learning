"""
Script de Python para capturar datos del Arduino Nano 33 BLE
Lee datos del Serial y los muestra en consola
"""

import serial
import serial.tools.list_ports
import time
import csv
from datetime import datetime

class ArduinoSerialReader:
    def __init__(self, baudrate=115200):
        self.baudrate = baudrate
        self.serial_port = None
        self.is_connected = False
        
    def listar_puertos(self):
        """Lista todos los puertos seriales disponibles"""
        puertos = serial.tools.list_ports.comports()
        print("\n" + "="*50)
        print("PUERTOS SERIALES DISPONIBLES:")
        print("="*50)
        
        if not puertos:
            print("❌ No se encontraron puertos seriales")
            return []
        
        for i, puerto in enumerate(puertos, 1):
            print(f"{i}. {puerto.device} - {puerto.description}")
        
        return puertos
    
    def conectar(self, puerto=None):
        """Conecta al puerto serial del Arduino"""
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
            print(f"\n🔌 Conectando a {puerto}...")
            self.serial_port = serial.Serial(puerto, self.baudrate, timeout=1)
            time.sleep(2)  # Esperar a que se establezca la conexión
            self.is_connected = True
            print("✅ Conectado exitosamente!")
            return True
        except serial.SerialException as e:
            print(f"❌ Error al conectar: {e}")
            return False
    
    def leer_linea(self):
        """Lee una línea del serial"""
        if not self.is_connected:
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
        if not self.is_connected:
            print("❌ No conectado al Arduino")
            return
        
        try:
            self.serial_port.write(f"{comando}\n".encode())
            print(f"📤 Comando enviado: {comando}")
        except Exception as e:
            print(f"❌ Error al enviar: {e}")
    
    def leer_continuo(self):
        """Lee datos continuamente y los muestra en consola"""
        print("\n" + "="*50)
        print("📡 LEYENDO DATOS DEL SERIAL")
        print("="*50)
        print("Presiona Ctrl+C para detener\n")
        
        try:
            while True:
                linea = self.leer_linea()
                if linea:
                    print(linea)
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\n\n✋ Lectura detenida por el usuario")
    
    def capturar_imagen_csv(self, nombre_archivo=None):
        """Captura datos CSV de una imagen del Arduino"""
        if nombre_archivo is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            nombre_archivo = f"captura_{timestamp}.csv"
        
        print(f"\n📸 Capturando imagen en formato CSV...")
        print(f"📁 Archivo: {nombre_archivo}")
        
        # Enviar comando para captura ML
        self.enviar_comando('3')
        time.sleep(0.5)
        
        datos_csv = []
        capturando = False
        
        print("\n⏳ Esperando datos...")
        
        try:
            while True:
                linea = self.leer_linea()
                
                if linea:
                    print(linea)  # Mostrar en consola
                    
                    # Detectar inicio de datos CSV
                    if "INICIO DATOS CSV" in linea or "===" in linea:
                        capturando = True
                        continue
                    
                    # Detectar fin de datos CSV
                    if "FIN DATOS CSV" in linea or "Copia estos datos" in linea:
                        break
                    
                    # Capturar líneas con datos (contienen comas)
                    if capturando and ',' in linea and not linea.startswith('#'):
                        datos_csv.append(linea)
                
                time.sleep(0.01)
        
        except KeyboardInterrupt:
            print("\n⚠️  Captura interrumpida")
        
        # Guardar a archivo
        if datos_csv:
            with open(nombre_archivo, 'w', newline='') as f:
                for linea in datos_csv:
                    f.write(linea + '\n')
            
            print(f"\n✅ Datos guardados en: {nombre_archivo}")
            print(f"📊 Total de líneas: {len(datos_csv)}")
            return nombre_archivo
        else:
            print("❌ No se capturaron datos")
            return None
    
    def menu_interactivo(self):
        """Menú interactivo para controlar el Arduino"""
        while True:
            print("\n" + "="*50)
            print("MENÚ DE CONTROL")
            print("="*50)
            print("1. Capturar imagen (comando 1)")
            print("2. Vista previa ASCII (comando 2)")
            print("3. Capturar para ML y guardar CSV (comando 3)")
            print("4. Secuencia de imágenes (comando 4)")
            print("5. Test de cámara (comando T)")
            print("6. Mostrar menú Arduino (comando M)")
            print("7. Leer datos en tiempo real")
            print("8. Enviar comando personalizado")
            print("0. Salir")
            print("="*50)
            
            opcion = input("\nSelecciona una opción: ").strip()
            
            if opcion == '1':
                self.enviar_comando('1')
                time.sleep(0.1)
                self.leer_respuesta()
            elif opcion == '2':
                self.enviar_comando('2')
                time.sleep(0.1)
                self.leer_respuesta()
            elif opcion == '3':
                self.capturar_imagen_csv()
            elif opcion == '4':
                self.enviar_comando('4')
                time.sleep(0.1)
                self.leer_respuesta()
            elif opcion == '5':
                self.enviar_comando('T')
                time.sleep(0.1)
                self.leer_respuesta()
            elif opcion == '6':
                self.enviar_comando('M')
                time.sleep(0.1)
                self.leer_respuesta()
            elif opcion == '7':
                self.leer_continuo()
            elif opcion == '8':
                cmd = input("Comando a enviar: ").strip()
                self.enviar_comando(cmd)
                time.sleep(0.1)
                self.leer_respuesta()
            elif opcion == '0':
                print("\n👋 Cerrando conexión...")
                break
            else:
                print("❌ Opción inválida")
    
    def leer_respuesta(self, timeout=3):
        """Lee la respuesta del Arduino por un tiempo determinado"""
        print("\n📨 Respuesta del Arduino:")
        print("-" * 50)
        
        inicio = time.time()
        while time.time() - inicio < timeout:
            linea = self.leer_linea()
            if linea:
                print(linea)
            time.sleep(0.01)
        
        print("-" * 50)
    
    def cerrar(self):
        """Cierra la conexión serial"""
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
            print("🔌 Conexión cerrada")


def main():
    print("╔════════════════════════════════════════════════╗")
    print("║   LECTOR SERIAL - ARDUINO NANO 33 BLE         ║")
    print("║   Captura de datos de cámara y sensores       ║")
    print("╚════════════════════════════════════════════════╝")
    
    reader = ArduinoSerialReader()
    
    if reader.conectar():
        try:
            reader.menu_interactivo()
        except KeyboardInterrupt:
            print("\n\n⚠️  Programa interrumpido")
        finally:
            reader.cerrar()
    else:
        print("❌ No se pudo conectar al Arduino")


if __name__ == "__main__":
    main()