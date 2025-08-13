#!/usr/bin/env python3
"""
Sistema ESP32 S3 - Interfaz DISTRIBUIDA RS485/RS232
Comunicación bidireccional entre ESP1 y ESP2 con soporte multi-computadora

CARACTERÍSTICAS PRINCIPALES:
✓ Modo LOCAL: Una PC controla ambos ESP (tradicional)
✓ Modo DISTRIBUIDO: Cada PC controla un ESP, comunicación RS485
✓ Conexión serial robusta a ESP32
✓ Control maestro/esclavo desde interfaz
✓ LEDs remotos via RS485 (ESP1 ↔ ESP2)
✓ Gráficas en tiempo real optimizadas
✓ Visualización de 4 sensores
✓ Protocolo JSON a 20Hz
✓ Auto-detección de ESP local en modo distribuido
"""

import sys
import json
import time
from collections import deque
import serial
import serial.tools.list_ports
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QLabel, QFrame, QGridLayout, QGroupBox,
    QCheckBox, QSplitter, QTabWidget, QRadioButton, QLineEdit, QScrollArea
)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import pyqtgraph as pg

class SerialWorker(QThread):
    """Worker thread para comunicación serial robusta"""
    data_received = pyqtSignal(str, dict)
    connection_status = pyqtSignal(str, bool)
    debug_message = pyqtSignal(str)
    
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
                self.port, self.baud_rate, timeout=0.1
            )
            self.running = True
            self.connection_status.emit(self.port, True)
            self.debug_message.emit(f"✓ Conectado a {self.port}")
            
            buffer = ""
            while self.running:
                try:
                    if self.serial_connection.in_waiting:
                        data = self.serial_connection.read(
                            self.serial_connection.in_waiting
                        ).decode('utf-8', errors='ignore')
                        buffer += data
                        
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if line:
                                self.process_line(line)
                    
                    self.msleep(5)  # 200Hz polling
                    
                except Exception as e:
                    self.debug_message.emit(f"Error leyendo {self.port}: {e}")
                    self.msleep(100)
                    
        except Exception as e:
            self.debug_message.emit(f"Error conectando a {self.port}: {e}")
            self.connection_status.emit(self.port, False)
        finally:
            if self.serial_connection:
                self.serial_connection.close()
            self.connection_status.emit(self.port, False)
    
    def process_line(self, line):
        """Procesar línea y extraer JSON"""
        try:
            if line.startswith('{') and line.endswith('}'):
                data = json.loads(line)
                if 'device' in data:
                    self.esp_name = data['device']
                self.data_received.emit(self.port, data)
            elif "LED" in line or "Datos recibidos" in line:
                self.debug_message.emit(f"{self.esp_name}: {line}")
        except json.JSONDecodeError:
            pass
    
    def write_data(self, data):
        """Enviar datos al puerto serial"""
        try:
            if self.serial_connection and self.running:
                self.serial_connection.write(data)
                return True
        except Exception as e:
            self.debug_message.emit(f"Error enviando a {self.port}: {e}")
        return False
    
    def stop(self):
        self.running = False

