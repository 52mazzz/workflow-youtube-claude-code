"""Chemins et lecture communs à tous les scripts de montage (une vidéo = videos/<id>/video.json)."""
import json, os, subprocess
from pathlib import Path

HF = Path(__file__).resolve().parent.parent  # 08_HYPERFRAMES (l'atelier)
ROOT = HF.parent  # montage/ du dépôt (ancien « Claude montage »)
# rushs bruts (lecture seule) : Documents\TSAR\Videos\<Nom de la vidéo>\Rush\ ; TSAR_RUSH force un seul dossier.
# L'ancien dossier commun Documents\TSAR\Rush reste lu. Les noms date-heure d'OBS sont uniques : on cherche partout.
TSAR = Path.home() / "Documents" / "TSAR"
VIDEOS_RUSH = TSAR / "Videos"
RUSH_EXT = (".mkv", ".mp4", ".mov")


def dossiers_rush() -> list[Path]:
    if os.environ.get("TSAR_RUSH"):
        return [Path(os.environ["TSAR_RUSH"])]
    racines = [VIDEOS_RUSH, TSAR / "Vidéos"]  # le dossier porte l'accent sur le fixe (2026-10-13)
    return [d for r in racines for d in sorted(r.glob("*/Rush"))] + [d for d in [TSAR / "Rush"] if d.is_dir()]


def rushes(motif: str = "*") -> list[Path]:
    """Rushs dont le nom correspond au motif (« 2026-10-02* », avec ou sans extension), tous dossiers confondus."""
    out = []
    for d in dossiers_rush():
        out += [f for f in d.glob(motif if Path(motif).suffix else motif + ".*") if f.suffix.lower() in RUSH_EXT]
    return sorted(out, key=lambda f: f.name)


def rush(nom: str, dossier=None) -> Path:
    """Chemin d'un rush d'après son nom (« 2026-10-02 11-34-03 », extension facultative), d'abord dans `dossier`
    (rush_dir d'une liste de dérushage) s'il est donné, sinon dans tous les dossiers de rushs."""
    import glob
    if dossier:
        for f in [Path(dossier) / nom] + [Path(dossier) / f"{nom}{e}" for e in RUSH_EXT]:
            if f.is_file():
                return f
    trouves = rushes(glob.escape(nom))
    if not trouves:
        raise FileNotFoundError(f"rush introuvable : {nom} (dans {', '.join(map(str, dossiers_rush())) or VIDEOS_RUSH})")
    return trouves[0]


def est_rush(chemin) -> bool:
    """Plan de rush (et non scène de motion design exportée en .mp4) dans une timeline CapCut : rangé dans un
    dossier de rushs, ou .mkv d'OBS rangé ailleurs."""
    p = Path(chemin)
    if p.suffix.lower() not in RUSH_EXT:
        return False
    return p.suffix.lower() == ".mkv" or any(d.resolve() in p.resolve().parents for d in dossiers_rush())


def dossier_rush_video(nom_video: str) -> Path:
    """Videos\\<Nom>\\Rush d'une vidéo : « pokemon-ia » retrouve « Pokémon IA » (accents, casse, espaces ignorés)."""
    import unicodedata
    cle = lambda s: "".join(c for c in unicodedata.normalize("NFKD", s.lower()) if c.isalnum())
    for d in sorted(VIDEOS_RUSH.glob("*/Rush")):
        if cle(d.parent.name) == cle(nom_video):
            return d
    return VIDEOS_RUSH / nom_video / "Rush"
DRAFTS = Path(os.path.expandvars(r"%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft"))
ANALYSE = ROOT / "02_ANALYSE"
MUSIQUES = ROOT / "04_RESSOURCES" / "musiques"
SFX = HF / "assets" / "sfx"
# whisper.cpp 1.9.2 sur la carte graphique s'il est présent : .whisper/cuda (release cublas, PC fixe NVIDIA), sinon
# .whisper/vulkan (compilé, puce Intel Arc du portable), sinon la version processeur. TSAR_WHISPER=cpu force le processeur.
_CUDA = HF / ".whisper" / "cuda" / "whisper-cli.exe"
_VK = HF / ".whisper" / "vulkan" / "whisper-cli.exe"
_CPU = HF / ".whisper" / "v1.9.2" / "Release" / "whisper-cli.exe"
WHISPER = _CPU if os.environ.get("TSAR_WHISPER", "").lower() == "cpu" else next(
    (p for p in (_CUDA, _VK) if p.exists()), _CPU)
MODEL = HF / ".whisper" / "ggml-large-v3-turbo-q5_0.bin"


