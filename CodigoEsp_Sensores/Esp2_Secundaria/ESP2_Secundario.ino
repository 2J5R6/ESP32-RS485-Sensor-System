/*
 * ESP32 S3 - ESP2 Secundario  
 * Sistema de comunicación RS485/RS232 con sensores múltiples
 * 
 * CONFIGURACIÓN DE PINES:
 * - Sensores Analógicos:
 *   • Potenciómetro: pin 6
 *   • LDR: pin 7
 *   • Encoder/Velocidad: pin 15
 * - MPU6050 I2C:
 *   • SDA: pin 43, SCL: pin 44 (pines I2C por defecto ESP32-S3)
 * - RS485:
 *   • RO (Receptor Output): pin 39
 *   • RE (Receptor Enable): pin 38
 *   • DE (Driver Enable): pin 37
 *   • DI (Driver Input): pin 36
 * - LEDs de Control:
 *   • LED Verde: pin 21
 *   • LED Rojo: pin 20
 *   • LED Amarillo: pin 19
 * 
 * PROTOCOLO DE COMUNICACIÓN:
 * - RS232 (USB): JSON compacto hacia PC a 20Hz
 * - RS485: Half-dúplex alternado con ESP1
 * - Comandos LED desde PC interpretados en tiempo real
 */

#include <Wire.h>
// #include <MPU6050.h>  // MPU6050 temporalmente deshabilitado
#include <ArduinoJson.h>
#include <HardwareSerial.h>

// ============ DEFINICIÓN DE PINES ============
// Sensores Analógicos
#define PIN_POTENCIOMETRO   6
#define PIN_LDR             7
#define PIN_ENCODER        15

// MPU6050 I2C (pines por defecto)
#define SDA_PIN            43
#define SCL_PIN            44

// RS485 Half-Duplex
#define RS485_RO           39  // Receptor Output
#define RS485_RE           38  // Receptor Enable (activo bajo)
#define RS485_DE           37  // Driver Enable (activo alto)
#define RS485_DI           36  // Driver Input

// LEDs de Control
#define LED_VERDE          21
#define LED_ROJO           20
#define LED_AMARILLO       19

// ============ CONFIGURACIÓN DE COMUNICACIÓN ============
#define BAUD_RATE_USB      115200
#define BAUD_RATE_RS485    9600
#define UPDATE_FREQUENCY   20     // Hz
#define UPDATE_INTERVAL    (1000/UPDATE_FREQUENCY)  // 50ms

// ============ VARIABLES GLOBALES ============
// Objetos de comunicación
HardwareSerial RS485Serial(1);  // UART1 para RS485
// MPU6050 mpu;  // MPU6050 temporalmente deshabilitado

// Variables de sensores (sin MPU6050 por ahora)
struct SensorData {
  float potenciometro;
  float ldr;
  float encoder;
  // float accel_x, accel_y, accel_z;  // MPU6050 deshabilitado
  // float gyro_x, gyro_y, gyro_z;    // MPU6050 deshabilitado
  unsigned long timestamp;
} localSensors, remoteSensors;

// Variables de control de tiempo
unsigned long lastSensorRead = 0;
unsigned long lastRS485Send = 0;
unsigned long lastRS485Receive = 0;
bool rs485_tx_mode = false;  // ESP2 inicia en modo recepción (opuesto a ESP1)

// Estados de LEDs
bool led_verde_state = false;
bool led_rojo_state = false;
bool led_amarillo_state = false;

// Buffer circular para datos RS485
#define BUFFER_SIZE 256
char rs485_buffer[BUFFER_SIZE];
int buffer_index = 0;

