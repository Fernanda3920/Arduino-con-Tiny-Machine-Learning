"""
Convierte datos CSV de Arduino a imágenes PNG
Versión simplificada - Solo conversión de archivos CSV
"""

import numpy as np
from PIL import Image
import csv
import os
from datetime import datetime

class CSVtoImageConverter:
    def __init__(self, ancho=22, alto=18):
        """
        Inicializa el convertidor
        
        Args:
            ancho: Ancho de la imagen (22 píxeles por default del Arduino)
            alto: Alto de la imagen (18 píxeles por default del Arduino)
        """
        self.ancho = ancho
        self.alto = alto
        self.carpeta_salida = "imagenes_arduino"
        
        # Crear carpeta si no existe
        if not os.path.exists(self.carpeta_salida):
            os.makedirs(self.carpeta_salida)
            print(f"📁 Carpeta creada: {self.carpeta_salida}")
    
    def csv_a_array(self, archivo_csv):
        """
        Lee un archivo CSV y lo convierte en array numpy
        
        Args:
            archivo_csv: Ruta al archivo CSV
            
        Returns:
            Array numpy con los valores de píxeles
        """
        datos = []
        
        try:
            with open(archivo_csv, 'r') as f:
                reader = csv.reader(f)
                for linea in reader:
                    # Saltar líneas vacías o comentarios
                    if not linea or (linea[0].startswith('#')):
                        continue
                    
                    # Convertir a enteros
                    fila = [int(val) for val in linea if val.strip()]
                    datos.extend(fila)
            
            return np.array(datos, dtype=np.uint8)
        
        except Exception as e:
            print(f"❌ Error leyendo CSV: {e}")
            return None
    
    def array_a_imagen(self, datos, escalar=10):
        """
        Convierte array de datos en imagen PIL
        
        Args:
            datos: Array numpy con valores de píxeles
            escalar: Factor de escalado (default 10x para mejor visualización)
            
        Returns:
            Objeto PIL.Image
        """
        try:
            # Validar cantidad de datos
            total_esperado = self.ancho * self.alto
            
            if len(datos) != total_esperado:
                print(f"⚠️  Ajustando dimensiones: {len(datos)} píxeles")
                # Calcular nuevas dimensiones
                total_pixeles = len(datos)
                # Intentar encontrar dimensiones que funcionen
                for h in range(10, 50):
                    if total_pixeles % h == 0:
                        w = total_pixeles // h
                        self.ancho = w
                        self.alto = h
                        print(f"   Nuevo tamaño: {w}x{h}")
                        break
            
            # Reshape a matriz 2D
            imagen_array = datos.reshape((self.alto, self.ancho))
            
            # Crear imagen en escala de grises
            imagen = Image.fromarray(imagen_array, mode='L')
            
            # Escalar para mejor visualización
            if escalar > 1:
                nuevo_ancho = self.ancho * escalar
                nuevo_alto = self.alto * escalar
                imagen = imagen.resize((nuevo_ancho, nuevo_alto), Image.NEAREST)
            
            return imagen
        
        except Exception as e:
            print(f"❌ Error creando imagen: {e}")
            return None
    
    def guardar_imagen(self, imagen, nombre_base, formato='PNG'):
        """
        Guarda la imagen en disco
        
        Args:
            imagen: Objeto PIL.Image
            nombre_base: Nombre base del archivo
            formato: 'PNG' o 'JPEG'
            
        Returns:
            Ruta del archivo guardado
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        extension = 'png' if formato == 'PNG' else 'jpg'
        nombre_archivo = f"{self.carpeta_salida}/{nombre_base}_{timestamp}.{extension}"
        
        try:
            if formato == 'JPEG':
                # Convertir a RGB para JPEG
                imagen = imagen.convert('RGB')
            
            imagen.save(nombre_archivo, formato)
            print(f"✅ Imagen guardada: {nombre_archivo}")
            return nombre_archivo
        
        except Exception as e:
            print(f"❌ Error guardando imagen: {e}")
            return None
    
    def convertir_csv_a_imagen(self, archivo_csv, escalar=10, formato='PNG'):
        """
        Pipeline completo: CSV → Array → Imagen → Guardar
        
        Args:
            archivo_csv: Ruta al archivo CSV
            escalar: Factor de escalado
            formato: 'PNG' o 'JPEG'
        """
        print(f"\n{'='*60}")
        print(f"CONVIRTIENDO: {archivo_csv}")
        print(f"{'='*60}")
        
        # Leer CSV
        datos = self.csv_a_array(archivo_csv)
        if datos is None:
            return None
        
        print(f"📊 Total píxeles: {len(datos)}")
        print(f"📐 Dimensiones: {self.ancho}x{self.alto}")
        
        # Crear imagen
        imagen = self.array_a_imagen(datos, escalar)
        if imagen is None:
            return None
        
        print(f"🖼️  Imagen escalada: {imagen.width}x{imagen.height}")
        
        # Guardar
        nombre_base = os.path.splitext(os.path.basename(archivo_csv))[0]
        archivo_salida = self.guardar_imagen(imagen, nombre_base, formato)
        
        return archivo_salida


def main():
    print("╔════════════════════════════════════════════════════════╗")
    print("║   CONVERTIDOR CSV → IMAGEN (Arduino)                  ║")
    print("╚════════════════════════════════════════════════════════╝")
    
    converter = CSVtoImageConverter()
    
    # Solicitar datos al usuario
    print("\n")
    archivo = input("Ruta del archivo CSV: ").strip()
    
    if not archivo:
        print("❌ Debes proporcionar una ruta al archivo")
        return
    
    if not os.path.exists(archivo):
        print(f"❌ El archivo no existe: {archivo}")
        return
    
    escalar = input("\nFactor de escalado (default 10): ").strip()
    escalar = int(escalar) if escalar else 10
    
    formato = input("Formato de salida (PNG/JPEG, default PNG): ").strip().upper()
    formato = formato if formato in ['PNG', 'JPEG'] else 'PNG'
    
    # Convertir
    resultado = converter.convertir_csv_a_imagen(archivo, escalar, formato)
    
    if resultado:
        print(f"\n{'='*60}")
        print("✅ CONVERSIÓN COMPLETADA")
        print(f"{'='*60}")
        print(f"📂 Carpeta de salida: {converter.carpeta_salida}/")
        print(f"🖼️  Archivo: {os.path.basename(resultado)}")
    else:
        print("\n❌ La conversión falló")


if __name__ == "__main__":
    main()