/*
 * ESP32 S3 - ESP1 Principal - SISTEMA MAESTRO/ESCLAVO
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
bool is_master = true;  // ESP1 es maestro por defecto
String device_role = "MAESTRO";

unsigned long lastSensorRead = 0;
unsigned long lastDataSend = 0;
#define SENSOR_INTERVAL 50   // Leer sensores cada 50ms (20Hz)
#define SEND_INTERVAL 50     // Enviar datos cada 50ms (20Hz)

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("=== ESP1 INICIANDO - SISTEMA MAESTRO/ESCLAVO ===");
  
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
  
  Serial.println("ESP1 LISTO - Configuracion Maestro/Esclavo");
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
  Serial.print("{\"device\":\"ESP1\",\"role\":\"");
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
  if (remoteSensors.timestamp > 0 && (millis() - remoteSensors.timestamp < 1000)) {
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
  
  // Pedir datos de ESP2 cada cierto tiempo (más frecuente)
  static unsigned long lastRequest = 0;
  if (millis() - lastRequest > 100) {  // Cada 100ms (10Hz)
    requestESP2Data();
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
      Serial.println("ESP1 configurado como MAESTRO - Enviando datos");
      // Notificar a ESP2 que ESP1 es maestro
      sendRoleCommandToESP2("SET_SLAVE");
    }
    else if (input == "SET_SLAVE") {
      is_master = false;
      device_role = "ESCLAVO";
      Serial.println("ESP1 configurado como ESCLAVO - Solo escuchando");
      // Notificar a ESP2 que ESP1 es esclavo
      sendRoleCommandToESP2("SET_MASTER");
    }
    // Comandos JSON de LEDs (retrocompatibilidad)
    else if (input.startsWith("{") && input.endsWith("}")) {
      processLEDCommands(input);
    }
    // Comandos de LED para ESP1 (locales)
    else if (input.indexOf("esp1_led_verde") >= 0 || (input.indexOf("led_verde") >= 0 && input.indexOf("esp2") < 0)) {
      if (input.indexOf("true") >= 0 || input.indexOf("1") >= 0 || input.indexOf("ON") >= 0) {
        led_verde_state = true;
        digitalWrite(LED_VERDE, HIGH);
        Serial.println("ESP1 - LED Verde ON");
      } else {
        led_verde_state = false;
        digitalWrite(LED_VERDE, LOW);
        Serial.println("ESP1 - LED Verde OFF");
      }
    }
    else if (input.indexOf("esp1_led_rojo") >= 0 || (input.indexOf("led_rojo") >= 0 && input.indexOf("esp2") < 0)) {
      if (input.indexOf("true") >= 0 || input.indexOf("1") >= 0 || input.indexOf("ON") >= 0) {
        led_rojo_state = true;
        digitalWrite(LED_ROJO, HIGH);
        Serial.println("ESP1 - LED Rojo ON");
      } else {
        led_rojo_state = false;
        digitalWrite(LED_ROJO, LOW);
        Serial.println("ESP1 - LED Rojo OFF");
      }
    }
    else if (input.indexOf("esp1_led_amarillo") >= 0 || (input.indexOf("led_amarillo") >= 0 && input.indexOf("esp2") < 0)) {
      if (input.indexOf("true") >= 0 || input.indexOf("1") >= 0 || input.indexOf("ON") >= 0) {
        led_amarillo_state = true;
        digitalWrite(LED_AMARILLO, HIGH);
        Serial.println("ESP1 - LED Amarillo ON");
      } else {
        led_amarillo_state = false;
        digitalWrite(LED_AMARILLO, LOW);
        Serial.println("ESP1 - LED Amarillo OFF");
      }
    }
    // Comandos de LED para ESP2 (remotos - enviar por RS485)
    else if (input.indexOf("esp2_led_verde") >= 0) {
      String state = (input.indexOf("true") >= 0 || input.indexOf("1") >= 0 || input.indexOf("ON") >= 0) ? "true" : "false";
      sendLEDCommandToESP2("led_verde", state);
      Serial.println("Comando LED enviado a ESP2: led_verde=" + state);
    }
    else if (input.indexOf("esp2_led_rojo") >= 0) {
      String state = (input.indexOf("true") >= 0 || input.indexOf("1") >= 0 || input.indexOf("ON") >= 0) ? "true" : "false";
      sendLEDCommandToESP2("led_rojo", state);
      Serial.println("Comando LED enviado a ESP2: led_rojo=" + state);
    }
    else if (input.indexOf("esp2_led_amarillo") >= 0) {
      String state = (input.indexOf("true") >= 0 || input.indexOf("1") >= 0 || input.indexOf("ON") >= 0) ? "true" : "false";
      sendLEDCommandToESP2("led_amarillo", state);
      Serial.println("Comando LED enviado a ESP2: led_amarillo=" + state);
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
  
  // Comandos para ESP2
  if (jsonInput.indexOf("\"target\":\"ESP2\"") > 0) {
    forwardCommandToESP2(jsonInput);
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

void requestESP2Data() {
  setRS485TransmitMode();
  delay(5);
  
  RS485Serial.println("GET_SENSORS");
  RS485Serial.flush();
  
  delay(10);
  setRS485ReceiveMode();
}

void forwardCommandToESP2(String jsonCommand) {
  setRS485TransmitMode();
  delay(5);
  
  RS485Serial.println("CMD:" + jsonCommand);
  RS485Serial.flush();
  
  delay(10);
  setRS485ReceiveMode();
}

void sendRoleCommandToESP2(String role) {
  setRS485TransmitMode();
  delay(5);
  
  RS485Serial.println("ROLE:" + role);
  RS485Serial.flush();
  
  delay(10);
  setRS485ReceiveMode();
  Serial.println("Comando de rol enviado a ESP2: " + role);
}

void sendLEDCommandToESP2(String ledName, String state) {
  setRS485TransmitMode();
  delay(5);
  
  RS485Serial.println("LED:" + ledName + ":" + state);
  RS485Serial.flush();
  
  delay(10);
  setRS485ReceiveMode();
}

void receiveFromRS485() {
  while (RS485Serial.available()) {
    String data = RS485Serial.readStringUntil('\n');
    data.trim();
    
    if (data.length() > 0) {
      // Procesar datos de sensores: "SENS:pot,ldr,enc"
      if (data.startsWith("SENS:")) {
        String sensorData = data.substring(5);
        int comma1 = sensorData.indexOf(',');
        int comma2 = sensorData.lastIndexOf(',');
        
        if (comma1 > 0 && comma2 > comma1) {
          remoteSensors.potenciometro = sensorData.substring(0, comma1).toInt();
          remoteSensors.ldr = sensorData.substring(comma1 + 1, comma2).toInt();
          remoteSensors.encoder = sensorData.substring(comma2 + 1).toInt();
          remoteSensors.timestamp = millis();
          Serial.print("Datos recibidos de ESP2: pot=");
          Serial.print(remoteSensors.potenciometro);
          Serial.print(" ldr=");
          Serial.print(remoteSensors.ldr);
          Serial.print(" enc=");
          Serial.println(remoteSensors.encoder);
        }
      }
      // Comando de rol recibido
      else if (data.startsWith("ROLE:")) {
        String roleCommand = data.substring(5);
        if (roleCommand == "SET_MASTER") {
          is_master = true;
          device_role = "MAESTRO";
          Serial.println("ESP1 configurado como MAESTRO por ESP2");
        } else if (roleCommand == "SET_SLAVE") {
          is_master = false;
          device_role = "ESCLAVO";
          Serial.println("ESP1 configurado como ESCLAVO por ESP2");
        }
      }
      // Comando de LED recibido: "LED:led_verde:true"
      else if (data.startsWith("LED:")) {
        String ledCommand = data.substring(4);
        int colon = ledCommand.indexOf(':');
        if (colon > 0) {
          String ledName = ledCommand.substring(0, colon);
          String state = ledCommand.substring(colon + 1);
          
          if (ledName == "led_verde") {
            led_verde_state = (state == "true");
            digitalWrite(LED_VERDE, led_verde_state ? HIGH : LOW);
            Serial.print("ESP1 - LED Verde ");
            Serial.print(led_verde_state ? "ON" : "OFF");
            Serial.println(" (por ESP2)");
          }
          else if (ledName == "led_rojo") {
            led_rojo_state = (state == "true");
            digitalWrite(LED_ROJO, led_rojo_state ? HIGH : LOW);
            Serial.print("ESP1 - LED Rojo ");
            Serial.print(led_rojo_state ? "ON" : "OFF");
            Serial.println(" (por ESP2)");
          }
          else if (ledName == "led_amarillo") {
            led_amarillo_state = (state == "true");
            digitalWrite(LED_AMARILLO, led_amarillo_state ? HIGH : LOW);
            Serial.print("ESP1 - LED Amarillo ");
            Serial.print(led_amarillo_state ? "ON" : "OFF");
            Serial.println(" (por ESP2)");
          }
        }
      }
    }
  }
}

// FIN DEL CÓDIGO ESP1
