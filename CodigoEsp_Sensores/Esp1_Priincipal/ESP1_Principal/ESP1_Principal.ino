/*
 * ESP32 S3 - ESP1 Principal - VERSION SIMPLE PARA TEST
 * Solo control de LEDs via Serial y RS485
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

// ============ VARIABLES GLOBALES ============
HardwareSerial RS485Serial(1);
String rs485_buffer = "";

void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println("ESP1 INICIANDO - VERSION SIMPLE");
  
  // Configurar LEDs
  pinMode(LED_VERDE, OUTPUT);
  pinMode(LED_ROJO, OUTPUT);
  pinMode(LED_AMARILLO, OUTPUT);
  
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
  
  Serial.println("ESP1 LISTO");
  Serial.println("Comandos disponibles:");
  Serial.println("LEDS ESP1:");
  Serial.println("1 = LED Verde ON");
  Serial.println("0 = LED Verde OFF");
  Serial.println("2 = LED Rojo ON");  
  Serial.println("3 = LED Rojo OFF");
  Serial.println("4 = LED Amarillo ON");
  Serial.println("5 = LED Amarillo OFF");
  Serial.println("LEDS ESP2:");
  Serial.println("ESP2_1 = LED Verde ESP2 ON");
  Serial.println("ESP2_0 = LED Verde ESP2 OFF");
  Serial.println("ESP2_2 = LED Rojo ESP2 ON");
  Serial.println("ESP2_3 = LED Rojo ESP2 OFF");
  Serial.println("ESP2_4 = LED Amarillo ESP2 ON");
  Serial.println("ESP2_5 = LED Amarillo ESP2 OFF");
  
  // Test rápido
  digitalWrite(LED_VERDE, HIGH);
  delay(200);
  digitalWrite(LED_VERDE, LOW);
  Serial.println("Test LED completado");
}

void loop() {
  // Procesar comandos del Serial Monitor
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    Serial.println("CMD: " + cmd);
    
    // Comandos locales ESP1
    if (cmd == "1") {
      digitalWrite(LED_VERDE, HIGH);
      Serial.println("ESP1 LED Verde ON");
    }
    else if (cmd == "0") {
      digitalWrite(LED_VERDE, LOW);
      Serial.println("ESP1 LED Verde OFF");
    }
    else if (cmd == "2") {
      digitalWrite(LED_ROJO, HIGH);
      Serial.println("ESP1 LED Rojo ON");
    }
    else if (cmd == "3") {
      digitalWrite(LED_ROJO, LOW);
      Serial.println("ESP1 LED Rojo OFF");
    }
    else if (cmd == "4") {
      digitalWrite(LED_AMARILLO, HIGH);
      Serial.println("ESP1 LED Amarillo ON");
    }
    else if (cmd == "5") {
      digitalWrite(LED_AMARILLO, LOW);
      Serial.println("ESP1 LED Amarillo OFF");
    }
    // Comandos para ESP2 via RS485
    else if (cmd.startsWith("ESP2_")) {
      sendToESP2(cmd);
    }
  }
  
  // Escuchar respuestas de RS485
  receiveFromRS485();
  
  delay(10);
}

// ============ FUNCIONES AUXILIARES ============

void setRS485ReceiveMode() {
  digitalWrite(RS485_RE, LOW);
  digitalWrite(RS485_DE, LOW);
}

void setRS485TransmitMode() {
  digitalWrite(RS485_RE, HIGH);
  digitalWrite(RS485_DE, HIGH);
  delay(1);
}

void sendToESP2(String comando) {
  Serial.println("Enviando a ESP2: " + comando);
  
  setRS485TransmitMode();
  delay(10);
  
  RS485Serial.println(comando);
  RS485Serial.flush();
  delay(10);  // Asegurar envío completo
  
  setRS485ReceiveMode();
  delay(20);  // Dar tiempo al ESP2 para procesar
  
  Serial.println("Comando enviado a ESP2");
  
  // Esperar respuesta por 1000ms con timeout más largo
  unsigned long timeout = millis() + 1000;
  String buffer = "";
  
  while (millis() < timeout) {
    if (RS485Serial.available()) {
      char c = RS485Serial.read();
      if (c == '\n') {
        if (buffer.length() > 0) {
          Serial.println("✓ Respuesta ESP2: " + buffer);
          return;  // Salir cuando recibamos respuesta
        }
      } else if (c != '\r') {
        buffer += c;
      }
    }
    delay(5);
  }
  Serial.println("⚠ Timeout - No se recibió respuesta de ESP2");
}

void receiveFromRS485() {
  if (RS485Serial.available()) {
    String data = RS485Serial.readStringUntil('\n');
    data.trim();
    
    if (data.length() > 0) {
      Serial.println("📨 Recibido de ESP2: " + data);
      
      // Procesar comandos que vengan de ESP2
      if (data.startsWith("ESP1_")) {
        processRemoteCommand(data);
      }
    }
  }
}

void processRemoteCommand(String comando) {
  Serial.println("Procesando comando remoto: " + comando);
  
  if (comando == "ESP1_1") {
    digitalWrite(LED_VERDE, HIGH);
    Serial.println("ESP1 LED Verde ON (desde ESP2)");
  }
  else if (comando == "ESP1_0") {
    digitalWrite(LED_VERDE, LOW);
    Serial.println("ESP1 LED Verde OFF (desde ESP2)");
  }
  else if (comando == "ESP1_2") {
    digitalWrite(LED_ROJO, HIGH);
    Serial.println("ESP1 LED Rojo ON (desde ESP2)");
  }
  else if (comando == "ESP1_3") {
    digitalWrite(LED_ROJO, LOW);
    Serial.println("ESP1 LED Rojo OFF (desde ESP2)");
  }
}

// FIN DEL CÓDIGO SIMPLIFICADO ESP1
