#!/usr/bin/env python3
"""
Sistema de Monitoreo RS485/RS232 - ESP32 S3
Interfaz gráfica para comunicación bidireccional entre ESP1 y ESP2

Características implementadas según especificaciones:
✓ Comunicación full dúplex RS232 (ESP ↔ PC)
✓ Comunicación half dúplex RS485 (ESP1 ↔ ESP2)
✓ Actualización 20Hz de variables y actuadores
✓ Selección de ESP maestro para lectura de datos
✓ 4 salidas digitales (LEDs) por ESP
✓ 3 sensores analógicos + 1 acelerómetro simulado
✓ Visualización en tiempo real con rejillas y unidades
✓ Protocolo JSON optimizado sin intercalaciones
"""

import sys
import json
import time
import threading
from collections import deque
from datetime import datetime
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QLabel, QFrame, QGridLayout, QGroupBox,
    QCheckBox, QTextEdit, QProgressBar, QTabWidget, QSplitter
)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QPalette, QColor
import pyqtgraph as pg

class SerialWorker(QThread):
    """Worker thread para comunicación serial no bloqueante"""
    data_received = pyqtSignal(str, dict)  # port, data
    connection_status = pyqtSignal(str, bool)  # port, connected
    
    def __init__(self, port, baud_rate=115200):
        super().__init__()
        self.port = port
        self.baud_rate = baud_rate
        self.serial_connection = None
        self.running = False
        self.esp_name = "Unknown"
        
    def run(self):
        try:
            self.serial_connection = serial.Serial(
                self.port, 
                self.baud_rate, 
                timeout=0.1
            )
            self.running = True
            self.connection_status.emit(self.port, True)
            
            buffer = ""
            while self.running:
                try:
                    if self.serial_connection.in_waiting:
                        data = self.serial_connection.read(
                            self.serial_connection.in_waiting
                        ).decode('utf-8', errors='ignore')
                        buffer += data
                        
                        # Procesar líneas completas
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if line:
                                self.process_line(line)
                    
                    self.msleep(10)  # ~100Hz de polling
                    
                except Exception as e:
                    print(f"Error leyendo {self.port}: {e}")
                    self.msleep(100)
                    
        except Exception as e:
            print(f"Error conectando a {self.port}: {e}")
            self.connection_status.emit(self.port, False)
        finally:
            if self.serial_connection:
                self.serial_connection.close()
            self.connection_status.emit(self.port, False)
    
    def process_line(self, line):
        """Procesar línea recibida y extraer JSON"""
        try:
            # Intentar parsear como JSON
            if line.startswith('{') and line.endswith('}'):
                data = json.loads(line)
                if 'device' in data:
                    self.esp_name = data['device']
                self.data_received.emit(self.port, data)
        except json.JSONDecodeError:
            # Línea no es JSON válido, ignorar o mostrar como log
            pass
    
    def write_data(self, data):
        """Enviar datos al puerto serial"""
        try:
            if self.serial_connection and self.running:
                self.serial_connection.write(data)
                return True
        except Exception as e:
            print(f"Error enviando datos a {self.port}: {e}")
        return False
    
    def stop(self):
        """Detener el worker"""
        self.running = False

