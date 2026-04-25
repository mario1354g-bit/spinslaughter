<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import {
    Application,
    Assets,
    ColorMatrixFilter,
    Container,
    Graphics,
    Sprite,
    Text,
    Texture
  } from 'pixi.js';
  import {
    ASSET_PATH,
    CANVAS_HEIGHT,
    CANVAS_WIDTH,
    MAX_REEL_ROWS,
    REEL_AREA_HEIGHT,
    REEL_AREA_WIDTH,
    REEL_AREA_X,
    REEL_AREA_Y,
    REEL_COUNT,
    ROWS_PER_REEL,
    SYMBOL_GAP,
    SYMBOL_SIZE
  } from '$lib/game/constants';
  import { eventEmitter } from '$lib/game/eventEmitter';
  import { REEL6_POOL, SPIN_POOL, SYMBOLS } from '$lib/game/symbols';
  import type { Board, WinLine } from '$lib/game/types';

  let canvas: HTMLCanvasElement;
  let app: Application | undefined;
  let root = new Container();
  let bgLayer = new Container();
  let reelLayer = new Container();
  let fxLayer = new Container();
  let overlayLayer = new Container();
  let currentBoard: Board = emptyBoard();
  let symbols: Container[][] = [];
  let loaded = false;
  let unsubscribe = () => {};
  let resolveReady: (() => void) | undefined;
  const readyPromise = new Promise<void>((resolve) => {
    resolveReady = resolve;
  });
  const textureCache = new Map<string, Texture>();

  const BIG_WIN_LABELS = ['BIG WIN', 'MEGA WIN', 'EPIC WIN', 'LEGENDARY WIN'];
  const BACKGROUND_ASSET = `${ASSET_PATH}/backgrounds/background_desert_futuristic_night.png`;
  const PARTICLE_ASSETS = [
    'blood_drop',
    'debris_chunk',
    'ember_particle',
    'flare_ring',
    'sand_grain',
    'smoke_puff',
    'spark'
  ].map((name) => `${ASSET_PATH}/particles/${name}.png`);
  let bigWinShownThisSpin = false;
  let bestWinAmountThisSpin = 0;
  let bestWinLevelThisSpin = 0;
  let redSymbols: Container[] = [];

  export let socialMode = false;

  export async function ready() {
    await readyPromise;
  }

  function term(cashText: string, socialText: string) {
    return socialMode ? socialText : cashText;
  }

  function emptyBoard(): Board {
    return ROWS_PER_REEL.map((rows) => Array.from({ length: rows }, () => ({ name: 'T' })));
  }

  function attractBoard(): Board {
    const pattern = [
      ['TO', 'K'],
      ['T', 'LS', 'Q'],
      ['J', 'IY', 'WS'],
      ['IS', 'K', 'T'],
      ['Q', 'TO', 'LS'],
      ['WS', 'IY']
    ];
    return ROWS_PER_REEL.map((rows, reel) =>
      Array.from({ length: rows }, (_, row) => ({ name: pattern[reel]?.[row] ?? SPIN_POOL[(reel + row) % SPIN_POOL.length] }))
    );
  }

  function sleep(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function easeOutCubic(t: number) {
    return 1 - Math.pow(1 - t, 3);
  }

  function easeOutBack(t: number) {
    const c1 = 1.70158;
    const c3 = c1 + 1;
    return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
  }

  function reelX(reel: number) {
    return REEL_AREA_X + reel * (SYMBOL_SIZE + SYMBOL_GAP);
  }

  function reelYOffset(reel: number) {
    const rows = ROWS_PER_REEL[reel];
    const reelHeight = rows * SYMBOL_SIZE + (rows - 1) * SYMBOL_GAP;
    return (REEL_AREA_HEIGHT - reelHeight) / 2;
  }

  function cellY(reel: number, row: number) {
    return REEL_AREA_Y + reelYOffset(reel) + row * (SYMBOL_SIZE + SYMBOL_GAP);
  }

  function textureFor(symbol: string): Texture {
    const asset = SYMBOLS[symbol]?.asset ?? SYMBOLS.T.asset;
    return textureCache.get(asset) ?? Texture.from(asset);
  }

  function textureAsset(asset: string): Texture {
    return textureCache.get(asset) ?? Texture.from(asset);
  }

  function isRedFocus(symbol: string) {
    return symbol === 'WD';
  }

  function makeColorGrade(symbol: string) {
    const filter = new ColorMatrixFilter();
    if (isRedFocus(symbol)) {
      filter.saturate(-0.22, false);
      filter.contrast(0.12, true);
      filter.brightness(0.96, true);
      return filter;
    }
    if (SYMBOLS[symbol]?.tier === 'high' || SYMBOLS[symbol]?.tier === 'premium') {
      filter.saturate(-0.16, false);
      filter.brightness(0.94, true);
      filter.contrast(0.06, true);
      return filter;
    }
    if (SYMBOLS[symbol]?.tier === 'scatter') {
      filter.saturate(-0.2, false);
      filter.brightness(0.92, true);
      filter.contrast(0.08, true);
      return filter;
    }
    filter.saturate(-1, false);
    filter.brightness(0.76, true);
    filter.contrast(0.08, true);
    return filter;
  }

  function makeSymbol(symbol: string, reel: number, row: number) {
    const container = new Container();
    container.x = reelX(reel);
    container.y = cellY(reel, row);
    const red = isRedFocus(symbol);
    const frame = new Graphics()
      .roundRect(0, 0, SYMBOL_SIZE, SYMBOL_SIZE, 18)
      .fill({ color: red ? 0x251014 : 0x131210, alpha: 0.94 })
      .stroke({ color: red ? 0xa42a37 : 0x403a35, width: red ? 4 : 2, alpha: red ? 0.82 : 0.72 });
    const sprite = new Sprite(textureFor(symbol));
    sprite.width = SYMBOL_SIZE - 16;
    sprite.height = SYMBOL_SIZE - 16;
    sprite.x = 8;
    sprite.y = 8;
    sprite.filters = [makeColorGrade(symbol)];
    sprite.alpha = red ? 0.96 : 0.88;
    const grime = new Graphics()
      .roundRect(8, 8, SYMBOL_SIZE - 16, SYMBOL_SIZE - 16, 14)
      .stroke({ color: red ? 0xd93652 : 0x110a08, width: red ? 3 : 1, alpha: red ? 0.58 : 0.45 });
    if (red) {
      const underglow = new Graphics()
        .roundRect(5, 5, SYMBOL_SIZE - 10, SYMBOL_SIZE - 10, 18)
        .stroke({ color: 0xff314f, width: 6, alpha: 0.22 });
      container.addChild(underglow);
    }
    container.addChild(frame, sprite, grime);
    return container;
  }

  function symbolSprite(container: Container) {
    return container.children.find((child): child is Sprite => child instanceof Sprite);
  }

  function paintSymbol(container: Container, symbol: string) {
    const sprite = symbolSprite(container);
    if (!sprite) return;
    sprite.texture = textureFor(symbol);
    sprite.width = SYMBOL_SIZE - 16;
    sprite.height = SYMBOL_SIZE - 16;
    sprite.x = 8;
    sprite.y = 8;
    sprite.filters = [makeColorGrade(symbol)];
    sprite.alpha = isRedFocus(symbol) ? 0.96 : 0.88;
  }

  function spinPoolForReel(reel: number) {
    return reel === 5 ? REEL6_POOL : SPIN_POOL;
  }

  function renderBoard(board: Board) {
    currentBoard = board;
    reelLayer.removeChildren();
    symbols = [];
    redSymbols = [];
    const back = new Graphics()
      .roundRect(REEL_AREA_X - 28, REEL_AREA_Y - 28, REEL_AREA_WIDTH + 56, REEL_AREA_HEIGHT + 56, 30)
      .fill({ color: 0x070605, alpha: 0.82 })
      .stroke({ color: 0x682015, width: 4, alpha: 0.9 });
    reelLayer.addChild(back);
    for (let reel = 0; reel < REEL_COUNT; reel++) {
      const reelFrame = new Graphics()
        .roundRect(reelX(reel) - 6, REEL_AREA_Y + reelYOffset(reel) - 6, SYMBOL_SIZE + 12, ROWS_PER_REEL[reel] * SYMBOL_SIZE + (ROWS_PER_REEL[reel] - 1) * SYMBOL_GAP + 12, 18)
        .fill({ color: 0x11100f, alpha: 0.9 })
        .stroke({ color: reel === 5 ? 0x8c1c18 : 0x3d302b, width: reel === 5 ? 4 : 2, alpha: 0.9 });
      reelLayer.addChild(reelFrame);
      symbols[reel] = [];
      for (let row = 0; row < ROWS_PER_REEL[reel]; row++) {
        const container = makeSymbol(board[reel]?.[row]?.name ?? 'T', reel, row);
        symbols[reel][row] = container;
        if (board[reel]?.[row]?.name === 'WD') redSymbols.push(container);
        reelLayer.addChild(container);
      }
    }
  }

  function renderFallbackBackground() {
    bgLayer.removeChildren();
    const sky = new Graphics()
      .rect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
      .fill({ color: 0x070504, alpha: 1 });
    const desert = new Graphics()
      .rect(0, 540, CANVAS_WIDTH, 540)
      .fill({ color: 0x21140f, alpha: 1 });
    const haze = new Graphics()
      .rect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
      .fill({ color: 0x4b1813, alpha: 0.14 });
    bgLayer.addChild(sky, desert, haze);
  }

  function cloneBoard(board: Board): Board {
    return board.map((reel) => reel.map((cell) => ({ ...cell })));
  }

  function reelBounds(reel: number) {
    return {
      x: reelX(reel) - 8,
      y: REEL_AREA_Y + reelYOffset(reel) - 8,
      width: SYMBOL_SIZE + 16,
      height: ROWS_PER_REEL[reel] * SYMBOL_SIZE + (ROWS_PER_REEL[reel] - 1) * SYMBOL_GAP + 16
    };
  }

  async function reelFlash(reel: number, color = 0xff6f35, delay = 0) {
    if (delay > 0) await sleep(delay);
    const bounds = reelBounds(reel);
    const flash = new Graphics()
      .roundRect(bounds.x, bounds.y, bounds.width, bounds.height, 20)
      .stroke({ color, width: 8, alpha: 0.9 })
      .fill({ color, alpha: 0.1 });
    flash.alpha = 0;
    overlayLayer.addChild(flash);
    for (let frame = 0; frame < 14; frame++) {
      const t = frame / 13;
      flash.alpha = Math.sin(t * Math.PI) * 0.95;
      flash.scale.set(1 + t * 0.025);
      await sleep(15);
    }
    flash.destroy();
  }

  async function shockwave(x: number, y: number, color = 0xff6f35, maxRadius = 105) {
    const ring = new Graphics();
    ring.x = x;
    ring.y = y;
    overlayLayer.addChild(ring);
    for (let frame = 0; frame < 18; frame++) {
      const t = frame / 17;
      ring.clear()
        .circle(0, 0, 18 + maxRadius * easeOutCubic(t))
        .stroke({ color, width: 10 * (1 - t), alpha: 0.85 * (1 - t) });
      await sleep(14);
    }
    ring.destroy();
  }

  async function scatterAnticipation(reel: number, delay = 0) {
    if (delay > 0) await sleep(delay);
    const bounds = reelBounds(reel);
    const group = new Container();
    const glow = new Graphics()
      .roundRect(bounds.x - 8, bounds.y - 8, bounds.width + 16, bounds.height + 16, 22)
      .stroke({ color: 0xf05b24, width: 10, alpha: 0.62 })
      .fill({ color: 0x3d1605, alpha: 0.12 });
    const silhouette = new Sprite(textureFor('SC'));
    silhouette.anchor.set(0.5);
    silhouette.x = bounds.x + bounds.width / 2;
    silhouette.y = bounds.y + bounds.height / 2;
    silhouette.width = SYMBOL_SIZE * 0.84;
    silhouette.height = SYMBOL_SIZE * 0.84;
    silhouette.alpha = 0.15;
    silhouette.filters = [makeColorGrade('SC')];
    group.addChild(glow, silhouette);
    overlayLayer.addChild(group);
    for (let frame = 0; frame < 22; frame++) {
      const t = frame / 21;
      const pulse = Math.sin(t * Math.PI * 4);
      group.alpha = 0.25 + Math.abs(pulse) * 0.55;
      silhouette.scale.set(1 + Math.abs(pulse) * 0.08);
      emitParticle('ember_particle', bounds.x + bounds.width / 2 + (Math.random() - 0.5) * 110, bounds.y + bounds.height / 2 + (Math.random() - 0.5) * 180, 1, 0xf05b24);
      await sleep(20);
    }
    group.destroy({ children: true });
  }

  function triggerSymbolArrivalFx(name: string, reel: number, row: number) {
    const center = cellCenter(reel, row);
    if (name === 'WD') {
      emitParticle('ember_particle', center.x, center.y, 9, 0xbd263b);
      void shockwave(center.x, center.y, 0xb52a3a, 84);
    }
    if (name === 'SC') {
      emitParticle('ember_particle', center.x, center.y, 8, 0xff6b25);
      void shockwave(center.x, center.y, 0xff6b25, 78);
    }
    if (name === 'LS') emitParticle('ember_particle', center.x, center.y, 4, 0x8f2a2e);
  }

  async function dropSymbol(symbolContainer: Container, finalY: number, delay: number, name: string, reel: number, row: number) {
    symbolContainer.y = finalY - 520 - row * 80;
    symbolContainer.alpha = 0;
    symbolContainer.scale.set(0.88);
    if (delay > 0) await sleep(delay);
    const frames = 20;
    for (let frame = 0; frame <= frames; frame++) {
      const t = frame / frames;
      const ease = easeOutBack(t);
      symbolContainer.y = finalY - (1 - Math.min(ease, 1)) * (520 + row * 80) + Math.sin(t * Math.PI) * 10;
      symbolContainer.alpha = Math.min(1, t * 1.35);
      symbolContainer.scale.set(0.88 + Math.min(ease, 1) * 0.12);
      await sleep(13);
    }
    symbolContainer.y = finalY;
    symbolContainer.alpha = 1;
    symbolContainer.scale.set(1);
    triggerSymbolArrivalFx(name, reel, row);
  }

  async function spinSymbol(symbolContainer: Container, finalY: number, delay: number, name: string, reel: number, row: number) {
    if (delay > 0) await sleep(delay);
    const pool = spinPoolForReel(reel);
    const stride = SYMBOL_SIZE + SYMBOL_GAP;
    const frames = 36 + reel * 2;
    symbolContainer.y = finalY;
    symbolContainer.alpha = 0.72;
    symbolContainer.scale.set(0.96, 1.08);

    for (let frame = 0; frame <= frames; frame++) {
      const t = frame / frames;
      const ease = easeOutCubic(t);
      if (frame < frames - 5 && frame % 2 === 0) {
        const poolIndex = (frame + reel * 3 + row * 2 + Math.floor(Math.random() * pool.length)) % pool.length;
        paintSymbol(symbolContainer, pool[poolIndex]);
      }
      const loopOffset = ((frame * 46 + row * 23) % stride) - stride / 2;
      symbolContainer.y = finalY + loopOffset * (1 - ease) * 0.92;
      symbolContainer.alpha = 0.72 + ease * 0.28;
      symbolContainer.rotation = (Math.random() - 0.5) * 0.018 * (1 - ease);
      symbolContainer.scale.set(0.96 + ease * 0.04, 1.08 - ease * 0.08);
      await sleep(18);
    }

    paintSymbol(symbolContainer, name);
    symbolContainer.y = finalY;
    symbolContainer.alpha = 1;
    symbolContainer.rotation = 0;
    symbolContainer.scale.set(1);
    triggerSymbolArrivalFx(name, reel, row);
  }

  async function spinTo(board: Board, anticipation: number[], mode: string, presentation?: 'buyTrigger') {
    bigWinShownThisSpin = false;
    bestWinAmountThisSpin = 0;
    bestWinLevelThisSpin = 0;
    eventEmitter.broadcast({
      type: 'toast',
      message: presentation === 'buyTrigger' ? 'FLARES LANDING' : mode === 'base' ? 'FLARES ARMING' : 'WARPATH SPINS',
      tone: mode === 'base' ? 'amber' : 'red'
    });
    renderBoard(cloneBoard(board));
    const animations: Promise<void>[] = [];
    for (let reel = 0; reel < REEL_COUNT; reel++) {
      const delayBase = reel * 132 + (anticipation[reel] ? 220 : 0);
      if (anticipation[reel]) animations.push(scatterAnticipation(reel, Math.max(0, delayBase - 210)));
      animations.push(reelFlash(reel, anticipation[reel] ? 0xf05b24 : 0x80604d, delayBase + 380));
      for (let row = 0; row < ROWS_PER_REEL[reel]; row++) {
        const name = board[reel]?.[row]?.name ?? (reel === 5 ? REEL6_POOL[0] : SPIN_POOL[0]);
        animations.push(spinSymbol(symbols[reel][row], cellY(reel, row), delayBase + row * 28, name, reel, row));
      }
    }
    await Promise.all(animations);
    await screenShake(4, 160);
    emitAmbient('smoke', 4);
  }

  function cellCenter(reel: number, row: number) {
    return { x: reelX(reel) + SYMBOL_SIZE / 2, y: cellY(reel, row) + SYMBOL_SIZE / 2 };
  }

  function particleTexture(name: string) {
    return textureAsset(`${ASSET_PATH}/particles/${name}.png`);
  }

  function emitParticle(name: string, x: number, y: number, count: number, tint?: number) {
    for (let i = 0; i < count; i++) {
      const sprite = new Sprite(particleTexture(name));
      sprite.anchor.set(0.5);
      sprite.x = x + (Math.random() - 0.5) * 30;
      sprite.y = y + (Math.random() - 0.5) * 30;
      sprite.scale.set(0.18 + Math.random() * 0.45);
      sprite.alpha = 0.8;
      if (tint) sprite.tint = tint;
      fxLayer.addChild(sprite);
      const vx = (Math.random() - 0.5) * 8;
      const vy = (Math.random() - 0.8) * 8;
      const life = 35 + Math.random() * 45;
      let age = 0;
      const ticker = () => {
        age += 1;
        sprite.x += vx;
        sprite.y += vy + age * 0.08;
        sprite.rotation += 0.08;
        sprite.alpha = Math.max(0, 1 - age / life);
        sprite.scale.x *= 0.992;
        sprite.scale.y *= 0.992;
        if (age >= life && app) {
          app.ticker.remove(ticker);
          sprite.destroy();
        }
      };
      app?.ticker.add(ticker);
    }
  }

  function emitAmbient(kind: 'embers' | 'smoke' | 'sand', amount: number) {
    for (let i = 0; i < amount; i++) {
      const x = Math.random() * CANVAS_WIDTH;
      const y = kind === 'embers' ? 880 + Math.random() * 160 : 520 + Math.random() * 380;
      emitParticle(kind === 'embers' ? 'ember_particle' : kind === 'sand' ? 'sand_grain' : 'smoke_puff', x, y, kind === 'sand' ? 2 : 1);
    }
  }

  async function highlightWins(wins: WinLine[], totalWin: number) {
    for (const reel of symbols) for (const sym of reel) sym.alpha = 0.28;
    const positions = wins.flatMap((win) => win.positions);
    for (const [reel, row] of positions) {
      const sym = symbols[reel]?.[row];
      if (!sym) continue;
      sym.alpha = 1;
      sym.scale.set(1.07);
      const center = cellCenter(reel, row);
      emitParticle(totalWin > 20 ? 'blood_drop' : 'spark', center.x, center.y, totalWin > 20 ? 7 : 5);
      void shockwave(center.x, center.y, totalWin > 20 ? 0xff352e : 0xffa64c, 74);
    }
    await screenShake(Math.min(20, 4 + totalWin / 10), Math.min(900, 180 + totalWin * 8));
    await sleep(620);
    for (const reel of symbols) for (const sym of reel) {
      sym.alpha = 1;
      sym.scale.set(1);
    }
  }

  async function cascadeExplode(positions: [number, number][], board: Board, multiplier: number, step: number) {
    for (const [reel, row] of positions) {
      const center = cellCenter(reel, row);
      emitParticle('debris_chunk', center.x, center.y, 5);
      emitParticle('blood_drop', center.x, center.y, 2);
      void shockwave(center.x, center.y, 0xff472f, 82 + step * 5);
    }
    await screenShake(5 + step * 2, 180);
    await sleep(220);
    renderBoard(board);
    for (let reel = 0; reel < REEL_COUNT; reel++) {
      for (let row = 0; row < ROWS_PER_REEL[reel]; row++) {
        const sym = symbols[reel][row];
        sym.y -= 44 + row * 16;
      }
    }
    const settle: Promise<void>[] = [];
    for (let reel = 0; reel < REEL_COUNT; reel++) {
      for (let row = 0; row < ROWS_PER_REEL[reel]; row++) {
        const sym = symbols[reel][row];
        settle.push(dropSymbol(sym, cellY(reel, row), reel * 32 + row * 28, board[reel]?.[row]?.name ?? 'T', reel, row));
      }
    }
    const stamp = new Text({
      text: `CASCADE +${step}  x${multiplier}`,
      style: { fontFamily: 'Impact', fontSize: 54, fill: 0xff6330, stroke: { color: 0x000000, width: 6 } }
    });
    stamp.anchor.set(0.5);
    stamp.x = CANVAS_WIDTH / 2;
    stamp.y = REEL_AREA_Y - 70;
    overlayLayer.addChild(stamp);
    await Promise.all(settle);
    await sleep(180);
    stamp.destroy();
  }

  async function wildPulse(multiplier: number, wildReels: number[]) {
    const curtains: Promise<void>[] = [];
    for (const reel of wildReels) {
      curtains.push(wildReelCurtain(reel, multiplier));
      for (let row = 0; row < ROWS_PER_REEL[reel]; row++) {
        const center = cellCenter(reel, row);
        emitParticle('ember_particle', center.x, center.y, 4, 0xb7263a);
        void shockwave(center.x, center.y, 0xb7263a, 96);
      }
    }
    await screenShake(10 + multiplier, 350);
    await Promise.all(curtains);
    await sleep(360);
  }

  async function wildReelCurtain(reel: number, multiplier: number) {
    const bounds = reelBounds(reel);
    const group = new Container();
    const curtain = new Graphics()
      .rect(bounds.x - 10, bounds.y - 10, bounds.width + 20, bounds.height + 20)
      .fill({ color: 0x3a050b, alpha: 0.18 })
      .stroke({ color: 0xc92a3f, width: 8, alpha: 0.72 });
    const label = new Text({
      text: `x${multiplier}`,
      style: { fontFamily: 'Impact', fontSize: 52, fill: 0xffd1bd, stroke: { color: 0x120406, width: 8 } }
    });
    label.anchor.set(0.5);
    label.x = bounds.x + bounds.width / 2;
    label.y = bounds.y + bounds.height / 2;
    group.addChild(curtain, label);
    overlayLayer.addChild(group);
    for (let frame = 0; frame < 26; frame++) {
      const t = frame / 25;
      const pulse = Math.sin(t * Math.PI * 5);
      group.alpha = 0.25 + Math.abs(pulse) * 0.75;
      group.scale.set(1 + Math.abs(pulse) * 0.018);
      await sleep(16);
    }
    group.destroy({ children: true });
  }

  async function globalMultiplierStamp(multiplier: number, label: string) {
    const text = new Text({
      text: label || `WARPATH x${multiplier}`,
      style: { fontFamily: 'Impact', fontSize: 60, fill: 0xff4058, stroke: { color: 0x000000, width: 9 }, letterSpacing: 5 }
    });
    text.anchor.set(0.5);
    text.x = REEL_AREA_X + REEL_AREA_WIDTH / 2;
    text.y = REEL_AREA_Y - 52;
    text.alpha = 0;
    text.scale.set(0.72);
    overlayLayer.addChild(text);
    for (let frame = 0; frame < 20; frame++) {
      const t = frame / 19;
      text.alpha = Math.sin(t * Math.PI);
      text.scale.set(0.72 + easeOutBack(Math.min(1, t * 1.7)) * 0.28);
      text.y = REEL_AREA_Y - 52 - easeOutCubic(t) * 26;
      if (frame % 4 === 0) emitParticle('ember_particle', text.x + (Math.random() - 0.5) * 360, text.y + (Math.random() - 0.5) * 80, 2, 0xb72b39);
      await sleep(16);
    }
    text.destroy();
  }

  async function bigWinPopup(amount: number, level: number) {
    if (amount <= 0 || level < 2) return;
    if (bigWinShownThisSpin) return;
    bigWinShownThisSpin = true;
    const labelText = BIG_WIN_LABELS[Math.max(0, Math.min(BIG_WIN_LABELS.length - 1, level - 2))];
    const group = new Container();
    const blocker = new Graphics()
      .rect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT)
      .fill({ color: level >= 4 ? 0x4b0000 : 0x000000, alpha: level >= 4 ? 0.28 : 0.14 });
    const panel = new Graphics()
      .rect(-470, -165, 940, 330)
      .fill({ color: level >= 5 ? 0x21070b : 0x170d09, alpha: 0.94 })
      .stroke({ color: level >= 5 ? 0xff3550 : 0xff7b32, width: 8, alpha: 0.92 });
    panel.x = CANVAS_WIDTH / 2;
    panel.y = CANVAS_HEIGHT / 2;
    const slashTop = new Graphics()
      .rect(-430, -125, 860, 18)
      .fill({ color: level >= 5 ? 0xb82738 : 0xc45b2c, alpha: 0.9 });
    slashTop.x = CANVAS_WIDTH / 2;
    slashTop.y = CANVAS_HEIGHT / 2;
    slashTop.rotation = -0.025;
    const slashBottom = new Graphics()
      .rect(-430, 110, 860, 14)
      .fill({ color: level >= 5 ? 0xb82738 : 0xc45b2c, alpha: 0.82 });
    slashBottom.x = CANVAS_WIDTH / 2;
    slashBottom.y = CANVAS_HEIGHT / 2;
    slashBottom.rotation = -0.025;
    const title = new Text({
      text: labelText,
      style: {
        fontFamily: 'Impact',
        fontSize: level >= 5 ? 108 : 94,
        fill: level >= 5 ? 0xffd5cb : 0xffd6a0,
        stroke: { color: 0x000000, width: 12 },
        letterSpacing: 8
      }
    });
    title.anchor.set(0.5);
    title.x = CANVAS_WIDTH / 2;
    title.y = CANVAS_HEIGHT / 2 - 42;
    const value = new Text({
      text: `${amount.toFixed(2)}x ${term('BET', 'PLAY')}`,
      style: { fontFamily: 'Impact', fontSize: 62, fill: 0xffb86b, stroke: { color: 0x000000, width: 8 }, letterSpacing: 4 }
    });
    value.anchor.set(0.5);
    value.x = CANVAS_WIDTH / 2;
    value.y = CANVAS_HEIGHT / 2 + 76;
    group.addChild(blocker, panel, slashTop, slashBottom, title, value);
    group.alpha = 0;
    group.scale.set(0.62);
    overlayLayer.addChild(group);
    for (let frame = 0; frame < 44; frame++) {
      const t = frame / 43;
      const ease = easeOutBack(Math.min(1, t * 1.3));
      group.alpha = Math.min(1, t * 2.2);
      group.scale.set(0.62 + ease * 0.38 + Math.sin(t * Math.PI * 6) * 0.018);
      title.rotation = Math.sin(t * Math.PI * 5) * 0.012;
      if (frame % 4 === 0) {
        emitParticle(level >= 4 ? 'blood_drop' : 'spark', CANVAS_WIDTH / 2 + (Math.random() - 0.5) * 720, CANVAS_HEIGHT / 2 + (Math.random() - 0.5) * 280, 3);
      }
      await sleep(18);
    }
    await screenShake(7 + level * 2, 220);
    await sleep(520);
    for (let frame = 0; frame < 16; frame++) {
      const t = frame / 15;
      group.alpha = 1 - t;
      group.scale.set(1 + t * 0.18);
      await sleep(18);
    }
    group.destroy({ children: true });
  }

  function noteWinForPopup(amount: number, level: number) {
    if (level > bestWinLevelThisSpin || (level === bestWinLevelThisSpin && amount > bestWinAmountThisSpin)) {
      bestWinLevelThisSpin = level;
      bestWinAmountThisSpin = amount;
    }
  }

  function levelForTotal(amount: number) {
    if (amount >= 100) return 5;
    if (amount >= 50) return 4;
    if (amount >= 20) return 3;
    if (amount >= 5) return 2;
    return 1;
  }

  async function finalWinCelebration(totalAmount: number) {
    const level = Math.max(bestWinLevelThisSpin, levelForTotal(totalAmount));
    const amount = Math.max(bestWinAmountThisSpin, totalAmount);
    await bigWinPopup(amount, level);
  }

  async function characterTakeover(symbol: string, targetReels: number[]) {
    const config = SYMBOLS[symbol];
    const sprite = Sprite.from(config?.tallAsset ?? SYMBOLS.LS.tallAsset!);
    sprite.anchor.set(0.5);
    sprite.x = reelX(targetReels[0]) + ((SYMBOL_SIZE + SYMBOL_GAP) * targetReels.length) / 2 - SYMBOL_GAP;
    sprite.y = REEL_AREA_Y + REEL_AREA_HEIGHT / 2;
    sprite.width = SYMBOL_SIZE * targetReels.length;
    sprite.height = REEL_AREA_HEIGHT + 70;
    sprite.alpha = 0;
    overlayLayer.addChild(sprite);
    for (let i = 0; i < 18; i++) {
      sprite.alpha = i / 18;
      sprite.scale.set(1 + Math.sin(i / 18) * 0.05);
      await sleep(24);
    }
    await screenShake(14, 450);
    await sleep(500);
    sprite.destroy();
  }

  async function featureIntro(
    _mode: 'warpath',
    spins: number,
    source: 'trigger' | 'buy' = 'trigger',
    multiplierStart = 2,
    purchaseCost = 0
  ) {
    const group = new Container();
    const blocker = new Graphics().rect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT).fill({ color: 0x090504, alpha: 0.9 });
    const redWash = new Graphics().rect(0, 0, CANVAS_WIDTH, CANVAS_HEIGHT).fill({ color: 0x53070e, alpha: 0.22 });
    const soldier = Sprite.from(SYMBOLS.WD.tallAsset ?? SYMBOLS.WD.asset);
    soldier.anchor.set(0.5);
    soldier.x = CANVAS_WIDTH + 170;
    soldier.y = CANVAS_HEIGHT / 2 + 10;
    soldier.width = 360;
    soldier.height = 920;
    soldier.filters = [makeColorGrade('WD')];
    const panel = new Graphics()
      .rect(-520, -170, 1040, 340)
      .fill({ color: 0x160806, alpha: 0.94 })
      .stroke({ color: 0xbd2a3d, width: 8, alpha: 0.92 });
    panel.x = CANVAS_WIDTH / 2 - 230;
    panel.y = CANVAS_HEIGHT / 2;
    const title = new Text({
      text: `${spins} WARPATH SPINS`,
      style: { fontFamily: 'Impact', fontSize: 104, align: 'center', fill: 0xffd9ca, stroke: { color: 0x000000, width: 12 }, letterSpacing: 8 }
    });
    title.anchor.set(0.5);
    title.x = panel.x;
    title.y = panel.y - 46;
    const subtitle = new Text({
      text: `${source === 'buy' ? `FEATURE START ${purchaseCost}x` : 'FLARE BONUS TRIGGERED'}\nSTART x${multiplierStart} · CASCADES RAISE IT`,
      style: { fontFamily: 'Impact', fontSize: 50, align: 'center', fill: 0xff5b6d, stroke: { color: 0x000000, width: 8 }, letterSpacing: 3 }
    });
    subtitle.anchor.set(0.5);
    subtitle.x = panel.x;
    subtitle.y = panel.y + 72;
    const cards = Array.from({ length: 6 }, (_, index) => {
	      const card = Sprite.from(SYMBOLS.SC.asset);
      card.anchor.set(0.5);
      card.width = 118;
      card.height = 118;
      card.x = panel.x - 330 + index * 132;
      card.y = -130 - index * 34;
      card.alpha = 0;
	      card.filters = [makeColorGrade('SC')];
      return card;
    });
    group.addChild(blocker, redWash, ...cards, soldier, panel, title, subtitle);
    overlayLayer.addChild(group);
    for (let frame = 0; frame < 72; frame++) {
      const t = frame / 71;
      const ease = easeOutCubic(t);
      soldier.x = CANVAS_WIDTH + 170 - ease * 500;
      soldier.rotation = Math.sin(t * Math.PI * 2) * 0.018;
      panel.scale.set(0.86 + easeOutBack(Math.min(1, t * 1.2)) * 0.14);
      title.scale.set(1 + Math.sin(t * Math.PI * 6) * 0.018);
      redWash.alpha = 0.12 + Math.sin(t * Math.PI * 4) * 0.06;
      for (let index = 0; index < cards.length; index++) {
        const local = Math.max(0, Math.min(1, (t - index * 0.055) * 2.2));
        cards[index].alpha = Math.min(1, local * 1.4);
        cards[index].y = -130 - index * 34 + easeOutBack(local) * (CANVAS_HEIGHT / 2 + 334 + index * 34);
        cards[index].rotation = (index - 2.5) * 0.025 + Math.sin(t * Math.PI * 4 + index) * 0.025;
      }
      if (frame % 3 === 0) emitParticle('ember_particle', CANVAS_WIDTH / 2 + (Math.random() - 0.5) * 1000, CANVAS_HEIGHT / 2 + (Math.random() - 0.5) * 430, 3, 0xb72b39);
      await sleep(18);
    }
    await screenShake(16, 520);
    await sleep(620);
    for (let frame = 0; frame < 20; frame++) {
      const t = frame / 19;
      group.alpha = 1 - t;
      group.scale.set(1 + t * 0.06);
      await sleep(18);
    }
    group.destroy({ children: true });
  }

  async function screenShake(intensity: number, duration: number) {
    const start = performance.now();
    while (performance.now() - start < duration) {
      root.x = (Math.random() - 0.5) * intensity;
      root.y = (Math.random() - 0.5) * intensity;
      await sleep(16);
    }
    root.x = 0;
    root.y = 0;
  }

  async function init() {
    app = new Application();
    await app.init({
      canvas,
      width: CANVAS_WIDTH,
      height: CANVAS_HEIGHT,
      backgroundColor: 0x050403,
      antialias: true,
      resolution: window.devicePixelRatio || 1,
      autoDensity: true
    });
    app.stage.addChild(root);
    root.addChild(bgLayer, reelLayer, fxLayer, overlayLayer);
    renderFallbackBackground();
    currentBoard = attractBoard();
    renderBoard(currentBoard);

    const assets = [
      BACKGROUND_ASSET,
      ...PARTICLE_ASSETS,
      ...Object.values(SYMBOLS).flatMap((s) => [s.asset, s.tallAsset].filter(Boolean) as string[])
    ];
    try {
      await Assets.load(assets);
      for (const asset of assets) {
        const texture = Assets.get(asset) as Texture | undefined;
        if (texture) textureCache.set(asset, texture);
      }
    } catch (error) {
      console.warn('[Warpath] Some Pixi assets failed to preload; continuing with visible fallback stage.', error);
    }

    bgLayer.removeChildren();
    const bg = new Sprite(textureAsset(BACKGROUND_ASSET));
    bg.width = CANVAS_WIDTH;
    bg.height = CANVAS_HEIGHT;
    const bgGrade = new ColorMatrixFilter();
    bgGrade.saturate(-0.78, false);
    bgGrade.brightness(0.7, true);
    bg.filters = [bgGrade];
    bgLayer.addChild(bg);
    renderBoard(currentBoard);
    app.ticker.add(() => {
      const pulse = Math.sin(performance.now() / 220) * 0.018;
      redSymbols = redSymbols.filter((sym) => !sym.destroyed);
      for (const sym of redSymbols) {
        sym.scale.set(1.02 + pulse);
        sym.rotation = Math.sin(performance.now() / 360 + sym.x) * 0.006;
      }
      if (Math.random() < 0.18) emitAmbient('embers', 1);
    });
    unsubscribe = eventEmitter.subscribeOnMount({
      reelsSpin: (event) => spinTo(event.board, event.anticipation, event.mode, event.presentation),
      winHighlight: (event) => highlightWins(event.wins, event.totalWin),
      cascadeExplode: (event) => cascadeExplode(event.positions, event.board, event.multiplier, event.step),
      wildPulse: (event) => wildPulse(event.multiplier, event.wildReels),
      globalMultiplier: (event) => globalMultiplierStamp(event.multiplier, event.label),
      winCounter: (event) => noteWinForPopup(event.amount, event.level),
      finalWin: (event) => finalWinCelebration(event.amount),
      characterTakeover: (event) => characterTakeover(event.symbol, event.targetReels),
      featureIntro: (event) => featureIntro(event.mode, event.spins, event.source, event.multiplierStart, event.purchaseCost)
    });
    loaded = true;
    resolveReady?.();
  }

  onMount(() => {
    void init();
  });

  onDestroy(() => {
    unsubscribe();
    app?.destroy(true);
  });
</script>

<canvas bind:this={canvas} class:loaded aria-label="Warpath Reels PixiJS game canvas"></canvas>

<style>
  canvas {
    width: 100%;
    height: 100%;
    display: block;
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  canvas.loaded {
    opacity: 1;
  }
</style>
