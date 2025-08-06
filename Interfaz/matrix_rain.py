from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPainter, QColor, QFont
import random

class MatrixRain(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.characters = "101010101010*@#$%&?"
        self.drops = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update)
        self.timer.start(100)
        self.setStyleSheet("background: transparent;")

    def initializeDrops(self):
        self.drops = []
        for i in range(self.width() // 20):  # Espaciado entre gotas
            self.drops.append({
                'x': random.randint(0, self.width()),
                'y': random.randint(-100, 0),
                'speed': random.randint(2, 5),
                'length': random.randint(5, 15)
            })

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.initializeDrops()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setFont(QFont('Ubuntu Mono', 14))

        for drop in self.drops:
            for i in range(drop['length']):
                opacity = 255 - (i * (255 // drop['length']))
                color = QColor(0, 255, 0, opacity)
                painter.setPen(color)
                char = random.choice(self.characters)
                painter.drawText(drop['x'], drop['y'] - i * 20, char)
            
            drop['y'] += drop['speed']
            
            if drop['y'] > self.height():
                drop['y'] = random.randint(-100, 0)
                drop['x'] = random.randint(0, self.width())