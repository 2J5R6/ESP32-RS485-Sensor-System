# Sistema de Comunicación RS485/RS232 - ESP32 S3

Sistema completo de comunicación entre dos microcontroladores ESP32 S3 usando protocolo RS485 (half-dúplex) para intercambio de datos de sensores y RS232 (full-dúplex USB) para comunicación con PC.

## 🚀 Características del Sistema

### Hardware
- **2x ESP32 S3**: Microcontroladores principales
- **6x Sensores Analógicos**: 3 por ESP (potenciómetro, LDR, encoder)  
- **2x MPU6050**: Sensor MEMS digital I2C por ESP
- **6x LEDs**: 3 por ESP (verde, rojo, amarillo)
- **2x Módulos RS485**: Para comunicación entre ESPs

### Comunicación
- **RS485 Half-Dúplex**: 9600 bps entre ESP1 ↔ ESP2
- **RS232 Full-Dúplex**: 115200 bps ESP → PC (USB)
- **Frecuencia**: 20Hz (50ms) para todas las comunicaciones
- **Protocolo**: JSON compacto para eficiencia

### Software
- **Código Arduino**: 2 sketches optimizados (.ino)
- **Interfaz Python**: Monitor gráfico en tiempo real
- **Control Remoto**: LEDs controlables desde PC
- **Visualización**: Gráficas XY tiempo vs valor

## 📁 Estructura del Proyecto

```
Lab1RS485_RS232/
├── CodigoEsp_Sensores/
│   ├── ESP1_Principal.ino          # Código para ESP32 #1
│   ├── ESP2_Secundario.ino         # Código para ESP32 #2
│   └── CodigoEsp_Sensores.ino      # Archivo de referencia
├── Interfaz/
│   ├── esp32_monitor.py            # Nueva interfaz principal
│   ├── interface.py                # Interfaz original
│   ├── matrix_rain.py             # Efectos visuales
│   └── requirements.txt           # Dependencias Python
├── INSTALACION_LIBRERIAS.md       # Guía de instalación Arduino
└── README.md                      # Este archivo
```

## ⚙️ Configuración de Hardware

### ESP1 (Principal)
| Componente | Pin | Descripción |
|------------|-----|-------------|
| Potenciómetro | 8 | Sensor analógico 1 |
| LDR | 18 | Sensor de luz |
| Encoder | 17 | Sensor de velocidad |
| MPU6050 SDA | 43 | I2C Data |
| MPU6050 SCL | 44 | I2C Clock |
| RS485 RO | 7 | Receptor Output |
| RS485 RE | 6 | Receptor Enable |
| RS485 DE | 5 | Driver Enable |
| RS485 DI | 4 | Driver Input |
| LED Verde | 12 | Salida digital |
| LED Rojo | 11 | Salida digital |
| LED Amarillo | 10 | Salida digital |

### ESP2 (Secundario)
| Componente | Pin | Descripción |
|------------|-----|-------------|
| Potenciómetro | 6 | Sensor analógico 1 |
| LDR | 7 | Sensor de luz |
| Encoder | 15 | Sensor de velocidad |
| MPU6050 SDA | 43 | I2C Data |
| MPU6050 SCL | 44 | I2C Clock |
| RS485 RO | 39 | Receptor Output |
| RS485 RE | 38 | Receptor Enable |
| RS485 DE | 37 | Driver Enable |
| RS485 DI | 36 | Driver Input |
| LED Verde | 21 | Salida digital |
| LED Rojo | 20 | Salida digital |
| LED Amarillo | 19 | Salida digital |

## 🛠️ Instalación

### 1. Arduino IDE y Librerías
Seguir guía completa en [`INSTALACION_LIBRERIAS.md`](INSTALACION_LIBRERIAS.md)

**Librerías necesarias:**
- ESP32 Board Package (Espressif)
- ArduinoJson v6.x
- MPU6050 Library
- Adafruit MPU6050
- Adafruit Unified Sensor

### 2. Python y Dependencias
```bash
cd Interfaz
pip install -r requirements.txt
```

**Dependencias principales:**
- PyQt6 (interfaz gráfica)
- pyserial (comunicación serie)
- pyqtgraph (gráficas tiempo real)
- numpy (procesamiento datos)

## 🚀 Uso del Sistema

### 1. Cargar Código en ESP32s
1. Abrir Arduino IDE
2. Cargar `ESP1_Principal.ino` en primer ESP32 S3
3. Cargar `ESP2_Secundario.ino` en segundo ESP32 S3
4. Verificar conexiones serial en monitor (115200 bps)

