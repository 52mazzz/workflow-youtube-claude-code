"""Génère compositions/<type>.html (un fichier fin par élément du kit, éditable dans le Studio Hyperframes).
Toute la logique est dans kit/tsar.js ; ici seulement : taille, durée par défaut, variables et leurs valeurs par défaut.
Relancer après avoir ajouté un type dans SPECS.   python scripts/make_compositions.py"""
import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
S = lambda i, d, label=None: {"id": i, "type": "string", "label": label or i, "default": d}
C = lambda i, d, label=None: {"id": i, "type": "color", "label": label or i, "default": d}
N = lambda i, d, label=None: {"id": i, "type": "number", "label": label or i, "default": d}
Bo = lambda i, d, label=None: {"id": i, "type": "boolean", "label": label or i, "default": d}
J = lambda i, d, label=None: S(i, json.dumps(d, ensure_ascii=False), label)

# type : (durée par défaut, transparent ?, variables)
SPECS = {
    "chapitre": (3.2, True, [S("surtitre", "PARTIE 1"), S("titre", "Claude Opus 5.5"), C("couleur", "#E07A5A")]),
    "test": (3.0, True, [S("fenetre", "Test 01 · Claude"), S("titre", "Nuit"), C("couleur", "#E07A5A")]),
    "annotation": (3.5, True, [S("texte", "Nuages et ciel modélisés en 3D"), C("couleur", "#E07A5A"), Bo("alerte", False)]),
    "etiquette": (3.7, True, [S("texte", "Minecraft · vanilla"), C("couleur", "#8BC34A"), S("position", "haut-gauche"), N("taille", 34), S("icone", "")]),
    "etiquettes": (6.0, True, [J("items", [[0.0, "Vanilla", "#8BC34A"], [2.0, "Claude", "#E07A5A", "burst"], [4.0, "Astra", "#3CCFB0", "knot"]]), N("taille", 52)]),
    "point": (2.5, True, [S("texte", "+1 Claude"), C("couleur", "#E07A5A")]),
    "manche": (4.0, True, [N("n", 1), N("total", 7), S("theme", "Lumières"), S("nomA", "Claude Opus 5.5"), S("nomB", "GPT-6 Astra"),
                           S("courtA", "Claude"), S("courtB", "Astra"), C("couleurA", "#E07A5A"), C("couleurB", "#3CCFB0"),
                           N("avantA", 0), N("avantB", 0), S("gagnant", "a"), N("a", 2.7)]),
    "reaction": (1.9, True, [S("humeur", "surprise"), N("x", 1600), N("taille", 500)]),
    "soustitre": (2.5, True, [J("mots", [{"text": "C'est", "t": 0.0}, {"text": "vraiment", "t": 0.25}, {"text": "choquant", "t": 0.6}]),
                              N("taille", 76), N("bas", 110), N("largeur", 1500), S("style", "")]),
    "obturateur": (0.5, True, []),
    "flash": (0.42, True, []),
    "abonnement": (4.6, True, [S("nom", "tsar rouge555"), S("handle", "letsar555"), S("detail", ""), N("y", 740), N("taille", 1)]),
    "barres": (6.5, True, [S("titre", "Temps de création"), J("lignes", [{"nom": "GPT-6 Astra", "couleur": "#3CCFB0", "valeur": 60, "texte": "36 min", "t": 0.8},
                                                                          {"nom": "Claude Opus 5.5", "couleur": "#E07A5A", "valeur": 100, "texte": "~1 h", "t": 3.0}])]),
    "scene_fenetre": (6.0, False, [C("fond", "#E5383B"), S("titre", "Nouveau prompt"), C("couleur", "#E5383B"), S("surtitre", "LA MISSION"),
                                   J("lignes", [{"t": 0.4, "texte": "Crée ton propre shader Minecraft."}, {"t": 1.8, "texte": "Objectif : le jeu le plus réaliste possible.", "gris": True}]),
                                   N("taille", 64), N("largeur", 1360), S("humeur", "")]),
    "scene_description": (5.0, False, [C("fond", "#E5383B"), S("titre", "J'ai fait refaire Pokémon à Claude et ChatGPT"), S("chaine", "tsar rouge555"),
                                       S("intro", "Le prompt donné aux deux IA :"),
                                       J("lignes", [{"t": 0.5, "texte": "Crée le jeu de capture de créatures le plus impressionnant possible…"}]),
                                       J("surligne", ["10 créatures"]), S("etiquette", "Le prompt est dans la description"), N("etiquetteA", 0.6)]),
    "scene_vs": (9.5, False, [C("fond", "#E5383B"), J("A", {"nom": "Claude Opus 5.5", "couleur": "#E07A5A", "ecran": "ciel", "texte": "OPUS 5.5", "marque": "Anthropic", "entree": 0.05, "icone": "burst"}),
                              J("B", {"nom": "ChatGPT 6 Astra", "couleur": "#3CCFB0", "ecran": "galaxie", "texte": "GPT-6 · Astra", "marque": "OpenAI", "entree": 2.0, "icone": "knot"}),
                              N("vs", 3.2)]),
    "scene_vainqueur": (3.0, False, [S("titre", "Résultat final"), S("nom", "Claude Opus 5.5"), C("couleur", "#E07A5A"), S("detail", "6 manches à 1")]),
    "scene_outro": (4.3, False, [S("question", 'Et toi, tu préfères <span style="color:var(--claude)">Claude</span> ou <span style="color:var(--astra)">Astra</span> ?'),
                                 S("appel", "Dis-le en commentaire"), S("merci", "Merci d'avoir regardé !")]),
    "scene_fond": (5.0, False, [C("couleur", "#E5383B")]),
    # style WOLF, méthode par défaut de la vidéo longue (2026-10-06), comme ses vidéos
    "pastille": (20.0, True, [S("texte", "Le combat"), N("taille", 64), J("etat", [[12.0, "ok"]]), S("place", ""), N("haut", 300)]),
    "carte": (8.0, True, [S("texte", "CLAUDE"), C("fond", "#2F6FED"), S("logo", "claude"), N("plein", 2.5)]),
    "progression": (2.5, False, [J("tests", [{"nom": "Le combat", "gagnant": "a"}, {"nom": "La carte", "gagnant": "b"}, {"nom": "Les bugs", "gagnant": ""}]),
                                 N("actuel", 1), N("a", 1.0), S("nomA", "CLAUDE"), C("couleurA", "#E07A5A"), S("logoA", "claude"),
                                 S("nomB", "CHATGPT"), C("couleurB", "#3CCFB0"), S("logoB", "chatgpt")]),
    # frise des objets entre deux tests, caméra qui glisse (rick-morty-ia, 2026-10-15)
    "frise": (2.4, False, [J("objets", [{"nom": "Pistolet à portails"}, {"nom": "Le vaisseau"}, {"nom": "Cornichon Rick"}]),
                           N("actuel", 1), N("a", 0.7), C("couleur", "#E5383B"), C("fond", "#E5383B"), S("style_fond", "vagues")]),
    "capture": (3.0, True, [S("image", "assets/logos/claude.svg"), J("zone", [0.3, 0.45, 0.4, 0.1]), J("zones", []), N("a", 0.6), N("largeur", 1300)]),
    "insert": (0.8, False, [S("image", "assets/logos/claude.svg"), C("fond", "#0C0E12")]),
    "vignette": (1.5, True, [S("image", "assets/logos/claude.svg"), N("largeur", 520), N("hauteur", 520), N("x", 0.5), N("y", 0.5),
                             N("rotation", -4), C("fond", "#0C0E12"), C("bord", "#FFFFFF"), Bo("cadre", True)]),
    # direction « duel lisible et nerveux » (2026-10-07)
    "noms_partage": (3.0, True, [S("nomA", "CLAUDE"), S("nomB", "CHATGPT")]),
    "duel": (2.6, True, [S("nomA", "CLAUDE"), S("logoA", "claude"), C("couleurA", "#E07A5A"), N("a", 0.0),
                         S("nomB", "CHATGPT"), S("logoB", "chatgpt"), C("couleurB", "#3CCFB0"), N("b", 0.6), N("vs", 1.2), Bo("seul", False)]),
    "titre_jeu": (1.6, True, [S("image", ""), S("texte", "MINECRAFT"), N("largeur", 1100)]),
    "minuteur": (3.0, True, [N("de", 2700), N("a", 2697), S("position", "haut-gauche"), N("taille", 220)]),
    "accelere": (4.0, True, [S("texte", "×10")]),
    "a_venir": (3.0, True, [S("texte", "À VENIR")]),
    "note": (4.0, True, [S("nom", "CLAUDE"), S("logo", "claude"), C("couleur", "#E07A5A"), S("note", "8/10"),
                         J("points", [["+", "Les combats"], ["+", "Les créatures"], ["-", "La carte est vide"]]), N("a", 0.6)]),
    "fleche": (2.5, True, [S("texte", "La capture"), N("x", 0.62), N("y", 0.55), S("cote", "gauche")]),
    "mot": (1.2, True, [S("texte", "PUBLICITÉ"), C("couleur", "#FFFFFF")]),
    "scene_mots": (3.0, False, [C("fond", "#E5383B"), J("items", [{"t": 0.0, "texte": "UNE PHRASE", "icone": "bulle"},
                                                                   {"t": 0.8, "texte": "10 MINUTES", "icone": "chrono", "couleur": "#F5B942"},
                                                                   {"t": 1.6, "texte": "CLAUDE", "logo": "claude", "souligne": True}])]),
    "score": (1.8, True, [N("avantA", 0), N("avantB", 0), S("point", "a"), N("a", 0.8), S("nomA", "CLAUDE"), C("couleurA", "#E07A5A"),
                          S("logoA", "claude"), S("nomB", "CHATGPT"), C("couleurB", "#3CCFB0"), S("logoB", "chatgpt")]),
}