def _nvenc() -> bool:
    if os.environ.get("TSAR_GPU", "1") == "0":
        return False
    try:
        return "h264_nvenc" in subprocess.run(["ffmpeg", "-hide_banner", "-encoders"], capture_output=True, text=True).stdout \
            and subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=s=256x256:d=0.1", "-c:v", "h264_nvenc",
                                "-f", "null", "-"], capture_output=True).returncode == 0
    except OSError:
        return False


NVENC = _nvenc()  # encodeur H.264 de la carte NVIDIA (PC fixe) ; TSAR_GPU=0 force le processeur


def h264(crf: int, preset: str = "medium") -> list:
    """Arguments ffmpeg d'encodage H.264 : NVENC à qualité constante équivalente si la carte est là, sinon libx264.
    Preset p4 (mesuré le 2026-10-08 sur la 3070 Ti) : même SSIM / PSNR que p5, fichier 7 % plus lourd, mais 1,7× plus
    rapide quand les morceaux de rendu.py se partagent la puce d'encodage (p5 la sature à ~230 i/s). Décodage par la
    carte (-hwaccel cuda) essayé : aucun gain, les filtres et l'encodage limitent, pas le décodage."""
    if NVENC:
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-tune", "hq", "-rc", "vbr", "-cq", str(crf + 1), "-b:v", "0"]
    return ["-c:v", "libx264", "-preset", preset, "-crf", str(crf)]
# whisper écrit tantôt « trois », tantôt « 3 » (selon la version, processeur ou Vulkan) : les comparaisons de mots
# (verify_cuts.norm, short.norm) ramènent les deux côtés à la même forme
NOMBRES = {w: str(i) for i, w in enumerate(
    "zero un deux trois quatre cinq six sept huit neuf dix onze douze treize quatorze quinze seize".split())}
NOMBRES["une"] = "1"
VAD_CLI =WHISPER.with_name("whisper-vad-speech-segments.exe")
VAD_MODEL = HF / ".whisper" / "ggml-silero-v5.1.2.bin"  # Silero VAD (~1 Mo, huggingface ggml-org/whisper-vad)


def video(vid: str) -> dict:
    """Réglages d'une vidéo (videos/<id>/video.json), avec les dossiers utiles."""
    cfg = json.loads((HF / "videos" / vid / "video.json").read_text(encoding="utf-8-sig"))
    cfg["dir"] = HF / "videos" / vid
    cfg["out"] = ROOT / "06_CAPCUT" / vid
    cfg["out"].mkdir(parents=True, exist_ok=True)
    return cfg


def taille(cfg) -> tuple[int, int]:
    """(largeur, hauteur) de l'image finale : video.json "format": "vertical" (Short, 1080×1920) ou 16:9 par défaut."""
    return (1080, 1920) if (cfg or {}).get("format") == "vertical" else (1920, 1080)


def draft(project: str) -> dict:
    return json.loads((DRAFTS / project / "draft_content.json").read_text(encoding="utf-8-sig"))


def remap(t: float, cuts) -> float:
    """Temps d'avant les coupes (cut-range) → temps dans la timeline actuelle."""
    return t - sum(min(max(t - a, 0), b - a) for a, b in cuts)


def run(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def read_json(p: Path, default=None):
    return json.loads(p.read_text(encoding="utf-8-sig")) if p.exists() else default


def write_json(p: Path, data):
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


_SEUILS = {}


def audio16k(path) -> Path:
    """Son d'un rush en WAV 16 kHz mono, extrait une fois (02_ANALYSE/audio_16k/rush_<nom>.wav, refait si le rush
    change) : couper 300 blocs dans ce fichier est bien plus rapide que de relire chaque fois la vidéo d'une heure.
    Un fichier qui n'est pas un rush vidéo est rendu tel quel."""
    path = Path(path)
    if path.suffix.lower() not in (".mkv", ".mp4", ".mov"):
        return path
    dst = ANALYSE / "audio_16k" / f"rush_{path.stem}.wav"
    if not dst.exists() or dst.stat().st_mtime < path.stat().st_mtime:
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_suffix(".tmp.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(path), "-vn", "-ac", "1", "-ar", "16000",
                        "-c:a", "pcm_s16le", str(tmp)], check=True)
        tmp.replace(dst)
    return dst


_FOND = {}