void setup() {
  // ============ INICIALIZACIÓN SERIAL ============
  Serial.begin(BAUD_RATE_USB);
  while (!Serial) delay(10);
  
  // Configurar RS485 en UART1
  RS485Serial.begin(BAUD_RATE_RS485, SERIAL_8N1, RS485_RO, RS485_DI);
  
  Serial.println("=== ESP32-S3 ESP2 Iniciando ===");
  Serial.println("Sistema RS485/RS232 con sensores multiples");
  
  // ============ CONFIGURACIÓN DE PINES ============
  // Pines de sensores analógicos como entrada
  pinMode(PIN_POTENCIOMETRO, INPUT);
  pinMode(PIN_LDR, INPUT);
  pinMode(PIN_ENCODER, INPUT);
  
  // Pines RS485 de control
  pinMode(RS485_RE, OUTPUT);
  pinMode(RS485_DE, OUTPUT);
  setRS485ReceiveMode();  // ESP2 inicia en modo recepción
  
  // LEDs como salida
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_ROJO, OUTPUT);
  pinMode(LED_AMARILLO, OUTPUT);
  
  // Apagar todos los LEDs inicialmente
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_ROJO, LOW);
  digitalWrite(LED_AMARILLO, LOW);
  
  // ============ INICIALIZACIÓN I2C Y MPU6050 ============
  // Wire.begin(SDA_PIN, SCL_PIN);          // MPU6050 deshabilitado
  // Wire.setClock(400000);                 // MPU6050 deshabilitado
  
  // mpu.initialize();                      // MPU6050 deshabilitado
  // if (mpu.testConnection()) {            // MPU6050 deshabilitado
  //   Serial.println("* MPU6050 inicializado correctamente");
  //   mpu.setFullScaleAccelRange(MPU6050_ACCEL_FS_2);
  //   mpu.setFullScaleGyroRange(MPU6050_GYRO_FS_250);
  //   mpu.setDLPFMode(MPU6050_DLPF_BW_20);
  // } else {
  //   Serial.println("* Error: No se pudo inicializar MPU6050");
  // }                                      // MPU6050 deshabilitado
  
  Serial.println("* MPU6050 temporalmente deshabilitado");
  Serial.println("* ESP2 listo para operacion");
  Serial.println("Frecuencia de actualizacion: 20Hz (50ms)");
}

void loop() {
  unsigned long currentTime = millis();
  
  // ============ LECTURA DE SENSORES (20Hz) ============
  if (currentTime - lastSensorRead >= UPDATE_INTERVAL) {
    readAllSensors();
    sendDataToPC();
    lastSensorRead = currentTime;
  }
  
  // ============ COMUNICACIÓN RS485 HALF-DUPLEX ============
  // ESP2 alterna opuesto a ESP1: recibe primero, luego transmite
  if (!rs485_tx_mode && (currentTime - lastRS485Receive >= UPDATE_INTERVAL)) {
    receiveDataViaRS485();
    lastRS485Receive = currentTime;
    rs485_tx_mode = true;   // Cambiar a modo transmisión
  }
  else if (rs485_tx_mode && (currentTime - lastRS485Send >= UPDATE_INTERVAL)) {
    sendDataViaRS485();
    lastRS485Send = currentTime;
    rs485_tx_mode = false;  // Cambiar a modo recepción
    setRS485ReceiveMode();
  }
  
  // ============ PROCESAMIENTO DE COMANDOS PC ============
  processPC_Commands();
}

// ============ FUNCIONES DE LECTURA DE SENSORES ============
void readAllSensors() {
  localSensors.timestamp = millis();
  
  // Lectura de sensores analógicos (12 bits, 0-4095)
  localSensors.potenciometro = analogRead(PIN_POTENCIOMETRO) * (3.3 / 4095.0);
  localSensors.ldr = analogRead(PIN_LDR) * (3.3 / 4095.0);
  localSensors.encoder = analogRead(PIN_ENCODER) * (3.3 / 4095.0);
  
  // Lectura del MPU6050 usando librería básica (DESHABILITADO)
  // int16_t ax, ay, az, gx, gy, gz;
  // mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
  
  // Convertir valores raw a unidades físicas (DESHABILITADO)
  // localSensors.accel_x = ax / 16384.0;  // Para rango ±2g
  // localSensors.accel_y = ay / 16384.0;
  // localSensors.accel_z = az / 16384.0;
  // localSensors.gyro_x = gx / 131.0;     // Para rango ±250°/s
  // localSensors.gyro_y = gy / 131.0;
  // localSensors.gyro_z = gz / 131.0;
}

