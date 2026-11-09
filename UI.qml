import QtQuick
import QtQuick.Controls.Material
import QtQuick.Dialogs
import QtQuick.Layouts
import QtCore

ApplicationWindow {
    title: qsTr("Art Transformer")
    visible: true
    width: 1200
    height: 800
    property bool amVerarbeiten: false
    property bool istFehler: false
    Material.theme: Material.Dark
    Material.accent: "#00f0ff"
    Material.background: "#0b0b0d"
    font.family: jetBrainsFont.font.family

    FontLoader {
        id: jetBrainsFont
        source: "font_library/JetBrainsMonoNL-Regular.ttf"
    }

    footer: ToolBar {
        Label {
            id: statusText
            anchors.fill: parent
            anchors.leftMargin: 12
            verticalAlignment: Text.AlignVCenter
            text: ""
            color: istFehler ? "#ff2e88" : Material.foreground
        }
    }

    StackLayout {
        id: seiten
        anchors.fill: parent
        currentIndex: 0

        RowLayout {

            Pane {

                  Layout.preferredWidth: 280
                  Layout.fillHeight: true
                  Material.background: "#16161a"

                  ColumnLayout {
                                anchors.fill: parent

                                Button {
                                        id: bild_quelle

                                        text: qsTr("Datei wählen")
                                        onClicked: fileDialog.open()
                                }

                                WertRegler {
                                    id: zellenSlider
                                    Layout.fillWidth: true
                                    name: qsTr("Zellengröße:")
                                    einheit: " px"
                                    from: 4; to:20; stepSize: 1
                                    value: 4
                                }

                                WertRegler {
                                    id: toleranzSlider
                                    Layout.fillWidth: true
                                    name: qsTr("Toleranz:")
                                    from: 1; to:80; stepSize: 1
                                    value: 10
                                }

                                RowLayout {

                                            Button {
                                                text: qsTr("Farbe wählen")
                                                onClicked: colorDialog.open()
                                            }

                                            Rectangle {
                                                width: 40
                                                height: 40
                                                radius: 5

                                                color: colorDialog.selectedColor
                                            }
                                }

                                ComboBox {
                                    id: modus
                                    model: ["punkte", "zeichen"]
                                }

                                Switch {
                                    id: korrektur
                                    text: qsTr("Mit Korrektur")
                                    checked: false
                                }

                                Button {
                                        id: verarbeiten

                                        text: qsTr("Bild verarbeiten")
                                        onClicked: backend.verarbeiten(zellenSlider.value, toleranzSlider.value, modus.currentText, korrektur.checked)
                                        enabled: !amVerarbeiten

                                }

                                Button {
                                        id: nochmalVerarbeiten
                                        text: qsTr("Neu Rendern")
                                        onClicked: backend.neu_rendern(zellenSlider.value, toleranzSlider.value, modus.currentText)
                                        enabled: finalImage.status === Image.Ready && !amVerarbeiten
                                }

                                Item {
                                     Layout.fillHeight: true
                                }

                                Button {
                                    id: png_Download
                                    text: qsTr("PNG speichern")
                                    onClicked: { speicherDialog.art = "png"; speicherDialog.open() }
                                    enabled: finalImage.status === Image.Ready && !amVerarbeiten
                                }

                                Button {
                                    id: text_Download
                                    text: qsTr("TXT speichern")
                                    onClicked: { speicherDialog.art = "txt"; speicherDialog.open() }
                                    enabled: finalImage.status === Image.Ready && !amVerarbeiten
                                }
                  }
            }

            RowLayout {
                       Layout.fillWidth: true
                       Layout.fillHeight: true

                        ColumnLayout {
                                      Layout.fillWidth: true
                                      Layout.fillHeight: true

                                      Label {
                                             text: qsTr("Original")
                                      }

                                       Item {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true


                                            Image {
                                                id: previewImage
                                                anchors.fill: parent
                                                fillMode: Image.PreserveAspectFit
                                                mipmap: true

                                            }
                                            Label {
                                                id: fehlerText
                                                anchors.centerIn: parent
                                                text: qsTr("Noch kein Bild gewählt")
                                                color: "#999999"
                                                visible: previewImage.status !== Image.Ready
                                            }
                                       }
                        }


                        ColumnLayout {
                                      Layout.fillWidth: true
                                      Layout.fillHeight: true

                                      Label {
                                             text: qsTr("Ergebnis")
                                      }

                                      Item {
                                            Layout.fillWidth: true
                                            Layout.fillHeight: true

                                                Image {
                                                    id: finalImage
                                                    cache: false
                                                    anchors.fill: parent
                                                    fillMode: Image.PreserveAspectFit
                                                    mipmap: true
                                                }

                                                BusyIndicator {
                                                    anchors.centerIn: parent
                                                    running: amVerarbeiten
                                                }
                                      }

                        }
            }
        }
            FileDialog {
                id: fileDialog
                fileMode: FileDialog.OpenFile
                nameFilters: ["Bilder (*.png *.jpg *.jpeg *.webp)"]

                onAccepted: {
                    finalImage.source = ""
                    previewImage.source = fileDialog.selectedFile
                    backend.bild_gewaehlt(fileDialog.selectedFile)
                }
            }

            FileDialog {
                id: speicherDialog
                property string art: "png"
                fileMode: FileDialog.SaveFile
                currentFolder: StandardPaths.writableLocation(StandardPaths.DownloadLocation)
                defaultSuffix: art
                nameFilters: art === "png" ? ["PNG-Bild (*.png)"] : ["Textdatei (*.txt)"]
                onAccepted: backend.download(selectedFile, art)
            }


            ColorDialog {
                id: colorDialog
                selectedColor: "white"
                onAccepted: backend.color_conversion(selectedColor)
                Component.onCompleted: backend.color_conversion(selectedColor)

            }

            Connections {
                target: backend
                function onInfoBereit(nachricht) {
                    statusText.text = nachricht
                    istFehler = false
                }
                function onFehlerBereit(nachricht) {
                    statusText.text = nachricht
                    amVerarbeiten = false
                    istFehler = true
                    seiten.currentIndex = 0
                }
                function onVerarbeitungFehler(nachricht) {
                    statusText.text = `${qsTr("Fehler bei der Verarbeitung")}: ${nachricht}`
                    amVerarbeiten = false
                    istFehler = true
                    seiten.currentIndex = 0
                }
                function onErgebnisBereit(bild) {
                    statusText.text = qsTr("Fertig, Ergebnis kann gespeichert werden")
                    finalImage.source = ""
                    finalImage.source = bild
                    amVerarbeiten = false
                    istFehler = false
                    seiten.currentIndex = 0
                }
                function onVerarbeitenGestartet(nachricht) {
                    statusText.text = qsTr("Verarbeite...")
                    amVerarbeiten = nachricht
                    istFehler = false
                    seiten.currentIndex = 0
                }
                function onZwischenbildBereit(bild) {
                    statusText.text = qsTr("Korrektur nach Bearbeitung bestätigen")
                    korrekturSeite.bild = ""
                    korrekturSeite.bild = bild
                    amVerarbeiten = false
                    istFehler = false
                    seiten.currentIndex = 1
                }
            }


        Correction {
            id: korrekturSeite
            onAbgebrochen: seiten.currentIndex = 0
        }
    }
}