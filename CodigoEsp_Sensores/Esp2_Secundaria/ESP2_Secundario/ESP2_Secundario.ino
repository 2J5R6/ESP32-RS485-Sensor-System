/*
 * ESP32 S3 - ESP2 Secundario - VERSION SIMPLE PARA TEST
 * Solo control de LEDs via RS485
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
  
  Serial.println("ESP2 INICIANDO - VERSION SIMPLE");
  
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
  
  Serial.println("ESP2 LISTO - ESPERANDO COMANDOS");
  Serial.println("Comandos que acepta:");
  Serial.println("ESP2_1 = LED Verde ON");
  Serial.println("ESP2_0 = LED Verde OFF");
  Serial.println("ESP2_2 = LED Rojo ON");
  Serial.println("ESP2_3 = LED Rojo OFF");
  Serial.println("ESP2_4 = LED Amarillo ON");
  Serial.println("ESP2_5 = LED Amarillo OFF");
  
  // Test rápido para verificar LEDs
  Serial.println("PROBANDO LEDs EXTERNOS...");
  digitalWrite(LED_VERDE, HIGH);
  delay(1000);  // 1 segundo para que puedas ver
  digitalWrite(LED_VERDE, LOW);
  
  digitalWrite(LED_ROJO, HIGH);
  delay(1000);
  digitalWrite(LED_ROJO, LOW);
  
  digitalWrite(LED_AMARILLO, HIGH);
  delay(1000);
  digitalWrite(LED_AMARILLO, LOW);
  
  Serial.println("Test de LEDs completado");
}

void loop() {
  // Escuchar comandos de RS485
  receiveFromRS485();
  
  // También poder enviar comandos de prueba desde Serial Monitor ESP2
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    
    Serial.println("CMD ESP2: " + cmd);
    
    // Comandos locales ESP2
    if (cmd == "1") {
      digitalWrite(LED_VERDE, HIGH);
      Serial.println("ESP2 LED Verde ON (local)");
    }
    else if (cmd == "0") {
      digitalWrite(LED_VERDE, LOW);
      Serial.println("ESP2 LED Verde OFF (local)");
    }
    // Enviar mensaje a ESP1
    else if (cmd.startsWith("ESP1_")) {
      sendToESP1(cmd);
    }
  }
  
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

void receiveFromRS485() {
  if (RS485Serial.available()) {
    String comando = RS485Serial.readStringUntil('\n');
    comando.trim();
    
    Serial.println("Comando recibido de ESP1: " + comando);
    
    // Procesar todos los comandos de LEDs
    if (comando == "ESP2_1") {
      digitalWrite(LED_VERDE, HIGH);
      Serial.println("ESP2 LED Verde ON");
      sendResponseToESP1("ESP2 LED Verde ON");
    }
    else if (comando == "ESP2_0") {
      digitalWrite(LED_VERDE, LOW);
      Serial.println("ESP2 LED Verde OFF");
      sendResponseToESP1("ESP2 LED Verde OFF");
    }
    else if (comando == "ESP2_2") {
      digitalWrite(LED_ROJO, HIGH);
      Serial.println("ESP2 LED Rojo ON");
      sendResponseToESP1("ESP2 LED Rojo ON");
    }
    else if (comando == "ESP2_3") {
      digitalWrite(LED_ROJO, LOW);
      Serial.println("ESP2 LED Rojo OFF");
      sendResponseToESP1("ESP2 LED Rojo OFF");
    }
    else if (comando == "ESP2_4") {
      digitalWrite(LED_AMARILLO, HIGH);
      Serial.println("ESP2 LED Amarillo ON");
      sendResponseToESP1("ESP2 LED Amarillo ON");
    }
    else if (comando == "ESP2_5") {
      digitalWrite(LED_AMARILLO, LOW);
      Serial.println("ESP2 LED Amarillo OFF");
      sendResponseToESP1("ESP2 LED Amarillo OFF");
    }
  }
}

void sendResponseToESP1(String respuesta) {
  delay(50);  // Esperar que ESP1 termine de transmitir
  setRS485TransmitMode();
  delay(10);  // Tiempo para estabilizar
  
  RS485Serial.println("OK: " + respuesta);
  RS485Serial.flush();
  delay(50);  // Asegurar que se envíe completamente
  
  setRS485ReceiveMode();
  
  Serial.println("Respuesta enviada a ESP1: " + respuesta);
}

void sendToESP1(String comando) {
  Serial.println("ESP2 enviando a ESP1: " + comando);
  
  setRS485TransmitMode();
  delay(10);
  
  RS485Serial.println(comando);
  RS485Serial.flush();
  delay(10);
  
  setRS485ReceiveMode();
  delay(20);
  
  Serial.println("Mensaje enviado a ESP1");
}

// FIN DEL CÓDIGO SIMPLIFICADO ESP2
