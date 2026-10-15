// Transcrit chaque rush (audio 16 kHz extrait dans 02_ANALYSE/audio_16k) avec whisper.cpp.
// whisper.cpp >= 1.7 + DTW : horodatage précis de chaque mot (timestampMs), indispensable
// pour caler textes et animations sur la voix.
// Sortie : 02_ANALYSE/transcriptions/<rush>.json (mots horodatés) + .txt lisible.
// Usage : node scripts/transcribe.ts   (depuis 08_HYPERFRAMES) [nomDuFichier.wav ...]
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
type Caption = { text: string; startMs: number; endMs: number; timestampMs: number | null; confidence: number | null };

// large-v3-turbo : bien meilleur en français que medium, et son DTW cale les mots à ~0,1 s près.
const MODEL_FILE = "ggml-large-v3-turbo-q5_0.bin";
const MODEL_URL = `https://huggingface.co/ggerganov/whisper.cpp/resolve/main/${MODEL_FILE}`;
const DTW_PRESET = "large.v3.turbo";
const whisperDir = path.join(process.cwd(), ".whisper");
// Carte graphique si présente : .whisper/cuda (NVIDIA, PC fixe), sinon .whisper/vulkan (puce Arc du portable),
// sinon processeur ; TSAR_WHISPER=cpu force le processeur (même règle que scripts/commun.py)
const gpuCli = ["cuda", "vulkan"].map((d) => path.join(whisperDir, d, "whisper-cli.exe")).find((p) => fs.existsSync(p));
const whisperCli = gpuCli && process.env.TSAR_WHISPER?.toLowerCase() !== "cpu"
  ? gpuCli
  : path.join(whisperDir, "v1.9.2", "Release", "whisper-cli.exe");
const modelPath = path.join(whisperDir, MODEL_FILE);
const audioDir = path.resolve("..", "02_ANALYSE", "audio_16k");
const outDir = path.resolve("..", "02_ANALYSE", "transcriptions");

if (!fs.existsSync(whisperCli)) {
  throw new Error(
    `whisper-cli introuvable : ${whisperCli}\n` +
      "Télécharger whisper-bin-x64.zip (release v1.9.2 de ggml-org/whisper.cpp) et l'extraire dans .whisper/v1.9.2",
  );
}
if (!fs.existsSync(modelPath)) {
  console.log(`Téléchargement du modèle ${MODEL_FILE}…`);
  const response = await fetch(MODEL_URL);
  fs.writeFileSync(modelPath, Buffer.from(await response.arrayBuffer()));
}
fs.mkdirSync(outDir, { recursive: true });

const requested = process.argv.slice(2);
const files = (requested.length ? requested : fs.readdirSync(audioDir)).filter((f) =>
  f.endsWith(".wav"),
);

const fmt = (ms: number) => (ms / 1000).toFixed(2).padStart(6, " ");

for (const file of files) {
  const name = path.basename(file, ".wav");
  const jsonBase = path.join(outDir, `${name}.whisper`);
  console.log(`Transcription : ${name}`);
  execFileSync(
    whisperCli,
    [
      "-m", modelPath,
      "-f", path.join(audioDir, file),
      "-l", "fr",
      "--dtw", DTW_PRESET,
      "-nfa", // le DTW ne fonctionne pas avec la flash attention
      "-ojf", "-of", jsonBase,
      "-t", "8",
      "-np",
    ],
    { stdio: "ignore" },
  );
  const whisperCppOutput: WhisperOutput = JSON.parse(fs.readFileSync(`${jsonBase}.json`, "utf8"));
  fs.rmSync(`${jsonBase}.json`);

  const captions = toWordCaptions(whisperCppOutput);
  fs.writeFileSync(path.join(outDir, `${name}.json`), JSON.stringify(captions, null, 2));

  // Version lisible : un mot par ligne, horodaté au début réel du mot (DTW).
  const lines = captions.map((c) => `${fmt(c.startMs)} ${fmt(c.endMs)}  ${c.text.trim()}`);
  fs.writeFileSync(path.join(outDir, `${name}.txt`), lines.join("\n") + "\n");
}

// Regroupe les tokens whisper en mots (un token qui commence par une espace ouvre un mot).
// Début d'un mot = horodatage DTW de son premier token ; fin = début du mot suivant,
// plafonnée à la fin whisper du dernier token.
function toWordCaptions(output: WhisperOutput): Caption[] {
  const words: { text: string; startMs: number; endMs: number }[] = [];
  for (const segment of output.transcription) {
    for (const token of segment.tokens) {
      if (token.text.startsWith("[_") || !token.text.trim()) continue;
      const dtwMs = token.t_dtw >= 0 ? token.t_dtw * 10 : token.offsets.from;
      const last = words[words.length - 1];
      if (token.text.startsWith(" ") || !last) {
        words.push({ text: token.text, startMs: dtwMs, endMs: token.offsets.to });
      } else {
        last.text += token.text;
        last.endMs = token.offsets.to;
      }
    }
  }
  return words.map((w, i) => ({
    text: w.text,
    startMs: w.startMs,
    endMs: Math.max(w.startMs, Math.min(w.endMs, words[i + 1]?.startMs ?? w.endMs)),
    timestampMs: w.startMs,
    confidence: null,
  }));
}

type WhisperOutput = {
  transcription: {
    tokens: { text: string; t_dtw: number; offsets: { from: number; to: number } }[];
  }[];
};