// ============ COMUNICACIÓN RS232 (USB) ============
void sendDataToPC() {
  // Mostrar datos simples para debug
  Serial.print("DEBUG - Pot: ");
  Serial.print(localSensors.potenciometro);
  Serial.print(" LDR: ");
  Serial.print(localSensors.ldr);
  Serial.print(" Enc: ");
  Serial.println(localSensors.encoder);
  
  // Crear JSON compacto para envío eficiente (sin MPU6050)
  StaticJsonDocument<256> doc;
  
  doc["device"] = "ESP2";
  doc["timestamp"] = localSensors.timestamp;
  
  // Sensores locales (solo analógicos)
  JsonObject local = doc.createNestedObject("local");
  local["pot"] = round(localSensors.potenciometro * 100) / 100.0;
  local["ldr"] = round(localSensors.ldr * 100) / 100.0;
  local["enc"] = round(localSensors.encoder * 100) / 100.0;
  // local["ax"] = 0.0;  // MPU6050 deshabilitado
  
  // Sensores remotos (de ESP1)
  JsonObject remote = doc.createNestedObject("remote");
  remote["pot"] = round(remoteSensors.potenciometro * 100) / 100.0;
  remote["ldr"] = round(remoteSensors.ldr * 100) / 100.0;
  remote["enc"] = round(remoteSensors.encoder * 100) / 100.0;
  // remote["ax"] = 0.0;  // MPU6050 deshabilitado
  
  // Estados de LEDs
  JsonObject leds = doc.createNestedObject("leds");
  leds["verde"] = led_verde_state;
  leds["rojo"] = led_rojo_state;
  leds["amarillo"] = led_amarillo_state;
  
  serializeJson(doc, Serial);
  Serial.println();  // Nueva línea para delimitador
}

// ============ COMUNICACIÓN RS485 HALF-DUPLEX ============
void setRS485TransmitMode() {
  digitalWrite(RS485_RE, HIGH);  // Deshabilitar receptor
  digitalWrite(RS485_DE, HIGH);  // Habilitar transmisor
  delayMicroseconds(10);         // Tiempo de settling
}

void setRS485ReceiveMode() {
  digitalWrite(RS485_DE, LOW);   // Deshabilitar transmisor
  digitalWrite(RS485_RE, LOW);   // Habilitar receptor
  delayMicroseconds(10);         // Tiempo de settling
}

void sendDataViaRS485() {
  setRS485TransmitMode();
  
  // Crear paquete compacto para RS485
  StaticJsonDocument<256> packet;
  packet["src"] = "ESP2";
  packet["ts"] = localSensors.timestamp;
  packet["pot"] = localSensors.potenciometro;
  packet["ldr"] = localSensors.ldr;
  packet["enc"] = localSensors.encoder;
  // packet["ax"] = localSensors.accel_x;  // MPU6050 deshabilitado
  
  String jsonString;
  serializeJson(packet, jsonString);
  
  Serial.print("DEBUG RS485 TX: ");
  Serial.println(jsonString);
  
  RS485Serial.print(jsonString);
  RS485Serial.print('\n');  // Delimitador de mensaje
  RS485Serial.flush();      // Asegurar transmisión completa
  
  delay(2);  // Pequeño delay para estabilidad
}

void receiveDataViaRS485() {
  setRS485ReceiveMode();
  
  // Leer datos disponibles en buffer circular
  while (RS485Serial.available() && buffer_index < BUFFER_SIZE - 1) {
    char c = RS485Serial.read();
    
    if (c == '\n') {  // Fin de mensaje
      rs485_buffer[buffer_index] = '\0';
      parseRS485Message();
      buffer_index = 0;
    } else {
      rs485_buffer[buffer_index++] = c;
    }
  }
  
  // Resetear buffer si se llena sin encontrar delimitador
  if (buffer_index >= BUFFER_SIZE - 1) {
    buffer_index = 0;
  }
}

