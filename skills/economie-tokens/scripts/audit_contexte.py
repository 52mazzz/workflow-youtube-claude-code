"""Audit du contexte chargé à chaque session Claude Code (estimation en tokens).

Usage : python audit_contexte.py [chemin_projet]
Rend un résumé court : postes fixes, skills les plus lourds, doublons, MCP.
"""
import json
import re
import sys
from pathlib import Path

HOME = Path.home() / ".claude"
CHARS_PAR_TOKEN = 3.7  # moyenne FR/EN, ordre de grandeur


def tok(texte: str) -> int:
    return round(len(texte) / CHARS_PAR_TOKEN)


def lire(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def frontmatter(texte: str) -> dict:
    m = re.match(r"^---\s*\n(.*?)\n---", texte, re.S)
    if not m:
        return {}
    out = {}
    for ligne in m.group(1).splitlines():
        if ":" in ligne and not ligne.startswith(" "):
            k, v = ligne.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def skills_dans(racine: Path):
    if not racine.exists():
        return []
    res = []
    for skill_md in racine.rglob("SKILL.md"):
        if "node_modules" in skill_md.parts:
            continue
        t = lire(skill_md)
        fm = frontmatter(t)
        if str(fm.get("disable-model-invocation", "")).lower() == "true":
            continue  # description jamais chargée dans le contexte
        nom = fm.get("name", skill_md.parent.name)
        desc = fm.get("description", "")
        res.append((nom, tok(nom + desc), tok(t), skill_md))
    return res


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except AttributeError:
        pass
    projet = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else Path.cwd()
    fixes = []  # (poste, tokens, détail)

    # CLAUDE.md global + projet (racine et parents jusqu'à HOME)
    claude_mds = [HOME / "CLAUDE.md"]
    d = projet
    while True:
        claude_mds += [d / "CLAUDE.md", d / ".claude" / "CLAUDE.md", d / "CLAUDE.local.md"]
        if d.parent == d or d == Path.home():
            break
        d = d.parent
    for p in dict.fromkeys(claude_mds):
        if p.exists():
            t = lire(p)
            fixes.append((f"CLAUDE.md : {p}", tok(t), f"{t.count(chr(10))} lignes"))

    # MEMORY.md du projet
    cle = re.sub(r"[^A-Za-z0-9]", "-", str(projet))
    mem = HOME / "projects" / cle / "memory" / "MEMORY.md"
    if mem.exists():
        t = lire(mem)
        fixes.append(("MEMORY.md (index)", tok(t), f"{t.count(chr(10))} lignes"))

    # Skills : utilisateur, projet, plugins
    sources = {
        "utilisateur": skills_dans(HOME / "skills"),
        "projet": skills_dans(projet / ".claude" / "skills"),
        "plugins": skills_dans(HOME / "plugins"),
    }
    tous = [s for lst in sources.values() for s in lst]
    total_desc = sum(s[1] for s in tous)
    fixes.append((f"Descriptions de skills ({len(tous)})", total_desc,
                  ", ".join(f"{k} {len(v)}" for k, v in sources.items())))

    # MCP
    mcp = []
    cfg = Path.home() / ".claude.json"
    if cfg.exists():
        try:
            data = json.loads(lire(cfg))
            mcp += list(data.get("mcpServers", {}))
            proj = data.get("projects", {}).get(str(projet).replace("\\", "/"), {}) or \
                data.get("projects", {}).get(str(projet), {})
            mcp += list(proj.get("mcpServers", {}))
        except (ValueError, AttributeError):
            pass
    pm = projet / ".mcp.json"
    if pm.exists():
        try:
            mcp += list(json.loads(lire(pm)).get("mcpServers", {}))
        except ValueError:
            pass

    print(f"Projet : {projet}\n")
    print("| Poste fixe (chaque session) | ~Tokens | Détail |\n|---|---|---|")
    for poste, n, det in sorted(fixes, key=lambda x: -x[1]):
        print(f"| {poste} | {n:,} | {det} |".replace(f"{n:,}", f"{n:,}".replace(",", " ")))
    print(f"| **Total estimé** | **{sum(f[1] for f in fixes):,}** | hors prompt système et outils |\n".replace(",", " "))

    print("Descriptions de skills les plus longues :")
    for nom, d_tok, _, p in sorted(tous, key=lambda s: -s[1])[:8]:
        print(f"  {d_tok:>5} tok  {nom}  ({p.parent})")

    print("\nCorps SKILL.md les plus lourds (payés à chaque déclenchement) :")
    for nom, _, c_tok, p in sorted(tous, key=lambda s: -s[2])[:8]:
        print(f"  {c_tok:>6} tok  {nom}")

    noms = {}
    for nom, *_, p in tous:
        noms.setdefault(nom, []).append(p.parent)
    doublons = {n: ps for n, ps in noms.items() if len(ps) > 1}
    if doublons:
        print("\nDoublons de skills (même nom, chargés deux fois) :")
        for n, ps in doublons.items():
            print(f"  {n} : " + " | ".join(str(x) for x in ps))

    print(f"\nServeurs MCP configurés ({len(mcp)}) : " + (", ".join(mcp) if mcp else "aucun trouvé dans les fichiers"))
    print("(Connecteurs de l'app et plugins MCP non listés ici : vérifier avec /context ou /mcp.)")


if __name__ == "__main__":
    main()
