import shutil
import sys
import os
from PIL import Image
from PySide6.QtCore import QObject, Slot, QUrl, Signal, QThread
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from Image_conversion import bild_vorbereiten, bild_rendern, BILD_ERGEBNIS, TEXT_ERGEBNIS
from PySide6.QtQuickControls2 import QQuickStyle
from pathlib import Path
import malfeld #Registrierung für QML

USER_INTERFACE = Path(__file__).resolve().parent / "UI.qml"

ERGEBNIS_ART = {
    "png" : BILD_ERGEBNIS,
    "txt" : TEXT_ERGEBNIS
}

class BildBackend(QObject):
    infoBereit = Signal(str)
    ergebnisBereit = Signal(QUrl)
    zwischenbildBereit = Signal(QUrl)
    fehlerBereit = Signal(str)
    verarbeitenGestartet = Signal(bool)
    verarbeitungFehler = Signal(str)

    def __init__(self):
        super().__init__()
        self.pfad = None
        self.farbe = (0, 0, 0)
        self.zellen_groesse = None
        self.modus = None
        self._thread = None
        self._worker = None
        self._masken = None
        self._hat_zwischenstand = False
        self._toleranz = None

    @Slot(QUrl)
    def bild_gewaehlt(self, url):
        pfad = url.toLocalFile()

        try:
            groesse_kib = os.path.getsize(pfad) / 1024
            with Image.open(pfad) as img:
                breite, hoehe = img.size
        except Exception as e:
            self.infoBereit.emit(f"Kann Bild nicht lesen: {e}")
            return
        self.pfad = pfad
        self._hat_zwischenstand = False
        self._masken = None
        text = f"{os.path.basename(self.pfad)} - {breite}*{hoehe} px, {groesse_kib:.1f} KIB"
        self.infoBereit.emit(text)

    @Slot(str)
    def color_conversion(self, hex_farbe):
        hex_farbe = hex_farbe.lstrip("#")
        self.farbe = tuple(int(hex_farbe[i:i+2],16)for i in (0, 2, 4))


    @Slot(float, int, str, bool)
    def verarbeiten(self, zellen_groesse, toleranz, modus, mit_korrektur):
        self._masken = None
        if self.pfad is None:
            text = self.tr("ein Bild muss gewählt werden zum Verarbeiten")
            self.fehlerBereit.emit(text)
            return
        self._toleranz = toleranz
        if mit_korrektur:
            self.zellen_groesse = zellen_groesse
            self.modus = modus
            self._starte(Phase_oneWorker(self.pfad, toleranz), self._auf_zwischenbild)
        else:
            self._starte(StandardWorker(self.pfad, zellen_groesse, toleranz, self.farbe, modus), self._auf_ergebnis)

    @Slot(float, int, str)
    def neu_rendern(self, zellen_groesse, toleranz, modus):
        maske_hinzufuegen, maske_entfernen, maske_einfaerben = self._masken if self._masken else (None, None, None)
        if not self._hat_zwischenstand:
            text = self.tr("Bitte zuerst Bild verarbeiten")
            self.fehlerBereit.emit(text)
            return
        if self._toleranz == toleranz:
            self._starte(Phase_twoWorker(zellen_groesse, self.farbe, modus, maske_entfernen=maske_entfernen,maske_hinzufuegen=maske_hinzufuegen, maske_einfaerben=maske_einfaerben), self._auf_ergebnis)
        else:

            self._toleranz = toleranz
            self._starte(StandardWorker(self.pfad, zellen_groesse, toleranz, self.farbe, modus, maske_entfernen=maske_entfernen,maske_hinzufuegen=maske_hinzufuegen, maske_einfaerben=maske_einfaerben), self._auf_ergebnis)


    def _starte(self, worker, bei_fertig):
        self._thread = QThread()
        self._worker = worker

        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.fertig.connect(bei_fertig)
        self._worker.fehler.connect(self._auf_fehler)
        self._worker.fertig.connect(self._thread.quit)
        self._worker.fehler.connect(self._thread.quit)

        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        self.verarbeitenGestartet.emit(True)

        self._thread.start()

    @Slot(str)
    def _auf_ergebnis(self, pfad):
        self._hat_zwischenstand = True
        bild = QUrl.fromLocalFile(str(pfad))
        self.ergebnisBereit.emit(bild)
    @Slot(str)
    def _auf_zwischenbild(self, pfad):
        self._hat_zwischenstand = True
        bild = QUrl.fromLocalFile(str(pfad))
        self.zwischenbildBereit.emit(bild)
    @Slot(str)
    def _auf_fehler(self, meldung):
        self.verarbeitungFehler.emit(meldung)

    @Slot(QObject)
    def korrektur_bestaetigt(self, feld):
        if self.zellen_groesse is None:
            text = self.tr("Es ist ein Fehler bei der Vermittlung aufgetreten. Bitte wiederholen Sie den Schritt des Verarbeitens mit Korrektur eingeschaltet.")
            self.fehlerBereit.emit(text)
            return
        maske_hinzufuegen, maske_entfernen, maske_einfaerben = feld.masken()
        self._masken = maske_hinzufuegen, maske_entfernen, maske_einfaerben
        self._starte(Phase_twoWorker(self.zellen_groesse, self.farbe, self.modus, maske_entfernen=maske_entfernen, maske_hinzufuegen=maske_hinzufuegen, maske_einfaerben=maske_einfaerben), self._auf_ergebnis)

    @Slot(QUrl, str)
    def download(self, ziel, art):
        try:
            ziel = ziel.toLocalFile()
            quelle = ERGEBNIS_ART[art]
            shutil.copy(quelle, ziel)
            ergebnis = self.tr(f"Die Datei wurde in {ziel} gespeichert")
            self.infoBereit.emit(ergebnis)
        except Exception as e:
            problem = self.tr(f"Speichern fehlgeschlagen: {e}")
            self.fehlerBereit.emit(problem)