void parseRS485Message() {
  Serial.print("DEBUG RS485 RX: ");
  Serial.println(rs485_buffer);
  
  StaticJsonDocument<256> doc;
  DeserializationError error = deserializeJson(doc, rs485_buffer);
  
  if (!error) {
    // Verificar si es un comando
    if (doc["type"] == "command") {
      Serial.println("DEBUG - Comando recibido via RS485");
      String commandData = doc["data"];
      
      // Procesar el comando recibido
      StaticJsonDocument<128> cmd;
      DeserializationError cmdError = deserializeJson(cmd, commandData);
      
      if (!cmdError && cmd["target"] == "ESP2") {
        Serial.println("DEBUG - Ejecutando comando para ESP2 desde RS485");
        processLEDCommands(cmd, commandData);
      }
    }
    // Verificar si son datos de sensores
    else if (doc["src"] == "ESP1") {
      Serial.println("DEBUG - Datos de ESP1 recibidos correctamente");
      // Actualizar datos remotos de ESP1
      remoteSensors.timestamp = doc["ts"];
      remoteSensors.potenciometro = doc["pot"];
      remoteSensors.ldr = doc["ldr"];
      remoteSensors.encoder = doc["enc"];
      // remoteSensors.accel_x = doc["ax"];  // MPU6050 deshabilitado
    }
  } else {
    Serial.print("DEBUG - Error parseando RS485: ");
    Serial.println(error.c_str());
  }
}

// ============ PROCESAMIENTO DE COMANDOS PC ============
void processPC_Commands() {
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    Serial.print("DEBUG - Comando recibido: ");
    Serial.println(command);
    
    StaticJsonDocument<128> cmd;
    DeserializationError error = deserializeJson(cmd, command);
    
    if (!error) {
      // Si el comando es para ESP2 (esta tarjeta)
      if (cmd["target"] == "ESP2") {
        Serial.println("DEBUG - Comando para ESP2 procesado");
        processLEDCommands(cmd, command);
      }
      // Si el comando es para ESP1, reenviarlo por RS485
      else if (cmd["target"] == "ESP1") {
        Serial.println("DEBUG - Reenviando comando para ESP1 via RS485");
        sendCommandViaRS485(command);
      }
    } else {
      Serial.print("DEBUG - Error parseando comando: ");
      Serial.println(error.c_str());
    }
  }
}

// ============ PROCESAMIENTO DE COMANDOS LED ============
void processLEDCommands(StaticJsonDocument<128>& cmd, String& originalCommand) {
  bool commandProcessed = false;
  
  // Procesar comandos de LEDs
  if (cmd.containsKey("led_verde")) {
    led_verde_state = cmd["led_verde"];
    digitalWrite(LED_VERDE, led_verde_state ? HIGH : LOW);
    Serial.print("DEBUG - LED Verde: ");
    Serial.println(led_verde_state ? "ON" : "OFF");
    commandProcessed = true;
  }
  if (cmd.containsKey("led_rojo")) {
    led_rojo_state = cmd["led_rojo"];
    digitalWrite(LED_ROJO, led_rojo_state ? HIGH : LOW);
    Serial.print("DEBUG - LED Rojo: ");
    Serial.println(led_rojo_state ? "ON" : "OFF");
    commandProcessed = true;
  }
  if (cmd.containsKey("led_amarillo")) {
    led_amarillo_state = cmd["led_amarillo"];
    digitalWrite(LED_AMARILLO, led_amarillo_state ? HIGH : LOW);
    Serial.print("DEBUG - LED Amarillo: ");
    Serial.println(led_amarillo_state ? "ON" : "OFF");
    commandProcessed = true;
  }
  
  // Confirmación de comando ejecutado
  if (commandProcessed) {
    Serial.println("{\"ack\":\"ESP2\",\"cmd\":\"" + originalCommand + "\"}");
  }
}

// ============ ENVÍO DE COMANDOS VIA RS485 ============
void sendCommandViaRS485(String command) {
  setRS485TransmitMode();
  
  // Crear paquete de comando para RS485
  StaticJsonDocument<128> packet;
  packet["type"] = "command";
  packet["data"] = command;
  
  String jsonString;
  serializeJson(packet, jsonString);
  
  Serial.print("DEBUG RS485 CMD TX: ");
  Serial.println(jsonString);
  
  RS485Serial.print(jsonString);
  RS485Serial.print('\n');
  RS485Serial.flush();
  
  delay(5);  // Pequeño delay para comando
  setRS485ReceiveMode();
}
