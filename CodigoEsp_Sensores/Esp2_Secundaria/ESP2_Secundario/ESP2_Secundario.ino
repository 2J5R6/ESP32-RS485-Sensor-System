/*
 * ESP32 S3 - ESP2 Secundario - SISTEMA MAESTRO/ESCLAVO
 * Comunicación RS485/RS232 con comando de rol maestro/esclavo
 * Solo el ESP MAESTRO envía datos continuos
 */

#include <HardwareSerial.h>

// ============ DEFINICIÓN DE PINES ============
#define LED_VERDE          21
#define LED_ROJO           20  
#define LED_AMARILLO       19

#define RS485_DI           36  // Driver Input
#define RS485_DE           37  // Driver Enable  
#define RS485_RE           38  // Receptor Enable
#define RS485_RO           39  // Receptor Output

// Sensores Analógicos
#define PIN_POTENCIOMETRO   6
#define PIN_LDR             7
#define PIN_ENCODER         8

// ============ VARIABLES GLOBALES ============
HardwareSerial RS485Serial(1);

// Variables de sensores
struct SensorData {
  int potenciometro;
  int ldr;
  int encoder;
  unsigned long timestamp;
} localSensors, remoteSensors;

// Estados de LEDs
bool led_verde_state = false;
bool led_rojo_state = false;
bool led_amarillo_state = false;

// SISTEMA MAESTRO/ESCLAVO
bool is_master = false;  // ESP2 es esclavo por defecto
String device_role = "ESCLAVO";

unsigned long lastSensorRead = 0;
unsigned long lastDataSend = 0;
#define SENSOR_INTERVAL 50   // Leer sensores cada 50ms (20Hz)
#define SEND_INTERVAL 50     // Enviar datos cada 50ms (20Hz)

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("=== ESP2 INICIANDO - SISTEMA MAESTRO/ESCLAVO ===");
  
  // Configurar LEDs
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_ROJO, OUTPUT);
  pinMode(LED_AMARILLO, OUTPUT);
  
  // Configurar sensores
  pinMode(PIN_POTENCIOMETRO, INPUT);
  pinMode(PIN_LDR, INPUT);
  pinMode(PIN_ENCODER, INPUT);
  
  // Apagar LEDs
  digitalWrite(LED_VERDE, LOW);
  digitalWrite(LED_ROJO, LOW);
  digitalWrite(LED_AMARILLO, LOW);
  
  // Configurar RS485
  pinMode(RS485_RE, OUTPUT);
  pinMode(RS485_DE, OUTPUT);
  setRS485ReceiveMode();
  
  // Inicializar UART1 para RS485
  RS485Serial.begin(9600, SERIAL_8N1, RS485_RO, RS485_DI);
  
  Serial.println("ESP2 LISTO - Configuracion Maestro/Esclavo");
  Serial.print("Estado actual: ");
  Serial.println(device_role);
  Serial.println("Comandos disponibles:");
  Serial.println("  SET_MASTER - Convertir en maestro");
  Serial.println("  SET_SLAVE - Convertir en esclavo");
  Serial.println("  JSON LED commands: {\"led_verde\":true/false}");
  
  // Test inicial de sensores
  readLocalSensors();
  delay(100);
}

void loop() {
  unsigned long currentTime = millis();
  
  // Siempre leer sensores locales
  if (currentTime - lastSensorRead >= SENSOR_INTERVAL) {
    readLocalSensors();
    lastSensorRead = currentTime;
  }
  
  // Solo enviar datos si es MAESTRO
  if (is_master && (currentTime - lastDataSend >= SEND_INTERVAL)) {
    sendJSONData();
    lastDataSend = currentTime;
  }
  
  // Procesar comandos del monitor serial (interfaz Python)
  processSerialCommands();
  
  // Escuchar comunicación RS485
  receiveFromRS485();
  
  delay(5);
}

// ============ FUNCIONES DE SENSORES ============

void readLocalSensors() {
  localSensors.potenciometro = analogRead(PIN_POTENCIOMETRO);
  localSensors.ldr = analogRead(PIN_LDR);
  localSensors.encoder = analogRead(PIN_ENCODER);
  localSensors.timestamp = millis();
}

