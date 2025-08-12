# CONEXIONES DEL SISTEMA RS485

## ESPECIFICACIONES TÉCNICAS

### Módulos RS485 utilizados:
- **Transceiver**: MAX485 o similar
- **Modo**: Half-duplex (2 cables para comunicación)
- **Velocidad**: 9600 baudios
- **Voltaje**: 3.3V/5V compatible

---

## CONEXIONES FÍSICAS

### ESP1 Principal ↔ Módulo RS485 #1
```
ESP1 Pin  →  Módulo RS485 #1
36 (DI)   →  DI (Driver Input)
37 (DE)   →  DE (Driver Enable)
38 (RE)   →  RE (Receiver Enable) 
39 (RO)   →  RO (Receiver Output)
3.3V      →  VCC
GND       →  GND
```

### ESP2 Secundario ↔ Módulo RS485 #2
```
ESP2 Pin  →  Módulo RS485 #2
36 (DI)   →  DI (Driver Input)
37 (DE)   →  DE (Driver Enable)
38 (RE)   →  RE (Receiver Enable)
39 (RO)   →  RO (Receiver Output)
3.3V      →  VCC
GND       →  GND
```

### Conexión entre Módulos RS485
```
Módulo RS485 #1  ↔  Módulo RS485 #2
A+               ↔  A+
B-               ↔  B-
```

**IMPORTANTE**: Solo necesitas **2 cables** entre los módulos RS485:
- Cable A+ a A+
- Cable B- a B-

---

## CONEXIONES DE SENSORES

### ESP1 Principal:
```
Pin 6  →  Potenciómetro (señal)
Pin 7  →  LDR (señal)
Pin 8  →  Encoder (señal)
3.3V   →  VCC sensores
GND    →  GND sensores
```

### ESP2 Secundario:
```
Pin 6  →  Potenciómetro (señal)
Pin 7  →  LDR (señal)
Pin 8  →  Encoder (señal)
3.3V   →  VCC sensores
GND    →  GND sensores
```

---

## CONEXIONES DE LEDs

### ESP1 Principal:
```
Pin 19  →  LED Amarillo (ánodo) → Resistencia 220Ω → GND
Pin 20  →  LED Rojo (ánodo) → Resistencia 220Ω → GND
Pin 21  →  LED Verde (ánodo) → Resistencia 220Ω → GND
```

### ESP2 Secundario:
```
Pin 19  →  LED Amarillo (ánodo) → Resistencia 220Ω → GND
Pin 20  →  LED Rojo (ánodo) → Resistencia 220Ω → GND
Pin 21  →  LED Verde (ánodo) → Resistencia 220Ω → GND
```

---

## PRUEBAS INICIALES

### 1. Test de LEDs individuales
Conecta solo un ESP y carga el código. En el Serial Monitor:
```
TEST           // Prueba todos los LEDs
LED1_ON        // Enciende LED Verde
LED1_OFF       // Apaga LED Verde
LED2_ON        // Enciende LED Rojo
LED3_ON        // Enciende LED Amarillo
```

### 2. Test de comunicación RS485
1. **Conecta ambos ESP** con RS485
2. **Abre Serial Monitor del ESP1**
3. **Envía comando**: `ESP2_LED1_ON`
4. **Verifica**: LED verde del ESP2 debe encender

### 3. Test de sensores
Mueve los sensores y verifica en Serial Monitor:
```
ESP1:1234,2345,3456;ESP2:4567,5678,6789
```

---

## DIAGNÓSTICO DE PROBLEMAS

### Si no funciona RS485:
1. **Verificar conexiones A+ y B-**
2. **Verificar alimentación de módulos RS485**
3. **Verificar pines DE/RE conectados correctamente**
4. **Verificar GND común entre ambos sistemas**

### Si no encienden LEDs:
1. **Verificar resistencias en serie**
2. **Verificar polaridad de LEDs**
3. **Probar comando TEST primero**

### Si no leen sensores:
1. **Verificar alimentación de sensores**
2. **Verificar conexiones de señal**
3. **Verificar que sean sensores analógicos**

---

## COMANDOS DISPONIBLES

### Para ESP1 (directo):
- `TEST` - Prueba LEDs
- `LED1_ON/LED1_OFF` - Control LED Verde
- `LED2_ON/LED2_OFF` - Control LED Rojo  
- `LED3_ON/LED3_OFF` - Control LED Amarillo

### Para ESP2 (via RS485):
- `ESP2_TEST` - Prueba LEDs ESP2
- `ESP2_LED1_ON/ESP2_LED1_OFF` - Control LED Verde ESP2
- `ESP2_LED2_ON/ESP2_LED2_OFF` - Control LED Rojo ESP2
- `ESP2_LED3_ON/ESP2_LED3_OFF` - Control LED Amarillo ESP2