def fond_sonore(path, rate=8000, win=0.05):
    """Crête du fond (dB, 10e centile des crêtes de fenêtres de 50 ms, donc les pauses de la voix) : le son du
    jeu laissé bas sous la voix (OBS). Sans fond (silence numérique, pièce calme) : vers -60 dB ou moins.
    Mis en cache (mémoire + 02_ANALYSE/fond_sonore.json, par taille et date du fichier) : sans numpy, le calcul
    sur un rush d'une heure prend ~10 s, et nettoie_derush le demandait pour chaque clip (85 % de son temps)."""
    st = Path(path).stat()
    key = f"{Path(path).name}|{st.st_size}|{st.st_mtime_ns}"
    cache_f = ANALYSE / "fond_sonore.json"
    if not _FOND and cache_f.exists():
        try:
            _FOND.update(json.loads(cache_f.read_text(encoding="utf-8")))
        except ValueError:
            pass
    if key not in _FOND:
        _FOND[key] = _fond_sonore(path, rate, win)
        try:
            cache_f.write_text(json.dumps(_FOND, ensure_ascii=False, indent=1), encoding="utf-8")
        except OSError:
            pass
    return _FOND[key]


def _fond_sonore(path, rate, win):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1", "-ar", str(rate),
                          "-f", "s16le", "-"], capture_output=True).stdout
    n = int(rate * win)
    try:
        import numpy as np
        a = np.frombuffer(raw[: len(raw) // (2 * n) * 2 * n], dtype="<i2").astype(np.float64).reshape(-1, n)
        db = sorted(20 * np.log10(np.maximum(np.abs(a).max(axis=1) / 32768, 1e-6)))
    except ImportError:
        import array, math
        s = array.array("h", raw[: len(raw) // 2 * 2])
        db = sorted(20 * math.log10(max(max(abs(x) for x in s[i:i + n]) / 32768, 1e-6))
                    for i in range(0, len(s) - n + 1, n))
    return float(db[len(db) // 10]) if db else -120.0


def seuil_silence(path, defaut=-40.0):
    """Seuil de silencedetect adapté au rush : -40 dB par défaut ; si le son du jeu reste sous la voix
    (crête du fond au-dessus de -48 dB), crête du fond + 6 dB, entre -45 et -20 dB, pour que les pauses de la
    voix restent des « silences ». Mis en cache par fichier. SEUIL_SILENCE=-30 force une valeur."""
    if os.environ.get("SEUIL_SILENCE"):
        return float(os.environ["SEUIL_SILENCE"])
    key = str(path)
    if key not in _SEUILS:
        fond = fond_sonore(path)
        _SEUILS[key] = defaut if fond < -48 else max(-45.0, min(-20.0, round(fond + 6, 1)))
    return _SEUILS[key]


def voix(path, pad_ms=200):
    """Passages où quelqu'un parle (Silero VAD de whisper.cpp), en secondes : [(début, fin), …].
    Distingue la voix du son du jeu, ce que silencedetect ne sait pas faire. None si l'outil ou le modèle
    manque. On ne passe PAS --vad à whisper-cli : avec, les débuts de mots (DTW) restent sur l'audio
    raccourci et les reprises collées à 0,1 s sont fusionnées."""
    import re, tempfile
    if not (VAD_CLI.exists() and VAD_MODEL.exists()):
        return None
    with tempfile.TemporaryDirectory() as t:
        wav = Path(t) / "voix.wav"
        run("-i", str(path), "-vn", "-ac", "1", "-ar", "16000", str(wav))
        out = subprocess.run([str(VAD_CLI), "-vm", str(VAD_MODEL), "-f", str(wav), "-vp", str(pad_ms), "-np"],
                             capture_output=True, text=True, check=True).stdout
    return [(float(a) / 100, float(b) / 100) for a, b in re.findall(r"start = ([\d.]+), end = ([\d.]+)", out)]


def empreinte(*reglages, fichiers=()):
    """Empreinte d'un fichier produit : ses réglages (n'importe quel JSON) et ses sources. Un gros fichier
    (rush) compte par taille et date de modification, un petit (composition, kit) par son contenu."""
    import hashlib
    h = hashlib.sha256(json.dumps(reglages, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8"))
    for f in fichiers:
        f = Path(f)
        st = f.stat()
        h.update(f.name.encode("utf-8"))
        h.update(f.read_bytes() if st.st_size < 5_000_000 else f"{st.st_size}|{st.st_mtime_ns}".encode())
    return h.hexdigest()[:16]


def a_jour(dst, emp) -> bool:
    """dst existe et a été produit avec ces réglages et ces sources (fichier <dst>.empreinte à côté)."""
    dst = Path(dst)
    side = dst.with_name(dst.name + ".empreinte")
    return dst.exists() and side.exists() and side.read_text(encoding="utf-8").strip() == emp


def marquer(dst, emp) -> None:
    Path(dst).with_name(Path(dst).name + ".empreinte").write_text(emp + "\n", encoding="utf-8")
