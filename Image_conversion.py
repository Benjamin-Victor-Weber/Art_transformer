import numpy as np
from PIL import Image, ImageDraw, ImageFont
import cv2
from pathlib import Path

PARENT_FOLDER = Path(__file__).resolve().parent
AUSGABE = PARENT_FOLDER / "output"
VORDERGRUND = AUSGABE / "vordergrund.npy"
ZWISCHENSTAND = AUSGABE / "zwischenstand.png"
BILD_ERGEBNIS = AUSGABE / "final_punkt.png"
TEXT_ERGEBNIS = AUSGABE / "final_text.txt"
AUSGABE.mkdir(exist_ok=True)
SCHRIFTARTEN = PARENT_FOLDER / "font_library"
STANDARD_SCHRIFTART = SCHRIFTARTEN / "JetBrainsMonoNL-Regular.ttf"
class HintergrundEntferner:
    def __init__(self, toleranz, rand_breite, schwelle):
        self.toleranz = toleranz
        self.rand_breite = rand_breite
        self.schwelle = schwelle


    def entferne_hintergrund(self, bgr_bild):
        raise NotImplementedError("Unterklasse muss das selbst definieren")


    @staticmethod
    def sorting(bild, rand_breite, schwelle):

        if bild.mode in ["RGBA", "LA", "P"]:
            return AlphaHintergrund

        else:
            array_bild = np.array(bild)
            hoehe, breite = array_bild.shape[:2]
            zeile, spalte = np.indices((hoehe, breite))
            rand_maske = (zeile < rand_breite) | (zeile >= hoehe - rand_breite) | (spalte < rand_breite) | (spalte >= breite - rand_breite)
            rand_pixel = array_bild[rand_maske]
            abweichung = np.std(rand_pixel)
            modus = "komplex" if abweichung > schwelle else "simple"

            if modus == "simple":
                return SimpleHintergrund
            elif modus == "komplex":
                return KomplexerHintergrund


    def result(self, pil_bild):
        alpha_maske = np.array(pil_bild.convert("RGBA"))[:,:,3]
        schwelle, _ = cv2.threshold(alpha_maske.astype(np.uint8), 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        vordergrund = alpha_maske > schwelle
        weiss_Hintergrund = Image.new("RGBA", (pil_bild.size), (255, 255, 255, 255))
        neues_bild = Image.alpha_composite(weiss_Hintergrund, pil_bild.convert("RGBA"))
        neues_grau1 = neues_bild.convert("L")
        return neues_grau1, vordergrund

class SimpleHintergrund(HintergrundEntferner):
    def entferne_hintergrund(self, bgr_bild):
        array_bild = np.array(bgr_bild)
        alpha = np.full(array_bild.shape[:2], 255, dtype=np.uint8)
        hoehe, breite = array_bild.shape[:2]
        maske = np.zeros((hoehe + 2, breite + 2), dtype=np.uint8)
        seeds = [(0, 0), (breite - 1, 0), (0, hoehe - 1), (breite - 1,hoehe - 1)]
        for seed in seeds:
            retval, test_bild, maske, rect = cv2.floodFill(array_bild, maske, seed, (0, 0, 0), loDiff=self.toleranz, upDiff=self.toleranz)

        change_pixel = maske[1:-1, 1:-1]

        alpha[change_pixel == 1] = 0

        grau_bild = cv2.cvtColor(array_bild, cv2.COLOR_RGB2GRAY)

        ergebnis = np.dstack((grau_bild, alpha))

        pil_bild = Image.fromarray(ergebnis, mode="LA")

        return pil_bild


class KomplexerHintergrund(HintergrundEntferner):
    def __init__(self, toleranz, rand_breite, schwelle):
        super().__init__(toleranz, rand_breite, schwelle)
        from rembg import new_session # rembg lade ich erst hier da es sehr groß ist und nur für KomplexerHintergrund gebraucht wird
        self.session = new_session("isnet-anime")

    def entferne_hintergrund(self, bgr_bild):
        from rembg import remove
        output = remove(bgr_bild, session=self.session)
        return output

class AlphaHintergrund(HintergrundEntferner):
    def entferne_hintergrund(self, bgr_bild):
        return bgr_bild

def einfaerben(bild, maske):
    if maske is None:
        return bild
    if bild.shape == maske.shape:
        ergebnis = bild.copy()
        prog_bild = cv2.inpaint(ergebnis, (maske.astype(np.uint8)), 3, cv2.INPAINT_NS)
        return prog_bild
    else:
        raise ValueError(f"Maske {maske.shape} passt nicht zum Bild {bild.shape}")

def convert_drawn(bild, maske, wert):
    if maske is None:
        return bild
    if bild.shape == maske.shape and maske.dtype == bool:
        ergebnis = bild.copy()
        ergebnis[maske] = wert
        return ergebnis
    else:
        raise ValueError(f"Maske {maske.shape} passt nicht zum Bild {bild.shape}")

def kanten_filter(grau_bild):
    grau_np = np.array(grau_bild)
    outline_W = cv2.Canny(grau_np, 150, 250)
    outline_S = cv2.bitwise_not(outline_W)
    return outline_S


def berechne_ziel_zellen(original, zell_groesse, canvas_ziel_max):
    hoehe, breite = original.shape

    if hoehe > breite:
        ziel_hoehe = ziel_zellen_lange_achse = round(canvas_ziel_max / zell_groesse)
        ziel_breite = round(ziel_zellen_lange_achse * (breite / hoehe))
        ergebnis_h, ergebnis_l = min(ziel_hoehe, hoehe), min(ziel_breite, breite)
        ziel_zellen_groesse = canvas_ziel_max / ergebnis_h
        return ergebnis_h, ergebnis_l, ziel_zellen_groesse

    elif hoehe < breite:
        ziel_breite = ziel_zellen_lange_achse = round(canvas_ziel_max / zell_groesse)
        ziel_hoehe = round(ziel_zellen_lange_achse * (hoehe / breite))
        ergebnis_h, ergebnis_l = min(ziel_hoehe, hoehe), min(ziel_breite, breite)
        ziel_zellen_groesse = canvas_ziel_max / ergebnis_l
        return ergebnis_h, ergebnis_l, ziel_zellen_groesse

    elif hoehe == breite:
        ziel_hoehe = ziel_zellen_lange_achse = round(canvas_ziel_max / zell_groesse)
        ziel_breite = round(ziel_zellen_lange_achse * (breite / hoehe))
        ergebnis_h, ergebnis_l = min(ziel_hoehe, hoehe), min(ziel_breite, breite)
        ziel_zellen_groesse = canvas_ziel_max / ergebnis_h
        return ergebnis_h, ergebnis_l, ziel_zellen_groesse



def compression(im1,ziel_hoehe, ziel_breite, aggregat):
    o_height, o_length, = im1.shape[:2]
    image = np.array(im1)
    g_height, g_length = ziel_hoehe, ziel_breite
    blank_canvas = np.zeros((g_height, g_length), dtype=np.uint8)

    for g_x in range(g_height):
        for g_y in range(g_length):
            s_height = round(g_x * o_height / g_height)
            e_height = round((g_x + 1) * o_height / g_height)
            s_length = round(g_y * o_length / g_length)
            e_length = round((g_y + 1) * o_length / g_length)

            block = image[s_height:e_height, s_length:e_length]
            blank_canvas[g_x, g_y] = np.round(aggregat(block))
    return blank_canvas


def winkel_zu_zeichen(winkel):

    winkel_grad = winkel % 180
    if winkel_grad <= 45:
        return "-"
    if winkel_grad >= 45 and winkel_grad < 80:
        return "\\"
    if winkel_grad >= 80 and winkel_grad < 100:
        return "|"
    if winkel_grad >= 100 and winkel_grad <= 135:
        return "/"
    if winkel_grad > 135 and winkel_grad <= 180:
        return "-"

def dichte_zu_zeichen(helligkeit):
    if helligkeit <= 40:
        return "@"
    elif helligkeit >= 40 and helligkeit < 80:
        return "#"
    elif helligkeit >= 80 and helligkeit < 120:
        return ","
    elif helligkeit >= 120 and helligkeit <= 180:
        return "."
    else:
        return " "



class Renderer:
    def __init__(self, zell_groesse, farbe, font):
        self.zell_groesse = zell_groesse
        self.farbe = farbe
        self.font = font

    def zeichne_zelle(self, canvas, center_x, center_y, ist_kante, winkel, dichte_wert, subject):
        raise NotImplementedError("Unterklasse muss das selbst definieren")

    def rendern(self, kanten_array, dichte_array, vordergrund):
        z_x, z_y = kanten_array.shape[:2]
        g_x, g_y = round(z_x * self.zell_groesse), round(z_y * self.zell_groesse)
        canvas = Image.new("RGBA", (g_y, g_x), (0,0,0,0))
        y_grad_gesamt, x_grad_gesamt = np.gradient(dichte_array.astype(float))

        for a in range(z_x):
            for b in range(z_y):

                s_height = round(a * self.zell_groesse)
                e_height = round((a + 1) * self.zell_groesse)
                s_length = round(b * self.zell_groesse)
                e_length = round((b + 1) * self.zell_groesse)

                center_y, center_x = ((s_height + e_height) // 2), ((s_length + e_length) // 2)

                y_grad = y_grad_gesamt[a, b]
                x_grad = x_grad_gesamt[a, b]
                winkel = (np.degrees(np.arctan2(y_grad, x_grad)))+90

                ist_kante = (kanten_array[a, b] == 0)
                dichte_wert = dichte_array[a, b]
                subject = vordergrund[a, b]

                if ist_kante or dichte_wert <= 180:
                    self.zeichne_zelle(canvas, center_x, center_y, ist_kante=ist_kante, winkel=winkel, dichte_wert=dichte_wert, subject=subject)


        return canvas


class PunktRenderer(Renderer):
    def zeichne_zelle(self, canvas, center_x, center_y, ist_kante, winkel, dichte_wert, subject):
        draw = ImageDraw.Draw(canvas)
        radius = 0.5
        if ist_kante:
            dekungs_wert = 255
        elif dichte_wert <= 180:
            dekungs_wert = int(255 - dichte_wert)
        else:
            dekungs_wert = 0
        center = (center_x - radius, center_y - radius, center_x + radius, center_y + radius)
        draw.ellipse(center, fill=(*self.farbe, dekungs_wert))


class ZeichenRenderer(Renderer):
    def zeichne_zelle(self, canvas, center_x, center_y, ist_kante, winkel, dichte_wert, subject):
        if ist_kante:
            zeichen = winkel_zu_zeichen(winkel)
        else:
            zeichen = dichte_zu_zeichen(dichte_wert)
        draw = ImageDraw.Draw(canvas)
        draw.text((center_x, center_y), zeichen, fill=self.farbe, font=self.font, anchor="mm")


def als_text(kanten_array, dichte_array):
    z_x, z_y = kanten_array.shape[:2]
    y_grad_gesamt, x_grad_gesamt = np.gradient(dichte_array.astype(float))

    liste_hoehe = []
    for a in range(z_x):
        liste_breite = []
        for b in range(z_y):

            y_grad = y_grad_gesamt[a, b]
            x_grad = x_grad_gesamt[a, b]
            winkel = (np.degrees(np.arctan2(y_grad, x_grad))) + 90

            ist_kante = (kanten_array[a, b] == 0)
            dichte_wert = dichte_array[a, b]

            if ist_kante:
                zeichen = winkel_zu_zeichen(winkel)
            else:
                zeichen = dichte_zu_zeichen(dichte_wert)
            liste_breite.append(zeichen)
        liste_hoehe.append("".join(liste_breite))
    text_liste = "\n".join(liste_hoehe)
    return text_liste


def bild_vorbereiten(bild_pfad, toleranz=(10, 10, 10), rand_breite=5, schwelle=30):

    im1 = Image.open(bild_pfad)

    KlasseGefunden = HintergrundEntferner.sorting(im1, rand_breite, schwelle)
    entferner = KlasseGefunden(toleranz, rand_breite, schwelle)
    pil_bild = entferner.entferne_hintergrund(im1)
    fertig_grau, vordergrund = entferner.result(pil_bild)
    fertig_grau.save(ZWISCHENSTAND)
    np.save(VORDERGRUND, vordergrund)
    return ZWISCHENSTAND




def bild_rendern(maske_entfernen=None, maske_hinzufuegen=None, maske_einfaerben=None, zellen_groesse=4, canvas_ziel_max=3330, farbe=(255, 0, 0), font_pfad=STANDARD_SCHRIFTART, nutzer_auswahl="punkte", ziel_groesse=(853, 1440),text_breite = 100):

    vordergrund = np.load(VORDERGRUND)



    prep_bild = np.array(Image.open(ZWISCHENSTAND))

    inpainted_bild = einfaerben(prep_bild, maske_einfaerben)

    ready_picture = convert_drawn(bild=inpainted_bild, maske=maske_entfernen, wert=255)

    kanten_canny = kanten_filter(ready_picture)

    kanten_finale = convert_drawn(bild=kanten_canny, maske=maske_hinzufuegen, wert=0)


    ziel_hoehe, ziel_breite, ziel_zellen_groesse = berechne_ziel_zellen(ready_picture, zellen_groesse, canvas_ziel_max)

    subject = compression(vordergrund, ziel_hoehe, ziel_breite, aggregat=np.mean)
    kanten_kompakt = compression(kanten_finale, ziel_hoehe, ziel_breite, aggregat=np.min)
    dichte_kompakt = compression(ready_picture, ziel_hoehe, ziel_breite, aggregat=np.mean)

    bild_hoehe, bild_breite = ready_picture.shape[:2]
    zeilen_hoehe = round(text_breite * (bild_hoehe / bild_breite) / 2)
    kanten_kompakt_text = compression(kanten_finale, zeilen_hoehe, text_breite, aggregat=np.min)
    dichte_kompakt_text = compression(ready_picture, zeilen_hoehe, text_breite, aggregat=np.mean)

    text_rendern = als_text(kanten_kompakt_text, dichte_kompakt_text)

    with open(TEXT_ERGEBNIS, "w", encoding="utf-8") as file:
        file.write(text_rendern)

    zeichen_art = ImageFont.truetype(font_pfad, ziel_zellen_groesse * 0.9)

    RENDERER_REGISTRY = {
        "punkte": PunktRenderer,
        "zeichen": ZeichenRenderer,
    }

    renderer_klasse = RENDERER_REGISTRY[nutzer_auswahl]

    gerendert = renderer_klasse(ziel_zellen_groesse, farbe, zeichen_art).rendern(kanten_kompakt, dichte_kompakt, subject)

    gerendert.thumbnail(ziel_groesse)
    ziel_bild = BILD_ERGEBNIS
    gerendert.save(ziel_bild)
    return ziel_bild