void sendJSONData() {
  // Solo enviar si es maestro
  if (!is_master) {
    return;
  }
  
  // Crear JSON compatible con la interfaz Python
  Serial.print("{\"device\":\"ESP2\",\"role\":\"");
  Serial.print(device_role);
  Serial.print("\",\"timestamp\":");
  Serial.print(localSensors.timestamp);
  Serial.print(",\"local\":{\"pot\":");
  Serial.print((localSensors.potenciometro * 3.3) / 4095.0, 3);
  Serial.print(",\"ldr\":");
  Serial.print((localSensors.ldr * 3.3) / 4095.0, 3);
  Serial.print(",\"enc\":");
  Serial.print((localSensors.encoder * 3.3) / 4095.0, 3);
  Serial.print(",\"ax\":0.0}");
  
  // Datos remotos si existen
  if (remoteSensors.timestamp > 0) {
    Serial.print(",\"remote\":{\"pot\":");
    Serial.print((remoteSensors.potenciometro * 3.3) / 4095.0, 3);
    Serial.print(",\"ldr\":");
    Serial.print((remoteSensors.ldr * 3.3) / 4095.0, 3);
    Serial.print(",\"enc\":");
    Serial.print((remoteSensors.encoder * 3.3) / 4095.0, 3);
    Serial.print(",\"ax\":0.0}");
  } else {
    Serial.print(",\"remote\":{\"pot\":0.0,\"ldr\":0.0,\"enc\":0.0,\"ax\":0.0}");
  }
  
  Serial.println("}");
  
  // Pedir datos de ESP1 cada cierto tiempo
  static unsigned long lastRequest = 0;
  if (millis() - lastRequest > 200) {  // Cada 200ms
    requestESP1Data();
    lastRequest = millis();
  }
}

void processSerialCommands() {
  if (Serial.available()) {
    String input = Serial.readStringUntil('\n');
    input.trim();
    
    // Comandos de rol maestro/esclavo
    if (input == "SET_MASTER") {
      is_master = true;
      device_role = "MAESTRO";
      Serial.println("ESP2 configurado como MAESTRO - Enviando datos");
      // Notificar a ESP1 que ESP2 es maestro
      sendRoleCommandToESP1("SET_SLAVE");
    }
    else if (input == "SET_SLAVE") {
      is_master = false;
      device_role = "ESCLAVO";
      Serial.println("ESP2 configurado como ESCLAVO - Solo escuchando");
      // Notificar a ESP1 que ESP2 es esclavo
      sendRoleCommandToESP1("SET_MASTER");
    }
    // Comandos JSON de LEDs (retrocompatibilidad)
    else if (input.startsWith("{") && input.endsWith("}")) {
      processLEDCommands(input);
    }
    // Comandos de LED simples
    else if (input.indexOf("led_verde") >= 0) {
      if (input.indexOf("true") >= 0 || input.indexOf("1") >= 0 || input.indexOf("ON") >= 0) {
        led_verde_state = true;
        digitalWrite(LED_VERDE, HIGH);
        Serial.println("LED Verde ON");
      } else {
        led_verde_state = false;
        digitalWrite(LED_VERDE, LOW);
        Serial.println("LED Verde OFF");
      }
    }
    else if (input.indexOf("led_rojo") >= 0) {
      if (input.indexOf("true") >= 0 || input.indexOf("1") >= 0 || input.indexOf("ON") >= 0) {
        led_rojo_state = true;
        digitalWrite(LED_ROJO, HIGH);
        Serial.println("LED Rojo ON");
      } else {
        led_rojo_state = false;
        digitalWrite(LED_ROJO, LOW);
        Serial.println("LED Rojo OFF");
      }
    }
    else if (input.indexOf("led_amarillo") >= 0) {
      if (input.indexOf("true") >= 0 || input.indexOf("1") >= 0 || input.indexOf("ON") >= 0) {
        led_amarillo_state = true;
        digitalWrite(LED_AMARILLO, HIGH);
        Serial.println("LED Amarillo ON");
      } else {
        led_amarillo_state = false;
        digitalWrite(LED_AMARILLO, LOW);
        Serial.println("LED Amarillo OFF");
      }
    }
  }
}

