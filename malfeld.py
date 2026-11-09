from PySide6.QtQml import QmlElement
from PySide6.QtQuick import QQuickPaintedItem
from PySide6.QtGui import QPainter, QColor, QPen, QImage
from PySide6.QtCore import Qt, QPointF, Slot, QRectF
import numpy as np

QML_IMPORT_NAME = "Malwerkzeug"
QML_IMPORT_MAJOR_VERSION = 1



@QmlElement
class Malfeld(QQuickPaintedItem):


    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptedMouseButtons(Qt.LeftButton)
        self._hinzufuegen = QImage(1, 1, QImage.Format_ARGB32)
        self._hinzufuegen.fill(Qt.transparent)
        self._entfernen = QImage(1, 1, QImage.Format_ARGB32)
        self._entfernen.fill(Qt.transparent)
        self._einfaerben = QImage(1, 1, QImage.Format_ARGB32)
        self._einfaerben.fill(Qt.transparent)
        self.old_x = None
        self.old_y = None
        self._thickness = 2
        self.werkzeug = "hinzufuegen"
        self._zurueck_stapel = []
        self._vor_stapel = []

    @Slot(int, int)
    def bild_groesse_setzen(self, breite, hoehe):
        self._hinzufuegen = QImage(breite, hoehe, QImage.Format_ARGB32)
        self._hinzufuegen.fill(Qt.transparent)
        self._entfernen = QImage(breite, hoehe, QImage.Format_ARGB32)
        self._entfernen.fill(Qt.transparent)
        self._einfaerben = QImage(breite, hoehe, QImage.Format_ARGB32)
        self._einfaerben.fill(Qt.transparent)
        self._zurueck_stapel.clear()
        self._vor_stapel.clear()
        self.update()

    @Slot(str)
    def werkzeug_waehlen(self, name):
        self.werkzeug = name


    def _aktuelle_ebene(self):
        if self.werkzeug == "hinzufuegen":
            ebene = [self._hinzufuegen]
            return ebene
        elif self.werkzeug == "entfernen":
            ebene = [self._entfernen]
            return ebene
        elif self.werkzeug == "einfaerben":
            ebene = [self._einfaerben]
            return ebene
        elif self.werkzeug == "radierer":
            ebene = [self._hinzufuegen, self._entfernen, self._einfaerben]
            return ebene
        return []
    def _skaliere_position(self, event):
        skala_x, skala_y = self._skala()
        x = event.position().x() * skala_x
        y = event.position().y() * skala_y
        return x, y

    @Slot(int)
    def stift(self, dicke):
        self._thickness = dicke

    def _skala(self):
        skala_x = self._hinzufuegen.width() / self.width()
        skala_y = self._hinzufuegen.height() / self.height()
        return skala_x, skala_y

    def _maler_logik(self, ebene):
        maler = QPainter(ebene)
        maler.setRenderHint(QPainter.RenderHint.Antialiasing)
        skala_x, skala_y = self._skala()
        thickness = self._thickness * max(skala_x, skala_y)
        if self.werkzeug == "hinzufuegen":
            maler.setPen(QPen(QColor("green"), thickness))
            maler.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        elif self.werkzeug == "entfernen":
            maler.setPen(QPen(QColor("red"), thickness))
            maler.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        elif self.werkzeug == "einfaerben":
            maler.setPen(QPen(QColor("blue"), thickness))
            maler.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        elif self.werkzeug == "radierer":
            maler.setPen(QPen(QColor("black"), thickness))
            maler.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        return maler

    def _sichern(self):
        self._zurueck_stapel.append([self._hinzufuegen.copy(), self._entfernen.copy(), self._einfaerben.copy()])
        self._vor_stapel.clear()
        if len(self._zurueck_stapel) > 10:
            self._zurueck_stapel.pop(0)

    @Slot()
    def zurueck(self):
        if len(self._zurueck_stapel) == 0:
            return
        self._vor_stapel.append([self._hinzufuegen.copy(), self._entfernen.copy(), self._einfaerben.copy()])
        back = self._zurueck_stapel.pop()
        self._hinzufuegen, self._entfernen, self._einfaerben = back
        self.update()

    @Slot()
    def vor(self):
        if len(self._vor_stapel) == 0:
            return
        self._zurueck_stapel.append([self._hinzufuegen.copy(), self._entfernen.copy(), self._einfaerben.copy()])
        back = self._vor_stapel.pop()
        self._hinzufuegen, self._entfernen, self._einfaerben = back
        self.update()


    def mousePressEvent(self, event, /):
        x, y = self._skaliere_position(event)
        self._sichern()
        for ebene in self._aktuelle_ebene():
            maler = self._maler_logik(ebene)
            maler.drawPoint(QPointF(x, y,))
            maler.end()
        self.old_x, self.old_y = x, y
        self.update()

    def mouseMoveEvent(self, event, /):
        x, y = self._skaliere_position(event)
        for ebene in self._aktuelle_ebene():
            maler = self._maler_logik(ebene)
            maler.drawLine(QPointF(x, y), QPointF(self.old_x, self.old_y))
            maler.end()
        self.old_x, self.old_y = x, y
        self.update()

    def paint(self, painter):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        target_rect = QRectF(0, 0, self.width(), self.height())
        painter.setOpacity(0.5)
        painter.drawImage(target_rect, self._hinzufuegen)
        painter.drawImage(target_rect, self._entfernen)
        painter.drawImage(target_rect, self._einfaerben)



    def _ebene_zu_maske(self, ebene):
        breite, hoehe = ebene.width(), ebene.height()
        bpz = ebene.bytesPerLine()
        inhalt = np.frombuffer(ebene.constBits(), dtype=np.uint8)[: hoehe * bpz]
        export = inhalt.reshape(hoehe, bpz)[:, :breite * 4].reshape(hoehe, breite, 4)
        maske = export[:, :, 3] > 127
        return maske

    def masken(self):
        hinzufuegen = self._ebene_zu_maske(self._hinzufuegen)
        entfernen = self._ebene_zu_maske(self._entfernen)
        einfaerben = self._ebene_zu_maske(self._einfaerben)
        return hinzufuegen, entfernen, einfaerben