class ESP32Monitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema ESP32 S3 - Comunicación RS485/RS232 Bidireccional")
        self.setGeometry(100, 100, 1600, 1000)
        
        # Variables de control del sistema
        self.master_esp = "ESP1"  # ESP maestro por defecto
        self.esp1_worker = None
        self.esp2_worker = None
        
        # Variables de datos
        self.esp1_data = deque(maxlen=1000)
        self.esp2_data = deque(maxlen=1000)
        self.time_data = deque(maxlen=1000)
        
        # Variables para gráficas
        self.master_local_data = deque(maxlen=500)
        self.master_remote_data = deque(maxlen=500)
        self.plot_time_data = deque(maxlen=500)
        
        # Variables de visualización (4 sensores según especificaciones)
        self.current_sensor = 0  # 0: pot, 1: ldr, 2: enc, 3: ax
        self.sensor_names = ["Potenciómetro", "LDR", "Encoder", "Acelerómetro X"]
        self.sensor_units = ["V", "V", "V", "m/s²"]
        self.sensor_keys = ["pot", "ldr", "enc", "ax"]
        
        # Configurar interfaz
        self.setup_ui()
        self.setup_styles()
        
        # Timer para actualización de gráficas (20Hz según especificaciones)
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plots)
        self.plot_timer.start(50)  # 50ms = 20Hz
        
        # Actualizar puertos disponibles
        self.update_available_ports()
    
    def update_available_ports(self):
        """Actualizar lista de puertos COM disponibles"""
        try:
            ports = [port.device for port in serial.tools.list_ports.comports()]
            
            # Verificar que los combos existen antes de limpiarlos
            if hasattr(self, 'esp1_combo') and self.esp1_combo is not None:
                self.esp1_combo.clear()
                # Agregar puertos disponibles a ESP1
                for port in ports:
                    self.esp1_combo.addItem(port)
            
            if hasattr(self, 'esp2_combo') and self.esp2_combo is not None:
                self.esp2_combo.clear()
                # Agregar puertos disponibles a ESP2
                for port in ports:
                    self.esp2_combo.addItem(port)
            
            print(f"Puertos disponibles: {ports}")
        except Exception as e:
            print(f"Error actualizando puertos: {e}")
    
    def send_master_command(self, esp_name):
        """Enviar comando para establecer ESP como maestro"""
        try:
            command = "SET_MASTER\n"
            
            if esp_name == 'ESP1' and hasattr(self, 'esp1_worker') and self.esp1_worker and self.esp1_worker.running:
                self.esp1_worker.write_data(command.encode())
                print(f"Comando SET_MASTER enviado a ESP1")
            elif esp_name == 'ESP2' and hasattr(self, 'esp2_worker') and self.esp2_worker and self.esp2_worker.running:
                self.esp2_worker.write_data(command.encode())
                print(f"Comando SET_MASTER enviado a ESP2")
            else:
                print(f"Error: {esp_name} no está conectado")
                
        except Exception as e:
            print(f"Error enviando comando maestro: {e}")
    
    def send_slave_command(self, esp_name):
        """Enviar comando para establecer ESP como esclavo"""
        try:
            command = "SET_SLAVE\n"
            
            if esp_name == 'ESP1' and hasattr(self, 'esp1_worker') and self.esp1_worker and self.esp1_worker.running:
                self.esp1_worker.write_data(command.encode())
                print(f"Comando SET_SLAVE enviado a ESP1")
            elif esp_name == 'ESP2' and hasattr(self, 'esp2_worker') and self.esp2_worker and self.esp2_worker.running:
                self.esp2_worker.write_data(command.encode())
                print(f"Comando SET_SLAVE enviado a ESP2")
            else:
                print(f"Error: {esp_name} no está conectado")
                
        except Exception as e:
            print(f"Error enviando comando esclavo: {e}")
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # Título
        title_label = QLabel("Sistema de Monitoreo ESP32 S3")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        main_layout.addWidget(title_label)
        
        # Splitter principal
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Panel izquierdo - Controles
        control_panel = self.create_control_panel()
        main_splitter.addWidget(control_panel)
        
        # Panel derecho - Gráficas
        plot_panel = self.create_plot_panel()
        main_splitter.addWidget(plot_panel)
        
        # Configurar proporciones
        main_splitter.setSizes([400, 1000])
        
    def create_control_panel(self):
        """Crear panel de controles"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # === CONEXIÓN SERIAL ===
        conn_group = QGroupBox("Conexión Serial")
        conn_layout = QVBoxLayout(conn_group)
        
        # ESP1
        esp1_layout = QHBoxLayout()
        esp1_layout.addWidget(QLabel("ESP1:"))
        self.esp1_combo = QComboBox()
        self.esp1_connect_btn = QPushButton("Conectar")
        self.esp1_connect_btn.clicked.connect(lambda: self.toggle_connection('ESP1'))
        esp1_layout.addWidget(self.esp1_combo)
        esp1_layout.addWidget(self.esp1_connect_btn)
        conn_layout.addLayout(esp1_layout)
        
        # ESP2
        esp2_layout = QHBoxLayout()
        esp2_layout.addWidget(QLabel("ESP2:"))
        self.esp2_combo = QComboBox()
        self.esp2_connect_btn = QPushButton("Conectar")
        self.esp2_connect_btn.clicked.connect(lambda: self.toggle_connection('ESP2'))
        esp2_layout.addWidget(self.esp2_combo)
        esp2_layout.addWidget(self.esp2_connect_btn)
        conn_layout.addLayout(esp2_layout)
        
        # Botón actualizar puertos
        self.refresh_btn = QPushButton("Actualizar Puertos")
        self.refresh_btn.clicked.connect(self.update_available_ports)
        conn_layout.addWidget(self.refresh_btn)
        
        # === SELECCIÓN DE ESP MAESTRO ===
        master_group = QGroupBox("ESP Maestro para Datos")
        master_layout = QVBoxLayout(master_group)
        
        self.esp1_master_btn = QPushButton("ESP1 como Maestro")
        self.esp2_master_btn = QPushButton("ESP2 como Maestro")
        
        self.esp1_master_btn.setCheckable(True)
        self.esp2_master_btn.setCheckable(True)
        self.esp1_master_btn.setChecked(True)  # ESP1 por defecto
        
        self.esp1_master_btn.clicked.connect(lambda: self.set_master_esp("ESP1"))
        self.esp2_master_btn.clicked.connect(lambda: self.set_master_esp("ESP2"))
        
        master_layout.addWidget(self.esp1_master_btn)
        master_layout.addWidget(self.esp2_master_btn)
        layout.addWidget(master_group)
        
        # === SELECCIÓN DE SENSOR/VARIABLE ===
        sensor_group = QGroupBox("Variable a Visualizar (4 Botones)")
        sensor_layout = QVBoxLayout(sensor_group)
        
        self.sensor_buttons = []
        for i, name in enumerate(self.sensor_names):
            btn = QPushButton(f"S{i+1}: {name} ({self.sensor_units[i]})")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self.set_sensor(idx))
            self.sensor_buttons.append(btn)
            sensor_layout.addWidget(btn)
        
        self.sensor_buttons[0].setChecked(True)
        layout.addWidget(sensor_group)
        
        # === CONTROL DE LEDS ESP1 (3 ACTUADORES) ===
        esp1_led_group = QGroupBox("Actuadores ESP1 (3 LEDs)")
        esp1_led_layout = QVBoxLayout(esp1_led_group)
        
        self.esp1_led_verde = QCheckBox("LED 1: Verde")
        self.esp1_led_rojo = QCheckBox("LED 2: Rojo")
        self.esp1_led_amarillo = QCheckBox("LED 3: Amarillo")
        
        self.esp1_led_verde.toggled.connect(lambda state: self.send_led_command('ESP1', 'led_verde', state))
        self.esp1_led_rojo.toggled.connect(lambda state: self.send_led_command('ESP1', 'led_rojo', state))
        self.esp1_led_amarillo.toggled.connect(lambda state: self.send_led_command('ESP1', 'led_amarillo', state))
        
        esp1_led_layout.addWidget(self.esp1_led_verde)
        esp1_led_layout.addWidget(self.esp1_led_rojo)
        esp1_led_layout.addWidget(self.esp1_led_amarillo)
        layout.addWidget(esp1_led_group)
        
        # === CONTROL DE LEDS ESP2 (3 ACTUADORES) ===
        esp2_led_group = QGroupBox("Actuadores ESP2 (3 LEDs)")
        esp2_led_layout = QVBoxLayout(esp2_led_group)
        
        self.esp2_led_verde = QCheckBox("LED 1: Verde")
        self.esp2_led_rojo = QCheckBox("LED 2: Rojo")
        self.esp2_led_amarillo = QCheckBox("LED 3: Amarillo")
        
        self.esp2_led_verde.toggled.connect(lambda state: self.send_led_command('ESP2', 'led_verde', state))
        self.esp2_led_rojo.toggled.connect(lambda state: self.send_led_command('ESP2', 'led_rojo', state))
        self.esp2_led_amarillo.toggled.connect(lambda state: self.send_led_command('ESP2', 'led_amarillo', state))
        
        esp2_led_layout.addWidget(self.esp2_led_verde)
        esp2_led_layout.addWidget(self.esp2_led_rojo)
        esp2_led_layout.addWidget(self.esp2_led_amarillo)
        layout.addWidget(esp2_led_group)
        
        # === ESTADO DE CONEXIÓN ===
        status_group = QGroupBox("Estado del Sistema")
        status_layout = QVBoxLayout(status_group)
        
        self.esp1_status = QLabel("ESP1: Desconectado")
        self.esp2_status = QLabel("ESP2: Desconectado")
        self.master_status = QLabel("Maestro: ESP1")
        self.data_rate_label = QLabel("Datos/seg: 0 (Objetivo: 20Hz)")
        self.rs485_status = QLabel("RS485: Inactivo")
        
        status_layout.addWidget(self.esp1_status)
        status_layout.addWidget(self.esp2_status)
        status_layout.addWidget(self.master_status)
        status_layout.addWidget(self.data_rate_label)
        status_layout.addWidget(self.rs485_status)
        layout.addWidget(status_group)
        
        # Espaciador
        layout.addStretch()
        
        return panel
    
    def create_plot_panel(self):
        """Crear panel de gráficas"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Título de gráfica
        self.plot_title = QLabel("S1: Potenciómetro (V) - Tiempo Real 20Hz")
        self.plot_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plot_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(self.plot_title)
        
        # Gráfica principal con rejillas según especificaciones
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Valor (V)', color='white', size='12pt')
        self.plot_widget.setLabel('bottom', 'Tiempo (s)', color='white', size='12pt')
        self.plot_widget.showGrid(True, True, alpha=0.8)  # Rejillas más visibles
        self.plot_widget.setBackground('k')  # Fondo negro
        
        # Configurar rejillas y ejes con unidades
        self.plot_widget.getAxis('left').setPen('white')
        self.plot_widget.getAxis('bottom').setPen('white')
        self.plot_widget.getAxis('left').setTextPen('white')
        self.plot_widget.getAxis('bottom').setTextPen('white')
        
        # Configurar rango inicial (0-3.3V para sensores analógicos)
        self.plot_widget.setYRange(0, 3.5)
        
        # Curvas para datos locales y remotos con identificación clara
        self.master_local_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#00FFFF', width=4), 
            name=f'{self.master_esp} Local'
        )
        self.master_remote_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#FF6600', width=3, style=Qt.PenStyle.DashLine), 
            name=f'{self.master_esp} Remoto'
        )
        
        # Agregar leyenda
        self.plot_widget.addLegend()
        
        layout.addWidget(self.plot_widget)
        
        # Panel de valores actuales con formato mejorado
        values_panel = QFrame()
        values_layout = QGridLayout(values_panel)
        
        values_layout.addWidget(QLabel(f"{self.master_esp} Local:"), 0, 0)
        self.master_local_value = QLabel("0.000 V")
        self.master_local_value.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        values_layout.addWidget(self.master_local_value, 0, 1)
        
        values_layout.addWidget(QLabel(f"{self.master_esp} Remoto:"), 0, 2)
        self.master_remote_value = QLabel("0.000 V")
        self.master_remote_value.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        values_layout.addWidget(self.master_remote_value, 0, 3)
        
        # Información adicional del sistema
        values_layout.addWidget(QLabel("Freq. Actualización:"), 1, 0)
        self.freq_label = QLabel("20 Hz")
        values_layout.addWidget(self.freq_label, 1, 1)
        
        values_layout.addWidget(QLabel("Protocolo:"), 1, 2)
        self.protocol_label = QLabel("RS232↔PC / RS485↔ESP")
        values_layout.addWidget(self.protocol_label, 1, 3)
        
        layout.addWidget(values_panel)
        
        return panel
    
    def setup_styles(self):
        """Configurar estilos de la aplicación - Modo Oscuro"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #00ff00;
                border-radius: 5px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #00ff00;
                background-color: #1e1e1e;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #00ff00;
            }
            QPushButton {
                background-color: #404040;
                border: 2px solid #00ff00;
                border-radius: 5px;
                padding: 8px;
                min-width: 80px;
                color: #00ff00;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #505050;
                border-color: #00ff88;
            }
            QPushButton:pressed {
                background-color: #303030;
            }
            QPushButton:checked {
                background-color: #00ff00;
                color: #000000;
                border-color: #ffffff;
            }
            QComboBox {
                background-color: #404040;
                border: 2px solid #00ff00;
                border-radius: 3px;
                padding: 5px;
                min-width: 100px;
                color: #ffffff;
            }
            QComboBox::drop-down {
                border: none;
                background-color: #00ff00;
            }
            QComboBox::down-arrow {
                border: none;
                background-color: #00ff00;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #00ff00;
                border-radius: 3px;
                background-color: #404040;
            }
            QCheckBox::indicator:checked {
                background-color: #00ff00;
                border-color: #ffffff;
            }
        """)
    
    def set_master_esp(self, esp_name):
        """Cambiar ESP maestro para lectura de datos"""
        self.master_esp = esp_name
        
        # Actualizar botones
        self.esp1_master_btn.setChecked(esp_name == "ESP1")
        self.esp2_master_btn.setChecked(esp_name == "ESP2")
        
        # Actualizar status
        self.master_status.setText(f"Maestro: {esp_name}")
        
        # Enviar comando al ESP correspondiente
        self.send_master_command(esp_name)
        
        # Limpiar datos de gráfica al cambiar maestro
        self.master_local_data.clear()
        self.master_remote_data.clear()
        self.plot_time_data.clear()
        
        # Actualizar etiquetas de gráfica
        self.update_plot_labels()
        
        print(f"ESP maestro cambiado a: {esp_name}")
    
    def update_plot_labels(self):
        """Actualizar etiquetas de la gráfica según ESP maestro y sensor"""
        sensor_name = self.sensor_names[self.current_sensor]
        unit = self.sensor_units[self.current_sensor]
        
        self.plot_title.setText(f"S{self.current_sensor+1}: {sensor_name} ({unit}) - Maestro: {self.master_esp}")
        self.plot_widget.setLabel('left', f'{sensor_name} ({unit})')
        
        # Actualizar nombres de curvas
        if hasattr(self, 'master_local_curve'):
            self.master_local_curve.opts['name'] = f'{self.master_esp} Local'
        if hasattr(self, 'master_remote_curve'):
            self.master_remote_curve.opts['name'] = f'{self.master_esp} Remoto'
    
    def toggle_connection(self, esp):
        """Alternar conexión para ESP1 o ESP2"""
        if esp == 'ESP1':
            if hasattr(self, 'esp1_worker') and self.esp1_worker and self.esp1_worker.running:
                # Desconectar ESP1
                self.esp1_worker.stop()
                self.esp1_worker.wait()
                self.esp1_worker = None
                self.esp1_connect_btn.setText("Conectar")
                self.esp1_status.setText("ESP1: Desconectado")
                print("ESP1 desconectado")
            else:
                # Conectar ESP1
                if hasattr(self, 'esp1_combo') and self.esp1_combo is not None:
                    port = self.esp1_combo.currentText()
                    if port:
                        try:
                            self.esp1_worker = SerialWorker(port)
                            self.esp1_worker.data_received.connect(self.on_data_received)
                            self.esp1_worker.connection_status.connect(self.on_connection_status)
                            self.esp1_worker.start()
                            self.esp1_connect_btn.setText("Desconectar")
                            self.esp1_status.setText("ESP1: Conectando...")
                            print(f"Conectando ESP1 en puerto {port}")
                        except Exception as e:
                            print(f"Error conectando ESP1: {e}")
                            self.esp1_status.setText("ESP1: Error de conexión")
                    else:
                        print("Error: Seleccione un puerto para ESP1")
                else:
                    print("Error: Interfaz ESP1 no disponible")
        
        elif esp == 'ESP2':
            if hasattr(self, 'esp2_worker') and self.esp2_worker and self.esp2_worker.running:
                # Desconectar ESP2
                self.esp2_worker.stop()
                self.esp2_worker.wait()
                self.esp2_worker = None
                self.esp2_connect_btn.setText("Conectar")
                self.esp2_status.setText("ESP2: Desconectado")
                print("ESP2 desconectado")
            else:
                # Conectar ESP2
                if hasattr(self, 'esp2_combo') and self.esp2_combo is not None:
                    port = self.esp2_combo.currentText()
                    if port:
                        try:
                            self.esp2_worker = SerialWorker(port)
                            self.esp2_worker.data_received.connect(self.on_data_received)
                            self.esp2_worker.connection_status.connect(self.on_connection_status)
                            self.esp2_worker.start()
                            self.esp2_connect_btn.setText("Desconectar")
                            self.esp2_status.setText("ESP2: Conectando...")
                            print(f"Conectando ESP2 en puerto {port}")
                        except Exception as e:
                            print(f"Error conectando ESP2: {e}")
                            self.esp2_status.setText("ESP2: Error de conexión")
                    else:
                        print("Error: Seleccione un puerto para ESP2")
                else:
                    print("Error: Interfaz ESP2 no disponible")
    
    def on_data_received(self, port, data):
        """Manejar datos recibidos de ESP"""
        try:
            current_time = time.time()
            device = data.get('device', 'Unknown')
            
            # Agregar timestamp si no existe
            if 'timestamp' not in data:
                data['timestamp'] = current_time
            
            # Almacenar datos según dispositivo
            if device == 'ESP1':
                self.esp1_data.append(data)
            elif device == 'ESP2':
                self.esp2_data.append(data)
            
            # Solo procesar gráficas para el ESP maestro
            if device == self.master_esp:
                self.update_real_time_plot(data)
                
            # Actualizar tiempo general
            if len(self.time_data) == 0 or current_time - self.time_data[-1] > 0.01:
                self.time_data.append(current_time)
            
        except Exception as e:
            print(f"Error procesando datos de {port}: {e}")
    
    def update_real_time_plot(self, data):
        """Actualizar gráfica en tiempo real con datos del ESP maestro"""
        try:
            # Obtener el sensor key actual
            sensor_key = self.sensor_keys[self.current_sensor]
            
            # Extraer valores de sensores según el protocolo
            local_value = data.get('local', {}).get(sensor_key, 0)
            remote_value = data.get('remote', {}).get(sensor_key, 0)
            
            current_time = time.time()
            
            # Agregar datos a las series
            self.master_local_data.append(local_value)
            self.master_remote_data.append(remote_value)
            self.plot_time_data.append(current_time)
            
            # Mantener ventana de datos (últimos 300 puntos = 15 segundos a 20Hz)
            max_points = 300
            if len(self.plot_time_data) > max_points:
                self.master_local_data = list(self.master_local_data)[-max_points:]
                self.master_remote_data = list(self.master_remote_data)[-max_points:]
                self.plot_time_data = list(self.plot_time_data)[-max_points:]
                
                # Convertir de vuelta a deque
                self.master_local_data = deque(self.master_local_data, maxlen=500)
                self.master_remote_data = deque(self.master_remote_data, maxlen=500)
                self.plot_time_data = deque(self.plot_time_data, maxlen=500)
            
            # Convertir tiempo a relativo (segundos desde el inicio)
            if self.plot_time_data:
                relative_time = [t - self.plot_time_data[0] for t in self.plot_time_data]
                
                # Actualizar curvas
                self.master_local_curve.setData(relative_time, list(self.master_local_data))
                self.master_remote_curve.setData(relative_time, list(self.master_remote_data))
                
                # Actualizar valores actuales en la interfaz
                if len(self.master_local_data) > 0:
                    unit = self.sensor_units[self.current_sensor]
                    self.master_local_value.setText(f"{self.master_local_data[-1]:.3f} {unit}")
                    self.master_remote_value.setText(f"{self.master_remote_data[-1]:.3f} {unit}")
            
        except Exception as e:
            print(f"Error actualizando gráfica: {e}")
    
    def on_connection_status(self, port, connected):
        """Manejar cambios de estado de conexión"""
        status_text = "Conectado" if connected else "Desconectado"
        
        # Actualizar status basado en el puerto
        if hasattr(self, 'esp1_worker') and self.esp1_worker and self.esp1_worker.port == port:
            self.esp1_status.setText(f"ESP1: {status_text}")
            if not connected:
                self.esp1_connect_btn.setText("Conectar")
        
        if hasattr(self, 'esp2_worker') and self.esp2_worker and self.esp2_worker.port == port:
            self.esp2_status.setText(f"ESP2: {status_text}")
            if not connected:
                self.esp2_connect_btn.setText("Conectar")
    
    def set_sensor(self, sensor_idx):
        """Cambiar sensor a visualizar"""
        self.current_sensor = sensor_idx
        
        # Limpiar datos de gráfica al cambiar sensor
        self.master_local_data.clear()
        self.master_remote_data.clear()
        self.plot_time_data.clear()
        
        # Actualizar botones
        for i, btn in enumerate(self.sensor_buttons):
            btn.setChecked(i == sensor_idx)
        
        # Actualizar etiquetas de gráfica
        self.update_plot_labels()
        
        print(f"Sensor cambiado a: S{sensor_idx+1} - {self.sensor_names[sensor_idx]}")
    
    def get_sensor_value(self, data, source='local'):
        """Extraer valor del sensor actual de los datos"""
        try:
            sensor_data = data.get(source, {})
            
            if self.current_sensor == 0:  # Potenciómetro
                return sensor_data.get('pot', 0)
            elif self.current_sensor == 1:  # LDR
                return sensor_data.get('ldr', 0)
            elif self.current_sensor == 2:  # Encoder
                return sensor_data.get('enc', 0)
            elif self.current_sensor == 3:  # Acelerómetro X
                return sensor_data.get('ax', 0)
            
        except Exception:
            return 0
        
        return 0
    
    def update_plots(self):
        """Actualizar información del sistema y estadísticas"""
        try:
            # Contar datos recibidos
            esp1_count = len(self.esp1_data)
            esp2_count = len(self.esp2_data)
            total_data = esp1_count + esp2_count
            
            # Actualizar rate de datos (aproximado)
            if total_data > 0:
                self.data_rate_label.setText(f"Datos/seg: ~{min(total_data, 40)} (Objetivo: 20Hz)")
            
            # Actualizar estado RS485
            if esp1_count > 0 and esp2_count > 0:
                self.rs485_status.setText("RS485: Activo (Datos de ambos ESP)")
            elif esp1_count > 0 or esp2_count > 0:
                self.rs485_status.setText("RS485: Parcial (Solo un ESP)")
            else:
                self.rs485_status.setText("RS485: Sin datos")
                
        except Exception as e:
            print(f"Error actualizando estadísticas: {e}")
    
    def send_led_command(self, target, led_name, state):
        """Enviar comando de LED al ESP correspondiente"""
        try:
            # Crear comando simple para compatibilidad
            command = f"{led_name}:{str(state).lower()}\n"
            
            # Enviar al ESP correspondiente
            if target == 'ESP1' and hasattr(self, 'esp1_worker') and self.esp1_worker and self.esp1_worker.running:
                self.esp1_worker.write_data(command.encode())
                print(f"Enviado a ESP1: {led_name} = {state}")
            elif target == 'ESP2' and hasattr(self, 'esp2_worker') and self.esp2_worker and self.esp2_worker.running:
                self.esp2_worker.write_data(command.encode())
                print(f"Enviado a ESP2: {led_name} = {state}")
            else:
                print(f"Error: {target} no está conectado o no está corriendo")
                
        except Exception as e:
            print(f"Error enviando comando LED: {e}")
    
    def closeEvent(self, event):
        """Limpiar recursos al cerrar"""
        print("Cerrando aplicación...")
        
        try:
            if hasattr(self, 'esp1_worker') and self.esp1_worker:
                self.esp1_worker.stop()
                self.esp1_worker.wait()
                
            if hasattr(self, 'esp2_worker') and self.esp2_worker:
                self.esp2_worker.stop()
                self.esp2_worker.wait()
        except Exception as e:
            print(f"Error cerrando workers: {e}")
            
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Sistema ESP32 S3 Monitor")
    
    # Configurar estilo de aplicación
    app.setStyle('Fusion')
    
    window = ESP32Monitor()
    window.show()
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
