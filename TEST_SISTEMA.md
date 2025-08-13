# PRUEBAS DEL SISTEMA ESP32 MAESTRO/ESCLAVO

## CAMBIOS REALIZADOS

### 1. CÓDIGO ESP32 - SISTEMA MAESTRO/ESCLAVO
- **ESP1**: Maestro por defecto, ESP2: Esclavo por defecto
- **REGLA**: Solo el ESP MAESTRO envía datos JSON continuos
- **Comandos de rol**:
  - `SET_MASTER` - Convertir ESP en maestro
  - `SET_SLAVE` - Convertir ESP en esclavo
- **LEDs restaurados**: `led_verde:true`, `led_rojo:false`, `led_amarillo:true`

### 2. INTERFAZ PYTHON CORREGIDA
- Corregido error "QComboBox has been deleted"
- Comando de LEDs simplificado para compatibilidad total
- Botones maestro/esclavo envían comandos SET_MASTER/SET_SLAVE

## PRUEBAS CON MONITOR SERIAL

### Paso 1: Verificar ESP1 (Maestro por defecto)
```
1. Abrir Monitor Serial Arduino IDE → ESP1
2. Deberías ver datos JSON cada 50ms
3. Probar comando: SET_SLAVE
4. Los datos JSON deben detenerse
5. Probar comando: SET_MASTER
6. Los datos JSON deben continuar
```

### Paso 2: Verificar LEDs en ESP1
```
1. Enviar: led_verde:true
2. LED verde debe encender
3. Enviar: led_verde:false
4. LED verde debe apagar
5. Probar con led_rojo y led_amarillo
```

### Paso 3: Verificar ESP2 (Esclavo por defecto)
```
1. Abrir Monitor Serial Arduino IDE → ESP2
2. NO deberías ver datos JSON (es esclavo)
3. Probar comando: SET_MASTER
4. Los datos JSON deben comenzar
5. Probar LEDs igual que ESP1
```

### Paso 4: Verificar Comunicación RS485
```
1. ESP1 como maestro, ESP2 como esclavo
2. ESP1 debe enviar datos locales + remotos de ESP2
3. Cambiar ESP2 a maestro
4. ESP2 debe enviar datos locales + remotos de ESP1
```

## COMANDOS DE PRUEBA

### Comandos de Rol:
- `SET_MASTER` → Convertir en maestro (envía datos)
- `SET_SLAVE` → Convertir en esclavo (solo escucha)

### Comandos de LEDs (Simples):
- `led_verde:true` → Encender LED verde
- `led_verde:false` → Apagar LED verde
- `led_rojo:true` → Encender LED rojo
- `led_rojo:false` → Apagar LED rojo
- `led_amarillo:true` → Encender LED amarillo
- `led_amarillo:false` → Apagar LED amarillo

### Comandos JSON (Retrocompatibilidad):
```json
{"led_verde":true}
{"led_rojo":false}
{"led_amarillo":true}
```

## INTERFAZ PYTHON

### Para probar la interfaz:
```bash
cd Interfaz
python esp32_monitor.py
```

### Verificaciones:
1. Los puertos COM aparecen sin error
2. Conexión exitosa a ESP
3. Botones maestro/esclavo funcionan
4. Control de LEDs funciona
5. Gráficas muestran datos del ESP maestro únicamente

## SOLUCIONES IMPLEMENTADAS

### Problema 1: Error QComboBox
- **Causa**: Referencias a widgets eliminados
- **Solución**: Verificación `hasattr()` antes de acceder

### Problema 2: Ambos ESP enviando datos
- **Causa**: No había sistema maestro/esclavo
- **Solución**: Variable `is_master` y comandos SET_MASTER/SET_SLAVE

### Problema 3: LEDs no funcionaban
- **Causa**: Formato JSON complejo
- **Solución**: Comandos simples `led_verde:true` + retrocompatibilidad JSON

## ESTADO ACTUAL
✅ Sistema maestro/esclavo implementado
✅ Solo ESP maestro envía datos (sin intercalaciones)
✅ LEDs funcionan con comandos simples
✅ Interfaz corregida (sin errores QComboBox)
✅ Comunicación RS485 entre ESP
✅ Retrocompatibilidad con comandos JSON

**SISTEMA LISTO PARA PRUEBAS CON HARDWARE**
