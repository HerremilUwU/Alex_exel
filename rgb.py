#ᓚᘏᗢ✮⋆˙✮ ⋆ ⭒˚｡⋆
def hex_to_rgb01(hex_color: str):
    # Falls ein führendes "#" vorhanden ist, entfernen
    hex_color = hex_color.lstrip('#')

    # Falls Kurzschreibweise wie #FA0 verwendet wird → erweitern
    if len(hex_color) == 3:
        hex_color = ''.join([c * 2 for c in hex_color])

    # Sicherstellen, dass genau 6 Zeichen vorhanden sind
    if len(hex_color) != 6:
        raise ValueError("Ungültiger Hex-Code. Muss 3 oder 6 Hex-Zeichen haben.")

    # Hex → Integer → 0-1 normalisieren
    r = int(hex_color[0:2], 16) / 255.0
    g = int(hex_color[2:4], 16) / 255.0
    b = int(hex_color[4:6], 16) / 255.0

    return (r, g, b)

if __name__ == "__main__":
    hex_input = input("Bitte Hex-Farbcode eingeben (z.B. #FF8800 oder FA0): ")
    try:
        rgb = hex_to_rgb01(hex_input)
        print("RGB (0-1):", rgb)
    except ValueError as e:
        print("Fehler:", e)