class StandardWorker(QObject):
    fertig = Signal(str)
    fehler = Signal(str)



    def __init__(self, pfad, zellen_groesse, toleranz, farbe, modus,  maske_entfernen=None, maske_hinzufuegen=None, maske_einfaerben=None):
        super().__init__()
        self.pfad = pfad
        self.zellen_groesse = zellen_groesse
        self.toleranz = toleranz
        self.farbe = farbe
        self.modus = modus
        self.entfernen = maske_entfernen
        self.hinzufuegen = maske_hinzufuegen
        self.einfaerben = maske_einfaerben

    @Slot()
    def run(self):
        try:
            bild_vorbereiten(
                self.pfad,
                toleranz=(self.toleranz, self.toleranz, self.toleranz),
            )
            ergebnis = bild_rendern(
                zellen_groesse=round(self.zellen_groesse),
                farbe=self.farbe,
                nutzer_auswahl=self.modus,
                maske_entfernen=self.entfernen,
                maske_hinzufuegen=self.hinzufuegen,
                maske_einfaerben=self.einfaerben,
            )
            self.fertig.emit(str(ergebnis))
        except Exception as e:
            self.fehler.emit(str(e))



class Phase_oneWorker(QObject):
    fertig = Signal(str)
    fehler = Signal(str)

    def __init__(self, pfad, toleranz):
        super().__init__()
        self.pfad = pfad
        self.toleranz = toleranz

    @Slot()
    def run(self):
        try:
            ergebnis = bild_vorbereiten(
                self.pfad,
                toleranz=(self.toleranz, self.toleranz, self.toleranz),
            )
            self.fertig.emit(str(ergebnis))
        except Exception as e:
            self.fehler.emit(str(e))

class Phase_twoWorker(QObject):
    fertig = Signal(str)
    fehler = Signal(str)

    def __init__(self, zellen_groesse, farbe, modus, maske_entfernen, maske_hinzufuegen, maske_einfaerben):
        super().__init__()
        self.zellen_groesse = zellen_groesse
        self.farbe = farbe
        self.modus = modus
        self.entfernen = maske_entfernen
        self.hinzufuegen = maske_hinzufuegen
        self.einfaerben = maske_einfaerben

    @Slot()
    def run(self):
        try:
            ergebnis = bild_rendern(
                zellen_groesse=round(self.zellen_groesse),
                farbe=self.farbe,
                nutzer_auswahl=self.modus,
                maske_entfernen=self.entfernen,
                maske_hinzufuegen=self.hinzufuegen,
                maske_einfaerben=self.einfaerben,
            )
            self.fertig.emit(str(ergebnis))
        except Exception as e:
            self.fehler.emit(str(e))

app = QGuiApplication(sys.argv)
def qml_warnungen(warnungen):
    for w in warnungen:
        print("QML:", w.toString(), flush=True)

engine = QQmlApplicationEngine()

engine.warnings.connect(qml_warnungen)

backend = BildBackend()
engine.rootContext().setContextProperty("backend", backend)

QQuickStyle.setStyle("Material")

engine.load(USER_INTERFACE)
sys.exit(app.exec())