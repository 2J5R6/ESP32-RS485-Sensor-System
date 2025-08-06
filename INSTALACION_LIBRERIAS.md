# Librerías Necesarias para ESP32 S3

## Instalación en Arduino IDE

### 1. ESP32 Board Package
- En Arduino IDE: Archivo → Preferencias
- Agregar URL: `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json`
- Herramientas → Placa → Gestor de Tarjetas
- Buscar "ESP32" por Espressif Systems
- Instalar versión más reciente

### 2. Librerías Requeridas
Ir a Herramientas → Administrar Bibliotecas y buscar:

#### ArduinoJson (v6.x)
- Autor: Benoît Blanchon
- Descripción: Para manejo de JSON en comunicaciones
- Comando: `ArduinoJson by Benoit Blanchon`

#### MPU6050 Library
- Autor: Electronic Cats
- Descripción: Control del sensor MPU6050
- Comando: `MPU6050 by Electronic Cats`

#### Adafruit MPU6050 (Alternativa)
- Autor: Adafruit
- Descripción: Librería más completa para MPU6050
- Comando: `Adafruit MPU6050`

#### Adafruit Sensor (Dependencia)
- Autor: Adafruit
- Descripción: Librería base para sensores Adafruit
- Comando: `Adafruit Unified Sensor`

### 3. Configuración de Board ESP32-S3
- Herramientas → Placa → ESP32 Arduino → ESP32S3 Dev Module
- Configuraciones recomendadas:
  - USB CDC On Boot: "Enabled"
  - CPU Frequency: "240MHz (WiFi/BT)"
  - Flash Mode: "QIO"
  - Flash Size: "4MB (32Mb)"
  - Partition Scheme: "Default 4MB with spiffs"
  - PSRAM: "OPI PSRAM"

### 4. Configuración de Puertos
- Herramientas → Puerto → Seleccionar puerto COM correspondiente
- Velocidad de subida: 921600

## Conexiones Físicas Recomendadas

### ESP1 (Principal)
```
Sensores Analógicos:
- Potenciómetro: pin 8 → VCC 3.3V, GND, salida al pin 8
- LDR: pin 18 → VCC 3.3V mediante resistor 10kΩ, GND directo, salida al pin 18
- Encoder: pin 17 → según especificaciones del encoder

MPU6050:
- VCC → 3.3V
- GND → GND
- SDA → pin 43 (I2C Data)
- SCL → pin 44 (I2C Clock)

RS485:
- RO → pin 7
- RE → pin 6
- DE → pin 5
- DI → pin 4
- VCC → 5V
- GND → GND

LEDs:
- LED Verde → pin 12 + resistor 220Ω → GND
- LED Rojo → pin 11 + resistor 220Ω → GND
- LED Amarillo → pin 10 + resistor 220Ω → GND
```

### ESP2 (Secundario)
```
Sensores Analógicos:
- Potenciómetro: pin 6 → VCC 3.3V, GND, salida al pin 6
- LDR: pin 7 → VCC 3.3V mediante resistor 10kΩ, GND directo, salida al pin 7
- Encoder: pin 15 → según especificaciones del encoder

MPU6050:
- VCC → 3.3V
- GND → GND
- SDA → pin 43 (I2C Data)
- SCL → pin 44 (I2C Clock)

RS485:
- RO → pin 39
- RE → pin 38
- DE → pin 37
- DI → pin 36
- VCC → 5V
- GND → GND

LEDs:
- LED Verde → pin 21 + resistor 220Ω → GND
- LED Rojo → pin 20 + resistor 220Ω → GND
- LED Amarillo → pin 19 + resistor 220Ω → GND
```

### Conexión RS485 entre ESP1 y ESP2
```
ESP1         ESP2
DI (4)   →   A
RO (7)   ←   B
DE (5)       
RE (6)       

ESP2
DI (36)  →   A
RO (39)  ←   B
DE (37)      
RE (38)      

Usar módulo RS485 como MAX485 o similar
Conectar A y B entre ambos módulos
```

## Troubleshooting

### Error de compilación:
1. Verificar que todas las librerías estén instaladas
2. Seleccionar board ESP32-S3 correcto
3. Verificar que el cable USB soporte datos (no solo carga)

### Error de subida:
1. Presionar BOOT button en ESP32 antes de subir código
2. Verificar puerto COM correcto
3. Cerrar monitor serial antes de subir

### Error de comunicación RS485:
1. Verificar conexiones A y B
2. Asegurar que ambos ESP usen la misma velocidad (9600)
3. Verificar que pines RE/DE funcionen correctamente

### Error I2C MPU6050:
1. Verificar conexiones SDA/SCL
2. Verificar alimentación 3.3V al MPU6050
3. Usar scanner I2C para detectar dirección (0x68 por defecto)
