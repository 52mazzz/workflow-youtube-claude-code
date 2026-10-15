/* Moteur du kit TSAR pour Hyperframes (porté du projet Remotion 03_REMOTION, vidéo 0927).
 *
 * Principe : chaque élément est une fonction pure du temps, update(t) — même calcul qu'en Remotion
 * (progress(t, début, durée, courbe)) — appelée par UNE horloge GSAP en pause, pilotée par Hyperframes.
 * Seek-safe et déterministe : aucun Date.now, hasard seedé, pas de réseau.
 *
 * Usage dans une composition :
 *   <div id="root" data-composition-id="chapitre" data-start="0" data-duration="3.2" data-width="1920" data-height="1080">
 *   <script> TSAR.run("chapitre", "chapitre"); </script>
 * Les réglages viennent des variables (data-composition-variables / --variables-file).
 */
(function () {
  const FPS = 60;
  const f = (frames) => frames / FPS; // frames (60 i/s, comme en Remotion) → secondes
  const E = (name) => gsap.parseEase(name);
  const EASE = {
    out: E("expo.out"), // bezier(.16,1,.3,1) : entrée franche puis douce
    inOut: E("power3.inOut"), // bezier(.65,0,.35,1)
    in: E("expo.in"), // bezier(.7,0,.84,0) : sorties
    pop: E("back.out(1.7)"), // spring(damping 14, stiffness 180) : léger rebond
    lin: E("none"),
  };
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  // taille de la page (data-width / data-height, lue par run) : 1920×1080, ou 1080×1920 pour un Short (vertical).
  // Short : l'interface de YouTube cache le bas (titre, chaîne : sous ~1450 px) et la colonne de boutons à droite ;
  // les repères vont donc en haut (pastille, carte réduite, minuteur, accéléré) et le mot-clé vers 65 % de la hauteur.
  let SW = 1920, SH = 1080;
  const vertical = () => SH > SW;
  /** 0 → 1 entre start et start+dur (secondes), avec la courbe donnée. */
  const progress = (t, start, dur, ease = EASE.out) => ease(clamp01((t - start) / Math.max(1e-6, dur)));

  const COLORS = { accent: "#E5383B", text: "#F4F4F5", muted: "#A1A1AA", dim: "#63636B", or: "#F5B942",
    claude: "#E07A5A", astra: "#3CCFB0", vanilla: "#8BC34A" };

  // hasard déterministe (mulberry32)
  const rng = (seed) => () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
    let x = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
    return ((x ^ (x >>> 14)) >>> 0) / 4294967296;
  };

  /** Crée un élément : h("div", "classe", {style}, enfants|html) */
  function h(tag, cls, style, children) {
    const el = document.createElement(tag);
    if (cls) el.className = cls;
    if (style) Object.assign(el.style, style);
    if (typeof children === "string") el.innerHTML = children;
    else if (children) [].concat(children).forEach((c) => c && el.appendChild(c));
    return el;
  }

  // ───────────── icônes SVG (jamais d'emoji)
  const P = {
    check: '<path d="M5 12.5 L10 17.5 L19 7"/>',
    alert: '<path d="M12 6 V13.5"/><circle cx="12" cy="18" r="0.6" fill="currentColor"/>',
    ban: '<circle cx="12" cy="12" r="9"/><path d="M5.6 5.6 L18.4 18.4"/>',
    trophy: '<path d="M7 4 H17 V9 A5 5 0 0 1 7 9 Z"/><path d="M7 6 H4 A3 3 0 0 0 7 11"/><path d="M17 6 H20 A3 3 0 0 1 17 11"/><path d="M12 14 V17"/><path d="M8 20 H16"/>',
    chat: '<path d="M4 5 H20 V16 H10 L5 20 V16 H4 Z"/>',
    bell: '<path d="M6 16 V11 A6 6 0 0 1 18 11 V16 L19.5 17.5 H4.5 Z"/><path d="M10 20 A2 2 0 0 0 14 20"/>',
  };
  function icon(name, size, color = "#0A0A0C") {
    if (name === "burst") {
      let s = "";
      for (let i = 0; i < 12; i++) {
        const a = (i / 12) * Math.PI * 2 + (i % 2) * 0.12, r = i % 3 === 0 ? 40 : 33;
        s += `<line x1="${Math.cos(a) * 8}" y1="${Math.sin(a) * 8}" x2="${Math.cos(a) * r}" y2="${Math.sin(a) * r}" stroke="${color}" stroke-width="7" stroke-linecap="round"/>`;
      }
      return `<svg width="${size}" height="${size}" viewBox="-50 -50 100 100">${s}</svg>`;
    }
    if (name === "knot") {
      return `<svg width="${size}" height="${size}" viewBox="-50 -50 100 100" fill="none" stroke="${color}" stroke-width="8">` +
        [0, 60, 120].map((r) => `<ellipse rx="36" ry="15" transform="rotate(${r})"/>`).join("") + "</svg>";
    }
    if (!P[name]) return "";
    return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="${color}" style="color:${color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">${P[name]}</svg>`;
  }

  // ───────────── briques de style
  /** Ouverture d'une fenêtre / étiquette : fondu 8 images, échelle 0.92 → 1 avec rebond (26 images). */
  const openStyle = (el, t, start) => {
    const p = progress(t, start, f(26), EASE.pop), fade = progress(t, start, f(8));
    el.style.opacity = fade;
    el.style.transform = `translateY(${(1 - fade) * 24}px) scale(${0.92 + 0.08 * p})`;
  };
  /** Sortie commune : fondu + légère descente sur les 8 dernières images. */
  const exitStyle = (el, t, D) => {
    const out = progress(t, D - f(8), f(8), EASE.in);
    el.style.opacity = 1 - out;
    el.style.transform = `translateY(${out * 20}px)`;
  };

  function win({ title, color, width, height, bodyStyle }) {
    const controls = `<svg width="104" height="20" viewBox="0 0 104 20" fill="none" stroke="#8A8F99" stroke-width="2" stroke-linecap="round"><path d="M4 10 H18"/><rect x="44" y="3" width="14" height="14" rx="2.5"/><path d="M88 4 L100 16 M100 4 L88 16"/></svg>`;
    const body = h("div", "win-body", bodyStyle);
    const el = h("div", "win", { width: width ? width + "px" : null, height: height ? height + "px" : null }, [
      h("div", "win-bar", null, [h("span", "win-dot", { background: color }), h("span", "win-title", null, title), h("span", null, null, controls)]),
      body,
    ]);
    return { el, body };
  }

  function label({ text, color, size = 30, ico = "", html }) {
    const el = h("div", "label", {
      gap: size * 0.5 + "px", padding: `${size * 0.42}px ${size * 0.8}px ${size * 0.42}px ${size * 0.45}px`,
      borderRadius: size * 0.45 + "px", fontSize: size + "px",
    });
    el.appendChild(h("span", "label-ico", { width: size * 1.25 + "px", height: size * 1.25 + "px", borderRadius: size * 0.3 + "px", background: color }, ico));
    el.appendChild(h("span", null, null, html || escapeHtml(text)));
    return el;
  }

  const escapeHtml = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
  const aiIcon = (ia, size) => (ia === "claude" ? icon("burst", size, "#FFFFFF") : ia === "astra" ? icon("knot", size, "#FFFFFF") : "");

  /** Fond de la chaîne : lignes ondulées diagonales sur noir, couleur selon la scène. */
  function wave(parent, color = COLORS.accent, dim = 0.5, speed = 1, W = 1920, H = 1080) {
    const N = Math.round(26 * (W + H * 0.8) / (1920 + 1080 * 0.8));
    const NS = "http://www.w3.org/2000/svg";
    const box = h("div", "fill", { background: "#050506" });
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("width", W); svg.setAttribute("height", H); svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.style.position = "absolute";
    const paths = [];
    for (let i = 0; i < N; i++) {
      const p = document.createElementNS(NS, "path");
      p.setAttribute("fill", "none"); p.setAttribute("stroke", color); p.setAttribute("stroke-width", 7 + (i % 3) * 1.5);
      p.setAttribute("stroke-linecap", "round"); p.setAttribute("opacity", 0.7);
      svg.appendChild(p); paths.push(p);
    }
    box.appendChild(svg);
    box.appendChild(h("div", "fill", { background: `radial-gradient(60% 60% at 50% 50%, rgba(5,5,6,${0.55 + dim}) 0%, rgba(5,5,6,${dim}) 70%, rgba(5,5,6,0.15) 100%)` }));
    parent.appendChild(box);
    const spacing = (W + H * 0.8) / N;
    return (t) => {
      const phase = t * 0.45 * speed;
      paths.forEach((p, i) => {
        const offset = i * spacing - H * 0.8, pts = [];
        for (let y = -80; y <= H + 80; y += 20) {
          const u = y / H;
          const x = offset + (H - y) * 0.8 + Math.sin(u * 6.3 + phase + i * 0.3) * 62 + Math.sin(u * 13 - phase * 0.8 + i * 0.85) * 18;
          pts.push(`${x.toFixed(1)},${y}`);
        }
        p.setAttribute("d", "M " + pts.join(" L "));
      });
    };
  }

  const MOODS = { doute: "doute", explication: "explication", gene: "gene_goutte", reflexion: "reflexion", rire: "rire_larmes", surprise: "surprise" };
  /** Tsar surgit du bas de l'écran, réagit, puis repart. */
  function mascot(parent, { mood = "surprise", start = 0, end, x = 1600, size = 500, tilt = 0, root = "", bas = 0 }) {
    const img = h("img", null, { position: "absolute", width: size + "px", height: size + "px", left: x - size / 2 + "px",
      bottom: bas - size * 0.06 + "px", transformOrigin: "50% 100%", filter: "drop-shadow(0 20px 40px rgba(0,0,0,.6))" });
    img.src = `${root}assets/tsar/tsar_${MOODS[mood] || mood}.png`;
    // bas > 0 (Short) : Tsar surgit d'une ligne à `bas` px du bas, au-dessus de l'interface ; ce qui passe sous la ligne est
    // coupé sur l'image elle-même (clip-path : un conteneur overflow hidden le cachait entièrement au rendu)
    parent.appendChild(img);
    return (t) => {
      const enter = progress(t, start, f(24), EASE.pop), exit = progress(t, end - f(10), f(10), EASE.in);
      img.style.visibility = t >= start && t < end ? "visible" : "hidden";
      const ty = (1 - enter + exit) * size * 0.95;
      img.style.transform = `translateY(${ty}px) rotate(${tilt - 8 + 8 * enter}deg)`;
      if (bas) img.style.clipPath = `inset(-60px -60px ${Math.max(0, size * 0.06 + ty)}px -60px)`;
    };
  }

  /** Fait apparaître un bloc (fondu + montée) à `start`. */
  const reveal = (el, start, rise = 16) => (t) => {
    const p = progress(t, start, f(16));
    el.style.opacity = p;
    el.style.transform = `translateY(${(1 - p) * rise}px)`;
  };

  // ───────────── éléments (un par type de composition)
  const B = {};

  /** Titre de partie : fenêtre en bas à gauche, fond teinté. vars : surtitre, titre, couleur */
  B.chapitre = ({ stage, v, D }) => {
    const color = v.couleur || COLORS.accent, kicker = v.surtitre || "PARTIE 1";
    const layer = h("div", "layer", { justifyContent: "flex-start", alignItems: "flex-end", padding: "0 0 110px 100px" });
    const k = h("div", "mono", { color }, escapeHtml(kicker));
    const title = h("div", "big", { fontSize: "104px", marginTop: "12px" }, escapeHtml(v.titre || "Titre"));
    const bar = h("div", null, { marginTop: "22px", height: "8px", width: "220px", borderRadius: "4px", background: color, boxShadow: "0 4px 14px rgba(0,0,0,.4)", transformOrigin: "left" });
    const w = win({ title: kicker.charAt(0) + kicker.slice(1).toLowerCase(), color, bodyStyle: { padding: "34px 50px 40px", background: `linear-gradient(120deg, ${color}40 0%, transparent 70%)` } });
    w.body.append(k, title, bar);
    layer.appendChild(w.el); stage.appendChild(layer);
    return (t) => {
      exitStyle(layer, t, D); openStyle(w.el, t, 0);
      const txt = progress(t, f(8), f(16));
      k.style.opacity = txt; title.style.opacity = txt; title.style.transform = `translateX(${(1 - txt) * -30}px)`;
      bar.style.transform = `scaleX(${progress(t, f(12), f(20), EASE.inOut)})`;
    };
  };

  /** Étiquette d'un test : petite fenêtre en bas à gauche. vars : fenetre ("Test 01 · Claude"), titre, couleur */
  B.test = ({ stage, v, D }) => {
    const color = v.couleur || COLORS.claude;
    const layer = h("div", "layer", { alignItems: "flex-end", padding: "0 0 100px 96px" });
    const title = h("div", "big", { fontSize: "110px", textTransform: "uppercase" }, escapeHtml(v.titre || "Nuit"));
    const bar = h("div", null, { marginTop: "16px", height: "8px", width: "160px", borderRadius: "4px", background: color, transformOrigin: "left" });
    const w = win({ title: v.fenetre || "Test 01", color, bodyStyle: { padding: "26px 44px 32px" } });
    w.body.append(title, bar); layer.appendChild(w.el); stage.appendChild(layer);
    return (t) => { exitStyle(layer, t, D); openStyle(w.el, t, 0); bar.style.transform = `scaleX(${progress(t, f(12), f(14), EASE.inOut)})`; };
  };

  /** Annotation (détail remarqué) en haut à droite. vars : texte, couleur, alerte (défaut → rouge + icône alerte) */
  B.annotation = ({ stage, v, D }) => {
    const warn = !!v.alerte;
    const layer = h("div", "layer", { justifyContent: "flex-end", alignItems: "flex-start", padding: "86px 96px" });
    const l = label({ text: v.texte || "Détail", color: warn ? COLORS.accent : v.couleur || COLORS.claude, size: 34, ico: warn ? icon("alert", 28, "#FFFFFF") : icon("check", 28) });
    layer.appendChild(l); stage.appendChild(layer);
    return (t) => { exitStyle(layer, t, D); openStyle(l, t, 0); };
  };

  /** Pastille d'info. vars : texte, couleur, position (haut-gauche|haut-centre|bas-gauche), taille, icone (burst|knot|check|trophy|…) */
  B.etiquette = ({ stage, v, D }) => {
    const pos = v.position || "haut-gauche", size = +v.taille || 34;
    const layer = h("div", "layer", {
      justifyContent: pos.endsWith("centre") ? "center" : "flex-start", alignItems: pos.startsWith("bas") ? "flex-end" : "flex-start",
      padding: pos.endsWith("centre") ? "76px 0" : "72px 96px" });
    const ico = v.icone === "burst" || v.icone === "knot" ? icon(v.icone, size * 0.9, "#FFFFFF") : v.icone ? icon(v.icone, size * 0.8) : "";
    const l = label({ text: v.texte || "Minecraft · vanilla", color: v.couleur || COLORS.vanilla, size, ico });
    layer.appendChild(l); stage.appendChild(layer);
    return (t) => { exitStyle(layer, t, D); openStyle(l, t, 0); };
  };

  /** Suite d'étiquettes qui se remplacent (comparaison). vars : items = [[seconde, texte, couleur, icone?], …], taille */
  B.etiquettes = ({ stage, v, D }) => {
    const items = typeof v.items === "string" ? JSON.parse(v.items) : v.items || [];
    const size = +v.taille || 52;
    const layer = h("div", "layer", { justifyContent: "center", alignItems: "flex-start", padding: "76px 0" });
    const labels = items.map(([at, text, color, ico]) => {
      const l = label({ text, color, size, ico: ico ? icon(ico, size * 0.88, "#FFFFFF") : "" });
      l.style.position = "absolute"; layer.appendChild(l); return [at, l];
    });
    stage.appendChild(layer);
    return (t) => {
      exitStyle(layer, t, D);
      const cur = [...labels].reverse().find(([at]) => t >= at);
      labels.forEach(([at, l]) => { l.style.visibility = l === (cur && cur[1]) ? "visible" : "hidden"; if (cur && l === cur[1]) openStyle(l, t, at); });
    };
  };

  /** Point marqué : « +1 Claude » en haut au centre. vars : texte, couleur */
  B.point = ({ stage, v, D }) => {
    const layer = h("div", "layer", { justifyContent: "center", alignItems: "flex-start", paddingTop: "90px" });
    const pill = h("div", "big", { fontSize: "64px", padding: "18px 40px", borderRadius: "999px", background: v.couleur || COLORS.claude, color: "#0A0A0A", boxShadow: "0 14px 40px rgba(0,0,0,.45)" }, escapeHtml(v.texte || "+1 Claude"));
    layer.appendChild(pill); stage.appendChild(layer);
    return (t) => {
      exitStyle(layer, t, D);
      const p = progress(t, 0, f(24), EASE.pop);
      pill.style.opacity = Math.min(1, p * 2); pill.style.transform = `scale(${0.6 + 0.4 * p})`;
    };
  };

  /** Une manche du verdict : titre, gros « +1 », fenêtre de score qui se met à jour.
   *  vars : n, total, theme, nomA, nomB, couleurA, couleurB, avantA, avantB, gagnant (a|b), a (seconde du point) */
  B.manche = ({ stage, v, D }) => {
    const n = v.n || 1, total = v.total || 7, win_ = v.gagnant === "b" ? "b" : "a", at = +v.a || 1;
    const col = { a: v.couleurA || COLORS.claude, b: v.couleurB || COLORS.astra };
    const nom = { a: v.nomA || "Claude Opus 5.5", b: v.nomB || "GPT-6 Astra" };
    const court = { a: v.courtA || "Claude", b: v.courtB || "Astra" };
    const before = { a: +v.avantA || 0, b: +v.avantB || 0 };
    const layer = h("div", "fill");
    const top = h("div", "layer", { justifyContent: "center", alignItems: "flex-start", paddingTop: "70px" });
    const ttl = label({ text: `Manche ${n}/${total} · ${v.theme || "Lumières"}`, color: COLORS.accent, size: 36,
      ico: `<span class="mono" style="color:#fff;letter-spacing:0;font-size:22px">${n}</span>` });
    top.appendChild(ttl);
    const mid = h("div", "layer", { justifyContent: "center", alignItems: "center" });
    const badge = h("div", "big", { fontSize: "120px", padding: "20px 56px", borderRadius: "32px", background: col[win_], color: "#0A0A0A",
      border: "6px solid #FFFFFF", boxShadow: "0 18px 50px rgba(0,0,0,.5)" }, "+1 " + escapeHtml(court[win_]));
    mid.appendChild(badge);
    const bottom = h("div", "layer", { justifyContent: "center", alignItems: "flex-end", paddingBottom: "56px" });
    const tag = (k) => h("span", null, { display: "inline-flex", alignItems: "center", gap: "12px", fontWeight: 800, fontSize: "32px" },
      [h("span", null, { width: "12px", height: "12px", borderRadius: "3px", background: col[k] }), h("span", null, null, escapeHtml(nom[k]))]);
    const sA = h("span", null, { display: "inline-block" }), sB = h("span", null, { display: "inline-block" });
    const score = h("span", "big", { fontSize: "60px", display: "flex", alignItems: "center" }, [sA, h("span", null, { color: COLORS.dim, margin: "0 16px" }, "–"), sB]);
    const w = win({ title: "Score", color: COLORS.accent, bodyStyle: { display: "flex", alignItems: "center", gap: "36px", padding: "18px 40px" } });
    w.body.append(tag("a"), score, tag("b"));
    bottom.appendChild(w.el);
    layer.append(top, mid, bottom); stage.appendChild(layer);
    return (t) => {
      exitStyle(layer, t, D); openStyle(ttl, t, 0); openStyle(w.el, t, f(12));
      const won = t >= at;
      sA.textContent = before.a + (won && win_ === "a" ? 1 : 0);
      sB.textContent = before.b + (won && win_ === "b" ? 1 : 0);
      const bump = won ? 1 + 0.25 * (1 - progress(t, at, f(20))) : 1;
      (win_ === "a" ? sA : sB).style.transform = `scale(${bump})`;
      const pop = progress(t, at, f(26), EASE.pop), fade = progress(t, at, f(8)), out = progress(t, at + 1.8, f(10), EASE.in);
      badge.style.visibility = won ? "visible" : "hidden";
      badge.style.opacity = fade * (1 - out);
      badge.style.transform = `translateY(${(1 - fade) * 24}px) scale(${(0.5 + 0.5 * pop) * (1 - 0.2 * out)})`;
    };
  };

  /** Réaction de Tsar en bas à droite. vars : humeur (doute|explication|gene|reflexion|rire|surprise), x */
  B.reaction = ({ stage, v, D }) => vertical()
    ? mascotCadre(stage, { mood: v.humeur || "surprise", D, x: +v.x > 0 && +v.x <= SW - 100 ? +v.x : 700 })
    : mascot(stage, { mood: v.humeur || "surprise", start: 0, end: D, x: +v.x || 1600, size: +v.taille || 500 });

  /** Short : Tsar dans un cadre arrondi (fond rouge de la chaîne, liseré blanc) qui surgit au-dessus de l'interface ;
   *  le buste est coupé par le bord du cadre, jamais au milieu de l'écran (retour du 2026-10-08 : « on voit le bas
   *  coupé »). La valeur par défaut des compositions (x 1600) est hors d'un écran de 1080 px → 700. */
  function mascotCadre(parent, { mood, D, x, size = 420, bas = 430 }) {
    const card = h("div", null, { position: "absolute", left: x - size / 2 + "px", bottom: bas + "px", width: size + "px", height: size + "px",
      borderRadius: "44px", overflow: "hidden", border: "8px solid #FFFFFF", transformOrigin: "50% 100%",
      background: "radial-gradient(70% 70% at 50% 40%, #FF5A5D 0%, #E5383B 45%, #7A1416 100%)", boxShadow: "0 24px 60px rgba(0,0,0,.55)" });
    const img = h("img", null, { position: "absolute", left: "-4%", width: "108%", bottom: "-6%" });
    img.src = `assets/tsar/tsar_${MOODS[mood] || mood}.png`;
    card.appendChild(img); parent.appendChild(card);
    return (t) => {
      const p = progress(t, 0, f(16), EASE.pop), out = progress(t, D - f(8), f(8), EASE.in);
      card.style.opacity = Math.min(1, p * 3) * (1 - out);
      card.style.transform = `scale(${(0.4 + 0.6 * p) * (1 - 0.3 * out)}) rotate(${-10 + 7 * p}deg)`;
      img.style.transform = `translateY(${(1 - progress(t, f(4), f(16), EASE.out)) * 40}%)`;
    };
  }

  /** Sous-titre punchline : blanc, gros contour noir, chaque mot arrive quand il est dit.
   *  vars : mots = [{text, t}] (t en s depuis le début de l'élément), taille, bas (px depuis le bas), largeur */
  B.soustitre = ({ stage, v, D }) => {
    const words = typeof v.mots === "string" ? JSON.parse(v.mots) : v.mots || [{ text: "Sous-titre", t: 0 }];
    // style "reference" (Short de LAirHisson, 2026-10-13) : Montserrat 900 blanc sans contour, halo sombre flou autour
    // des lettres ; le groupe surgit à 60 % et rebondit à sa taille (back.out) en 9 images, puis disparaît net
    const ref = v.style === "reference";
    const size = +v.taille || 76, stroke = ref ? 0 : Math.round(size * 0.16);
    const layer = h("div", "layer", { justifyContent: "center", alignItems: "flex-end", paddingBottom: (+v.bas || 110) + "px" });
    const box = h("div", "cap", { maxWidth: (+v.largeur || 1500) + "px", columnGap: size * 0.29 + "px", rowGap: "4px", fontSize: size + "px",
      ...(ref ? { fontFamily: "Montserrat, var(--display)", letterSpacing: "-1.5px" } : {}) });
    const spans = words.map((w) => { const s = h("span", null, { WebkitTextStroke: `${stroke}px #0A0A0C`,
      ...(ref ? { textShadow: "0 0 10px rgba(0,0,0,.8), 0 3px 8px rgba(0,0,0,.65), 0 0 24px rgba(0,0,0,.45)" } : {}) },
      escapeHtml(w.text)); box.appendChild(s); return [w.t, s]; });
    layer.appendChild(box); stage.appendChild(layer);
    if (ref) {  // le groupe entier grossit d'un bloc (les espaces entre les mots ne bougent pas)
      const at0 = Math.min(...spans.map(([at]) => at));
      return (t) => {
        spans.forEach(([at, s]) => { s.style.opacity = t >= at ? 1 : 0; });
        box.style.transform = `scale(${0.6 + 0.4 * progress(t, at0, f(9), EASE.pop)})`;
      };
    }
    return (t) => {
      layer.style.opacity = 1 - progress(t, D - f(7), f(7), EASE.in);
      spans.forEach(([at, s]) => {
        const p = progress(t, at, f(14), EASE.pop);
        s.style.opacity = progress(t, at, f(4));
        s.style.transform = `translateY(${(1 - p) * 18}px) scale(${0.75 + 0.25 * p})`;
      });
    };
  };

  /** Obturateur : volets noirs qui se ferment sur la coupe (milieu) puis se rouvrent, léger flash. */
  B.obturateur = ({ stage, D }) => {
    const top = h("div", null, { position: "absolute", left: 0, right: 0, top: 0, background: "#050506" });
    const bot = h("div", null, { position: "absolute", left: 0, right: 0, bottom: 0, background: "#050506" });
    const fl = h("div", "fill", { background: "#FFFFFF" });
    stage.append(top, bot, fl);
    const mid = D / 2;
    return (t) => {
      const cover = progress(t, 0, mid - f(2), EASE.in) * (1 - progress(t, mid + f(2), mid - f(2), EASE.out));
      top.style.height = bot.style.height = cover * 50.5 + "%";
      fl.style.opacity = t >= mid ? 0.35 * (1 - progress(t, mid, f(10))) : 0;
    };
  };

  /** Flash d'appareil photo : éclair blanc court, la coupe au premier tiers. */
  B.flash = ({ stage, D }) => {
    const fl = h("div", "fill", { background: "#FFFFFF" });
    stage.appendChild(fl);
    const mid = D / 3;
    return (t) => { fl.style.opacity = 0.85 * (t < mid ? progress(t, mid - f(4), f(4)) : 1 - progress(t, mid, D - mid, EASE.out)); };
  };

  /** Rappel d'abonnement, fenêtre de la chaîne (même style que les autres fenêtres) : à gauche la photo de profil,
   *  le nom et le @ ; à droite « S'abonner » puis la cloche. Le curseur clique S'abonner (le bouton passe en douceur
   *  au gris « Abonné »), puis la cloche (elle se remplit, sonne, « Notifications activées »). À poser uniquement au
   *  moment où le script demande explicitement de s'abonner.
   *  vars : nom, handle, detail (ligne grise sous le @, vide par défaut), y (centre vertical, px), taille (échelle) */
  B.abonnement = ({ stage, v, D }) => {
    const k = +v.taille || 1, cy = +v.y || 740;
    const layer = h("div", "fill");
    const wrap = h("div", null, { position: "absolute", left: "50%", top: cy + "px", transform: "translate(-50%, -50%)" });
    const w = win({ title: "youtube.com/@" + (v.handle || "letsar555"), color: COLORS.accent,
      bodyStyle: { display: "flex", alignItems: "center", gap: 34 * k + "px", padding: `${30 * k}px ${40 * k}px ${30 * k}px ${32 * k}px` } });
    w.el.style.transformOrigin = "50% 60%";
    // gauche : photo de profil ronde, liseré rouge de la chaîne
    const av = h("div", null, { width: 132 * k + "px", height: 132 * k + "px", borderRadius: "50%", flexShrink: 0, overflow: "hidden",
      boxShadow: `0 0 0 ${4 * k}px #15171C, 0 0 0 ${7 * k}px ${COLORS.accent}` });
    const img = h("img", null, { width: "100%", height: "100%", display: "block" });
    img.src = "assets/tsar/avatar_chaine.png";
    av.appendChild(img);
    const id = h("div", null, { display: "flex", flexDirection: "column", gap: 6 * k + "px", marginRight: 26 * k + "px", whiteSpace: "nowrap" }, [
      h("div", null, { fontWeight: 900, fontSize: 46 * k + "px", letterSpacing: "-0.5px" }, escapeHtml(v.nom || "tsar rouge555")),
      h("div", null, { fontFamily: "var(--mono)", fontSize: 24 * k + "px", color: "var(--muted)" }, "@" + escapeHtml(v.handle || "letsar555")
        + (v.detail ? " · " + escapeHtml(v.detail) : "")),
    ]);
    // droite : bouton S'abonner (deux libellés superposés pour un fondu propre) + cloche
    const btn = h("div", null, { position: "relative", height: 76 * k + "px", borderRadius: "999px", overflow: "hidden",
      fontWeight: 800, fontSize: 34 * k + "px", whiteSpace: "nowrap", display: "flex", alignItems: "center", justifyContent: "center" });
    const lblA = h("span", null, { position: "absolute", color: "#0F0F0F" }, "S'abonner");
    const lblB = h("span", null, { position: "absolute", color: "#F1F1F1" }, "Abonné");
    btn.append(lblA, lblB);
    const bellSz = 76 * k;
    const bell = h("div", null, { width: bellSz + "px", height: bellSz + "px", borderRadius: "50%", flexShrink: 0, background: "#2B2D33",
      display: "flex", alignItems: "center", justifyContent: "center", marginLeft: -16 * k + "px" });
    const bellSvg = (fill) => `<svg width="${40 * k}" height="${40 * k}" viewBox="0 0 24 24" fill="none" stroke="#F1F1F1" stroke-width="2"
      stroke-linecap="round" stroke-linejoin="round"><path d="M6 16 V11 A6 6 0 0 1 18 11 V16 L19.5 17.5 H4.5 Z" fill="#F1F1F1" fill-opacity="${fill}"/>
      <path d="M10 20 A2 2 0 0 0 14 20"/><g opacity="${fill}"><path d="M2.8 8.5 A9.5 9.5 0 0 1 5.2 4.2"/><path d="M21.2 8.5 A9.5 9.5 0 0 0 18.8 4.2"/></g></svg>`;
    // étiquette en pilule sous la fenêtre, comme les autres éléments de la chaîne
    const note = label({ text: "Notifications activées", color: COLORS.accent, size: 28 * k, ico: icon("bell", 24 * k, "#FFFFFF") });
    Object.assign(note.style, { position: "absolute", left: "50%", top: "100%", marginTop: 24 * k + "px" });
    w.body.append(av, id, btn, bell);
    wrap.append(w.el, note);
    const cursor = h("div", null, { position: "absolute", left: 0, top: 0, filter: "drop-shadow(0 4px 8px rgba(0,0,0,.5))" },
      `<svg width="${50 * k}" height="${50 * k}" viewBox="0 0 24 24"><path d="M4 2 L4 20 L9 15 L12 22 L15 21 L12 14 L19 14 Z" fill="#FFFFFF" stroke="#0A0A0C" stroke-width="1.5"/></svg>`);
    layer.append(wrap, cursor); stage.appendChild(layer);

    const mix = (a, b, p) => a.map((x, i) => Math.round(x + (b[i] - x) * p));
    const rgb = (c) => `rgb(${c.join(",")})`;
    const WHITE = [241, 241, 241], GREY = [58, 60, 66];
    const click1 = 1.55, click2 = 2.55;
    let widths = null, last = -1;
    return (t) => {
      if (!widths) widths = [lblA.offsetWidth + 80 * k, lblB.offsetWidth + 72 * k];
      // ouverture (fenêtre, puis photo, nom, bouton en léger décalé), sortie commune
      openStyle(w.el, t, 0);
      exitStyle(layer, t, D);
      const ap = progress(t, f(6), f(24), EASE.pop);
      av.style.transform = `scale(${0.6 + 0.4 * ap})`; av.style.opacity = progress(t, f(6), f(10));
      id.style.opacity = progress(t, f(12), f(14)); id.style.transform = `translateX(${(1 - progress(t, f(12), f(20))) * -18}px)`;
      const bp = progress(t, f(18), f(14));
      btn.style.opacity = bp;
      // clic 1 : appui (rebond doux), fondu blanc → gris, largeur qui s'ajuste, libellés croisés
      const s1 = progress(t, click1, f(14), EASE.inOut);
      const press1 = 1 - 0.07 * Math.sin(Math.PI * clamp01((t - click1 + f(4)) / f(14)));
      btn.style.width = widths[0] + (widths[1] - widths[0]) * s1 + "px";
      btn.style.background = rgb(mix(WHITE, GREY, s1));
      btn.style.transform = `scale(${press1})`;
      lblA.style.opacity = 1 - s1; lblB.style.opacity = s1;
      lblA.style.transform = `translateY(${-s1 * 10}px)`; lblB.style.transform = `translateY(${(1 - s1) * 10}px)`;
      // la cloche glisse à côté du bouton une fois abonné
      const bl = progress(t, click1 + f(6), f(18), EASE.out);
      bell.style.opacity = bl; bell.style.marginLeft = (-16 - 50 * (1 - bl)) * k + "px";
      // clic 2 : la cloche se remplit et sonne (oscillation amortie)
      const s2 = progress(t, click2, f(10), EASE.out);
      const step = Math.round(s2 * 20);
      if (step !== last) { bell.innerHTML = bellSvg(s2.toFixed(2)); last = step; }
      const dt = t - click2;
      const ring = dt > 0 ? Math.sin(dt * 26) * 16 * Math.exp(-dt * 5) : 0;
      const press2 = 1 - 0.08 * Math.sin(Math.PI * clamp01((t - click2 + f(4)) / f(14)));
      bell.style.transform = `scale(${press2}) rotate(${ring}deg)`;
      bell.style.transformOrigin = "50% 25%";
      const np = progress(t, click2 + f(10), f(16));
      const npop = progress(t, click2 + f(10), f(26), EASE.pop);
      note.style.opacity = np; note.style.transform = `translate(-50%, ${(1 - np) * 14}px) scale(${0.92 + 0.08 * npop})`;
      // curseur : entre en bas à droite, se pose sur le bouton, clique, glisse vers la cloche, clique, repart
      const base = stage.getBoundingClientRect(), sc = base.width / 1920 || 1;
      const at = (el, fx, fy) => { const r = el.getBoundingClientRect();
        return [(r.left + r.width * fx - base.left) / sc, (r.top + r.height * fy - base.top) / sc]; };
      const p1 = at(btn, 0.62, 0.62), p2 = at(bell, 0.58, 0.64);
      const start = [p1[0] + 330 * k, p1[1] + 230 * k], away = [p2[0] + 240 * k, p2[1] + 260 * k];
      const m1 = progress(t, 0.55, click1 - 0.55 - f(3), EASE.inOut);
      const m2 = progress(t, click1 + f(14), click2 - click1 - f(17), EASE.inOut);
      const m3 = progress(t, click2 + f(20), f(30), EASE.inOut);
      const x = start[0] + (p1[0] - start[0]) * m1 + (p2[0] - p1[0]) * m2 + (away[0] - p2[0]) * m3;
      const y = start[1] + (p1[1] - start[1]) * m1 + (p2[1] - p1[1]) * m2 + (away[1] - p2[1]) * m3;
      cursor.style.transform = `translate(${x}px, ${y}px) scale(${Math.min(press1, press2) < 0.99 ? 0.88 : 1})`;
      cursor.style.opacity = progress(t, 0.45, f(10)) * (1 - progress(t, click2 + f(30), f(14)));
    };
  };

  /** Panneau à barres (classement, temps…) à droite. vars : titre, lignes = [{nom, couleur, valeur (0-100), texte, t}], note = {texte, t} */
  B.barres = ({ stage, v, D }) => {
    const rows = typeof v.lignes === "string" ? JSON.parse(v.lignes) : v.lignes || [];
    const layer = h("div", "layer", { justifyContent: "flex-end", alignItems: "center", paddingRight: "90px" });
    const w = win({ title: v.titre || "Classement", color: COLORS.accent, width: 740, bodyStyle: { padding: "40px 46px 46px", display: "flex", flexDirection: "column", gap: "38px" } });
    const ups = rows.map((r) => {
      const val = h("span", "big", { fontSize: "56px" }, escapeHtml(r.texte));
      const fill = h("div", null, { height: "100%", borderRadius: "11px", background: r.couleur, boxShadow: "0 4px 14px rgba(0,0,0,.4)" });
      const row = h("div", null, { display: "flex", flexDirection: "column", gap: "12px" }, [
        h("div", null, { display: "flex", justifyContent: "space-between", alignItems: "baseline" }, [
          h("span", null, { display: "inline-flex", alignItems: "center", gap: "12px", fontWeight: 800, fontSize: "34px" },
            [h("span", null, { width: "14px", height: "14px", borderRadius: "4px", background: r.couleur }), h("span", null, null, escapeHtml(r.nom))]), val]),
        h("div", null, { height: "22px", borderRadius: "11px", background: "rgba(255,255,255,.08)", overflow: "hidden" }, fill)]);
      w.body.appendChild(row);
      const at = +r.t || 0.5;
      return (t) => {
        const p = progress(t, at, f(16)), fl = progress(t, at + 0.5, f(30));
        row.style.opacity = p; row.style.transform = `translateX(${(1 - p) * 40}px)`;
        val.style.opacity = fl; fill.style.width = fl * (+r.valeur || 0) + "%";
      };
    });
    layer.appendChild(w.el); stage.appendChild(layer);
    return (t) => { exitStyle(layer, t, D); openStyle(w.el, t, f(6)); ups.forEach((u) => u(t)); };
  };

  // ───────────── scènes plein écran (MP4)

  /** Fenêtre d'info sur le fond ondulé. vars : fond (couleur), titre, couleur, surtitre, lignes = [{t, texte, barre?(s), gris?}], taille */
  B.scene_fenetre = ({ stage, v, D }) => {
    const bg = wave(stage, v.fond || COLORS.accent);
    const lines = typeof v.lignes === "string" ? JSON.parse(v.lignes) : v.lignes || [{ t: 0.3, texte: "Texte" }];
    const size = +v.taille || 64, color = v.couleur || COLORS.accent;
    const layer = h("div", "layer", { justifyContent: "center", alignItems: "center" });
    const w = win({ title: v.titre || "Fenêtre", color, width: +v.largeur || 1360, bodyStyle: { padding: "44px 60px 56px", display: "flex", flexDirection: "column", gap: "30px" } });
    if (v.surtitre) w.body.appendChild(h("div", "mono", { color: v.couleurSurtitre || COLORS.dim }, escapeHtml(v.surtitre)));
    const ups = lines.map((l) => {
      const txt = h("div", "big", { position: "relative", display: "inline-block", fontSize: size + "px", lineHeight: 1.2, letterSpacing: "-1px", color: l.gris ? COLORS.muted : COLORS.text }, escapeHtml(l.texte));
      const strike = h("div", null, { position: "absolute", left: "-2%", right: "-2%", top: "54%", height: "8px", borderRadius: "4px", background: COLORS.accent, transformOrigin: "left" });
      if (l.barre != null) txt.appendChild(strike);
      const holder = h("div", null, null, txt); w.body.appendChild(holder);
      const r = reveal(holder, +l.t || 0, 30);
      return (t) => {
        r(t);
        if (l.barre != null) { strike.style.transform = `scaleX(${progress(t, +l.barre, f(12), EASE.inOut)})`; txt.style.opacity = 1 - 0.55 * progress(t, +l.barre + f(10), f(10)); }
      };
    });
    layer.appendChild(w.el); stage.appendChild(layer);
    const m = v.humeur ? mascot(stage, { mood: v.humeur, start: +v.tsarDe || 0.5, end: +v.tsarA || D, x: 1650, size: 460 }) : null;
    return (t) => { bg(t); openStyle(w.el, t, 0); ups.forEach((u) => u(t)); m && m(t); };
  };

  /** Maquette de la description YouTube de la vidéo (style sombre de YouTube) sur le fond ondulé : titre, chaîne, puis le
   *  bloc de description qui s'ouvre et dont les lignes apparaissent ; mots surlignés ; étiquette en pilule avec flèche qui
   *  pointe le bloc. vars : titre, chaine, intro, lignes = [{t, texte}], surligne = [mots], etiquette, etiquetteA (s) */
  B.scene_description = ({ stage, v, D }) => {
    const bg = wave(stage, v.fond || COLORS.accent);
    const lines = typeof v.lignes === "string" ? JSON.parse(v.lignes) : v.lignes || [];
    const marks = typeof v.surligne === "string" ? JSON.parse(v.surligne) : v.surligne || [];
    const mark = (s) => marks.reduce((acc, m) => acc.split(escapeHtml(m)).join(
      `<span style="background:rgba(229,56,59,.28);color:#fff;border-radius:6px;padding:0 6px">${escapeHtml(m)}</span>`), escapeHtml(s));
    const layer = h("div", "layer", { justifyContent: "center", alignItems: "center", flexDirection: "column" });
    const page = h("div", null, { width: "1420px", display: "flex", flexDirection: "column", gap: "22px" });
    const title = h("div", "big", { fontSize: "50px", lineHeight: 1.15, letterSpacing: "-0.5px" }, escapeHtml(v.titre || "Titre de la vidéo"));
    const av = h("img", null, { width: "64px", height: "64px", borderRadius: "50%", boxShadow: `0 0 0 3px ${COLORS.accent}` });
    av.src = "assets/tsar/avatar_chaine.png";
    const chan = h("div", null, { display: "flex", alignItems: "center", gap: "18px" }, [av,
      h("div", null, { fontWeight: 800, fontSize: "32px" }, escapeHtml(v.chaine || "tsar rouge555"))]);
    const box = h("div", null, { background: "#272727", borderRadius: "22px", padding: "30px 36px 34px", display: "flex",
      flexDirection: "column", gap: "14px", boxShadow: "0 30px 80px rgba(0,0,0,.55)", position: "relative" });
    if (v.intro) box.appendChild(h("div", null, { fontWeight: 800, fontSize: "32px", color: "#F1F1F1" }, escapeHtml(v.intro)));
    const ups = lines.map((l) => {
      const el = h("div", null, { fontSize: "29px", lineHeight: 1.42, color: "#E4E4E4" }, mark(l.texte));
      box.appendChild(el);
      return reveal(el, +l.t || 0, 14);
    });
    page.append(title, chan, box);
    const tag = label({ text: v.etiquette || "Le prompt est dans la description", color: COLORS.accent, size: 34,
      ico: `<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"><path d="M12 4 V20 M5 13 L12 20 L19 13"/></svg>` });
    Object.assign(tag.style, { position: "absolute", right: "40px", top: "-34px" });
    box.appendChild(tag);
    layer.appendChild(page); stage.appendChild(layer);
    const tagAt = +v.etiquetteA || 0.6;
    return (t) => {
      bg(t); openStyle(page, t, 0);
      const bp = progress(t, f(10), f(20)); box.style.opacity = bp; box.style.transform = `translateY(${(1 - bp) * 30}px)`;
      ups.forEach((u) => u(t));
      const tp = progress(t, tagAt, f(26), EASE.pop), bob = Math.sin(Math.max(0, t - tagAt) * 5) * 6 * progress(t, tagAt + 0.4, f(10));
      tag.style.opacity = progress(t, tagAt, f(8));
      tag.style.transform = `translateY(${bob}px) scale(${0.85 + 0.15 * tp})`;
    };
  };

  /** Contenu des fenêtres des IA : ciel + logo (Claude), galaxie (Astra), ou dégradé simple. */
  function screen(kind, name, color, nameAt) {
    const box = h("div", "fill", { overflow: "hidden" });
    if (kind === "ciel") {
      box.style.background = "linear-gradient(180deg, #86B2DA 0%, #A7C6E2 55%, #E9D2B4 100%)";
      const clouds = [[80, 60, 260], [520, 40, 220], [-60, 250, 300], [560, 290, 320]].map(([x, y, w], i) => {
        const c = h("div", null, { position: "absolute", top: y + "px", width: w + "px", height: w * 0.36 + "px", borderRadius: "999px", background: "rgba(255,248,240,.85)", filter: "blur(18px)" });
        box.appendChild(c); return [c, x, i];
      });
      const center = h("div", "fill", { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "6px" });
      center.appendChild(h("div", null, { width: "150px", height: "150px", borderRadius: "999px", background: "#D9774F", display: "flex", alignItems: "center", justifyContent: "center", boxShadow: "0 12px 40px rgba(120,50,20,.3)" }, icon("burst", 104, "#FFFFFF")));
      const nm = h("div", null, { fontFamily: "var(--serif)", fontSize: "132px", color: "#fff", lineHeight: 1.05, textShadow: "0 4px 30px rgba(40,60,90,.25)" }, escapeHtml(name));
      center.appendChild(nm); box.appendChild(center);
      return { el: box, up: (t) => {
        const fr = t * FPS;
        clouds.forEach(([c, x, i]) => (c.style.left = x + ((fr * (0.25 + i * 0.08)) % 900) - 120 + "px"));
        const p = progress(t, nameAt, f(20)); nm.style.opacity = p; nm.style.transform = `translateY(${(1 - p) * 20}px)`;
      } };
    }
    if (kind === "galaxie") {
      box.style.background = "#020205";
      const NS = "http://www.w3.org/2000/svg", R = rng(27);
      const svg = document.createElementNS(NS, "svg");
      svg.setAttribute("viewBox", "0 0 760 380"); svg.setAttribute("width", "100%"); svg.setAttribute("height", "100%"); svg.style.position = "absolute";
      const stars = Array.from({ length: 90 }, () => { const c = document.createElementNS(NS, "circle"); c.setAttribute("cx", R() * 760); c.setAttribute("cy", R() * 380); c.setAttribute("r", 0.6 + R() * 1.6); c.setAttribute("fill", "#fff"); svg.appendChild(c); return c; });
      const g = document.createElementNS(NS, "g"); svg.appendChild(g);
      const arms = Array.from({ length: 520 }, (_, i) => {
        const c = document.createElementNS(NS, "circle"); c.setAttribute("r", 0.7 + R() * 1.8); c.setAttribute("fill", "#F2F4FF"); c.setAttribute("opacity", 0.4 + R() * 0.6); g.appendChild(c);
        return { c, arm: i % 2, tt: (i / 520) * 3.2 + R() * 0.12, dr: (R() - 0.5) * 14 };
      });
      box.appendChild(svg);
      const [a, b] = String(name).split(" · ");
      const left = h("div", "big", { position: "absolute", left: "26px", top: "50%", fontWeight: 800, fontSize: "58px", letterSpacing: "-1px" }, escapeHtml(a || name));
      const right = h("div", "big", { position: "absolute", right: "26px", top: "50%", fontWeight: 800, fontSize: "58px", letterSpacing: "-1px" }, escapeHtml(b || ""));
      box.append(left, right);
      return { el: box, up: (t) => {
        const fr = t * FPS, turn = fr * 0.004;
        stars.forEach((s, i) => s.setAttribute("opacity", 0.25 + 0.35 * Math.sin(fr * 0.05 + i)));
        arms.forEach((s) => { const an = s.tt * 2.4 + s.arm * Math.PI + turn, rad = 14 + s.tt * 44 + s.dr; s.c.setAttribute("cx", 380 + Math.cos(an) * rad); s.c.setAttribute("cy", 190 + Math.sin(an) * rad * 0.9); });
        const p = progress(t, nameAt, f(20));
        left.style.opacity = right.style.opacity = p;
        left.style.transform = `translate(${(1 - p) * -20}px, -50%)`; right.style.transform = `translate(${(1 - p) * 20}px, -50%)`;
      } };
    }
    box.style.background = `linear-gradient(160deg, ${color} 0%, #15171C 85%)`;
    const nm = h("div", "fill", { display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "var(--serif)", fontSize: "110px", color: "#fff" }, escapeHtml(name));
    box.appendChild(nm);
    return { el: box, up: (t) => { const p = progress(t, nameAt, f(20)); nm.style.opacity = p; } };
  }

  /** Deux IA face à face + pastille VS. vars : A et B = {nom, couleur, ecran (ciel|galaxie|degrade), texte, marque, entree, icone}, vs (s) */
  B.scene_vs = ({ stage, v, D }) => {
    const bg = wave(stage, v.fond || COLORS.accent);
    const A = Object.assign({ nom: "Claude Opus 5.5", couleur: COLORS.claude, ecran: "ciel", texte: "OPUS 5.5", marque: "Anthropic", entree: 0.05, icone: "burst" }, typeof v.A === "string" ? JSON.parse(v.A) : v.A);
    const Bb = Object.assign({ nom: "ChatGPT 6 Astra", couleur: COLORS.astra, ecran: "galaxie", texte: "GPT-6 · Astra", marque: "OpenAI", entree: 1.5, icone: "knot" }, typeof v.B === "string" ? JSON.parse(v.B) : v.B);
    const WIN = { w: 760, h: 440, top: 170, left: 150 };
    const ups = [A, Bb].map((s, i) => {
      const left = i === 0 ? WIN.left : 1920 - WIN.left - WIN.w;
      const w = win({ title: s.nom, color: s.couleur, width: WIN.w, height: WIN.h });
      Object.assign(w.el.style, { position: "absolute", top: WIN.top + "px", left: left + "px" });
      const sc = screen(s.ecran, s.texte, s.couleur, s.entree + 0.55); w.body.appendChild(sc.el);
      const maker = h("span", null, { color: COLORS.muted, fontWeight: 600 }, " · " + escapeHtml(s.marque || ""));
      const l = label({ text: s.nom, color: s.couleur, size: 32, ico: icon(s.icone, 28, "#FFFFFF") });
      l.lastChild.appendChild(maker);
      const lw = h("div", null, { position: "absolute", top: WIN.top + WIN.h + 34 + "px", left: left + "px", width: WIN.w + "px", display: "flex", justifyContent: "center" }, l);
      stage.append(w.el, lw);
      return (t) => {
        w.el.style.visibility = lw.style.visibility = t >= s.entree ? "visible" : "hidden";
        openStyle(w.el, t, s.entree); openStyle(l, t, s.entree + 0.25); sc.up(t); maker.style.opacity = progress(t, s.entree + 1.2, f(14));
      };
    });
    const vsAt = +v.vs || Bb.entree + 1.2, size = 150;
    const vs = h("div", null, { position: "absolute", left: 960 - size / 2 + "px", top: WIN.top + WIN.h / 2 - size / 2 + "px", width: size + "px", height: size + "px", borderRadius: "999px",
      background: "radial-gradient(circle at 35% 30%, #FF7A6B 0%, #E5383B 55%, #B81D2A 100%)", border: `${size * 0.045}px solid #fff`,
      boxShadow: "0 18px 50px rgba(0,0,0,.5), inset 0 -8px 20px rgba(0,0,0,.25)", display: "flex", alignItems: "center", justifyContent: "center",
      fontWeight: 900, fontSize: size * 0.38 + "px", color: "#fff", letterSpacing: "-2px", textShadow: "0 3px 10px rgba(0,0,0,.35)" }, "VS");
    stage.appendChild(vs);
    return (t) => {
      bg(t); ups.forEach((u) => u(t));
      const p = progress(t, vsAt, f(24), EASE.pop);
      vs.style.opacity = progress(t, vsAt, f(6)); vs.style.transform = `scale(${0.4 + 0.6 * p}) rotate(${(1 - p) * -25}deg)`;
    };
  };

  /** Vainqueur sur fond doré. vars : nom, couleur, detail ("6 manches à 1") */
  B.scene_vainqueur = ({ stage, v }) => {
    const bg = wave(stage, COLORS.or), color = v.couleur || COLORS.claude;
    const layer = h("div", "layer", { justifyContent: "center", alignItems: "center" });
    const w = win({ title: v.titre || "Résultat final", color: COLORS.or, width: 1320, bodyStyle: { padding: "56px 60px 64px", display: "flex", flexDirection: "column", alignItems: "center", gap: "26px" } });
    const l = label({ text: "Vainqueur", color: COLORS.or, size: 30, ico: icon("trophy", 26) });
    const name = h("div", "big", { fontSize: "150px", letterSpacing: "-5px", textShadow: "0 8px 40px rgba(0,0,0,.6)" }, escapeHtml(v.nom || "Claude Opus 5.5"));
    const bar = h("div", null, { height: "10px", width: "860px", borderRadius: "5px", background: color, boxShadow: "0 4px 14px rgba(0,0,0,.4)" });
    const det = h("div", "big", { fontSize: "72px", color: COLORS.muted }, escapeHtml(v.detail || ""));
    w.body.append(l, name, bar, det); layer.appendChild(w.el); stage.appendChild(layer);
    const r = reveal(det, 0.9);
    return (t) => {
      bg(t); openStyle(w.el, t, 0); openStyle(l, t, f(6));
      const land = progress(t, f(9), f(24));
      name.style.transform = `scale(${1.12 - 0.12 * land})`; name.style.filter = `blur(${(1 - land) * 14}px)`; name.style.opacity = Math.min(1, land * 1.6);
      bar.style.transform = `scaleX(${land})`; r(t);
    };
  };

  /** Fin de vidéo : question en fenêtre, « Dis-le en commentaire », merci, Tsar. vars : question (HTML simple autorisé : <b style>), merci */
  B.scene_outro = ({ stage, v, D }) => {
    const bg = wave(stage, COLORS.accent);
    const layer = h("div", "layer", { flexDirection: "column", justifyContent: "center", alignItems: "flex-start", gap: "30px", paddingLeft: "130px" });
    const w = win({ title: "Commentaires", color: COLORS.accent, width: 1180, bodyStyle: { padding: "44px 54px 50px" } });
    w.body.appendChild(h("div", "big", { fontSize: "104px", lineHeight: 1.05 }, v.question ||
      'Et toi, tu préfères <span style="color:var(--claude)">Claude</span> ou <span style="color:var(--astra)">Astra</span> ?'));
    const l = label({ text: v.appel || "Dis-le en commentaire", color: COLORS.accent, size: 34, ico: icon("chat", 24, "#FFFFFF") });
    const merci = h("div", "big", { fontSize: "56px", color: COLORS.muted }, escapeHtml(v.merci || "Merci d'avoir regardé !"));
    layer.append(w.el, l, merci); stage.appendChild(layer);
    const m = mascot(stage, { mood: "explication", start: 0.3, end: D + 1, x: 1600, size: 600 });
    const r = reveal(merci, 2.4);
    return (t) => { bg(t); openStyle(w.el, t, 0); openStyle(l, t, 0.9); r(t); m(t); };
  };

  /** Fond seul (pour poser autre chose dessus). vars : couleur */
  B.scene_fond = ({ stage, v }) => wave(stage, v.couleur || COLORS.accent);

  // ───────────── style WOLF dans la vidéo longue (méthode par défaut depuis le 2026-10-06), comme ses vidéos
  // (config/youtube/references/wolf/style.md § Éléments à l'écran) : gros texte blanc épais contouré de noir partout.
  /** Nombre d'une variable, 0 compris (« +v.a || 0.6 » remplaçait un 0 voulu par la valeur par défaut). */
  const num = (x, d) => (x === undefined || x === null || x === "" || isNaN(+x) ? d : +x);
  const list = (x) => (typeof x === "string" ? JSON.parse(x) : x || []);
  const WOLF_FONT = '"Montserrat", sans-serif';
  const PLAQUE = { background: "rgba(10,10,12,.86)", padding: "12px 26px 14px", borderRadius: "18px", boxShadow: "0 12px 30px rgba(0,0,0,.45)" };
  /** Largeur estimée d'un texte en Montserrat 900 (em) : déterministe, sans mesurer le DOM (les polices peuvent ne pas
   *  être chargées au montage de la scène). Sert à réduire un texte trop long au lieu de le laisser déborder. */
  const largeurEm = (txt) => [...String(txt)].reduce((n, c) => n + (c === " " ? 0.3 : /[A-ZÀ-Ý0-9]/.test(c) ? 0.76
    : /[il.,:;'!|]/.test(c) ? 0.32 : 0.62), 0.1);
  const fitSize = (txt, size, maxW) => (maxW ? Math.min(size, Math.floor(maxW / largeurEm(txt))) : size);
  const wolfText = (txt, size, color = "#FFFFFF", maxW = 0) => {
    size = fitSize(txt, size, maxW);
    return h("div", null, { fontFamily: WOLF_FONT, fontWeight: 900, fontSize: size + "px",
      lineHeight: 1.02, color, letterSpacing: "-1px", WebkitTextStroke: `${Math.max(4, Math.round(size / 10))}px #0A0A0C`,
      paintOrder: "stroke fill", textShadow: "0 8px 22px rgba(0,0,0,.45)", whiteSpace: "nowrap" }, escapeHtml(txt));
  };
  const wolfLogo = (logo, size, ring) => {
    const disc = h("div", null, { width: size + "px", height: size + "px", borderRadius: "50%", display: "flex", alignItems: "center",
      justifyContent: "center", background: logo === "claude" ? "#F4F1EA" : "#FFFFFF", border: `${Math.round(size / 30)}px solid ${ring}`,
      boxShadow: "0 16px 40px rgba(0,0,0,.45)", flex: "none" });
    const img = h("img", null, { width: size * 0.64 + "px", height: size * 0.64 + "px", objectFit: "contain" });
    img.src = `assets/logos/${logo}.svg`; disc.appendChild(img);
    return disc;
  };

  /** Étiquette permanente en bas à gauche : le nom de ce qu'on teste, en texte blanc contouré, tenu toute la séquence ;
   *  il passe au vert quand le test réussit (au rouge s'il rate : ajout pour les duels). vars : texte, taille, etat = [[s, "ok" | "rate"], …] */
  B.pastille = ({ stage, v, D }) => {
    const etat = list(v.etat).map(([t, e]) => [+t, e]).sort((a, b) => a[0] - b[0]);
    const txt = wolfText(v.texte || "Le combat", +v.taille || 64, "#FFFFFF", vertical() ? 860 : 1100);
    // Short : plaque sombre derrière le texte (un enregistrement d'écran a ses propres titres en haut : sans plaque, les deux
    // textes se mélangent, revue de site-ennui du 2026-10-08)
    // place "haut" (Short, 2026-10-13) : centrée au-dessus du carré de jeu
    const haut = vertical() && v.place === "haut";
    const box = h("div", null, haut ? { transformOrigin: "50% 50%", ...PLAQUE }
      : vertical() ? { position: "absolute", left: "50px", top: "150px", transformOrigin: "0 0", ...PLAQUE }
      : { position: "absolute", left: "64px", bottom: "56px", transformOrigin: "0 100%" }, txt);
    if (haut) {
      const row = h("div", null, { position: "absolute", left: 0, right: 0, top: (+v.haut || 300) + "px", display: "flex", justifyContent: "center" });
      row.appendChild(box); stage.appendChild(row);
    } else stage.appendChild(box);
    return (t) => {
      const st = [...etat].reverse().find(([x]) => t >= x);
      txt.style.color = !st ? "#FFFFFF" : st[1] === "ok" ? "#4BE36B" : "#FF4B4B";
      const intro = progress(t, 0, f(12), EASE.pop), hit = st ? 1 - progress(t, st[0], f(16), EASE.out) : 0;
      box.style.transform = `scale(${(0.6 + 0.4 * intro) * (1 + 0.25 * hit)})`;
      box.style.opacity = progress(t, 0, f(6)) * (1 - progress(t, D - f(6), f(6), EASE.in));
    };
  };

  /** Carte titre : plein écran (nom en gros texte blanc contouré sur fond bleu uni) pendant `plein` s (2 à 3 s chez
   *  WOLF), puis réduite dans le coin en haut à droite pendant la présentation, jusqu'à la fin de l'élément.
   *  vars : texte, fond, logo (claude | chatgpt | ""), plein (s) */
  B.carte = ({ stage, v, D }) => {
    const plein = Math.min(num(v.plein, 2.5), D);
    const bg = h("div", "fill", { background: v.fond || "#2F6FED" });
    const card = h("div", null, { position: "absolute", left: "50%", top: "50%", display: "flex", flexDirection: "column", alignItems: "center",
      gap: "40px", transformOrigin: "50% 50%" });
    if (v.logo) card.appendChild(wolfLogo(v.logo, 260, "#FFFFFF"));
    card.appendChild(wolfText(v.texte || "CLAUDE", vertical() ? 170 : 190, "#FFFFFF", vertical() ? 960 : 1600));
    stage.append(bg, card);
    const cx0 = SW / 2, cy0 = SH / 2, cx1 = vertical() ? SW - 190 : 1600, cy1 = vertical() ? 360 : 140;  // centre → coin en haut à droite
    return (t) => {
      const pin = progress(t, 0, f(12), EASE.pop);
      const k = progress(t, plein, f(20), EASE.inOut);                       // 0 plein écran → 1 dans le coin
      bg.style.opacity = 1 - progress(t, plein, f(10));
      const s = (1.15 - 0.15 * pin) * (1 - 0.72 * k);
      const x = cx0 + (cx1 - cx0) * k, y = cy0 + (cy1 - cy0) * k;
      card.style.transform = `translate(${x - cx0}px, ${y - cy0}px) translate(-50%, -50%) scale(${s})`;
      card.style.opacity = 1 - progress(t, D - f(6), f(6), EASE.in);
    };
  };

  /** Carte de progression qui revient entre les tests (frise « test 1 … test N », comme ses « level 1 … level 7 »),
   *  avec un panoramique jusqu'au test en cours ; les tests passés montrent le logo du gagnant, le test en cours
   *  reçoit le sien à `a` s. vars : tests = [{nom, gagnant: "a" | "b" | "nul" | ""}], actuel (index du test en
   *  cours, 0 = premier), a (s), nomA, couleurA, logoA, nomB, couleurB, logoB */
  B.progression = ({ stage, v, D }) => {
    const tests = list(v.tests), cur = Math.min(+v.actuel || 0, tests.length - 1), at = num(v.a, 1.0);
    const ia = { a: { couleur: v.couleurA || COLORS.claude, logo: v.logoA ?? "claude" }, b: { couleur: v.couleurB || COLORS.astra, logo: v.logoB ?? "chatgpt" } };
    const bg = h("div", "fill", { background: "radial-gradient(80% 60% at 50% 45%, #2A2F3A, #0C0E12)" });
    // 2026-10-10 : quand toutes les cartes tiennent à l'écran (4 tests ou moins), frise fixe et centrée, sans panoramique
    // (le défilement coupait les cartes voisines sur les bords)
    const n = tests.length, GAP = 36, tient = !vertical() && n <= 5;
    const W = tient ? Math.min(520, Math.floor((SW - 120 - GAP * (n - 1)) / n)) : 520;
    const track = h("div", null, { position: "absolute", top: "290px", left: tient ? Math.round((SW - (n * W + GAP * (n - 1))) / 2) + "px" : "0", display: "flex", gap: (tient ? GAP : 40) + "px", transformOrigin: "50% 50%" });
    const slots = tests.map((tst, i) => {
      const slot = h("div", null, { width: W + "px", height: "500px", borderRadius: "36px", display: "flex", flexDirection: "column",
        alignItems: "center", justifyContent: "center", gap: "34px", background: i === cur ? "#2F6FED" : "rgba(255,255,255,.08)",
        border: i === cur ? "8px solid #FFFFFF" : "8px solid rgba(255,255,255,.18)", flex: "none" });
      slot.appendChild(wolfText(`TEST ${i + 1}`, 64, "#FFFFFF", W - 60));
      slot.appendChild(wolfText(tst.nom || "", 58, "#FFFFFF", W - 60));
      const res = h("div", null, { height: "150px", display: "flex", alignItems: "center", gap: "18px" });
      slot.appendChild(res);
      track.appendChild(slot);
      return [tst, slot, res];
    });
    const fill = (res, g) => {
      res.innerHTML = "";
      if (g === "a" || g === "b") res.appendChild(wolfLogo(ia[g].logo, 140, ia[g].couleur));
      else if (g === "nul") { res.appendChild(wolfLogo(ia.a.logo, 110, ia.a.couleur)); res.appendChild(wolfLogo(ia.b.logo, 110, ia.b.couleur)); }
    };
    // test en cours compris : son logo est créé dès le départ (chargé avant le rendu) et montré à `a`
    slots.forEach(([tst, , res], i) => { if (i <= cur) fill(res, tst.gagnant); });
    stage.append(bg, track);
    const xOf = (i) => 960 - (i * (W + 40) + W / 2);                          // le test i au centre de l'écran
    return (t) => {
      const pan = progress(t, 0, Math.min(1.2, D * 0.5), EASE.inOut);
      if (tient) track.style.transform = `scale(${1 + 0.035 * progress(t, 0, D, EASE.inOut)})`; else track.style.transform = `translateX(${xOf(Math.max(0, cur - 1)) + (xOf(cur) - xOf(Math.max(0, cur - 1))) * pan}px)`;
      const [tst, slot, res] = slots[cur] || [];
      if (slot) {
        const won = tst.gagnant && t >= at;
        const q = won ? progress(t, at, f(12), EASE.pop) : 0;
        res.style.opacity = won ? 1 : 0; res.style.transform = `scale(${0.6 + 0.4 * q})`;
        slot.style.transform = `scale(${won ? 1 + 0.08 * (1 - progress(t, at, f(16))) : 1})`;
      }
      stage.style.opacity = progress(t, 0, f(5)) * (1 - progress(t, D - f(5), f(5), EASE.in));
    };
  };

  /** Capture zoomée (page web, consigne, fichier) avec la zone importante surlignée en jaune, comme ses « 31,000 Robux ».
   *  vars : image (chemin depuis 08_HYPERFRAMES, ex. videos/<id>/captures/x.png), zone = [x, y, l, h] en fractions
   *  de l'image, a (s : début du surlignage), largeur (px de la capture à l'écran) ; ou zones = [[s, x, y, l, h], …] :
   *  le surlignage et le cadrage passent d'une ligne à la suivante au fil de la voix (annonce d'une IA, consigne en
   *  plusieurs points ; ajout du 2026-10-08 : illustrer ce qui est dit sans montrer la suite de la vidéo) */
  B.capture = ({ stage, v, D }) => {
    const zs = list(v.zones).map((z) => z.map(Number)).sort((p, q) => p[0] - q[0]);
    const zone = zs.length ? zs[0].slice(1) : list(v.zone).length ? list(v.zone) : [0.3, 0.45, 0.4, 0.1];
    const at = zs.length ? zs[0][0] : num(v.a, 0.6), L = Math.min(+v.largeur || 1300, SW - 100);
    const frame = h("div", null, { position: "absolute", left: "50%", top: "50%", width: L + "px", borderRadius: "18px", overflow: "hidden",
      border: "6px solid #FFFFFF", boxShadow: "0 30px 80px rgba(0,0,0,.6)", transformOrigin: "50% 50%" });
    const img = h("img", null, { display: "block", width: "100%" });
    img.src = v.image || "";
    const mark = h("div", null, { position: "absolute", left: zone[0] * 100 + "%", top: zone[1] * 100 + "%", width: zone[2] * 100 + "%",
      height: zone[3] * 100 + "%", background: "rgba(255,230,0,.45)", border: "4px solid #FFE600", transformOrigin: "0 50%" });
    frame.append(img, mark);
    stage.appendChild(frame);
    const zoneAt = (t) => {                                                    // zone en cours, glissée vers la suivante
      if (!zs.length) return zone;
      let i = 0;
      while (i + 1 < zs.length && t >= zs[i + 1][0]) i++;
      if (i === 0) return zs[0].slice(1);
      const k = progress(t, zs[i][0], f(18), EASE.inOut);
      return zs[i].slice(1).map((x, j) => zs[i - 1][j + 1] + (x - zs[i - 1][j + 1]) * k);
    };
    const HMAX = vertical() ? 1100 : 900;                                      // une capture haute ne dépasse pas l'écran
    let W = L;
    return (t) => {
      if (img.naturalWidth && img.naturalHeight) W = Math.min(L, Math.round(HMAX * img.naturalWidth / img.naturalHeight));
      frame.style.width = W + "px";
      const pin = progress(t, 0, f(12), EASE.pop);
      const zn = zoneAt(t);
      Object.assign(mark.style, { left: zn[0] * 100 + "%", top: zn[1] * 100 + "%", width: zn[2] * 100 + "%", height: zn[3] * 100 + "%" });
      // zoom sur la zone surlignée après son tracé
      const z = progress(t, at + f(14), f(24), EASE.inOut) * (zs.length ? 0.5 : 1);
      const cx = (zn[0] + zn[2] / 2 - 0.5) * W, cy = (zn[1] + zn[3] / 2 - 0.5) * (frame.offsetHeight || W * 0.56);
      const s = (0.85 + 0.15 * pin) * (1 + 0.6 * z);
      frame.style.transform = `translate(-50%, -50%) scale(${s}) translate(${-cx * z}px, ${-cy * z}px)`;
      const m = progress(t, at, f(14), EASE.inOut);
      mark.style.transform = `scaleX(${m})`; mark.style.opacity = m > 0 ? 1 : 0;
      frame.style.opacity = progress(t, 0, f(5)) * (1 - progress(t, D - f(6), f(6), EASE.in));
    };
  };

  // ───────────── direction « duel lisible et nerveux » (2026-10-07) : éléments tirés des duels d'IA qui performent
  // (config/youtube/references/montage/analyse-2026-10-07.md) : accroche, minuteur, notes, flèches, mot-clé.

  /** Noms des deux IA sur l'écran partagé, dans le même texte que le VS (wolfText, 72 px) : vertical, A en bas de la
   *  moitié du haut et B en haut de celle du bas ; horizontal, en bas de chaque moitié (2026-10-13, sukuna-ia-short1).
   *  vars : nomA, nomB */
  B.noms_partage = ({ stage, v }) => {
    const V = vertical(), place = (k, style) => {
      const row = h("div", null, { position: "absolute", display: "flex", justifyContent: "center", ...style });
      row.appendChild(wolfText(v["nom" + k] || (k === "A" ? "CLAUDE" : "CHATGPT"), 72, "#FFFFFF", 560)); stage.appendChild(row);
    };
    if (V) { place("A", { left: 0, right: 0, top: "860px" }); place("B", { left: 0, right: 0, top: "990px" }); }
    else { place("A", { left: 0, width: "960px", bottom: "60px" }); place("B", { left: "960px", width: "960px", bottom: "60px" }); }
    return () => {};
  };

  /** Les deux IA qui entrent l'une après l'autre (logo + nom), puis « VS » entre elles (Minimunch, Silas, Prompt Potato).
   *  vars : nomA, logoA, couleurA, a (s), nomB, logoB, couleurB, b (s), vs (s) */
  B.duel = ({ stage, v, D }) => {
    const side = (k) => {
      const col = h("div", null, { display: "flex", flexDirection: "column", alignItems: "center", gap: "22px" });
      col.append(wolfLogo(v["logo" + k] ?? (k === "A" ? "claude" : "chatgpt"), 250, v["couleur" + k] || (k === "A" ? COLORS.claude : COLORS.astra)),
        wolfText(v["nom" + k] || (k === "A" ? "CLAUDE" : "CHATGPT"), 72, "#FFFFFF", 560));
      return col;
    };
    // seul : la première IA seule, même style que dans le VS (gojo-ia, 2026-10-13 : « Claude » de l'accroche)
    const seul = v.seul === true || v.seul === "true";
    const A = side("A"), Bc = side("B"), vs = wolfText("VS", 150, "#E5383B");
    if (seul) { Bc.style.display = vs.style.display = "none"; }
    // en vertical aussi côte à côte (gojo-ia, 2026-10-13 : en colonne, le nom de la 2e IA tombait sur les sous-titres)
    const row = h("div", null, { position: "absolute", left: 0, right: 0, top: vertical() ? "44%" : "50%", transform: "translateY(-50%)", display: "flex",
      flexDirection: "row", justifyContent: "center", alignItems: "center", gap: vertical() ? "26px" : "90px" }, [A, vs, Bc]);
    stage.appendChild(row);
    const ta = num(v.a, 0), tb = num(v.b, 0.6), tv = num(v.vs, 1.2);
    return (t) => {
      [[A, ta, -1], [Bc, tb, 1]].forEach(([c, t0, s]) => {
        const p = progress(t, t0, f(14), EASE.pop);
        c.style.opacity = t >= t0 ? 1 : 0; c.style.transform = `translateX(${s * 260 * (1 - p)}px) scale(${0.7 + 0.3 * p})`;
      });
      const q = progress(t, tv, f(10), EASE.pop);
      vs.style.opacity = t >= tv ? 1 : 0; vs.style.transform = `scale(${2.2 - 1.2 * q}) rotate(${-8 * (1 - q)}deg)`;
      row.style.opacity = 1 - progress(t, D - f(6), f(6), EASE.in);
    };
  };

  /** Titre du jeu dans sa propre police : son logo (image, chemin depuis 08_HYPERFRAMES) en gros au centre, sinon le nom
   *  en gros texte contouré. vars : image, texte, largeur (px) */
  B.titre_jeu = ({ stage, v, D }) => {
    const box = h("div", null, { position: "absolute", left: "50%", top: "50%", transformOrigin: "50% 50%" });
    if (v.image) {
      const img = h("img", null, { width: Math.min(+v.largeur || 1100, SW - 120) + "px", display: "block", filter: "drop-shadow(0 18px 40px rgba(0,0,0,.6))" });
      img.src = v.image; box.appendChild(img);
    } else box.appendChild(wolfText(v.texte || "MINECRAFT", vertical() ? 160 : 180, "#FFFFFF", SW - 320));
    stage.appendChild(box);
    return (t) => {
      const p = progress(t, 0, f(12), EASE.pop);
      box.style.transform = `translate(-50%, -50%) scale(${(1.25 - 0.25 * p) * (1 + 0.04 * Math.min(1, t / D))})`;
      box.style.opacity = progress(t, 0, f(4)) * (1 - progress(t, D - f(6), f(6), EASE.in));
    };
  };

  /** Minuteur qui défile (temps imparti, génération) : cadran avec anneau qui se vide et temps en gros chiffres.
   *  vars : de (s affichées au début, ex. 2700 = 45:00 ; 0 pour un temps qui monte), a (s affichées à la fin), position (haut-gauche par défaut : la
   *  carte réduite occupe le haut droite pendant les tests | haut-droite | centre), taille */
  B.minuteur = ({ stage, v, D }) => {
    const de = v.de === undefined || v.de === "" ? 2700 : +v.de;               // 0 permis : un minuteur qui monte (0:00 → 9:00)
    const a = v.a === undefined || v.a === "" ? Math.max(0, de - D) : +v.a, tot = Math.max(de, a, 1), S = +v.taille || (v.position === "centre" ? 420 : vertical() ? 200 : 220);
    const wrap = h("div", null, { position: "absolute", width: S + "px", height: S + "px",
      ...(v.position === "centre" ? { left: "50%", top: "50%", marginLeft: -S / 2 + "px", marginTop: -S / 2 + "px" }
        : v.position === "haut-droite" ? { right: "56px", top: vertical() ? "270px" : "48px" } : { left: vertical() ? "50px" : "56px", top: vertical() ? "270px" : "48px" }) });
    wrap.innerHTML = `<svg viewBox="0 0 100 100" width="${S}" height="${S}"><circle cx="50" cy="50" r="46" fill="rgba(10,10,12,.82)"/>
      <circle cx="50" cy="50" r="41" fill="none" stroke="rgba(255,255,255,.18)" stroke-width="5"/>
      <circle class="arc" cx="50" cy="50" r="41" fill="none" stroke="#E5383B" stroke-width="5" stroke-linecap="round"
        transform="rotate(-90 50 50)" stroke-dasharray="257.6" stroke-dashoffset="0"/></svg>`;
    const txt = h("div", null, { position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
      fontFamily: WOLF_FONT, fontWeight: 900, fontSize: S * 0.22 + "px", color: "#FFFFFF", fontVariantNumeric: "tabular-nums" });
    wrap.appendChild(txt); stage.appendChild(wrap);
    const arc = wrap.querySelector(".arc");
    const mmss = (s) => { s = Math.max(0, Math.round(s)); const hh = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), ss = s % 60;
      return (hh ? hh + ":" + String(m).padStart(2, "0") : m) + ":" + String(ss).padStart(2, "0"); };
    return (t) => {
      const k = Math.min(1, t / D), cur = de + (a - de) * k;
      txt.textContent = mmss(cur);
      arc.setAttribute("stroke-dashoffset", String(257.6 * (1 - cur / tot)));
      wrap.style.transform = `scale(${0.6 + 0.4 * progress(t, 0, f(10), EASE.pop)})`;
      wrap.style.opacity = progress(t, 0, f(4)) * (1 - progress(t, D - f(6), f(6), EASE.in));
    };
  };

  /** Pastille « accéléré » sur une génération ou un passage montré en accéléré (Code BH, tef), en haut au centre : le bas
   *  droite est à Tsar, qui réagit pendant l'attente, le haut droite à la carte réduite. vars : texte (ex. ×10) */
  B.accelere = ({ stage, v, D }) => {
    const box = h("div", null, { position: "absolute", left: "50%", top: vertical() ? "270px" : "44px", transform: "translateX(-50%)", display: "flex",
      alignItems: "center", gap: "14px", padding: "10px 22px", borderRadius: "16px", background: "rgba(10,10,12,.78)" });
    box.innerHTML = `<svg viewBox="0 0 40 24" width="70" height="42"><path d="M2 2 L18 12 L2 22 Z M20 2 L36 12 L20 22 Z" fill="#FFFFFF"/></svg>`;
    if (v.texte) box.appendChild(wolfText(v.texte, 52));
    stage.appendChild(box);
    return (t) => {
      box.style.opacity = progress(t, 0, f(5)) * (1 - progress(t, D - f(5), f(5), EASE.in)) * (0.75 + 0.25 * Math.abs(Math.cos(t * Math.PI)));
    };
  };

  /** Bandeau « À venir » pendant le montage des meilleurs moments de l'accroche (Prompt Potato « COMING UP »).
   *  vars : texte */
  B.a_venir = ({ stage, v, D }) => {
    const box = h("div", null, { position: "absolute", left: vertical() ? "50px" : "64px", top: vertical() ? "150px" : "52px", display: "grid", gap: "8px", transformOrigin: "0 50%",
      ...(vertical() ? PLAQUE : {}) });
    box.append(wolfText(v.texte || "À VENIR", 96));
    stage.appendChild(box);
    return (t) => {
      const p = progress(t, 0, f(10), EASE.out);
      box.style.transform = `translateX(${-80 * (1 - p)}px)`;
      box.style.opacity = p * (1 - progress(t, D - f(6), f(6), EASE.in));
    };
  };

  /** Carte de note d'une IA (Prompt Potato, Silas) : logo, nom, note en gros qui tombe à `a`, puis jusqu'à 3 points
   *  forts (+) ou faibles (−). vars : nom, logo, couleur, note (ex. « 7/10 »), points = [["+" | "-", texte], …], a (s) */
  B.note = ({ stage, v, D }) => {
    const pts = list(v.points), at = num(v.a, 0.6), col = v.couleur || COLORS.claude;
    const card = h("div", null, { position: "absolute", left: "50%", top: "50%", width: vertical() ? "940px" : "1180px", padding: "48px 56px", borderRadius: "34px",
      background: "rgba(12,12,14,.97)", border: `6px solid ${col}`, display: "grid", gridTemplateColumns: vertical() ? "1fr" : "auto 1fr", gap: "26px 46px",
      alignItems: "center", justifyItems: vertical() ? "center" : "stretch", boxShadow: "0 40px 90px rgba(0,0,0,.55)" });
    const head = h("div", null, { display: "flex", flexDirection: "column", alignItems: "center", gap: "18px" },
      [wolfLogo(v.logo ?? "claude", 210, col), wolfText(v.nom || "CLAUDE", 54, "#FFFFFF", 300)]);
    const big = wolfText(v.note || "7/10", 190, "#F5B942");
    const lines = pts.map(([s, txt]) => {
      const l = h("div", null, { display: "flex", gap: "18px", alignItems: "baseline", fontFamily: WOLF_FONT, fontWeight: 800, fontSize: "46px",
        color: "#FFFFFF" });
      l.append(h("span", null, { color: s === "-" ? "#FF4B4B" : "#4BE36B", fontWeight: 900, width: "34px" }, s === "-" ? "−" : "+"),
        h("span", null, {}, escapeHtml(txt)));
      return l;
    });
    const right = h("div", null, { display: "grid", gap: "14px" }, [big, ...lines]);
    card.append(head, right); stage.appendChild(card);
    return (t) => {
      const p = progress(t, 0, f(12), EASE.pop);
      card.style.transform = `translate(-50%, -50%) scale(${0.85 + 0.15 * p})`;
      card.style.opacity = progress(t, 0, f(5)) * (1 - progress(t, D - f(6), f(6), EASE.in));
      const q = progress(t, at, f(12), EASE.pop);
      big.style.opacity = t >= at ? 1 : 0; big.style.transform = `scale(${1.6 - 0.6 * q})`; big.style.transformOrigin = "0 50%";
      lines.forEach((l, i) => { const r = progress(t, at + 0.5 + i * 0.45, f(10), EASE.out); l.style.opacity = r; l.style.transform = `translateX(${30 * (1 - r)}px)`; });
    };
  };

  /** Étiquette avec flèche sur ce que fait le jeu (Code BH « L'Obélisque → », Prompt Potato) : texte blanc contouré et
   *  flèche dessinée vers le point visé. vars : texte, x, y (point visé, fractions de l'image), cote (gauche | droite | haut | bas) */
  B.fleche = ({ stage, v, D }) => {
    const X = (num(v.x, 0.5)) * SW, Y = (num(v.y, 0.5)) * SH, cote = v.cote || "gauche";
    const off = (vertical() ? { gauche: [-220, -220], droite: [220, -220], haut: [0, -280], bas: [0, 260] }
      : { gauche: [-360, -150], droite: [360, -150], haut: [0, -260], bas: [0, 230] })[cote] || (vertical() ? [-220, -220] : [-360, -150]);
    const [mx, my0, my1] = vertical() ? [320, 200, 1400] : [160, 90, 1000];   // le texte reste dans l'écran (Short : au-dessus de l'interface)
    const lx = Math.max(mx, Math.min(SW - mx, X + off[0])), ly = Math.max(my0, Math.min(my1, Y + off[1]));
    const label = h("div", null, { position: "absolute", left: lx + "px", top: ly + "px", transform: "translate(-50%, -50%)" }, wolfText(v.texte || "La capture", 60, "#FFFFFF", vertical() ? 600 : 700));
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 0 ${SW} ${SH}`); svg.setAttribute("width", String(SW)); svg.setAttribute("height", String(SH));
    Object.assign(svg.style, { position: "absolute", inset: 0 });
    const sx = lx + (X - lx) * 0.22, sy = ly + (Y - ly) * 0.22 + (cote === "haut" ? 40 : cote === "bas" ? -40 : 34);
    const ex = X - (X - sx) * 0.12, ey = Y - (Y - sy) * 0.12, cx = (sx + ex) / 2 + (ey - sy) * 0.25, cy = (sy + ey) / 2 - (ex - sx) * 0.25;
    const ang = Math.atan2(ey - cy, ex - cx), hl = 34;
    const d = `M${sx},${sy} Q${cx},${cy} ${ex},${ey}`;
    const head = `M${ex - hl * Math.cos(ang - 0.5)},${ey - hl * Math.sin(ang - 0.5)} L${ex},${ey} L${ex - hl * Math.cos(ang + 0.5)},${ey - hl * Math.sin(ang + 0.5)}`;
    svg.innerHTML = `<path class="c" d="${d}" fill="none" stroke="#0A0A0C" stroke-width="20" stroke-linecap="round"/>
      <path class="c" d="${d}" fill="none" stroke="#FFFFFF" stroke-width="10" stroke-linecap="round"/>
      <path class="h" d="${head}" fill="none" stroke="#0A0A0C" stroke-width="20" stroke-linecap="round" stroke-linejoin="round"/>
      <path class="h" d="${head}" fill="none" stroke="#FFFFFF" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>`;
    stage.append(svg, label);
    const curves = svg.querySelectorAll(".c"), heads = svg.querySelectorAll(".h");
    const len = curves[0].getTotalLength ? curves[0].getTotalLength() : 600;
    curves.forEach((c) => { c.setAttribute("stroke-dasharray", String(len)); });
    return (t) => {
      const p = progress(t, 0, f(10), EASE.pop);
      label.style.transform = `translate(-50%, -50%) scale(${0.6 + 0.4 * p})`;
      const dr = progress(t, f(4), f(12), EASE.out);
      curves.forEach((c) => c.setAttribute("stroke-dashoffset", String(len * (1 - dr))));
      const tete = progress(t, f(14), f(3), EASE.lin);                       // la tête suit le trait, en fondu
      heads.forEach((hd) => { hd.style.opacity = tete; });
      const o = progress(t, 0, f(4)) * (1 - progress(t, D - f(6), f(6), EASE.in));
      label.style.opacity = o; svg.style.opacity = o;
    };
  };

  /** Mot-clé en énorme légende, environ un par minute (Aywen « PUBLICITÉ ») : seulement le mot qui frappe, en bas au
   *  centre, au-dessus de l'étiquette. Pas des sous-titres. vars : texte, couleur */
  B.mot = ({ stage, v, D }) => {
    const txt = wolfText(v.texte || "PUBLICITÉ", 150, v.couleur || "#FFFFFF", SW - 220);
    const box = h("div", null, { position: "absolute", left: 0, right: 0, bottom: vertical() ? "560px" : "150px", display: "flex", justifyContent: "center" }, txt);
    stage.appendChild(box);
    return (t) => {
      const p = progress(t, 0, f(8), EASE.pop);
      txt.style.transform = `scale(${1.5 - 0.5 * p})`;
      box.style.opacity = progress(t, 0, f(3)) * (1 - progress(t, D - f(5), f(5), EASE.in));
    };
  };

  /** Insert flash de 0,5 à 1 s au milieu du jeu (logo du jeu, rappel d'un moment) : image plein écran, éclair blanc à
   *  l'entrée, léger zoom. vars : image (chemin depuis 08_HYPERFRAMES), fond */
  B.insert = ({ stage, v, D }) => {
    const bg = h("div", "fill", { background: v.fond || "#0C0E12" });
    const img = h("img", "fill", { width: "100%", height: "100%", objectFit: "cover" });
    img.src = v.image || "";
    const flash = h("div", "fill", { background: "#FFFFFF" });
    stage.append(bg, img, flash);
    return (t) => {
      flash.style.opacity = 1 - progress(t, 0, f(8));
      img.style.transform = `scale(${1.12 - 0.08 * progress(t, 0, D, EASE.lin)})`;
    };
  };

  /** Image dans une case propre (fond sombre, liseré blanc, coins arrondis, ombre) posée sur le jeu : entre en pop
   *  depuis le bas avec une légère rotation, ressort en se réduisant (sukuna-ia, 2026-10-10 : Sukuna, logo de l'anime).
   *  vars : image (chemin depuis 08_HYPERFRAMES), largeur, hauteur (px de la case), x, y (centre, fraction de l'écran),
   *  rotation (degrés à l'arrivée), fond, bord (couleur du liseré), cadre (false : l'image seule, avec une ombre, pour un
   *  gros logo au milieu de l'écran : accroche du Short gojo-ia, 2026-10-13) */
  B.vignette = ({ stage, v, D }) => {
    const W = +v.largeur || 520, H = +v.hauteur || 520, rot = num(v.rotation, -4);
    const cadre = !(v.cadre === false || v.cadre === "false");
    const box = h("div", null, { position: "absolute", left: num(v.x, 0.5) * SW + "px", top: num(v.y, 0.5) * SH + "px",
      width: W + "px", height: H + "px", marginLeft: -W / 2 + "px", marginTop: -H / 2 + "px", boxSizing: "border-box",
      ...(cadre ? { padding: "14px", borderRadius: "28px", background: v.fond || "#0C0E12", border: `6px solid ${v.bord || "#FFFFFF"}`,
        boxShadow: "0 24px 60px rgba(0,0,0,.65)", overflow: "hidden" } : {}), transformOrigin: "50% 50%" });
    const img = h("img", null, { width: "100%", height: "100%", objectFit: "contain", display: "block",
      ...(cadre ? { borderRadius: "16px" } : { filter: "drop-shadow(0 18px 36px rgba(0,0,0,.6))" }) });
    img.src = v.image || "";
    box.appendChild(img); stage.appendChild(box);
    return (t) => {
      const p = progress(t, 0, f(14), EASE.pop), q = progress(t, D - f(10), f(10), EASE.in);
      box.style.transform = `translateY(${(1 - p) * 140 + q * 40}px) rotate(${rot * (1 - p) * 2 + rot * 0.5}deg) scale(${(0.6 + 0.4 * p) * (1 - 0.35 * q)})`;
      box.style.opacity = progress(t, 0, f(4)) * (1 - q);
    };
  };

  /** Tableau de score qui revient entre les parties. vars : avantA, avantB, point (a | b | ""), a (seconde du point),
   *  nomA, couleurA, logoA, nomB, couleurB, logoB */
  B.score = ({ stage, v, D }) => {
    const duel = { a: { nom: v.nomA || "CLAUDE", couleur: v.couleurA || COLORS.claude, logo: v.logoA ?? "claude" },
                   b: { nom: v.nomB || "CHATGPT", couleur: v.couleurB || COLORS.astra, logo: v.logoB ?? "chatgpt" } };
    const upd = wolfLayers(stage, { duel, score: [{ t: 0, d: D, avant: [+v.avantA || 0, +v.avantB || 0], point: v.point || "", a: num(v.a, 0.8) }] });
    return (t) => upd(t, null);
  };

  /** Scène de mots : sur le fond de la chaîne, ce qui est dit se met en forme à l'écran au moment où c'est dit (mots en
   *  gros texte contouré, logos, icônes), chaque ligne qui arrive pousse les autres (la mise en page se recentre), avec
   *  un pop. Demande du 2026-10-08 pour l'accroche des Shorts (à la place de « À venir »).
   *  vars : fond (couleur du fond ondulé), items = [{t (s), texte, logo? (claude | chatgpt), icone? (bulle | chrono),
   *  couleur? (texte), taille? (px, 130 par défaut), ligne? (même numéro = même ligne), souligne? (trait rouge dessous)}] */
  B.scene_mots = ({ stage, v, D }) => {
    const bg = wave(stage, v.fond || COLORS.accent, 0.5, 1, SW, SH);
    const items = list(v.items).map((it) => ({ ...it, t: num(it.t, 0) })).sort((a, b) => a.t - b.t);
    const col = h("div", null, { position: "absolute", left: 0, right: 0, top: "50%", display: "flex", flexDirection: "column",
      alignItems: "center", transformOrigin: "50% 50%" });
    stage.appendChild(col);
    const lignes = [];
    items.forEach((it, i) => {
      const k = it.ligne ?? `seule${i}`;
      let L = lignes.find((l) => l.k === k);
      if (!L) {
        const inner = h("div", null, { display: "flex", alignItems: "center", justifyContent: "center", gap: "28px", padding: "14px 0" });
        const wrap = h("div", null, { overflow: "visible", height: "0px", display: "flex", alignItems: "center", justifyContent: "center" }, inner);
        col.appendChild(wrap);
        L = { k, t: it.t, wrap, inner, h: 0 };
        lignes.push(L);
      }
      const size = num(it.taille, 130), maxW = SW - 140;
      const el = h("div", null, { display: "flex", alignItems: "center", gap: "24px", transformOrigin: "50% 60%", position: "relative" });
      if (it.logo) el.appendChild(wolfLogo(it.logo, Math.round(size * 1.15), it.couleur || "#FFFFFF"));
      let arc = null;
      if (it.icone === "chrono") {
        const S = Math.round(size * 1.05), ic = h("div", null, { width: S + "px", height: S + "px", flex: "none" });
        ic.innerHTML = `<svg viewBox="0 0 100 100" width="${S}" height="${S}"><circle cx="50" cy="54" r="40" fill="#0A0A0C" stroke="#FFFFFF" stroke-width="7"/>
          <rect x="42" y="2" width="16" height="10" rx="3" fill="#FFFFFF"/><circle class="arc" cx="50" cy="54" r="27" fill="none" stroke="${it.couleur || COLORS.or}"
          stroke-width="16" transform="rotate(-90 50 54)" stroke-dasharray="169.6" stroke-dashoffset="169.6"/></svg>`;
        arc = ic.querySelector(".arc");
        el.appendChild(ic);
      } else if (it.icone === "bulle") {
        const S = Math.round(size * 1.05), ic = h("div", null, { width: S + "px", height: S + "px", flex: "none" });
        ic.innerHTML = `<svg viewBox="0 0 100 100" width="${S}" height="${S}"><path d="M10 14 H90 V70 H44 L22 90 V70 H10 Z" fill="#FFFFFF" stroke="#0A0A0C"
          stroke-width="6" stroke-linejoin="round"/><circle cx="32" cy="42" r="6" fill="#0A0A0C"/><circle cx="50" cy="42" r="6" fill="#0A0A0C"/>
          <circle cx="68" cy="42" r="6" fill="#0A0A0C"/></svg>`;
        el.appendChild(ic);
      }
      if (it.texte) el.appendChild(wolfText(it.texte, size, it.couleur || "#FFFFFF", maxW - (it.logo || it.icone ? size * 1.3 : 0)));
      let trait = null;
      if (it.souligne) {
        trait = h("div", null, { position: "absolute", left: "0", right: "0", bottom: "-14px", height: "14px", borderRadius: "7px",
          background: COLORS.accent, transformOrigin: "0 50%", boxShadow: "0 6px 16px rgba(0,0,0,.4)" });
        el.appendChild(trait);
      }
      L.inner.appendChild(el);
      it.el = el; it.arc = arc; it.trait = trait;
    });
    return (t) => {
      bg(t);
      // hauteur de chaque ligne qui s'ouvre quand elle arrive : les lignes déjà là glissent pour laisser la place
      let total = 0;
      lignes.forEach((L) => {
        if (!L.h) L.h = L.inner.offsetHeight || 170;
        const o = progress(t, L.t - f(2), f(14), EASE.out);
        L.wrap.style.height = L.h * o + "px";
        total += L.h * o;
      });
      col.style.transform = `translateY(${-total / 2}px) scale(${1 + 0.05 * Math.min(1, t / Math.max(1, D))})`;
      items.forEach((it) => {
        const p = progress(t, it.t, f(16), EASE.pop);
        it.el.style.opacity = t >= it.t ? Math.min(1, p * 2.5) : 0;
        it.el.style.transform = `translateY(${(1 - p) * 50}px) scale(${0.45 + 0.55 * p}) rotate(${(1 - p) * -6}deg)`;
        if (it.arc) it.arc.setAttribute("stroke-dashoffset", String(169.6 * (1 - progress(t, it.t + f(6), 0.7, EASE.inOut))));
        if (it.trait) it.trait.style.transform = `scaleX(${progress(t, it.t + f(8), f(14), EASE.inOut)})`;
      });
    };
  };

  // ───────────── short vertical (1080×1920)
  const SHADER = {
    vanilla: { name: "Minecraft normal", color: COLORS.vanilla, ico: "" },
    claude: { name: "Claude Opus 5.5", color: COLORS.claude, ico: "burst" },
    astra: { name: "ChatGPT 6 Astra", color: COLORS.astra, ico: "knot" },
  };
  const shaderLabel = (s, size) => label({ text: SHADER[s].name, color: SHADER[s].color, size, ico: SHADER[s].ico ? icon(SHADER[s].ico, size * 0.8, "#FFFFFF") : "" });

  /** Mots groupés par 3 au plus (coupure aussi après une ponctuation). */
  const chunks = (words) => {
    const out = []; let cur = [];
    words.forEach((w) => { cur.push(w); if (cur.length >= 3 || /[.,!?]$/.test(w.text)) { out.push(cur); cur = []; } });
    if (cur.length) out.push(cur);
    return out;
  };

  /** Short : plans recadrés + titre en fenêtre + étiquette du shader + gros sous-titres mot à mot + flash aux coupes.
   *  data = {duration, titre, segments:[{start, dur, label (nom|[noms]), cuts, winner, triptych, words:[{text,t}]}]}
   *  La vidéo de fond est dans #short-video-wrap (zoom lent appliqué ici). */
  B.short = ({ root, stage, v }) => {
    const data = v.data, segs = data.segments;
    const wrap = root.querySelector("#short-video-wrap");
    const title = win({ title: "TSAR", color: COLORS.accent, bodyStyle: { padding: "22px 34px 28px" } });
    title.body.appendChild(h("div", null, { fontWeight: 900, fontSize: "60px", lineHeight: 1.08, letterSpacing: "-1.5px", textAlign: "center" }, escapeHtml(data.titre)));
    const titleBox = h("div", null, { position: "absolute", top: "190px", left: "70px", right: "70px" }, title.el);
    const labelBox = h("div", null, { position: "absolute", top: "520px", width: "100%", display: "flex", justifyContent: "center" });
    const labels = {};
    ["vanilla", "claude", "astra"].forEach((s) => { labels[s] = shaderLabel(s, 44); labels[s].style.position = "absolute"; labelBox.appendChild(labels[s]); });
    labels.winner = label({ text: data.vainqueur || "Vainqueur : Opus 5.5", color: COLORS.or, size: 46, ico: icon("trophy", 30) });
    labels.winner.style.position = "absolute"; labelBox.appendChild(labels.winner);
    const tri = h("div", "fill");
    ["vanilla", "claude", "astra"].forEach((s, i) => tri.appendChild(h("div", null, { position: "absolute", top: i * 640 + 34 + "px", left: "34px" }, shaderLabel(s, 38))));
    const triLabels = [...tri.children].map((d) => d.firstChild);
    const capBox = h("div", null, { position: "absolute", left: 0, right: 0, height: 0, display: "flex", justifyContent: "center" });
    const cap = h("div", "cap", { maxWidth: "940px", columnGap: "24px", fontSize: "104px", lineHeight: 1.05, letterSpacing: "-2px", transform: "translateY(-50%)" });
    capBox.appendChild(cap);
    const flash = h("div", "fill", { background: "#FFFFFF", opacity: 0 });
    stage.append(titleBox, labelBox, tri, capBox, flash);
    const groups = chunks(segs.flatMap((s) => s.words));
    const spans = groups.map((g) => g.map((w) => { const s = h("span", null, { WebkitTextStroke: "16px #0A0A0C", textShadow: "0 10px 28px rgba(0,0,0,.55)" }, escapeHtml(w.text.replace(/[.,]$/, ""))); return [w.t, s]; }));
    let shownGroup = -1;
    return (t) => {
      const seg = [...segs].reverse().find((s) => t >= s.start) || segs[0];
      const local = t - seg.start;
      if (wrap) wrap.style.transform = `scale(${seg.triptych ? 1 : 1 + 0.05 * Math.min(1, local / seg.dur)})`;
      titleBox.style.visibility = labelBox.style.visibility = seg.triptych ? "hidden" : "visible";
      tri.style.visibility = seg.triptych ? "visible" : "hidden";
      if (seg.triptych) triLabels.forEach((l, i) => openStyle(l, t, seg.start + i * 0.1));
      openStyle(title.el, t, f(4));
      // étiquette du shader montré (change à chaque coupe dans le 1er passage)
      const multi = Array.isArray(seg.label);
      const ci = multi ? Math.max(0, seg.cuts.filter((c) => local >= c - 0.001).length - 1) : 0;
      const cur = seg.winner ? "winner" : multi ? seg.label[ci] : seg.label;
      const since = seg.start + (multi ? seg.cuts[ci] : 0);
      Object.entries(labels).forEach(([k, l]) => { l.style.visibility = k === cur ? "visible" : "hidden"; if (k === cur) openStyle(l, t, since); });
      // sous-titres
      const gi = groups.findIndex((g, i) => t >= g[0].t && (i === groups.length - 1 || t < groups[i + 1][0].t));
      if (gi !== shownGroup) { cap.replaceChildren(...(gi >= 0 ? spans[gi].map(([, s]) => s) : [])); shownGroup = gi; }
      capBox.style.top = (seg.triptych ? 1110 : 1230) + "px";
      if (gi >= 0) spans[gi].forEach(([at, s]) => {
        const p = progress(t, at, f(12), EASE.pop);
        s.style.opacity = progress(t, at, f(3)); s.style.transform = `scale(${0.7 + 0.3 * p})`;
      });
      // flash d'appareil photo sur chaque coupe entre passages (le déclic est dans l'audio)
      const last = [...segs.slice(1)].reverse().find((s) => t >= s.start);
      flash.style.opacity = last ? 0.55 * (1 - progress(t, last.start, f(9))) : 0;
    };
  };

  /** Scène verticale « les 2 IA » : fond de la chaîne, logo de chaque IA en haut à gauche / à droite (pop quand il
   *  dit « 2 IA »), fenêtre Minecraft en bas qui passe de vanilla au rendu transformé (au mot « transformer »),
   *  avec deux traits qui relient les IA à la fenêtre. s = {t, fin, logos (s), transforme (s), avant, apres, dossier} */
  function duelScene(stage, s) {
    const layer = h("div", "fill");
    const bg = wave(layer, COLORS.accent, 0.45, 1, 1080, 1920);
    const NS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(NS, "svg");
    svg.setAttribute("width", 1080); svg.setAttribute("height", 1920); svg.style.position = "absolute";
    const lines = [[270, 500, 420, 640], [810, 500, 660, 640]].map(([x1, y1, x2, y2]) => {
      const l = document.createElementNS(NS, "line");
      Object.entries({ x1, y1, x2, y2, stroke: "#FFFFFF", "stroke-width": 6, "stroke-linecap": "round", "stroke-dasharray": "14 16" })
        .forEach(([k, v]) => l.setAttribute(k, v));
      svg.appendChild(l); return l;
    });
    layer.appendChild(svg);
    const logo = (ia, x) => { // vrais logos (assets/logos/*.svg) dans une pastille blanche
      const box = h("div", null, { position: "absolute", top: "170px", left: x - 150 + "px", width: "300px", display: "flex",
        flexDirection: "column", alignItems: "center", gap: "22px" });
      const disc = h("div", null, { width: "230px", height: "230px", borderRadius: "50%", display: "flex", alignItems: "center",
        justifyContent: "center", background: ia === "claude" ? "#F4F1EA" : "#FFFFFF",
        border: `6px solid ${ia === "claude" ? COLORS.claude : COLORS.astra}`, boxShadow: "0 20px 50px rgba(0,0,0,.55)" });
      const img = h("img", null, { width: "150px", height: "150px", objectFit: "contain" });
      img.src = `assets/logos/${ia === "claude" ? "claude" : "chatgpt"}.svg`;
      disc.appendChild(img); box.appendChild(disc);
      box.appendChild(h("div", null, { fontFamily: '"Montserrat", sans-serif', fontWeight: 900, fontSize: "44px", color: "#FFFFFF",
        textShadow: "0 3px 10px rgba(0,0,0,.7)", whiteSpace: "nowrap" }, ia === "claude" ? "Claude" : "ChatGPT"));
      layer.appendChild(box); return box;
    };
    const L = logo("claude", 270), R = logo("astra", 810);
    const w = win({ title: "Minecraft", color: "#8BC34A", width: 920, bodyStyle: { flex: "none", height: "518px", overflow: "hidden" } });
    const imgA = h("img", "fill", { width: "100%", height: "100%", objectFit: "cover" });
    const imgB = h("img", "fill", { width: "100%", height: "100%", objectFit: "cover", opacity: 0 });
    imgA.src = `${s.dossier}/${s.avant}.png`; imgB.src = `${s.dossier}/${s.apres}.png`;
    const sweep = h("div", null, { position: "absolute", top: 0, bottom: 0, width: "220px",
      background: "linear-gradient(90deg, transparent, rgba(255,255,255,.75), transparent)" });
    w.body.append(imgA, imgB, sweep);
    const wb = h("div", null, { position: "absolute", top: "640px", left: "80px" }, w.el); // bas à 1216 px : les sous-titres (1236) restent dégagés
    layer.appendChild(wb);
    stage.appendChild(layer);
    return (t) => {
      const on = t >= s.t && t < s.fin;
      layer.style.visibility = on ? "visible" : "hidden";
      if (!on) return;
      bg(t - s.t);
      layer.style.opacity = progress(t, s.t, f(8)) * (1 - progress(t, s.fin - f(6), f(6), EASE.in));
      openStyle(w.el, t, s.t + 0.05);
      [[L, 0], [R, 0.12]].forEach(([b, dt]) => {
        const p = progress(t, s.logos + dt, f(20), EASE.pop);
        b.style.opacity = Math.min(1, p * 2); b.style.transform = `scale(${0.4 + 0.6 * p})`;
      });
      const k = progress(t, s.transforme, 0.5, EASE.inOut);
      lines.forEach((l) => { l.style.opacity = progress(t, s.transforme - 0.25, f(10)); l.setAttribute("stroke-dashoffset", -t * 60); });
      imgB.style.opacity = k;
      sweep.style.left = -220 + 1140 * k + "px";
      sweep.style.opacity = k > 0 && k < 1 ? 1 : 0;
    };
  }

  /** Éléments du style WOLF (référence config/youtube/references/wolf/style.md, test du Short glacon-ia) :
   *  pastille persistante « ce qu'on teste » qui passe au vert (réussi) ou au rouge (raté), carte titre plein écran
   *  (gros texte blanc contouré sur fond uni), tableau de score qui revient entre les parties, noms sur l'écran partagé.
   *  data : etiquettes [{de, a, texte, couleur, etat:[{t, etat}]}], cartes [{t, d, texte, fond, logo}],
   *         score [{t, d, avant:[a, b], point, a}], duel {a:{nom, couleur, logo}, b:{…}} ; plan.partage. */
  function wolfLayers(stage, data) {
    const duel = data.duel || { a: { nom: "CLAUDE", couleur: COLORS.claude, logo: "claude" }, b: { nom: "CHATGPT", couleur: COLORS.astra, logo: "chatgpt" } };
    const MONT = '"Montserrat", sans-serif';
    const logoDisc = (logo, size, ring) => {
      const disc = h("div", null, { width: size + "px", height: size + "px", borderRadius: "50%", display: "flex", alignItems: "center",
        justifyContent: "center", background: logo === "claude" ? "#F4F1EA" : "#FFFFFF", border: `${Math.round(size / 36)}px solid ${ring}`,
        boxShadow: "0 20px 50px rgba(0,0,0,.45)" });
      const img = h("img", null, { width: size * 0.65 + "px", height: size * 0.65 + "px", objectFit: "contain" });
      img.src = `assets/logos/${logo}.svg`; disc.appendChild(img);
      return disc;
    };
    const bigText = (txt, size) => h("div", null, { fontFamily: MONT, fontWeight: 900, fontSize: size + "px", lineHeight: 1.02, color: "#FFFFFF",
      textAlign: "center", letterSpacing: "-2px", maxWidth: "980px", WebkitTextStroke: `${Math.round(size / 11)}px #0A0A0C`, paintOrder: "stroke fill",
      textShadow: "0 12px 30px rgba(0,0,0,.45)" }, escapeHtml(txt));
    // écran partagé : trait blanc au milieu, nom de chaque côté
    const split = h("div", "fill");
    split.appendChild(h("div", null, { position: "absolute", left: 0, right: 0, top: "956px", height: "8px", background: "#FFFFFF", boxShadow: "0 0 18px rgba(0,0,0,.6)" }));
    [["a", "830px"], ["b", "1000px"]].forEach(([k, top]) => {
      const row = h("div", null, { position: "absolute", top, left: 0, right: 0, display: "flex", justifyContent: "center" });
      row.appendChild(h("span", null, { fontFamily: MONT, fontWeight: 900, fontSize: "64px", color: "#FFFFFF", padding: "8px 30px", borderRadius: "16px",
        background: duel[k].couleur, textShadow: "0 3px 8px rgba(0,0,0,.5)", boxShadow: "0 12px 30px rgba(0,0,0,.45)" }, escapeHtml(duel[k].nom)));
      split.appendChild(row);
    });
    // pastilles persistantes (en haut à gauche : le bas de l'écran est caché par l'interface des Shorts)
    const etiqs = (data.etiquettes || []).map((e) => {
      const l = label({ text: e.texte, color: e.couleur, size: 50, ico: "" });
      const box = h("div", null, { position: "absolute", top: "120px", left: "50px", transformOrigin: "0 50%" }, l);
      return [e, box, l];
    });
    // cartes titre
    const cartes = (data.cartes || []).map((c) => {
      const el = h("div", "fill", { background: `radial-gradient(75% 55% at 50% 45%, rgba(255,255,255,.16), rgba(0,0,0,.30)), ${c.fond}` });
      const inner = h("div", "fill", { display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "56px" });
      if (c.logo) inner.appendChild(logoDisc(c.logo, 300, "#FFFFFF"));
      inner.appendChild(bigText(c.texte, c.texte.length > 12 ? 130 : 170));
      el.appendChild(inner);
      return [c, el, inner];
    });
    // tableau de score
    const scores = (data.score || []).map((s) => {
      const el = h("div", "fill", { background: "rgba(5,5,6,.88)", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "70px" });
      el.appendChild(h("div", null, { fontFamily: MONT, fontWeight: 900, fontSize: "60px", letterSpacing: "10px", color: "#F4F4F5" }, "SCORE"));
      const row = h("div", null, { display: "flex", gap: "90px", alignItems: "flex-start" });
      const cols = {}, nums = {};
      ["a", "b"].forEach((k) => {
        const col = h("div", null, { display: "flex", flexDirection: "column", alignItems: "center", gap: "34px" });
        if (duel[k].logo) col.appendChild(logoDisc(duel[k].logo, 210, duel[k].couleur));
        col.appendChild(h("span", null, { fontFamily: MONT, fontWeight: 900, fontSize: "54px", color: "#FFFFFF", padding: "6px 26px", borderRadius: "14px",
          background: duel[k].couleur }, escapeHtml(duel[k].nom)));
        nums[k] = bigText(String(s.avant[k === "a" ? 0 : 1]), 230);
        col.appendChild(nums[k]); row.appendChild(col); cols[k] = col;
      });
      el.appendChild(row);
      return [s, el, cols, nums];
    });
    stage.append(split, ...etiqs.map((e) => e[1]), ...scores.map((s) => s[1]), ...cartes.map((c) => c[1]));
    return (t, sh) => {
      split.style.visibility = sh && sh.partage ? "visible" : "hidden";
      etiqs.forEach(([e, box, l]) => {
        const on = t >= e.de && t < e.a;
        box.style.visibility = on ? "visible" : "hidden";
        if (!on) return;
        openStyle(l, t, e.de);
        const st = [...e.etat].reverse().find((x) => t >= x.t);
        const ico = l.firstChild;
        if (st) {
          const ok = st.etat === "ok";
          ico.style.background = ok ? "#34C759" : "#E5383B";
          ico.innerHTML = icon(ok ? "check" : "ban", 40, "#FFFFFF");
          l.style.background = ok ? "rgba(22,92,44,.96)" : "rgba(120,20,24,.96)";
          box.style.transform = `scale(${1 + 0.22 * (1 - progress(t, st.t, f(14), EASE.out))})`;
        } else {
          ico.style.background = e.couleur; ico.innerHTML = ""; l.style.background = ""; box.style.transform = "none";
        }
      });
      scores.forEach(([s, el, cols, nums]) => {
        const on = t >= s.t && t < s.t + s.d;
        el.style.visibility = on ? "visible" : "hidden";
        if (!on) return;
        el.style.opacity = progress(t, s.t, f(5)) * (1 - progress(t, s.t + s.d - f(5), f(5), EASE.in));
        openStyle(cols.a, t, s.t); openStyle(cols.b, t, s.t + f(4));
        ["a", "b"].forEach((k, i) => {
          const won = s.point === k && t >= s.t + s.a;
          nums[k].textContent = String(s.avant[i] + (won ? 1 : 0));
          nums[k].style.color = won ? "#F5B942" : "#FFFFFF";
          nums[k].style.transform = `scale(${won ? 1 + 0.35 * (1 - progress(t, s.t + s.a, f(16), EASE.out)) : 1})`;
        });
      });
      cartes.forEach(([c, el, inner]) => {
        const on = t >= c.t && t < c.t + c.d;
        el.style.visibility = on ? "visible" : "hidden";
        if (!on) return;
        const pin = progress(t, c.t, f(10), EASE.pop);
        inner.style.transform = `scale(${(1.18 - 0.18 * pin) * (1 + 0.05 * Math.min(1, (t - c.t) / c.d))})`;
      });
    };
  }

  /** Short style LAirHisson (validé comme référence le 30/09/2026) : pas de titre, sous-titres 2–3 mots en
   *  minuscules (blanc, gras arrondi, ombre fine) vers 64 % de la hauteur, zooms punch / progressifs, secousses,
   *  éclairs sur les plans rapides, captures qui surgissent en haut, interrupteur rouge → vert (avant / après).
   *  data = {duration, plans:[{t,d,zoom,secousse,flash}], surgit:[{t,d,src}], interrupteur:[{t,etat,fin}], mots:[{text,t,p}]} */
  B.short_lh = ({ root, stage, v }) => {
    const data = v.data;
    const wrap = root.querySelector("#short-video-wrap");
    // sous-titres : groupes de 2–3 mots, coupés aussi à la ponctuation et entre deux passages
    const groups = [];
    let cur = [];
    data.mots.forEach((w, i) => {
      const next = data.mots[i + 1];
      cur.push(w);
      if (cur.length >= 3 || /[.,!?]$/.test(w.text) || (next && next.p !== w.p) || (cur.length === 2 && next && next.text.length > 9)) {
        groups.push(cur); cur = [];
      }
    });
    if (cur.length) groups.push(cur);
    const clean = (s) => s.toLowerCase().replace(/[,!?;:«»"]/g, "").replace(/\.+$/, ""); // garde « 5.5 »
    const cap = h("div", null, { position: "absolute", left: "60px", right: "60px", top: "1236px", display: "flex", justifyContent: "center",
      fontFamily: '"Montserrat", sans-serif', fontWeight: 800, fontSize: "72px", lineHeight: 1.1, color: "#FFFFFF", textAlign: "center",
      letterSpacing: "-0.5px", textShadow: "0 4px 10px rgba(0,0,0,.75), 0 0 3px rgba(0,0,0,.9), 0 2px 0 rgba(0,0,0,.5)", whiteSpace: "nowrap" });
    const capText = h("span", null, { display: "inline-block" });
    cap.appendChild(capText);
    // interrupteur
    const sw = h("div", null, { position: "absolute", top: "250px", left: "50%", marginLeft: "-85px", width: "170px", height: "92px",
      borderRadius: "46px", boxShadow: "0 10px 30px rgba(0,0,0,.45), inset 0 0 0 5px rgba(255,255,255,.9)" });
    const knob = h("div", null, { position: "absolute", top: "11px", left: "11px", width: "70px", height: "70px", borderRadius: "50%",
      background: "#FFFFFF", boxShadow: "0 4px 10px rgba(0,0,0,.35)" });
    sw.appendChild(knob);
    // nom de ce qu'on voit (Vanilla / Claude / Astra) sous l'interrupteur
    const NOMS = { vanilla: "#8BC34A", claude: "#E07A5A", astra: "#3CCFB0" };
    const swName = h("div", null, { position: "absolute", top: "360px", left: 0, right: 0, display: "flex", justifyContent: "center" });
    const swText = h("span", null, { fontFamily: '"Montserrat", sans-serif', fontWeight: 900, fontSize: "54px", letterSpacing: "1px",
      textTransform: "uppercase", color: "#FFFFFF", padding: "6px 26px", borderRadius: "14px",
      textShadow: "0 3px 8px rgba(0,0,0,.6)", boxShadow: "0 10px 26px rgba(0,0,0,.4)" });
    swName.appendChild(swText);
    // captures qui surgissent
    const etiqs = data.etiquettes || [];
    const pops = data.surgit.map((s) => {
      // sous la pastille persistante quand il y en a une (style WOLF)
      const box = h("div", null, { position: "absolute", top: (etiqs.length ? 250 : 170) + "px", left: "70px", right: "70px", display: "flex", justifyContent: "center" });
      // capture à sa taille (agrandie au plus à 820 px de large), bord fin qui épouse l'image
      const img = h("img", null, { display: "block", width: "820px", maxHeight: "620px", objectFit: "contain", borderRadius: "16px",
        boxShadow: "0 20px 50px rgba(0,0,0,.6), 0 0 0 2px rgba(255,255,255,.35)", transformOrigin: "50% 0%" });
      img.src = s.src;
      let el = img, mark = null;
      if (s.surligne) { // zone surlignée en jaune (chiffre, mot de la consigne), qui se trace de gauche à droite
        Object.assign(img.style, { width: s.w + "px", height: s.h + "px", maxHeight: "none" });
        el = h("div", null, { position: "relative", transformOrigin: "50% 0%" }, img);
        const z = s.surligne;
        mark = h("div", null, { position: "absolute", left: z.x - 8 + "px", top: z.y - 6 + "px", width: z.w + 16 + "px", height: z.h + 12 + "px",
          borderRadius: "10px", background: "rgba(245,185,66,.35)", boxShadow: "0 0 0 5px #F5B942", transformOrigin: "0 50%" });
        el.appendChild(mark);
      }
      box.appendChild(el); stage.appendChild(box);
      return [s, box, el, mark];
    });
    const flash = h("div", "fill", { background: "#FFFFFF", opacity: 0 });
    // scènes de motion design plein écran (sur le fond de la chaîne), sous les sous-titres
    const scenes = (data.scenes || []).map((s) => duelScene(stage, s));
    const wolf = wolfLayers(stage, data);
    stage.append(sw, swName, cap, flash);
    let shown = -1;
    return (t) => {
      // cadre : zoom punch (immédiat) ou progressif ; pas de secousse artificielle (refusée)
      const i = data.plans.findIndex((p, k) => t >= p.t && (k === data.plans.length - 1 || t < data.plans[k + 1].t));
      const sh = data.plans[Math.max(0, i)], next = data.plans[i + 1];
      const u = Math.min(1, (t - sh.t) / sh.d);
      let z = 1;
      // zooms naturels seulement : poussée douce sur tout le plan ([de, à]) ou montée douce en 0,6 s (nombre) ;
      // « cadre » = recadrage fixe (sujet loin), sans mouvement
      if (Array.isArray(sh.zoom)) z = sh.zoom[0] + (sh.zoom[1] - sh.zoom[0]) * EASE.inOut(u);
      else if (sh.zoom) z = 1 + (sh.zoom - 1) * progress(t, sh.t, 0.6, EASE.inOut);
      if (sh.cadre) z *= sh.cadre;
      // transition entre deux sujets : zoom rapide + flou qui sort du plan et entre dans le suivant
      let blur = 0;
      if (next && next.trans) { const q = progress(t, next.t - 0.14, 0.14, EASE.in); z *= 1 + 0.35 * q; blur = 14 * q; }
      if (sh.trans) { const q = 1 - progress(t, sh.t, 0.2, EASE.out); z *= 1 + 0.35 * q; blur = Math.max(blur, 14 * q); }
      if (wrap) { wrap.style.transform = `scale(${z})`; wrap.style.filter = blur > 0.1 ? `blur(${blur}px)` : "none"; }
      flash.style.opacity = sh.flash || sh.trans ? (sh.trans ? 0.45 : 0.7) * (1 - progress(t, sh.t, f(8))) : 0;
      scenes.forEach((up) => up(t));
      // captures
      pops.forEach(([s, box, img, mark]) => {
        const on = t >= s.t && t < s.t + s.d;
        box.style.visibility = on ? "visible" : "hidden";
        if (on) {
          const pin = progress(t, s.t, f(16), EASE.pop), pout = progress(t, s.t + s.d - f(8), f(8), EASE.in);
          img.style.opacity = Math.min(1, pin * 2) * (1 - pout);
          img.style.transform = `translateY(${(1 - pin) * -40}px) scale(${(0.75 + 0.25 * pin) * (1 - 0.1 * pout)})`;
          if (mark) { const q = progress(t, s.surligne.t, 0.3, EASE.inOut); mark.style.transform = `scaleX(${q})`; mark.style.opacity = q > 0 ? 1 : 0; }
        }
      });
      wolf(t, sh);
      // interrupteur
      const st = [...data.interrupteur].reverse().find((s) => t >= s.t && t < s.fin);
      sw.style.visibility = st ? "visible" : "hidden";
      if (st) {
        const first = data.interrupteur.find((s) => s.fin === st.fin);
        const p = progress(t, st.t, f(10), EASE.out);
        const on = st.etat === "on";
        const prevOn = (() => { const i = data.interrupteur.indexOf(st); const pr = data.interrupteur[i - 1]; return pr && pr.fin === st.fin ? pr.etat === "on" : !on; })();
        const pos = prevOn === on ? (on ? 1 : 0) : on ? p : 1 - p;
        knob.style.left = 11 + 78 * pos + "px";
        sw.style.background = pos > 0.5 ? "#34C759" : "#E5383B";
        const pin = progress(t, first.t, f(14), EASE.pop), pout = progress(t, st.fin - f(6), f(6), EASE.in);
        sw.style.opacity = Math.min(1, pin * 2) * (1 - pout);
        sw.style.transform = `scale(${0.7 + 0.3 * pin})`;
        const nom = st.nom || "";
        swText.textContent = nom;
        swText.style.background = NOMS[nom.toLowerCase()] || "#E5383B";
        const pn = progress(t, st.t, f(12), EASE.pop);
        swName.style.opacity = nom ? Math.min(1, pn * 2) * (1 - pout) : 0;
        swText.style.transform = `scale(${0.8 + 0.2 * pn})`;
      }
      swName.style.visibility = st && st.nom ? "visible" : "hidden";
      // sous-titres
      const gi = groups.findIndex((g, i) => t >= g[0].t && (i === groups.length - 1 || t < groups[i + 1][0].t));
      const g = groups[gi];
      const end = g ? g[g.length - 1].t + 1.2 : 0;
      if (gi !== shown) {
        const txt = g ? g.map((w) => clean(w.text)).filter(Boolean).join(" ") : "";
        capText.textContent = txt;
        cap.style.fontSize = Math.min(72, Math.floor(72 * 22 / Math.max(22, txt.length))) + "px"; // une ligne, jamais coupée
        shown = gi;
      }
      cap.style.visibility = data.sous_titres !== false && g && t < end ? "visible" : "hidden"; // style WOLF : sans sous-titres
      if (g) { const p = progress(t, g[0].t, f(6), EASE.pop); capText.style.transform = `scale(${0.85 + 0.15 * p})`; }
    };
  };

  // ───────────── démarrage
  function run(compId, type, extra) {
    const root = document.querySelector(`[data-composition-id="${compId}"]`);
    const D = parseFloat(root.getAttribute("data-duration"));
    SW = parseFloat(root.getAttribute("data-width")) || 1920; SH = parseFloat(root.getAttribute("data-height")) || 1080;
    const v = Object.assign({}, (window.__hyperframes && window.__hyperframes.getVariables && window.__hyperframes.getVariables()) || {}, extra || {});
    const stage = h("div", "stage");
    root.appendChild(stage);
    const update = B[type]({ root, stage, v, D });
    const clock = { t: 0 };
    const tl = gsap.timeline({ paused: true });
    tl.to(clock, { t: D, duration: D, ease: "none", onUpdate: () => update(clock.t) }, 0);
    update(0);
    window.__timelines[compId] = tl;
  }

  window.TSAR = { run, B, h, win, label, icon, wave, mascot, reveal, openStyle, exitStyle, progress, EASE, COLORS, f, escapeHtml };
})();
