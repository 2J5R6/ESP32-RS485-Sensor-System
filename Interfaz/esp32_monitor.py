#!/usr/bin/env python3
"""
Sistema de Monitoreo RS485/RS232 - ESP32 S3
Interfaz gráfica para comunicación con ESP1 y ESP2

Características:
✓ Detección automática de puertos COM
✓ Comunicación simultánea con ESP1 y ESP2
✓ Gráficas en tiempo real (20Hz)
✓ Control de LEDs para cada ESP
✓ Selección de variables a visualizar
✓ Protocolo JSON para comunicación
✓ Interfaz responsive y moderna
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
    
    def send_command(self, command):
        """Enviar comando al ESP"""
        if self.serial_connection and self.serial_connection.is_open:
            try:
                cmd_json = json.dumps(command) + '\n'
                self.serial_connection.write(cmd_json.encode('utf-8'))
                self.serial_connection.flush()
                return True
            except Exception as e:
                print(f"Error enviando comando a {self.port}: {e}")
        return False
    
    def stop(self):
        self.running = False

class ESP32Monitor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sistema ESP32 S3 - Comunicación RS485/RS232")
        self.setGeometry(100, 100, 1400, 900)
        
        # Variables de datos
        self.esp1_worker = None
        self.esp2_worker = None
        self.esp1_data = deque(maxlen=1000)  # Buffer para ESP1
        self.esp2_data = deque(maxlen=1000)  # Buffer para ESP2
        self.time_data = deque(maxlen=1000)  # Buffer de tiempo
        
        # Variables de visualización
        self.current_sensor = 0  # 0: pot, 1: ldr, 2: enc, 3: mpu
        self.sensor_names = ["Potenciómetro", "LDR", "Encoder", "Acelerómetro X"]
        self.sensor_units = ["V", "V", "V", "m/s²"]
        
        # Configurar interfaz
        self.setup_ui()
        self.setup_styles()
        
        # Timer para actualización de gráficas
        self.plot_timer = QTimer()
        self.plot_timer.timeout.connect(self.update_plots)
        self.plot_timer.start(50)  # 20Hz
        
        # Actualizar puertos disponibles
        self.update_available_ports()
    
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
        
        layout.addWidget(conn_group)
        
        # === SELECCIÓN DE SENSOR ===
        sensor_group = QGroupBox("Variable a Visualizar")
        sensor_layout = QVBoxLayout(sensor_group)
        
        self.sensor_buttons = []
        for i, name in enumerate(self.sensor_names):
            btn = QPushButton(f"{name} ({self.sensor_units[i]})")
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self.set_sensor(idx))
            self.sensor_buttons.append(btn)
            sensor_layout.addWidget(btn)
        
        self.sensor_buttons[0].setChecked(True)
        layout.addWidget(sensor_group)
        
        # === CONTROL DE LEDS ESP1 ===
        esp1_led_group = QGroupBox("LEDs ESP1")
        esp1_led_layout = QVBoxLayout(esp1_led_group)
        
        self.esp1_led_verde = QCheckBox("LED Verde")
        self.esp1_led_rojo = QCheckBox("LED Rojo")
        self.esp1_led_amarillo = QCheckBox("LED Amarillo")
        
        self.esp1_led_verde.toggled.connect(lambda state: self.send_led_command('ESP1', 'led_verde', state))
        self.esp1_led_rojo.toggled.connect(lambda state: self.send_led_command('ESP1', 'led_rojo', state))
        self.esp1_led_amarillo.toggled.connect(lambda state: self.send_led_command('ESP1', 'led_amarillo', state))
        
        esp1_led_layout.addWidget(self.esp1_led_verde)
        esp1_led_layout.addWidget(self.esp1_led_rojo)
        esp1_led_layout.addWidget(self.esp1_led_amarillo)
        layout.addWidget(esp1_led_group)
        
        # === CONTROL DE LEDS ESP2 ===
        esp2_led_group = QGroupBox("LEDs ESP2")
        esp2_led_layout = QVBoxLayout(esp2_led_group)
        
        self.esp2_led_verde = QCheckBox("LED Verde")
        self.esp2_led_rojo = QCheckBox("LED Rojo")
        self.esp2_led_amarillo = QCheckBox("LED Amarillo")
        
        self.esp2_led_verde.toggled.connect(lambda state: self.send_led_command('ESP2', 'led_verde', state))
        self.esp2_led_rojo.toggled.connect(lambda state: self.send_led_command('ESP2', 'led_rojo', state))
        self.esp2_led_amarillo.toggled.connect(lambda state: self.send_led_command('ESP2', 'led_amarillo', state))
        
        esp2_led_layout.addWidget(self.esp2_led_verde)
        esp2_led_layout.addWidget(self.esp2_led_rojo)
        esp2_led_layout.addWidget(self.esp2_led_amarillo)
        layout.addWidget(esp2_led_group)
        
        # === ESTADO DE CONEXIÓN ===
        status_group = QGroupBox("Estado")
        status_layout = QVBoxLayout(status_group)
        
        self.esp1_status = QLabel("ESP1: Desconectado")
        self.esp2_status = QLabel("ESP2: Desconectado")
        self.data_rate_label = QLabel("Datos/seg: 0")
        
        status_layout.addWidget(self.esp1_status)
        status_layout.addWidget(self.esp2_status)
        status_layout.addWidget(self.data_rate_label)
        layout.addWidget(status_group)
        
        # Espaciador
        layout.addStretch()
        
        return panel
    
    def create_plot_panel(self):
        """Crear panel de gráficas"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Título de gráfica
        self.plot_title = QLabel("Potenciómetro (V)")
        self.plot_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.plot_title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(self.plot_title)
        
        # Gráfica principal
        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setLabel('left', 'Valor', color='white', size='12pt')
        self.plot_widget.setLabel('bottom', 'Tiempo (s)', color='white', size='12pt')
        self.plot_widget.showGrid(True, True)
        self.plot_widget.setBackground('k')  # Fondo negro
        
        # Configurar colores del grid
        self.plot_widget.getAxis('left').setPen('white')
        self.plot_widget.getAxis('bottom').setPen('white')
        self.plot_widget.getAxis('left').setTextPen('white')
        self.plot_widget.getAxis('bottom').setTextPen('white')
        
        # Curvas para cada ESP con colores brillantes
        self.esp1_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#00FFFF', width=3), 
            name='ESP1 Local'
        )
        self.esp2_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#FF6600', width=3), 
            name='ESP2 Local'
        )
        self.esp1_remote_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#66FFFF', width=2, style=Qt.PenStyle.DashLine), 
            name='ESP1 Remoto'
        )
        self.esp2_remote_curve = self.plot_widget.plot(
            pen=pg.mkPen(color='#FFAA66', width=2, style=Qt.PenStyle.DashLine), 
            name='ESP2 Remoto'
        )
        
        # Agregar leyenda
        self.plot_widget.addLegend()
        
        layout.addWidget(self.plot_widget)
        
        # Panel de valores actuales
        values_panel = QFrame()
        values_layout = QGridLayout(values_panel)
        
        values_layout.addWidget(QLabel("ESP1 Local:"), 0, 0)
        self.esp1_local_value = QLabel("---")
        values_layout.addWidget(self.esp1_local_value, 0, 1)
        
        values_layout.addWidget(QLabel("ESP1 Remoto:"), 0, 2)
        self.esp1_remote_value = QLabel("---")
        values_layout.addWidget(self.esp1_remote_value, 0, 3)
        
        values_layout.addWidget(QLabel("ESP2 Local:"), 1, 0)
        self.esp2_local_value = QLabel("---")
        values_layout.addWidget(self.esp2_local_value, 1, 1)
        
        values_layout.addWidget(QLabel("ESP2 Remoto:"), 1, 2)
        self.esp2_remote_value = QLabel("---")
        values_layout.addWidget(self.esp2_remote_value, 1, 3)
        
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
    
    def update_available_ports(self):
        """Actualizar lista de puertos COM disponibles"""
        ports = [port.device for port in serial.tools.list_ports.comports()]
        
        # Actualizar combos
        self.esp1_combo.clear()
        self.esp2_combo.clear()
        
        for port in ports:
            self.esp1_combo.addItem(port)
            self.esp2_combo.addItem(port)
        
        print(f"Puertos disponibles: {ports}")
    
    def toggle_connection(self, esp):
        """Alternar conexión para ESP1 o ESP2"""
        if esp == 'ESP1':
            if self.esp1_worker and self.esp1_worker.running:
                # Desconectar
                self.esp1_worker.stop()
                self.esp1_worker.wait()
                self.esp1_worker = None
                self.esp1_connect_btn.setText("Conectar")
                self.esp1_status.setText("ESP1: Desconectado")
            else:
                # Conectar
                port = self.esp1_combo.currentText()
                if port:
                    self.esp1_worker = SerialWorker(port)
                    self.esp1_worker.data_received.connect(self.on_data_received)
                    self.esp1_worker.connection_status.connect(self.on_connection_status)
                    self.esp1_worker.start()
                    self.esp1_connect_btn.setText("Desconectar")
        
        elif esp == 'ESP2':
            if self.esp2_worker and self.esp2_worker.running:
                # Desconectar
                self.esp2_worker.stop()
                self.esp2_worker.wait()
                self.esp2_worker = None
                self.esp2_connect_btn.setText("Conectar")
                self.esp2_status.setText("ESP2: Desconectado")
            else:
                # Conectar
                port = self.esp2_combo.currentText()
                if port:
                    self.esp2_worker = SerialWorker(port)
                    self.esp2_worker.data_received.connect(self.on_data_received)
                    self.esp2_worker.connection_status.connect(self.on_connection_status)
                    self.esp2_worker.start()
                    self.esp2_connect_btn.setText("Desconectar")
    
    def on_data_received(self, port, data):
        """Manejar datos recibidos de ESP"""
        try:
            current_time = time.time()
            device = data.get('device', 'Unknown')
            
            # Agregar a buffer correspondiente
            if device == 'ESP1':
                self.esp1_data.append(data)
            elif device == 'ESP2':
                self.esp2_data.append(data)
            
            # Mantener sincronía de tiempo
            if len(self.time_data) == 0 or current_time - self.time_data[-1] > 0.01:
                self.time_data.append(current_time)
            
        except Exception as e:
            print(f"Error procesando datos de {port}: {e}")
    
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
        
        # Actualizar botones
        for i, btn in enumerate(self.sensor_buttons):
            btn.setChecked(i == sensor_idx)
        
        # Actualizar título
        self.plot_title.setText(f"{self.sensor_names[sensor_idx]} ({self.sensor_units[sensor_idx]})")
        self.plot_widget.setLabel('left', f'{self.sensor_names[sensor_idx]} ({self.sensor_units[sensor_idx]})')
    
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
        """Actualizar gráficas con datos más recientes"""
        if len(self.time_data) < 2:
            return
        
        try:
            # Obtener ventana de tiempo (últimos 30 segundos)
            current_time = time.time()
            window_start = current_time - 30
            
            # Filtrar datos por tiempo
            valid_times = [t for t in self.time_data if t >= window_start]
            if not valid_times:
                return
            
            # Preparar datos para gráficas
            times_relative = [(t - valid_times[0]) for t in valid_times]
            
            # ESP1 Data
            esp1_local_values = []
            esp1_remote_values = []
            esp2_local_values = []
            esp2_remote_values = []
            
            for t in valid_times:
                # Buscar datos más cercanos a cada tiempo
                esp1_data = self.find_closest_data(self.esp1_data, t)
                esp2_data = self.find_closest_data(self.esp2_data, t)
                
                esp1_local_values.append(self.get_sensor_value(esp1_data, 'local'))
                esp1_remote_values.append(self.get_sensor_value(esp1_data, 'remote'))
                esp2_local_values.append(self.get_sensor_value(esp2_data, 'local'))
                esp2_remote_values.append(self.get_sensor_value(esp2_data, 'remote'))
            
            # Actualizar curvas
            self.esp1_curve.setData(times_relative, esp1_local_values)
            self.esp1_remote_curve.setData(times_relative, esp1_remote_values)
            self.esp2_curve.setData(times_relative, esp2_local_values)
            self.esp2_remote_curve.setData(times_relative, esp2_remote_values)
            
            # Actualizar valores actuales
            if esp1_local_values:
                self.esp1_local_value.setText(f"{esp1_local_values[-1]:.2f}")
                self.esp1_remote_value.setText(f"{esp1_remote_values[-1]:.2f}")
            if esp2_local_values:
                self.esp2_local_value.setText(f"{esp2_local_values[-1]:.2f}")
                self.esp2_remote_value.setText(f"{esp2_remote_values[-1]:.2f}")
            
            # Actualizar rate de datos
            data_rate = len(self.esp1_data) + len(self.esp2_data)
            self.data_rate_label.setText(f"Datos/seg: {data_rate}")
            
        except Exception as e:
            print(f"Error actualizando gráficas: {e}")
    
    def find_closest_data(self, data_buffer, target_time):
        """Encontrar datos más cercanos a un tiempo dado"""
        if not data_buffer:
            return {}
        
        # Buscar el dato con timestamp más cercano
        closest_data = data_buffer[-1]  # Por defecto el más reciente
        min_diff = float('inf')
        
        for data in reversed(data_buffer):
            if 'timestamp' in data:
                data_time = data['timestamp'] / 1000.0  # Convertir ms a s
                diff = abs(target_time - data_time)
                if diff < min_diff:
                    min_diff = diff
                    closest_data = data
                elif diff > min_diff:
                    break  # Los datos están ordenados, no hay necesidad de seguir
        
        return closest_data
    
    def send_led_command(self, target, led_name, state):
        """Enviar comando de LED al ESP correspondiente"""
        command = {
            "target": target,
            led_name: state
        }
        
        try:
            if target == 'ESP1' and self.esp1_worker:
                success = self.esp1_worker.send_command(command)
                if not success:
                    print(f"Error enviando comando a ESP1: {command}")
            elif target == 'ESP2' and self.esp2_worker:
                success = self.esp2_worker.send_command(command)
                if not success:
                    print(f"Error enviando comando a ESP2: {command}")
        except Exception as e:
            print(f"Error enviando comando {command}: {e}")
    
    def closeEvent(self, event):
        """Limpiar recursos al cerrar"""
        if self.esp1_worker:
            self.esp1_worker.stop()
            self.esp1_worker.wait()
        if self.esp2_worker:
            self.esp2_worker.stop()
            self.esp2_worker.wait()
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
