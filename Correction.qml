import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Malwerkzeug 1.0

    ColumnLayout {
        property url bild
        signal abgebrochen()

        ButtonGroup {id: werkzeuge}


        RowLayout {

                 Button {
                    text: qsTr("hinzufügen")
                    checkable: true
                    highlighted: checked
                    checked: true
                    ButtonGroup.group: werkzeuge
                    onClicked: malfeld.werkzeug_waehlen("hinzufuegen")
                 }

                 Button {
                    text: qsTr("entfernen")
                    checkable: true
                    highlighted: checked
                    ButtonGroup.group: werkzeuge
                    onClicked: malfeld.werkzeug_waehlen("entfernen")
                 }

                 Button {
                    text: qsTr("einfärben")
                    checkable: true
                    highlighted: checked
                    ButtonGroup.group: werkzeuge
                    onClicked: malfeld.werkzeug_waehlen("einfaerben")
                 }

                 Button {
                     text: qsTr("Radiergummi")
                     checkable: true
                     highlighted: checked
                     ButtonGroup.group: werkzeuge
                     onClicked: malfeld.werkzeug_waehlen("radierer")
                 }

                 Button {
                    text: qsTr("Bestätigen")
                    onClicked: backend.korrektur_bestaetigt(malfeld)
                 }

                 Button {
                    text: qsTr("Abbrechen")
                    onClicked: abgebrochen()
                 }

                 Button {
                    id: zurueck
                    text: qsTr("zurück")
                    onClicked: malfeld.zurueck()
                 }

                 Button {
                    id: vorwaerts
                    text: qsTr("vorwärts")
                    onClicked: malfeld.vor()
                 }

                 WertRegler {
                    id: stiftSlider
                    Layout.fillWidth: true
                    name: qsTr("Stiftdicke:")
                    einheit: " px"
                    from: 2; to:70; stepSize: 1
                    value: 2
                    onValueChanged: {
                        if (!malfeld ) {return}
                        malfeld.stift(value)
                    }
                }

        }

        Item {
            id:malBereich
            Layout.fillWidth: true
            Layout.fillHeight: true

            Image {
            id: bildAnzeigen
            anchors.fill: parent
            fillMode: Image.PreserveAspectFit
            source: bild
            cache: false
                onStatusChanged: {
                    if (status === Image.Ready) {
                        malfeld.bild_groesse_setzen(sourceSize.width, sourceSize.height)
                    }
                }
            }

            Malfeld {
                id: malfeld
                anchors.centerIn: bildAnzeigen
                width: bildAnzeigen.paintedWidth
                height: bildAnzeigen.paintedHeight

            }
        }
    }
