/**
 * Audio helpers: chime (synthesised, no asset needed), reply playback with an analyser for the
 * LED/waveform, browser speech as a last-resort fallback, and the microphone recorder.
 */

let ctx: AudioContext | null = null;
export function audioContext(): AudioContext {
  if (!ctx) ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
  return ctx;
}

export async function unlockAudio(): Promise<void> {
  const c = audioContext();
  if (c.state === "suspended") await c.resume();
}

export async function playChime(volume = 0.6): Promise<void> {
  const c = audioContext();
  const now = c.currentTime;
  [880, 1318.5].forEach((freq, i) => {
    const osc = c.createOscillator();
    const gain = c.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0, now + i * 0.18);
    gain.gain.linearRampToValueAtTime(0.25 * volume, now + i * 0.18 + 0.02);
    gain.gain.exponentialRampToValueAtTime(0.001, now + i * 0.18 + 0.5);
    osc.connect(gain).connect(c.destination);
    osc.start(now + i * 0.18);
    osc.stop(now + i * 0.18 + 0.55);
  });
  await new Promise((r) => setTimeout(r, 750));
}

export interface PlayHandle {
  analyser: AnalyserNode | null;
  done: Promise<"audio" | "speech" | "none">;
  stop: () => void;
}

const VOICE_LANG: Record<string, string> = { hi: "hi-IN", hinglish: "hi-IN", en: "en-IN", mr: "mr-IN" };

function speak(text: string, lang: string, rate: number): Promise<"speech" | "none"> {
  return new Promise((resolve) => {
    if (!("speechSynthesis" in window)) return resolve("none");
    const u = new SpeechSynthesisUtterance(text);
    u.lang = VOICE_LANG[lang] ?? "hi-IN";
    u.rate = rate;
    u.onend = () => resolve("speech");
    u.onerror = () => resolve("none");
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  });
}

/**
 * Play the backend's generated audio. Very small files are the backend's offline silent
 * placeholder (mock TTS), so we fall back to the browser's own voice reading the SAME transcript.
 */
export function playReply(opts: { url?: string | null; bytes?: number; text: string; lang: string; volume?: number; slow?: boolean }): PlayHandle {
  const rate = opts.slow ? 0.8 : 1;
  if (!opts.url || (opts.bytes != null && opts.bytes < 1000)) {
    const done = speak(opts.text, opts.lang, rate);
    return { analyser: null, done, stop: () => window.speechSynthesis?.cancel() };
  }
  const el = new Audio();
  el.crossOrigin = "anonymous";
  el.src = opts.url;
  el.volume = opts.volume ?? 1;
  el.playbackRate = rate;
  let analyser: AnalyserNode | null = null;
  try {
    const c = audioContext();
    const src = c.createMediaElementSource(el);
    analyser = c.createAnalyser();
    analyser.fftSize = 64;
    src.connect(analyser).connect(c.destination);
  } catch {
    analyser = null;
  }
  const done = new Promise<"audio" | "speech" | "none">((resolve) => {
    el.onended = () => resolve("audio");
    el.onerror = () => speak(opts.text, opts.lang, rate).then(resolve);
    el.play().catch(() => speak(opts.text, opts.lang, rate).then(resolve));
  });
  return { analyser, done, stop: () => el.pause() };
}

export async function playBlob(blob: Blob, text: string, lang: string, slow = false): Promise<void> {
  if (blob.size < 1000) {
    await speak(text, lang, slow ? 0.8 : 1);
    return;
  }
  const url = URL.createObjectURL(blob);
  await playReply({ url, text, lang, slow }).done;
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------- recorder
export interface Recording {
  stop: () => Promise<{ blob: Blob; seconds: number }>;
  cancel: () => void;
}

export async function startRecording(): Promise<Recording> {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mime = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
  const rec = new MediaRecorder(stream, { mimeType: mime });
  const chunks: BlobPart[] = [];
  const started = Date.now();
  rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
  rec.start();
  const finish = () => stream.getTracks().forEach((t) => t.stop());
  return {
    stop: () =>
      new Promise((resolve) => {
        rec.onstop = () => {
          finish();
          resolve({ blob: new Blob(chunks, { type: "audio/webm" }), seconds: (Date.now() - started) / 1000 });
        };
        rec.stop();
      }),
    cancel: () => {
      rec.onstop = finish;
      rec.stop();
    },
  };
}