def font_faces() -> str:
    """@font-face en ligne (exigé par le lint Hyperframes), chemins depuis la racine du projet."""
    css = (ROOT / "assets" / "fonts" / "fonts.css").read_text(encoding="utf-8")
    return css.replace("../assets/fonts/", "assets/fonts/")


def page(kind: str, dur: float, transparent: bool, variables: list, width=1920, height=1080) -> str:
    vars_attr = json.dumps(variables, ensure_ascii=False).replace("'", "&#39;")
    bg = "transparent" if transparent else "#050506"
    return f"""<!doctype html>
<html lang="fr" data-composition-variables='{vars_attr}'>
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width={width}, height={height}" />
    <!-- Élément du kit TSAR ({"transparent → MOV pour CapCut" if transparent else "scène plein écran → MP4"}). Généré par scripts/make_compositions.py -->
    <script src="assets/vendor/gsap.min.js"></script>
    <link rel="stylesheet" href="kit/tsar.css" />
    <style>
{font_faces()}
      #root {{ width: 100%; height: 100%; background: {bg}; }}
    </style>
  </head>
  <body>
    <div id="root" data-composition-id="{kind}" data-start="0" data-duration="{dur}" data-fps="60" data-width="{width}" data-height="{height}"></div>
    <script src="kit/tsar.js"></script>
    <script>TSAR.run("{kind}", "{kind}");</script>
  </body>
</html>
"""


if __name__ == "__main__":
    out = ROOT / "compositions"
    out.mkdir(exist_ok=True)
    for kind, (dur, transparent, variables) in SPECS.items():
        (out / f"{kind}.html").write_text(page(kind, dur, transparent, variables), encoding="utf-8")
    print(len(SPECS), "compositions dans", out)
