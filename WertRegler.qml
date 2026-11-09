import QtQuick
import QtQuick.Controls.Material
import QtQuick.Layouts


ColumnLayout {
    property string name: ""
    property string einheit: ""
    property alias from: regler.from
    property alias to: regler.to
    property alias stepSize: regler.stepSize
    property alias value: regler.value

    RowLayout {
        Label { text: name }
        Item {Layout.fillWidth: true}
        Label {
            text: Math.round(value) + einheit
            color: Material.accent
            }
    }

    Slider {
        id: regler
        Layout.fillWidth: true
    }
}