### 2. Ejecutar Interfaz Python
```bash
cd Interfaz
python esp32_monitor.py
```

### 3. Conectar ESPs
1. En la interfaz, seleccionar puertos COM correspondientes
2. Hacer clic en "Conectar" para ESP1 y ESP2
3. Verificar status de conexión en panel izquierdo

### 4. Monitorear Sensores
- Seleccionar variable a visualizar (Potenciómetro, LDR, Encoder, Acelerómetro)
- Observar gráficas en tiempo real para ambos ESPs
- Ver valores numéricos actuales

### 5. Controlar LEDs
- Usar checkboxes en panel de control
- Controlar LEDs de cada ESP independientemente
- Observar confirmación de comandos

## 📊 Protocolo de Comunicación

### Datos de Sensores (ESP → PC)
```json
{
  "device": "ESP1",
  "timestamp": 12345678,
  "local": {
    "pot": 2.56,
    "ldr": 1.23,
    "enc": 3.21,
    "ax": -0.12,
    "ay": 0.98,
    "az": 9.81,
    "gx": 2.3,
    "gy": -1.1,
    "gz": 0.5
  },
  "remote": {
    "pot": 1.87,
    "ldr": 2.34,
    "enc": 0.98,
    "ax": 0.05
  },
  "leds": {
    "verde": true,
    "rojo": false,
    "amarillo": true
  }
}
```

### Comandos de Control (PC → ESP)
```json
{
  "target": "ESP1",
  "led_verde": true,
  "led_rojo": false,
  "led_amarillo": true
}
```

### Comunicación RS485 (ESP ↔ ESP)
```json
{
  "src": "ESP1",
  "ts": 12345678,
  "pot": 2.56,
  "ldr": 1.23,
  "enc": 3.21,
  "ax": -0.12
}
```

## 🔧 Características Técnicas

### Timing y Rendimiento
- **Frecuencia de muestreo**: 20Hz (50ms)
- **Resolución ADC**: 12 bits (0-4095)
- **Rango de voltaje**: 0-3.3V
- **Baud rate RS485**: 9600 bps
- **Baud rate RS232**: 115200 bps

### Algoritmos Implementados
- **Buffer circular**: Para datos RS485
- **Half-dúplex alternado**: Control automático RE/DE
- **Parsing JSON no bloqueante**: Procesamiento asincrónico
- **Filtrado temporal**: Ventana deslizante 30s
- **Interpolación de datos**: Para sincronización gráfica

### Características de Software
- **Thread-safe**: Comunicación en hilos separados
- **Real-time plotting**: Actualización 20Hz
- **Auto-detection**: Puertos COM automático
- **Error handling**: Recuperación ante fallos
- **Memory efficient**: Buffers limitados

## 🐛 Resolución de Problemas

### Problemas Comunes

**Error de conexión serial:**
- Verificar puerto COM correcto
- Asegurar que otro programa no use el puerto
- Comprobar cable USB (debe soportar datos)

**Sin datos de sensores:**
- Verificar conexiones de alimentación (3.3V)
- Comprobar resistencias pull-up en I2C
- Revisar continuidad en conexiones

**Comunicación RS485 fallida:**
- Verificar conexiones A y B entre módulos
- Confirmar pines RE/DE funcionando
- Usar osciloscopio para verificar señales

**Gráficas no se actualizan:**
- Verificar formato JSON de datos
- Comprobar timestamps en mensajes
- Revisar logs de error en consola

### Debugging

**Monitor Serial Arduino:**
```cpp
Serial.println("Debug: Enviando datos RS485");
Serial.printf("Sensor values: pot=%.2f, ldr=%.2f\n", pot_val, ldr_val);
```

**Debug Python:**
```python
print(f"Datos recibidos: {data}")
print(f"Puerto {port}: {connected}")
```

## 📈 Mejoras Futuras

- [ ] Almacenamiento de datos en archivo CSV
- [ ] Análisis estadístico de sensores  
- [ ] Comunicación WiFi opcional
- [ ] Interfaz web complementaria
- [ ] Alertas por thresholds
- [ ] Calibración automática de sensores
- [ ] Soporte para más tipos de sensores
- [ ] Dashboard con múltiples gráficas

## 📞 Soporte

Para problemas o mejoras:
1. Revisar este README completo
2. Consultar `INSTALACION_LIBRERIAS.md`
3. Verificar conexiones de hardware
4. Comprobar versiones de librerías

---

**Desarrollado para Universidad Militar Nueva Granada**  
**Curso: Comunicaciones - Laboratorio RS485/RS232**  
**Semestre VI**
