type AudioWindow = Window & typeof globalThis & { webkitAudioContext?: typeof AudioContext };
type MusicKey = 'base' | 'bonus';
type SfxKey =
  | 'uiClick'
  | 'spinStart'
  | 'cascade1'
  | 'cascade2'
  | 'cascade3'
  | 'wildLock'
  | 'multiplierRise'
  | 'featureIntro'
  | 'winSmall'
  | 'winBig'
  | 'winMega'
  | 'winLegendary';

interface AudioAsset {
  src: string;
  volume: number;
  loop?: boolean;
}

interface AudioManifest {
  music: Record<MusicKey, AudioAsset>;
  sfx: Record<SfxKey, AudioAsset>;
}

class WarpathAudio {
  private ctx: AudioContext | undefined;
  private master: GainNode | undefined;
  private musicBus: GainNode | undefined;
  private sfxBus: GainNode | undefined;
  private manifest: AudioManifest | undefined;
  private loadPromise: Promise<void> | undefined;
  private buffers = new Map<string, AudioBuffer>();
  private activeMusic: { key: MusicKey; source: AudioBufferSourceNode; gain: GainNode } | undefined;
  private muted = false;

  async unlock() {
    if (typeof window === 'undefined') return;
    if (!this.ctx) this.init();
    if (this.ctx?.state === 'suspended') await this.ctx.resume();
    await this.loadAssets();
    this.playMusic('base');
  }

  setMuted(muted: boolean) {
    this.muted = muted;
    if (!this.ctx || !this.master) return;
    this.master.gain.cancelScheduledValues(this.ctx.currentTime);
    this.master.gain.setTargetAtTime(muted ? 0 : 0.72, this.ctx.currentTime, 0.025);
  }

  playButton() {
    this.playSfx('uiClick');
  }

  playSpin(mode = 'base') {
    this.playMusic(mode === 'base' ? 'base' : 'bonus');
    this.playSfx('spinStart');
  }

  playCascade(step: number) {
    const key = `cascade${Math.max(1, Math.min(3, step))}` as SfxKey;
    this.playSfx(key);
  }

  playWild() {
    this.playSfx('wildLock');
  }

  playMultiplier() {
    this.playSfx('multiplierRise');
  }

  playFeatureIntro() {
    this.playMusic('bonus');
    this.playSfx('featureIntro');
  }

  playWin(amount: number, level: number) {
    if (amount <= 0) return;
    if (level >= 5 || amount >= 100) {
      this.playSfx('winLegendary');
      return;
    }
    if (level >= 4 || amount >= 50) {
      this.playSfx('winMega');
      return;
    }
    if (level >= 2 || amount >= 5) {
      this.playSfx('winBig');
      return;
    }
    this.playSfx('winSmall');
  }

  playFinalWin(amount: number) {
    if (amount >= 100) this.playSfx('winLegendary');
    else if (amount >= 50) this.playSfx('winMega');
    window.setTimeout(() => this.playMusic('base'), amount >= 20 ? 2200 : 800);
  }

  private init() {
    const AudioContextCtor = window.AudioContext ?? (window as AudioWindow).webkitAudioContext;
    if (!AudioContextCtor) return;

    this.ctx = new AudioContextCtor();
    this.master = this.ctx.createGain();
    this.musicBus = this.ctx.createGain();
    this.sfxBus = this.ctx.createGain();
    const compressor = this.ctx.createDynamicsCompressor();

    this.master.gain.value = this.muted ? 0 : 0.72;
    this.musicBus.gain.value = 1;
    this.sfxBus.gain.value = 1;
    compressor.threshold.value = -18;
    compressor.knee.value = 24;
    compressor.ratio.value = 4;
    compressor.attack.value = 0.008;
    compressor.release.value = 0.18;

    this.musicBus.connect(this.master);
    this.sfxBus.connect(this.master);
    this.master.connect(compressor);
    compressor.connect(this.ctx.destination);
  }

  private async loadAssets() {
    if (!this.ctx) return;
    if (this.loadPromise) return this.loadPromise;

    this.loadPromise = (async () => {
      const response = await fetch('/assets/audio/manifest.json');
      if (!response.ok) throw new Error('Unable to load audio manifest');
      this.manifest = (await response.json()) as AudioManifest;
      const assets = [
        ...Object.entries(this.manifest.music).map(([key, asset]) => [`music:${key}`, asset] as const),
        ...Object.entries(this.manifest.sfx).map(([key, asset]) => [`sfx:${key}`, asset] as const)
      ];
      await Promise.all(
        assets.map(async ([key, asset]) => {
          const audio = await fetch(asset.src);
          if (!audio.ok) throw new Error(`Unable to load audio asset ${asset.src}`);
          const data = await audio.arrayBuffer();
          this.buffers.set(key, await this.ctx!.decodeAudioData(data));
        })
      );
    })();

    return this.loadPromise;
  }

  private playMusic(key: MusicKey) {
    if (!this.ctx || !this.musicBus) return;
    void this.loadAssets()
      .then(() => {
        if (!this.ctx || !this.musicBus || !this.manifest) return;
        if (this.activeMusic?.key === key) return;
        const buffer = this.buffers.get(`music:${key}`);
        if (!buffer) return;

        const now = this.ctx.currentTime;
        const asset = this.manifest.music[key];
        const source = this.ctx.createBufferSource();
        const gain = this.ctx.createGain();
        source.buffer = buffer;
        source.loop = asset.loop ?? true;
        gain.gain.setValueAtTime(0.0001, now);
        gain.gain.exponentialRampToValueAtTime(Math.max(0.0002, asset.volume), now + 0.8);
        source.connect(gain);
        gain.connect(this.musicBus);
        source.start(now);

        if (this.activeMusic) {
          const previous = this.activeMusic;
          previous.gain.gain.cancelScheduledValues(now);
          previous.gain.gain.setTargetAtTime(0.0001, now, 0.28);
          previous.source.stop(now + 1.0);
        }
        this.activeMusic = { key, source, gain };
      })
      .catch((error) => console.warn('[WarpathAudio] music unavailable', error));
  }

  private playSfx(key: SfxKey) {
    if (!this.ctx || !this.sfxBus) return;
    void this.loadAssets()
      .then(() => {
        if (!this.ctx || !this.sfxBus || !this.manifest) return;
        const buffer = this.buffers.get(`sfx:${key}`);
        const asset = this.manifest.sfx[key];
        if (!buffer || !asset) return;

        const source = this.ctx.createBufferSource();
        const gain = this.ctx.createGain();
        source.buffer = buffer;
        gain.gain.value = asset.volume;
        source.connect(gain);
        gain.connect(this.sfxBus);
        source.start();
      })
      .catch((error) => console.warn(`[WarpathAudio] sfx unavailable: ${key}`, error));
  }
}

export const warpathAudio = new WarpathAudio();