class ESP32Interface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema ESP32 S3 - Control RS485/RS232 [DISTRIBUIDO]")
        self.setGeometry(100, 100, 1900, 1000)
        
        # Variables del sistema
        self.esp1_worker = None
        self.esp2_worker = None
        self.master_esp = "ESP1"
        
        # Variables para modo distribuido
        self.operation_mode = "LOCAL"  # LOCAL o DISTRIBUIDO
        self.local_esp = None  # ESP conectado localmente
        self.remote_ip = "192.168.1.100"  # IP de la otra computadora
        
        # Datos para gráficas (optimizados)
        self.plot_data_local = deque(maxlen=300)   # 15 segundos a 20Hz
        self.plot_data_remote = deque(maxlen=300)
        self.plot_time = deque(maxlen=300)
        
        # Sensores disponibles - ACTUALIZADO con MPU6050
        self.sensors = ["pot", "ldr", "enc", "ax", "ay", "az", "gx", "gy", "gz", "temp"]
        self.sensor_names = [
            "Potenciómetro", "LDR", "Encoder", 
            "Acelerómetro X", "Acelerómetro Y", "Acelerómetro Z",
            "Giroscopio X", "Giroscopio Y", "Giroscopio Z",
            "Temperatura MPU"
        ]
        self.sensor_units = [
            "V", "V", "V", 
            "g", "g", "g", 
            "°/s", "°/s", "°/s",
            "°C"
        ]
        self.current_sensor = 0
        
        # Configurar UI
        self.setup_ui()
        self.setup_styles()
        
        # Timer para actualización
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(50)  # 20Hz
        
        # Cargar puertos disponibles
        self.refresh_ports()
    
    def setup_ui(self):
        """Configurar interfaz de usuario"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Panel de control izquierdo
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # Panel de gráficas derecho
        plot_panel = self.create_plot_panel()
        main_layout.addWidget(plot_panel)
        
        # Proporción 30-70
        main_layout.setStretch(0, 30)
        main_layout.setStretch(1, 70)
    
    def create_control_panel(self):
        """Panel de controles"""
        panel = QWidget()
        panel.setMaximumWidth(500)
        layout = QVBoxLayout(panel)
        
        # Título
        title = QLabel("Control ESP32 S3 [DISTRIBUIDO]")
        title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # === MODO DE OPERACIÓN ===
        mode_group = QGroupBox("Modo de Operación")
        mode_layout = QVBoxLayout(mode_group)
        
        self.local_mode_btn = QRadioButton("Modo LOCAL (1 PC, 2 ESP)")
        self.distributed_mode_btn = QRadioButton("Modo DISTRIBUIDO (2 PC, 1 ESP c/u)")
        self.local_mode_btn.setChecked(True)
        
        self.local_mode_btn.toggled.connect(lambda: self.set_operation_mode("LOCAL"))
        self.distributed_mode_btn.toggled.connect(lambda: self.set_operation_mode("DISTRIBUIDO"))
        
        mode_layout.addWidget(self.local_mode_btn)
        mode_layout.addWidget(self.distributed_mode_btn)
        
        # # IP de la otra computadora (solo para modo distribuido)
        # ip_layout = QHBoxLayout()
        # ip_layout.addWidget(QLabel("IP otra PC:"))
        # self.remote_ip_input = QLineEdit("192.168.1.100")
        # self.remote_ip_input.setEnabled(False)
        # ip_layout.addWidget(self.remote_ip_input)
        # mode_layout.addLayout(ip_layout)
        
        layout.addWidget(mode_group)
        
        # === CONEXIONES ===
        conn_group = QGroupBox("Conexiones Serial")
        conn_layout = QVBoxLayout(conn_group)
        
        # ESP1
        esp1_layout = QHBoxLayout()
        esp1_layout.addWidget(QLabel("ESP1:"))
        self.esp1_combo = QComboBox()
        self.esp1_btn = QPushButton("Conectar")
        self.esp1_btn.clicked.connect(lambda: self.toggle_connection('ESP1'))
        esp1_layout.addWidget(self.esp1_combo)
        esp1_layout.addWidget(self.esp1_btn)
        conn_layout.addLayout(esp1_layout)
        
        # ESP2
        esp2_layout = QHBoxLayout()
        esp2_layout.addWidget(QLabel("ESP2:"))
        self.esp2_combo = QComboBox()
        self.esp2_btn = QPushButton("Conectar")
        self.esp2_btn.clicked.connect(lambda: self.toggle_connection('ESP2'))
        esp2_layout.addWidget(self.esp2_combo)
        esp2_layout.addWidget(self.esp2_btn)
        conn_layout.addLayout(esp2_layout)
        
        # Refresh
        refresh_btn = QPushButton("🔄 Actualizar Puertos")
        refresh_btn.clicked.connect(self.refresh_ports)
        conn_layout.addWidget(refresh_btn)
        
        layout.addWidget(conn_group)
        
        # === MAESTRO/ESCLAVO ===
        master_group = QGroupBox("Control Maestro/Esclavo")
        master_layout = QVBoxLayout(master_group)
        
        self.esp1_master_btn = QPushButton("ESP1 como Maestro")
        self.esp2_master_btn = QPushButton("ESP2 como Maestro")
        
        self.esp1_master_btn.setCheckable(True)
        self.esp2_master_btn.setCheckable(True)
        self.esp1_master_btn.setChecked(True)
        
        self.esp1_master_btn.clicked.connect(lambda: self.set_master("ESP1"))
        self.esp2_master_btn.clicked.connect(lambda: self.set_master("ESP2"))
        
        master_layout.addWidget(self.esp1_master_btn)
        master_layout.addWidget(self.esp2_master_btn)
        layout.addWidget(master_group)
        
        # === SELECCIÓN DE SENSORES ===
        sensor_group = QGroupBox("Sensores (MPU6050 Integrado)")
        sensor_main_layout = QVBoxLayout(sensor_group)
        
        # Crear área de scroll para los sensores
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(250)  # Altura fija para el área de scroll
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        # Widget contenedor para los sensores dentro del scroll
        sensor_scroll_widget = QWidget()
        sensor_layout = QVBoxLayout(sensor_scroll_widget)
        sensor_layout.setSpacing(5)  # Reducir espaciado entre botones
        
        # Sensores analógicos
        analog_label = QLabel("📊 Sensores Analógicos:")
        analog_label.setStyleSheet("color: #00ff88; font-weight: bold; margin-top: 5px;")
        sensor_layout.addWidget(analog_label)
        
        self.sensor_buttons = []
        # Primeros 3 botones para sensores analógicos
        for i in range(3):
            name, unit = self.sensor_names[i], self.sensor_units[i]
            btn = QPushButton(f"S{i+1}: {name} ({unit})")
            btn.setCheckable(True)
            btn.setMinimumHeight(30)  # Altura mínima para los botones
            btn.clicked.connect(lambda checked, idx=i: self.set_sensor(idx))
            self.sensor_buttons.append(btn)
            sensor_layout.addWidget(btn)
        
        # Separador para MPU6050
        mpu_label = QLabel("🎯 MPU6050 (6-DOF):")
        mpu_label.setStyleSheet("color: #ff8800; font-weight: bold; margin-top: 10px;")
        sensor_layout.addWidget(mpu_label)
        
        # Acelerómetro
        accel_sublabel = QLabel("   📈 Acelerómetro:")
        accel_sublabel.setStyleSheet("color: #ffff00; font-size: 10px; margin-left: 10px;")
        sensor_layout.addWidget(accel_sublabel)
        
        for i in range(3, 6):  # ax, ay, az
            name, unit = self.sensor_names[i], self.sensor_units[i]
            btn = QPushButton(f"S{i+1}: {name} ({unit})")
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.clicked.connect(lambda checked, idx=i: self.set_sensor(idx))
            self.sensor_buttons.append(btn)
            sensor_layout.addWidget(btn)
            
        # Giroscopio
        gyro_sublabel = QLabel("   🌀 Giroscopio:")
        gyro_sublabel.setStyleSheet("color: #ffff00; font-size: 10px; margin-left: 10px;")
        sensor_layout.addWidget(gyro_sublabel)
        
        for i in range(6, 9):  # gx, gy, gz
            name, unit = self.sensor_names[i], self.sensor_units[i]
            btn = QPushButton(f"S{i+1}: {name} ({unit})")
            btn.setCheckable(True)
            btn.setMinimumHeight(30)
            btn.clicked.connect(lambda checked, idx=i: self.set_sensor(idx))
            self.sensor_buttons.append(btn)
            sensor_layout.addWidget(btn)
            
        # Temperatura
        temp_sublabel = QLabel("   🌡️ Temperatura:")
        temp_sublabel.setStyleSheet("color: #ffff00; font-size: 10px; margin-left: 10px;")
        sensor_layout.addWidget(temp_sublabel)
        
        name, unit = self.sensor_names[9], self.sensor_units[9]
        btn = QPushButton(f"S10: {name} ({unit})")
        btn.setCheckable(True)
        btn.setMinimumHeight(30)
        btn.clicked.connect(lambda checked, idx=9: self.set_sensor(idx))
        self.sensor_buttons.append(btn)
        sensor_layout.addWidget(btn)
        
        # Agregar algo de espaciado al final
        sensor_layout.addStretch()
        
        # Configurar el scroll area
        scroll_area.setWidget(sensor_scroll_widget)
        sensor_main_layout.addWidget(scroll_area)
        
        self.sensor_buttons[0].setChecked(True)
        layout.addWidget(sensor_group)
        
        # === LEDs ESP1 ===
        esp1_led_group = QGroupBox("LEDs ESP1")
        esp1_led_layout = QVBoxLayout(esp1_led_group)
        
        self.esp1_verde = QCheckBox("🟢 LED Verde")
        self.esp1_rojo = QCheckBox("🔴 LED Rojo")
        self.esp1_amarillo = QCheckBox("🟡 LED Amarillo")
        
        self.esp1_verde.toggled.connect(lambda s: self.send_led_command('ESP1', 'led_verde', s))
        self.esp1_rojo.toggled.connect(lambda s: self.send_led_command('ESP1', 'led_rojo', s))
        self.esp1_amarillo.toggled.connect(lambda s: self.send_led_command('ESP1', 'led_amarillo', s))
        
        esp1_led_layout.addWidget(self.esp1_verde)
        esp1_led_layout.addWidget(self.esp1_rojo)
        esp1_led_layout.addWidget(self.esp1_amarillo)
        layout.addWidget(esp1_led_group)
        
        # === LEDs ESP2 ===
        esp2_led_group = QGroupBox("LEDs ESP2")
        esp2_led_layout = QVBoxLayout(esp2_led_group)
        
        self.esp2_verde = QCheckBox("🟢 LED Verde")
        self.esp2_rojo = QCheckBox("🔴 LED Rojo")
        self.esp2_amarillo = QCheckBox("🟡 LED Amarillo")
        
        self.esp2_verde.toggled.connect(lambda s: self.send_led_command('ESP2', 'led_verde', s))
        self.esp2_rojo.toggled.connect(lambda s: self.send_led_command('ESP2', 'led_rojo', s))
        self.esp2_amarillo.toggled.connect(lambda s: self.send_led_command('ESP2', 'led_amarillo', s))
        
        esp2_led_layout.addWidget(self.esp2_verde)
        esp2_led_layout.addWidget(self.esp2_rojo)
        esp2_led_layout.addWidget(self.esp2_amarillo)
        layout.addWidget(esp2_led_group)
        
        # === PRUEBAS ===
        test_group = QGroupBox("Pruebas Rápidas")
        test_layout = QVBoxLayout(test_group)
        
        test_remote_btn = QPushButton("🔄 Probar LEDs Remotos")
        test_remote_btn.clicked.connect(self.test_remote_leds)
        test_layout.addWidget(test_remote_btn)
        
        layout.addWidget(test_group)
        
        # === ESTADO ===
        status_group = QGroupBox("Estado del Sistema")
        status_layout = QVBoxLayout(status_group)
        
        self.esp1_status = QLabel("ESP1: Desconectado")
        self.esp2_status = QLabel("ESP2: Desconectado")
        self.master_status = QLabel("Maestro: ESP1")
        
        status_layout.addWidget(self.esp1_status)
        status_layout.addWidget(self.esp2_status)
        status_layout.addWidget(self.master_status)
        layout.addWidget(status_group)
        
        layout.addStretch()
        return panel
    
    def create_plot_panel(self):
        """Panel de gráficas optimizado"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Título dinámico
        self.plot_title = QLabel("Potenciómetro (V) - Tiempo Real")
        self.plot_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.plot_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.plot_title)
        
        # Gráfica principal
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground('k')
        self.plot_widget.showGrid(True, True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Voltaje (V)')
        self.plot_widget.setLabel('bottom', 'Tiempo (s)')
        self.plot_widget.setYRange(0, 3.5)
        
        # Curvas de datos - Etiquetas adaptadas para modo distribuido
        if hasattr(self, 'operation_mode') and self.operation_mode == "DISTRIBUIDO":
            local_label = f'{self.master_esp} (Maestro)'
            remote_label = f'{"ESP2" if self.master_esp == "ESP1" else "ESP1"} (Esclavo)'
        else:
            local_label = 'Local'
            remote_label = 'Remoto'
            
        self.local_curve = self.plot_widget.plot(
            pen=pg.mkPen('#00FFFF', width=3), name=local_label
        )
        self.remote_curve = self.plot_widget.plot(
            pen=pg.mkPen('#FF6600', width=2, style=Qt.PenStyle.DashLine), name=remote_label
        )
        
        # Leyenda
        self.plot_widget.addLegend()
        
        layout.addWidget(self.plot_widget)
        
        # Panel de valores actuales - Etiquetas dinámicas
        values_frame = QFrame()
        values_layout = QGridLayout(values_frame)
        
        values_layout.addWidget(QLabel("Maestro:"), 0, 0)
        self.local_value = QLabel("0.000 V")
        self.local_value.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        values_layout.addWidget(self.local_value, 0, 1)
        
        values_layout.addWidget(QLabel("Esclavo:"), 0, 2)
        self.remote_value = QLabel("0.000 V")
        self.remote_value.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        values_layout.addWidget(self.remote_value, 0, 3)
        
        values_layout.addWidget(QLabel("Frecuencia:"), 1, 0)
        self.freq_label = QLabel("20 Hz")
        values_layout.addWidget(self.freq_label, 1, 1)
        
        values_layout.addWidget(QLabel("Protocolo:"), 1, 2)
        self.protocol_label = QLabel("RS232/RS485")
        values_layout.addWidget(self.protocol_label, 1, 3)
        
        layout.addWidget(values_frame)
        
        return panel
    
    def setup_styles(self):
        """Estilos de la aplicación"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: white;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #00ff00;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
                color: #00ff00;
                background-color: #2a2a2a;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                background-color: #404040;
                border: 2px solid #00ff00;
                border-radius: 6px;
                padding: 8px 16px;
                color: #00ff00;
                font-weight: bold;
                min-height: 25px;
            }
            QPushButton:hover {
                background-color: #505050;
                border-color: #00ff88;
            }
            QPushButton:checked {
                background-color: #00ff00;
                color: #000000;
            }
            QComboBox {
                background-color: #404040;
                border: 2px solid #00ff00;
                border-radius: 4px;
                padding: 5px;
                color: white;
                min-width: 120px;
            }
            QCheckBox {
                color: white;
                font-weight: bold;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #00ff00;
                border-radius: 4px;
                background-color: #404040;
            }
            QCheckBox::indicator:checked {
                background-color: #00ff00;
            }
            QLabel {
                color: white;
            }
            QScrollArea {
                border: 1px solid #00ff00;
                border-radius: 4px;
                background-color: #2a2a2a;
            }
            QScrollBar:vertical {
                background-color: #404040;
                width: 12px;
                border-radius: 6px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #00ff00;
                border-radius: 6px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #00ff88;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background-color: transparent;
            }
        """)
    
    def set_operation_mode(self, mode):
        """Cambiar modo de operación"""
        self.operation_mode = mode
        
        if mode == "LOCAL":
            self.remote_ip_input.setEnabled(False)
            print("Modo cambiado a: LOCAL (1 PC controla 2 ESP)")
        elif mode == "DISTRIBUIDO":
            self.remote_ip_input.setEnabled(True)
            print("Modo cambiado a: DISTRIBUIDO (2 PC, 1 ESP cada una)")
    
    def refresh_ports(self):
        """Actualizar puertos COM disponibles"""
        try:
            ports = [p.device for p in serial.tools.list_ports.comports()]
            
            # Limpiar y recargar
            if hasattr(self, 'esp1_combo'):
                self.esp1_combo.clear()
                self.esp2_combo.clear()
                
                for port in ports:
                    self.esp1_combo.addItem(port)
                    self.esp2_combo.addItem(port)
                    
                print(f"Puertos disponibles: {ports}")
        except Exception as e:
            print(f"Error actualizando puertos: {e}")
    
    def toggle_connection(self, esp):
        """Conectar/desconectar ESP"""
        if esp == 'ESP1':
            if self.esp1_worker and self.esp1_worker.running:
                self.esp1_worker.stop()
                self.esp1_worker.wait()
                self.esp1_worker = None
                self.esp1_btn.setText("Conectar")
                self.esp1_status.setText("ESP1: Desconectado")
            else:
                port = self.esp1_combo.currentText()
                if port:
                    self.esp1_worker = SerialWorker(port)
                    self.esp1_worker.data_received.connect(self.on_data_received)
                    self.esp1_worker.connection_status.connect(self.on_connection_status)
                    self.esp1_worker.debug_message.connect(self.on_debug_message)
                    self.esp1_worker.start()
                    self.esp1_btn.setText("Desconectar")
                    self.esp1_status.setText("ESP1: Conectando...")
        
        elif esp == 'ESP2':
            if self.esp2_worker and self.esp2_worker.running:
                self.esp2_worker.stop()
                self.esp2_worker.wait()
                self.esp2_worker = None
                self.esp2_btn.setText("Conectar")
                self.esp2_status.setText("ESP2: Desconectado")
            else:
                port = self.esp2_combo.currentText()
                if port:
                    self.esp2_worker = SerialWorker(port)
                    self.esp2_worker.data_received.connect(self.on_data_received)
                    self.esp2_worker.connection_status.connect(self.on_connection_status)
                    self.esp2_worker.debug_message.connect(self.on_debug_message)
                    self.esp2_worker.start()
                    self.esp2_btn.setText("Desconectar")
                    self.esp2_status.setText("ESP2: Conectando...")
    
    def set_master(self, esp_name):
        """Establecer ESP maestro"""
        self.master_esp = esp_name
        
        # Actualizar botones
        self.esp1_master_btn.setChecked(esp_name == "ESP1")
        self.esp2_master_btn.setChecked(esp_name == "ESP2")
        
        # Enviar comando
        self.send_master_command(esp_name)
        
        # Limpiar gráficas
        self.plot_data_local.clear()
        self.plot_data_remote.clear()
        self.plot_time.clear()
        
        self.master_status.setText(f"Maestro: {esp_name}")
        print(f"ESP maestro cambiado a: {esp_name}")
    
    def set_sensor(self, sensor_idx):
        """Cambiar sensor a visualizar"""
        self.current_sensor = sensor_idx
        
        # Actualizar botones
        for i, btn in enumerate(self.sensor_buttons):
            btn.setChecked(i == sensor_idx)
        
        # Actualizar títulos
        sensor_name = self.sensor_names[sensor_idx]
        unit = self.sensor_units[sensor_idx]
        self.plot_title.setText(f"{sensor_name} ({unit}) - Tiempo Real")
        self.plot_widget.setLabel('left', f'{sensor_name} ({unit})')
        
        # Configurar rangos según el sensor
        if sensor_idx < 3:  # Sensores analógicos (0-3.3V)
            self.plot_widget.setYRange(0, 3.5)
        elif sensor_idx < 6:  # Acelerómetro (±2g)
            self.plot_widget.setYRange(-2.5, 2.5)
        elif sensor_idx < 9:  # Giroscopio (±250°/s)
            self.plot_widget.setYRange(-300, 300)
        else:  # Temperatura (0-50°C)
            self.plot_widget.setYRange(0, 50)
        
        # Limpiar datos
        self.plot_data_local.clear()
        self.plot_data_remote.clear()
        self.plot_time.clear()
        
        print(f"Sensor cambiado a: {sensor_name}")
        
        # Actualizar colores de curvas según el tipo de sensor
        if sensor_idx < 3:  # Analógicos - azul/naranja
            self.local_curve.setPen(pg.mkPen('#00FFFF', width=3))
            self.remote_curve.setPen(pg.mkPen('#FF6600', width=2, style=Qt.PenStyle.DashLine))
        elif sensor_idx < 6:  # Acelerómetro - verde/rojo
            self.local_curve.setPen(pg.mkPen('#00FF00', width=3))
            self.remote_curve.setPen(pg.mkPen('#FF0000', width=2, style=Qt.PenStyle.DashLine))
        elif sensor_idx < 9:  # Giroscopio - magenta/amarillo
            self.local_curve.setPen(pg.mkPen('#FF00FF', width=3))
            self.remote_curve.setPen(pg.mkPen('#FFFF00', width=2, style=Qt.PenStyle.DashLine))
        else:  # Temperatura - rojo/azul
            self.local_curve.setPen(pg.mkPen('#FF4444', width=3))
            self.remote_curve.setPen(pg.mkPen('#4444FF', width=2, style=Qt.PenStyle.DashLine))
    
    def send_master_command(self, esp_name):
        """Enviar comando SET_MASTER"""
        command = "SET_MASTER\n"
        
        if esp_name == 'ESP1' and self.esp1_worker and self.esp1_worker.running:
            self.esp1_worker.write_data(command.encode())
            print("Comando SET_MASTER enviado a ESP1")
        elif esp_name == 'ESP2' and self.esp2_worker and self.esp2_worker.running:
            self.esp2_worker.write_data(command.encode())
            print("Comando SET_MASTER enviado a ESP2")
    
    def send_led_command(self, target, led_name, state):
        """Enviar comando de LED (adaptado para modo distribuido)"""
        # Comando específico para evitar conflictos
        command = f"{target.lower()}_{led_name}:{str(state).lower()}\n"
        
        if self.operation_mode == "DISTRIBUIDO":
            # En modo distribuido, determinar si el comando es local o remoto
            if target == self.local_esp:
                # ESP local - envío directo
                if target == 'ESP1' and self.esp1_worker and self.esp1_worker.running:
                    self.esp1_worker.write_data(command.encode())
                    print(f"LED ESP1 LOCAL: {led_name} = {state}")
                elif target == 'ESP2' and self.esp2_worker and self.esp2_worker.running:
                    self.esp2_worker.write_data(command.encode())
                    print(f"LED ESP2 LOCAL: {led_name} = {state}")
            else:
                # ESP remoto - envío via RS485
                if self.local_esp == 'ESP1' and self.esp1_worker and self.esp1_worker.running:
                    self.esp1_worker.write_data(command.encode())
                    print(f"LED {target} REMOTO via ESP1→RS485: {led_name} = {state}")
                elif self.local_esp == 'ESP2' and self.esp2_worker and self.esp2_worker.running:
                    self.esp2_worker.write_data(command.encode())
                    print(f"LED {target} REMOTO via ESP2→RS485: {led_name} = {state}")
        else:
            # Modo local normal
            if target == 'ESP1' and self.esp1_worker and self.esp1_worker.running:
                self.esp1_worker.write_data(command.encode())
                print(f"LED ESP1: {led_name} = {state}")
            elif target == 'ESP2' and self.esp2_worker and self.esp2_worker.running:
                self.esp2_worker.write_data(command.encode())
                print(f"LED ESP2: {led_name} = {state}")
    
    def test_remote_leds(self):
        """Probar LEDs remotos (adaptado para modo distribuido)"""
        print(f"Probando LEDs remotos - Modo: {self.operation_mode}")
        
        if self.operation_mode == "DISTRIBUIDO":
            # En modo distribuido, probar comunicación con el ESP remoto
            if self.local_esp == "ESP1" and self.esp1_worker and self.esp1_worker.running:
                commands = ["esp2_led_verde:true\n", "esp2_led_rojo:true\n", "esp2_led_amarillo:true\n"]
                for cmd in commands:
                    self.esp1_worker.write_data(cmd.encode())
                    print(f"ESP1→ESP2 via RS485: {cmd.strip()}")
                    
            elif self.local_esp == "ESP2" and self.esp2_worker and self.esp2_worker.running:
                commands = ["esp1_led_verde:true\n", "esp1_led_rojo:true\n", "esp1_led_amarillo:true\n"]
                for cmd in commands:
                    self.esp2_worker.write_data(cmd.encode())
                    print(f"ESP2→ESP1 via RS485: {cmd.strip()}")
        else:
            # Modo local normal
            if self.esp1_worker and self.esp1_worker.running:
                commands = ["esp2_led_verde:true\n", "esp2_led_rojo:true\n", "esp2_led_amarillo:true\n"]
                for cmd in commands:
                    self.esp1_worker.write_data(cmd.encode())
                    print(f"ESP1 → ESP2: {cmd.strip()}")
            
            if self.esp2_worker and self.esp2_worker.running:
                commands = ["esp1_led_verde:true\n", "esp1_led_rojo:true\n", "esp1_led_amarillo:true\n"]
                for cmd in commands:
                    self.esp2_worker.write_data(cmd.encode())
                    print(f"ESP2 → ESP1: {cmd.strip()}")
    
    def on_data_received(self, port, data):
        """Procesar datos JSON recibidos"""
        try:
            device = data.get('device', 'Unknown')
            
            # Auto-detectar ESP local en modo distribuido
            if self.operation_mode == "DISTRIBUIDO" and not self.local_esp:
                if device in ["ESP1", "ESP2"]:
                    self.local_esp = device
                    print(f"Auto-detectado ESP local: {device}")
            
            # PROCESAR DATOS PARA GRÁFICAS - CAMBIO IMPORTANTE:
            # En modo DISTRIBUIDO: ambas interfaces grafican los datos del maestro
            # En modo LOCAL: solo grafica el ESP maestro
            if self.operation_mode == "DISTRIBUIDO":
                # En modo distribuido, cualquier ESP puede tener los datos del maestro
                # El ESP esclavo recibe los datos del maestro por RS485
                if 'local' in data and 'remote' in data:
                    # Si tiene datos local Y remote, es el ESP maestro
                    if device == self.master_esp:
                        self.update_plot_data(data)
                        print(f"Graficando datos del maestro {device} (directo)")
                    else:
                        # Si es el ESP esclavo pero tiene datos, significa que recibió del maestro
                        # Los datos 'remote' del esclavo son en realidad los datos del maestro
                        self.update_plot_data_from_slave(data)
                        print(f"Graficando datos del maestro via {device} (RS485)")
                elif device == self.master_esp:
                    # Solo tiene datos locales, es el ESP maestro
                    self.update_plot_data(data)
            else:
                # Modo local normal - solo procesar datos del ESP maestro
                if device == self.master_esp:
                    self.update_plot_data(data)
        except Exception as e:
            print(f"Error procesando datos: {e}")
    
    def update_plot_data(self, data):
        """Actualizar datos de gráfica desde ESP maestro"""
        try:
            sensor_key = self.sensors[self.current_sensor]
            
            # Extraer valores
            local_val = data.get('local', {}).get(sensor_key, 0)
            remote_val = data.get('remote', {}).get(sensor_key, 0)
            
            # Agregar a datos
            current_time = time.time()
            self.plot_data_local.append(local_val)
            self.plot_data_remote.append(remote_val)
            self.plot_time.append(current_time)
            
        except Exception as e:
            print(f"Error actualizando datos de gráfica: {e}")
    
    def update_plot_data_from_slave(self, data):
        """Actualizar datos de gráfica desde ESP esclavo (que recibió datos del maestro)"""
        try:
            sensor_key = self.sensors[self.current_sensor]
            
            # El ESP esclavo tiene los datos del maestro en 'remote'
            # y sus propios datos en 'local'
            if self.master_esp == "ESP1":
                # Si ESP1 es maestro, ESP2 (esclavo) tiene:
                # - data['local'] = datos de ESP2
                # - data['remote'] = datos de ESP1 (maestro) recibidos por RS485
                master_local_val = data.get('remote', {}).get(sensor_key, 0)  # Datos del ESP1 maestro
                master_remote_val = data.get('local', {}).get(sensor_key, 0)  # Datos del ESP2 esclavo
            else:
                # Si ESP2 es maestro, ESP1 (esclavo) tiene:
                # - data['local'] = datos de ESP1  
                # - data['remote'] = datos de ESP2 (maestro) recibidos por RS485
                master_local_val = data.get('remote', {}).get(sensor_key, 0)  # Datos del ESP2 maestro
                master_remote_val = data.get('local', {}).get(sensor_key, 0)  # Datos del ESP1 esclavo
            
            # Agregar a datos (mismo formato que el maestro)
            current_time = time.time()
            self.plot_data_local.append(master_local_val)
            self.plot_data_remote.append(master_remote_val)
            self.plot_time.append(current_time)
            
        except Exception as e:
            print(f"Error actualizando datos desde esclavo: {e}")
    
    def update_display(self):
        """Actualizar visualización (20Hz)"""
        try:
            if len(self.plot_time) > 1:
                # Tiempo relativo
                time_rel = [t - self.plot_time[0] for t in self.plot_time]
                
                # Actualizar curvas
                self.local_curve.setData(time_rel, list(self.plot_data_local))
                self.remote_curve.setData(time_rel, list(self.plot_data_remote))
                
                # Actualizar valores actuales
                if self.plot_data_local:
                    unit = self.sensor_units[self.current_sensor]
                    self.local_value.setText(f"{self.plot_data_local[-1]:.3f} {unit}")
                    self.remote_value.setText(f"{self.plot_data_remote[-1]:.3f} {unit}")
                    
        except Exception as e:
            print(f"Error actualizando display: {e}")
    
    def on_connection_status(self, port, connected):
        """Actualizar estado de conexión"""
        status = "Conectado" if connected else "Desconectado"
        
        if hasattr(self, 'esp1_worker') and self.esp1_worker and self.esp1_worker.port == port:
            self.esp1_status.setText(f"ESP1: {status}")
            if not connected:
                self.esp1_btn.setText("Conectar")
                
        if hasattr(self, 'esp2_worker') and self.esp2_worker and self.esp2_worker.port == port:
            self.esp2_status.setText(f"ESP2: {status}")
            if not connected:
                self.esp2_btn.setText("Conectar")
    
    def on_debug_message(self, message):
        """Mostrar mensajes de debug"""
        print(message)
    
    def closeEvent(self, event):
        """Limpiar al cerrar"""
        print("Cerrando sistema...")
        
        if self.esp1_worker:
            self.esp1_worker.stop()
            self.esp1_worker.wait()
        if self.esp2_worker:
            self.esp2_worker.stop()
            self.esp2_worker.wait()
            
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Sistema ESP32 S3 - Distribuido")
    app.setStyle('Fusion')
    
    window = ESP32Interface()
    window.show()
    
    print("=== Sistema ESP32 S3 [DISTRIBUIDO] Iniciado ===")
    print("MODOS DISPONIBLES:")
    print("1. LOCAL: Una PC controla ambos ESP")
    print("2. DISTRIBUIDO: Cada PC controla un ESP, comunicación RS485")
    print("")
    print("FUNCIONALIDADES:")
    print("✓ Auto-detección de ESP local")
    print("✓ Comandos LED via RS485 entre PCs")
    print("✓ Gráficas de datos remotos")
    print("✓ Sincronización maestro/esclavo")
    
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