void processLEDCommands(String jsonInput) {
  // Procesar comandos JSON de LEDs
  if (jsonInput.indexOf("\"led_verde\":true") > 0) {
    led_verde_state = true;
    digitalWrite(LED_VERDE, HIGH);
    Serial.println("LED Verde ON (JSON)");
  }
  if (jsonInput.indexOf("\"led_verde\":false") > 0) {
    led_verde_state = false;
    digitalWrite(LED_VERDE, LOW);
    Serial.println("LED Verde OFF (JSON)");
  }
  if (jsonInput.indexOf("\"led_rojo\":true") > 0) {
    led_rojo_state = true;
    digitalWrite(LED_ROJO, HIGH);
    Serial.println("LED Rojo ON (JSON)");
  }
  if (jsonInput.indexOf("\"led_rojo\":false") > 0) {
    led_rojo_state = false;
    digitalWrite(LED_ROJO, LOW);
    Serial.println("LED Rojo OFF (JSON)");
  }
  if (jsonInput.indexOf("\"led_amarillo\":true") > 0) {
    led_amarillo_state = true;
    digitalWrite(LED_AMARILLO, HIGH);
    Serial.println("LED Amarillo ON (JSON)");
  }
  if (jsonInput.indexOf("\"led_amarillo\":false") > 0) {
    led_amarillo_state = false;
    digitalWrite(LED_AMARILLO, LOW);
    Serial.println("LED Amarillo OFF (JSON)");
  }
  
  // Comandos para ESP1
  if (jsonInput.indexOf("\"target\":\"ESP1\"") > 0) {
    forwardCommandToESP1(jsonInput);
  }
}

// ============ FUNCIONES RS485 ============

void setRS485ReceiveMode() {
  digitalWrite(RS485_RE, LOW);
  digitalWrite(RS485_DE, LOW);
}

void setRS485TransmitMode() {
  digitalWrite(RS485_RE, HIGH);
  digitalWrite(RS485_DE, HIGH);
  delay(1);
}

void forwardCommandToESP1(String jsonCommand) {
  setRS485TransmitMode();
  delay(5);
  
  RS485Serial.println("CMD:" + jsonCommand);
  RS485Serial.flush();
  
  delay(10);
  setRS485ReceiveMode();
}

void sendRoleCommandToESP1(String role) {
  setRS485TransmitMode();
  delay(5);
  
  RS485Serial.println("ROLE:" + role);
  RS485Serial.flush();
  
  delay(10);
  setRS485ReceiveMode();
  Serial.println("Comando de rol enviado a ESP1: " + role);
}

void requestESP1Data() {
  setRS485TransmitMode();
  delay(5);
  
  RS485Serial.println("GET_SENSORS");
  RS485Serial.flush();
  
  delay(10);
  setRS485ReceiveMode();
}

void receiveFromRS485() {
  while (RS485Serial.available()) {
    String data = RS485Serial.readStringUntil('\n');
    data.trim();
    
    if (data.length() > 0) {
      // Solicitud de sensores
      if (data == "GET_SENSORS") {
        sendSensorsViaRS485();
      }
      // Comando JSON
      else if (data.startsWith("CMD:")) {
        String jsonCmd = data.substring(4);
        processLEDCommands(jsonCmd);
      }
      // Procesar datos de sensores: "SENS:pot,ldr,enc"
      else if (data.startsWith("SENS:")) {
        String sensorData = data.substring(5);
        int comma1 = sensorData.indexOf(',');
        int comma2 = sensorData.lastIndexOf(',');
        
        if (comma1 > 0 && comma2 > comma1) {
          remoteSensors.potenciometro = sensorData.substring(0, comma1).toInt();
          remoteSensors.ldr = sensorData.substring(comma1 + 1, comma2).toInt();
          remoteSensors.encoder = sensorData.substring(comma2 + 1).toInt();
          remoteSensors.timestamp = millis();
        }
      }
      // Comando de rol recibido
      else if (data.startsWith("ROLE:")) {
        String roleCommand = data.substring(5);
        if (roleCommand == "SET_MASTER") {
          is_master = true;
          device_role = "MAESTRO";
          Serial.println("ESP2 configurado como MAESTRO por ESP1");
        } else if (roleCommand == "SET_SLAVE") {
          is_master = false;
          device_role = "ESCLAVO";
          Serial.println("ESP2 configurado como ESCLAVO por ESP1");
        }
      }
    }
  }
}

void sendSensorsViaRS485() {
  setRS485TransmitMode();
  delay(5);
  
  // Formato simple: SENS:pot,ldr,enc
  RS485Serial.print("SENS:");
  RS485Serial.print(localSensors.potenciometro);
  RS485Serial.print(",");
  RS485Serial.print(localSensors.ldr);
  RS485Serial.print(",");
  RS485Serial.println(localSensors.encoder);
  RS485Serial.flush();
  
  delay(10);
  setRS485ReceiveMode();
}

// FIN DEL CÓDIGO ESP2
