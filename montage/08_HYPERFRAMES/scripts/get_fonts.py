"""Télécharge les polices de la chaîne (Google Fonts, licence SIL OFL) en woff2 local → assets/fonts/.
Hyperframes exige un @font-face vers un fichier local (rendu déterministe, pas de réseau au rendu)."""
import re, urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "assets" / "fonts"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36"}
FAMILIES = {"Inter Tight": [500, 600, 800, 900], "JetBrains Mono": [400, 500, 700], "DM Serif Display": [400], "Montserrat": [800, 900]}

OUT.mkdir(parents=True, exist_ok=True)
css_out = []
for fam, weights in FAMILIES.items():
    url = f"https://fonts.googleapis.com/css2?family={fam.replace(' ', '+')}:wght@{';'.join(map(str, weights))}&display=block"
    css = urllib.request.urlopen(urllib.request.Request(url, headers=UA)).read().decode()
    # un bloc par (sous-ensemble, graisse) : on garde latin + latin-ext
    for comment, block in re.findall(r"/\* ([\w-]+) \*/\s*(@font-face \{.*?\})", css, re.S):
        if comment not in ("latin", "latin-ext"):
            continue
        w = re.search(r"font-weight: (\d+)", block).group(1)
        src = re.search(r"url\((.*?)\)", block).group(1)
        rng = re.search(r"unicode-range: (.*?);", block).group(1)
        name = f"{fam.replace(' ', '')}-{w}-{comment}.woff2"
        (OUT / name).write_bytes(urllib.request.urlopen(urllib.request.Request(src, headers=UA)).read())
        css_out.append(f'@font-face {{ font-family: "{fam}"; font-weight: {w}; font-style: normal; font-display: block;\n'
                       f'  src: url("../assets/fonts/{name}") format("woff2"); unicode-range: {rng}; }}')
        print(name)
(OUT / "fonts.css").write_text("\n".join(css_out) + "\n", encoding="utf-8")
print(len(css_out), "polices →", OUT)
