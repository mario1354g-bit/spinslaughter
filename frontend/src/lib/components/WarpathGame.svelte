<script lang="ts">
  import { onDestroy, onMount } from 'svelte';
  import PixiStage from './PixiStage.svelte';
  import WarpathAudio from './WarpathAudio.svelte';
  import { BET_LEVELS, CANVAS_HEIGHT, CANVAS_WIDTH, TOTAL_WAYS } from '$lib/game/constants';
  import { eventEmitter } from '$lib/game/eventEmitter';
  import { BOOK_MODE_COSTS, pickBook, type BookMode } from '$lib/game/books';
  import { playBookEvents } from '$lib/game/bookPlayer';
  import type { Book, BookEvent } from '$lib/game/types';
  import { formatMoneyUnits, scaledWinUnits, toMoneyUnits } from '$lib/rgs/currency';
  import {
    RgsClient,
    RgsError,
    extractBookFromReplay,
    extractBookFromRound,
    fetchReplayRound,
    hasReplayParams,
    hasRgsSession,
    isActiveRound,
    readReplayLaunchParams,
    readRgsLaunchParams,
    type RgsAuthResponse,
    type RgsConfig
  } from '$lib/rgs/client';

  type BuyOption = {
    mode: Exclude<BookMode, 'base'>;
    spins: number;
    scatters: number;
    label: string;
    asset: string;
  };

  const BUY_OPTIONS: BuyOption[] = [
    { mode: 'warpath_buy_8', spins: 8, scatters: 3, label: '3 SCATTERS', asset: '/assets/ui/buy_warpath_8.png' },
    { mode: 'warpath_buy_10', spins: 10, scatters: 4, label: '4 SCATTERS', asset: '/assets/ui/buy_warpath_10.png' },
    { mode: 'warpath_buy_12', spins: 12, scatters: 5, label: '5 SCATTERS', asset: '/assets/ui/buy_warpath_12.png' }
  ];

  const LOCAL_BALANCE_UNITS = toMoneyUnits(100000);
  const LOCAL_BET_LEVELS = BET_LEVELS.map(toMoneyUnits);

  const PAYTABLE_ROWS = [
    { symbol: 'Crimson Commander', values: ['0.80', '2.50', '8.00', '30.00'] },
    { symbol: 'Desert Elder', values: ['0.55', '1.80', '5.50', '18.00'] },
    { symbol: 'Young Raider', values: ['0.45', '1.40', '4.20', '13.00'] },
    { symbol: 'Desert Commander', values: ['0.35', '1.05', '3.20', '10.00'] },
    { symbol: 'Field Operative', values: ['0.30', '0.85', '2.50', '8.00'] },
    { symbol: 'K', values: ['0.18', '0.45', '1.20', '3.20'] },
    { symbol: 'Q', values: ['0.15', '0.38', '1.00', '2.70'] },
    { symbol: 'J', values: ['0.12', '0.30', '0.80', '2.20'] },
    { symbol: '10', values: ['0.10', '0.25', '0.65', '1.80'] }
  ];

  let stage: PixiStage;
  let scale = 1;
  let viewportWidth = CANVAS_WIDTH;
  let viewportHeight = CANVAS_HEIGHT;
  let resizeFrame = 0;
  let playing = false;
  let balanceUnits = LOCAL_BALANCE_UNITS;
  let currency = 'USD';
  let betLevels = LOCAL_BET_LEVELS;
  let betIndex = 2;
  let currentWinUnits = 0;
  let totalWinUnits = 0;
  let winLevel = 0;
  let escalationLevel = 1;
  let freeSpinLabel = '';
  let multiplierLabel = '';
  let toast = 'READY';
  let toastTone: 'red' | 'amber' | 'blue' = 'amber';
  let introVisible = true;
  let stageReady = false;
  let unsubscribe = () => {};
  let soundOn = true;
  let infoOpen = false;
  let awaitingBonusSpin = false;
  let buyMenuOpen = false;
  let selectedBuyMode: BuyOption['mode'] = BUY_OPTIONS[0].mode;
  let rgsClient: RgsClient | null = null;
  let runtimeMode: 'rgs' | 'local' | 'replay' = 'local';
  let sessionStatus: 'loading' | 'ready' | 'local' | 'error' = 'loading';
  let pendingRoundBook: Book | null = null;
  let socialMode = false;
  let replayMode = false;
  let replayStatus: 'idle' | 'loading' | 'ready' | 'playing' | 'complete' | 'error' = 'idle';
  let replayBook: Book | null = null;
  let replayBaseBetUnits = toMoneyUnits(1);
  let replayCostMultiplier = 1;
  let replayPayoutMultiplier = 0;
  let replayModeName = 'base';

  $: betUnits = betLevels[betIndex] ?? LOCAL_BET_LEVELS[2];
  $: activeBetUnits = replayMode ? replayBaseBetUnits : betUnits;
  $: selectedBuyOption = BUY_OPTIONS.find((option) => option.mode === selectedBuyMode) ?? BUY_OPTIONS[0];
  $: selectedBuyCostUnits = modeCostUnits(selectedBuyOption.mode);
  $: replayRealCostUnits = Math.round(replayBaseBetUnits * replayCostMultiplier);
  $: replayPayoutUnits = scaledWinUnits(replayPayoutMultiplier, replayBaseBetUnits);
  $: playDisabled = replayMode || ((sessionStatus === 'loading' || sessionStatus === 'error') && !awaitingBonusSpin);

  function modeCostUnits(mode: BookMode) {
    return Math.round(betUnits * BOOK_MODE_COSTS[mode]);
  }

  function display(amount: number) {
    return formatMoneyUnits(amount, currency);
  }

  function term(cashText: string, socialText: string) {
    return socialMode ? socialText : cashText;
  }

  function getViewportSize() {
    const viewport = window.visualViewport;
    return {
      width: Math.max(1, viewport?.width ?? window.innerWidth),
      height: Math.max(1, viewport?.height ?? window.innerHeight)
    };
  }

  function resize() {
    if (resizeFrame) window.cancelAnimationFrame(resizeFrame);
    resizeFrame = window.requestAnimationFrame(() => {
      resizeFrame = 0;
      const viewport = getViewportSize();
      viewportWidth = viewport.width;
      viewportHeight = viewport.height;
      scale = Math.min(viewport.width / CANVAS_WIDTH, viewport.height / CANVAS_HEIGHT);
    });
  }

  function adjustBet(direction: number) {
    if (playing || betLevels.length <= 1) return;
    betIndex = Math.max(0, Math.min(betLevels.length - 1, betIndex + direction));
  }

  function openBonusMenu() {
    if (playing || playDisabled) return;
    eventEmitter.broadcast({ type: 'audioUnlock' });
    infoOpen = false;
    buyMenuOpen = true;
  }

  function selectBuyOption(option: BuyOption) {
    selectedBuyMode = option.mode;
  }

  function closeBuyMenu() {
    buyMenuOpen = false;
  }

  function confirmBuyContext() {
    if (playing) return;
    const mode = selectedBuyOption.mode;
    buyMenuOpen = false;
    void play(mode);
  }

  function enterGame() {
    if (replayMode) {
      void startReplay();
      return;
    }
    eventEmitter.broadcast({ type: 'audioUnlock' });
    introVisible = false;
    toast = sessionStatus === 'loading' ? 'CONNECTING TO RGS' : pendingRoundBook ? 'ROUND READY TO RESUME' : 'HUNT WILDS AND FLARES';
    toastTone = 'red';
  }

  function toggleSound() {
    soundOn = !soundOn;
    eventEmitter.broadcast({ type: 'audioUnlock' });
    eventEmitter.broadcast({ type: 'audioMuteSet', muted: !soundOn });
    toast = soundOn ? 'SOUND ON' : 'SOUND OFF';
    toastTone = 'amber';
  }

  function continueBonusSpin() {
    if (!awaitingBonusSpin) return;
    awaitingBonusSpin = false;
    toast = 'FIRING WARPATH SPIN';
    toastTone = 'red';
    eventEmitter.broadcast({ type: 'bonusSpinContinue' });
  }

  function handleSpinClick() {
    if (awaitingBonusSpin) {
      continueBonusSpin();
      return;
    }
    if (playing || playDisabled) return;
    void play('base');
  }

  async function waitForStage(maxMs = 2500) {
    if (!stage) return;
    await Promise.race([
      stage.ready(),
      new Promise<void>((resolve) => {
        window.setTimeout(resolve, maxMs);
      })
    ]);
  }

  function normaliseBetLevels(config: RgsConfig) {
    const minBet = Number(config.minBet) || 0;
    const maxBet = Number(config.maxBet) || Number.MAX_SAFE_INTEGER;
    const stepBet = Math.max(1, Number(config.stepBet) || 1);
    const source = Array.isArray(config.betLevels) && config.betLevels.length > 0
      ? config.betLevels
      : [...LOCAL_BET_LEVELS, Number(config.defaultBetLevel)].filter(Boolean);
    const levels = Array.from(new Set(source.map(Number)))
      .filter((level) => Number.isFinite(level) && level >= minBet && level <= maxBet && level % stepBet === 0)
      .sort((a, b) => a - b);
    return levels.length > 0 ? levels : [Number(config.defaultBetLevel) || minBet || toMoneyUnits(1)];
  }

  function applyAuthResponse(response: RgsAuthResponse) {
    balanceUnits = Number(response.balance.amount) || 0;
    currency = response.balance.currency || currency;
    betLevels = normaliseBetLevels(response.config);
    const defaultBet = Number(response.config.defaultBetLevel) || betLevels[0];
    const defaultIndex = betLevels.findIndex((level) => level === defaultBet);
    betIndex = defaultIndex >= 0 ? defaultIndex : Math.max(0, betLevels.findIndex((level) => level >= defaultBet));
    if (betIndex < 0) betIndex = 0;
    socialMode = Boolean(response.config.jurisdiction?.socialCasino);
    if (isActiveRound(response.round)) {
      pendingRoundBook = extractBookFromRound(response.round);
    }
  }

  async function initialiseReplay() {
    const params = readReplayLaunchParams();
    if (!params.replay) return false;
    replayMode = true;
    runtimeMode = 'replay';
    sessionStatus = 'loading';
    replayStatus = 'loading';
    socialMode = params.social;
    currency = params.currency;
    replayBaseBetUnits = params.amount ?? toMoneyUnits(1);
    replayModeName = params.mode ?? 'base';
    toast = 'LOADING REPLAY';
    toastTone = 'blue';
    if (!hasReplayParams(params)) {
      sessionStatus = 'error';
      replayStatus = 'error';
      toast = 'REPLAY URL INVALID';
      toastTone = 'red';
      return true;
    }
    try {
      const response = await fetchReplayRound(params);
      replayBook = extractBookFromReplay(response);
      replayCostMultiplier = Number(response.costMultiplier) || BOOK_MODE_COSTS[replayModeName as BookMode] || 1;
      replayPayoutMultiplier = Number(response.payoutMultiplier) || replayBook?.payoutMultiplier || 0;
      if (!replayBook) throw new Error('Replay response did not include playable game state');
      sessionStatus = 'ready';
      replayStatus = 'ready';
      toast = 'REPLAY READY';
      toastTone = 'blue';
    } catch (error) {
      sessionStatus = 'error';
      replayStatus = 'error';
      toast = error instanceof RgsError ? `REPLAY ${error.code}` : 'REPLAY LOAD FAILED';
      toastTone = 'red';
    }
    return true;
  }

  async function initialiseRgs() {
    if (await initialiseReplay()) return;
    const params = readRgsLaunchParams();
    socialMode = params.social;
    if (!hasRgsSession(params)) {
      runtimeMode = 'local';
      sessionStatus = 'local';
      toast = 'LOCAL DEV MODE';
      toastTone = 'blue';
      return;
    }
    runtimeMode = 'rgs';
    sessionStatus = 'loading';
    rgsClient = new RgsClient(params.rgsUrl, params.sessionID);
    try {
      const response = await rgsClient.authenticate();
      applyAuthResponse(response);
      sessionStatus = 'ready';
      toast = pendingRoundBook ? 'ROUND READY TO RESUME' : 'RGS CONNECTED';
      toastTone = pendingRoundBook ? 'red' : 'blue';
    } catch (error) {
      sessionStatus = 'error';
      toast = error instanceof RgsError && error.code === 'ERR_IS' ? 'SESSION EXPIRED' : 'RGS AUTH FAILED';
      toastTone = 'red';
    }
  }

  async function startReplay() {
    if (!replayBook || playing || !['ready', 'complete'].includes(replayStatus)) return;
    eventEmitter.broadcast({ type: 'audioUnlock' });
    introVisible = false;
    playing = true;
    replayStatus = 'playing';
    awaitingBonusSpin = false;
    currentWinUnits = 0;
    totalWinUnits = 0;
    winLevel = 0;
    freeSpinLabel = '';
    multiplierLabel = '';
    toast = 'REPLAY PLAYING';
    toastTone = 'blue';
    try {
      await waitForStage();
      await playBookEvents(replayBook, { autoContinueGates: true });
      replayStatus = 'complete';
      toast = replayPayoutUnits > 0 ? `REPLAY RESULT ${display(replayPayoutUnits)}` : 'REPLAY COMPLETE';
      toastTone = replayPayoutUnits > 0 ? 'red' : 'blue';
    } catch {
      replayStatus = 'error';
      toast = 'REPLAY FAILED';
      toastTone = 'red';
    } finally {
      awaitingBonusSpin = false;
      playing = false;
    }
  }

  function eventProgressKey(book: Book, event: BookEvent) {
    return `${book.id}:${event.index}:${event.type}`;
  }

  async function playRgsRound(mode: BookMode) {
    if (!rgsClient) throw new Error('RGS client unavailable');
    let book = pendingRoundBook;
    let roundOpened = Boolean(book);
    pendingRoundBook = null;
    if (!book) {
      const response = await rgsClient.play(betUnits, mode);
      balanceUnits = Number(response.balance.amount) || balanceUnits;
      currency = response.balance.currency || currency;
      book = extractBookFromRound(response.round);
      roundOpened = true;
    }
    if (!book) throw new Error('RGS round did not include playable game state');
    try {
      await playBookEvents(book, {
        onEventProgress: (event) => rgsClient?.saveEvent(eventProgressKey(book, event)).catch(() => undefined)
      });
    } finally {
      if (roundOpened) {
        const endResponse = await rgsClient.endRound();
        balanceUnits = Number(endResponse.balance.amount) || balanceUnits;
        currency = endResponse.balance.currency || currency;
      }
    }
  }

  async function playLocalRound(mode: BookMode) {
    balanceUnits = Math.max(0, balanceUnits - modeCostUnits(mode));
    const book = await pickBook(mode);
    await playBookEvents(book);
  }

  async function play(mode: BookMode = 'base') {
    if (playing) return;
    if (sessionStatus === 'loading') {
      toast = 'CONNECTING TO RGS';
      toastTone = 'blue';
      return;
    }
    if (sessionStatus === 'error') {
      toast = 'SESSION UNAVAILABLE';
      toastTone = 'red';
      return;
    }
    eventEmitter.broadcast({ type: 'audioUnlock' });
    introVisible = false;
    playing = true;
    awaitingBonusSpin = false;
    currentWinUnits = 0;
    totalWinUnits = 0;
    winLevel = 0;
    freeSpinLabel = '';
    multiplierLabel = '';
    const costUnits = pendingRoundBook && runtimeMode === 'rgs' ? 0 : modeCostUnits(mode);
    if (balanceUnits < costUnits) {
      toast = 'INSUFFICIENT BALANCE';
      toastTone = 'red';
      playing = false;
      return;
    }
    try {
      await waitForStage();
      if (runtimeMode === 'rgs') {
        await playRgsRound(mode);
      } else {
        await playLocalRound(mode);
      }
    } catch (error) {
      toast = error instanceof RgsError ? `RGS ${error.code}` : 'ROUND FAILED';
      toastTone = 'red';
    } finally {
      awaitingBonusSpin = false;
      playing = false;
    }
  }

  onMount(() => {
    resize();
    void initialiseRgs();
    void stage?.ready().then(() => {
      stageReady = true;
    });
    window.addEventListener('resize', resize);
    window.addEventListener('orientationchange', resize);
    window.visualViewport?.addEventListener('resize', resize);
    window.visualViewport?.addEventListener('scroll', resize);
    const keydown = (event: KeyboardEvent) => {
      if (introVisible && (event.code === 'Space' || event.code === 'Enter')) {
        event.preventDefault();
        enterGame();
        return;
      }
      if (buyMenuOpen) {
        if (event.code === 'Escape') {
          buyMenuOpen = false;
        }
        return;
      }
      if (event.code === 'Space') {
        event.preventDefault();
        handleSpinClick();
      }
      if (event.code === 'Escape') {
        infoOpen = false;
      }
    };
    window.addEventListener('keydown', keydown);
    unsubscribe = eventEmitter.subscribeOnMount({
      winCounter: (event) => {
        const paid = scaledWinUnits(event.amount, activeBetUnits);
        currentWinUnits = paid;
        totalWinUnits += paid;
        if (runtimeMode === 'local') balanceUnits += paid;
        winLevel = event.level;
      },
      totalWinUpdate: (event) => {
        totalWinUnits = scaledWinUnits(event.amount, activeBetUnits);
      },
      finalWin: (event) => {
        totalWinUnits = scaledWinUnits(event.amount, activeBetUnits);
        if (event.amount > 0) {
          toast = `${term('PAID', 'WON')} ${display(totalWinUnits)}`;
          toastTone = event.amount > 75 ? 'red' : 'amber';
        }
      },
      escalationUpdate: (event) => {
        escalationLevel = event.level;
      },
      freeSpinUpdate: (event) => {
        multiplierLabel = event.multiplier ? `x${event.multiplier}` : multiplierLabel;
        freeSpinLabel = `${event.current}/${event.total} WARPATH SPINS${event.multiplier ? ` · x${event.multiplier}` : ''}`;
      },
      featureIntro: (event) => {
        multiplierLabel = event.multiplierStart ? `x${event.multiplierStart}` : '';
        toast = event.source === 'buy'
          ? `${event.triggerCount} FLARES HIT · ${event.spins} WARPATH SPINS`
          : `FLARE BONUS ${event.spins} SPINS · START ${multiplierLabel}`;
        toastTone = 'red';
      },
      bonusSpinGate: (event) => {
        awaitingBonusSpin = true;
        multiplierLabel = event.multiplier ? `x${event.multiplier}` : multiplierLabel;
        freeSpinLabel = `${event.current}/${event.total} WARPATH SPINS${event.multiplier ? ` · x${event.multiplier}` : ''}`;
        toast = event.label ?? `CLICK SPIN FOR WARPATH SPIN ${event.current}/${event.total}`;
        toastTone = 'red';
      },
      globalMultiplier: (event) => {
        multiplierLabel = `x${event.multiplier}`;
      },
      toast: (event) => {
        toast = event.message;
        toastTone = event.tone ?? 'amber';
      }
    });
    return () => {
      window.removeEventListener('resize', resize);
      window.removeEventListener('orientationchange', resize);
      window.visualViewport?.removeEventListener('resize', resize);
      window.visualViewport?.removeEventListener('scroll', resize);
      window.removeEventListener('keydown', keydown);
      if (resizeFrame) window.cancelAnimationFrame(resizeFrame);
    };
  });

  onDestroy(() => {
    unsubscribe();
  });
</script>

<div class="viewport" style:width={`${viewportWidth}px`} style:height={`${viewportHeight}px`}>
  <div class="game-shell" style:transform={`translate3d(-50%, -50%, 0) scale(${scale})`}>
    <WarpathAudio />
    <PixiStage bind:this={stage} />

    <div class="grain"></div>
    {#if introVisible}
      <section class="intro-screen" aria-label="Warpath Reels loading screen">
        <img src="/assets/ui/splash_warpath_reels.png" alt="Warpath Reels" />
        <div class="intro-vignette"></div>
        <div class="intro-panel">
          <button
            class="intro-button"
            disabled={replayMode && !['ready', 'complete'].includes(replayStatus)}
            aria-label={replayMode ? 'Play replay' : 'Enter Warpath'}
            on:click={enterGame}
          ></button>
          <div class="loadbar" class:ready={stageReady}><b></b></div>
        </div>
      </section>
    {/if}

    <header class="title-block">
      <img class="title-logo" src="/assets/ui/logo_warpath_reels_crisp.png" alt="Warpath Reels" />
    </header>

    <section class="meter">
      <span>WARPATH ESCALATION</span>
      <div class="pips">
        {#each [1, 2, 3, 4, 5] as level}
          <b class:active={level <= escalationLevel}>{level}</b>
        {/each}
      </div>
    </section>

    <section class="status" class:red={toastTone === 'red'} class:blue={toastTone === 'blue'}>
      {toast}
    </section>

    {#if replayMode}
      <section class="replay-panel" aria-label="Replay details">
        <span>REPLAY MODE</span>
        <strong>{replayStatus === 'loading' ? 'LOADING EVENT' : replayStatus === 'error' ? 'EVENT UNAVAILABLE' : replayModeName.toUpperCase()}</strong>
        <em>{term('BET', 'PLAY')} {display(replayBaseBetUnits)} · {term('REAL COST', 'REAL PLAY')} {display(replayRealCostUnits)}</em>
        <em>RESULT {display(replayPayoutUnits)}</em>
        <button disabled={!['ready', 'complete'].includes(replayStatus) || playing} on:click={startReplay}>
          {replayStatus === 'complete' ? 'PLAY AGAIN' : 'PLAY REPLAY'}
        </button>
      </section>
    {/if}

    <button class="sound-toggle" on:click={toggleSound} aria-label={soundOn ? 'Mute sound' : 'Unmute sound'}>
      {soundOn ? 'SOUND ON' : 'SOUND OFF'}
    </button>

    {#if freeSpinLabel}
      <section class="free-spins">{freeSpinLabel}</section>
    {/if}

    {#if multiplierLabel}
      <section class="multiplier-stamp">GLOBAL {multiplierLabel}</section>
    {/if}

    {#if currentWinUnits > 0 || totalWinUnits > 0}
      <section class="win-panel level-{winLevel}">
        <span>WIN</span>
        <strong>{display(currentWinUnits)}</strong>
        <em>TOTAL {display(totalWinUnits)}</em>
      </section>
    {/if}

    <footer class="controls">
      <div class="readout">
        <span>BALANCE</span>
        <strong>{display(balanceUnits)}</strong>
      </div>
      <div class="bet">
        <button on:click={() => adjustBet(-1)} disabled={playing || betLevels.length <= 1}>-</button>
        <div><span>{term('BET', 'PLAY')}</span><strong>{display(betUnits)}</strong></div>
        <button on:click={() => adjustBet(1)} disabled={playing || betLevels.length <= 1}>+</button>
      </div>
      <button
        class="spin"
        class:spinning={playing && !awaitingBonusSpin}
        class:awaiting={awaitingBonusSpin}
        disabled={playDisabled}
        aria-label={awaitingBonusSpin ? 'Next Warpath spin' : playing ? 'Spinning' : 'Spin'}
        on:click={handleSpinClick}
      ></button>
    </footer>

    <section class="bonus-launcher" aria-label={term('Buy Warpath Spins', 'Get Warpath Spins')}>
      <button class="bonus-button" disabled={playing || playDisabled} aria-label={term('Open bonus buy menu', 'Open feature menu')} on:click={openBonusMenu}>
        <img src="/assets/ui/bonus_missile_button.png" alt="" />
      </button>
    </section>

    {#if buyMenuOpen}
      <button class="modal-scrim" aria-label={term('Close buy feature dialog', 'Close feature dialog')} on:click={closeBuyMenu}></button>
      <dialog class="buy-modal" open aria-modal="true" aria-label={term('Buy Warpath Spins details', 'Warpath Spins feature details')}>
        <div class="rules-header">
          <div>
            <span>{term('BUY FEATURE', 'GET FEATURE')}</span>
            <h2>{selectedBuyOption.spins} WARPATH SPINS</h2>
          </div>
          <button class="rules-close" on:click={closeBuyMenu}>CLOSE</button>
        </div>

        <div class="buy-modal-body">
          <div class="buy-modal-left">
            <div class="buy-modal-preview">
              <img src={selectedBuyOption.asset} alt="" />
              <strong>{display(selectedBuyCostUnits)}</strong>
            </div>
            <div class="buy-option-grid" aria-label={term('Choose Warpath Spins buy feature', 'Choose Warpath Spins feature')}>
              {#each BUY_OPTIONS as option}
                <button
                  class="buy-option-card"
                  class:active={option.mode === selectedBuyMode}
                  on:click={() => selectBuyOption(option)}
                  aria-label={`Select ${option.spins} Warpath Spins`}
                >
                  <span>{option.spins}</span>
                  <em>{display(Math.round(betUnits * BOOK_MODE_COSTS[option.mode]))}</em>
                </button>
              {/each}
            </div>
          </div>
          <div class="buy-context-cards">
            <article>
              <b>FORCED TRIGGER</b>
              <span>{selectedBuyOption.scatters} Warpath Flare scatters land first, then the feature starts.</span>
            </article>
            <article>
              <b>PLAYER-CONTROLLED SPINS</b>
              <span>Each Warpath Spin waits for your click. The game does not auto-rush the bonus.</span>
            </article>
            <article>
              <b>STICKY WILD REELS</b>
              <span>Red soldier wild reels can lock during the feature. Cascades increase the multiplier.</span>
            </article>
          </div>
        </div>

        <div class="buy-actions">
          <button class="rules-close" on:click={closeBuyMenu}>BACK</button>
          <button class="buy-confirm" disabled={playing || playDisabled || balanceUnits < selectedBuyCostUnits} on:click={confirmBuyContext}>
            {term('BUY', 'PLAY FOR')} {display(selectedBuyCostUnits)}
          </button>
        </div>
      </dialog>
    {/if}

    <button
      class="info-toggle"
      on:click={() => (infoOpen = !infoOpen)}
      aria-label="Open paytable and rules"
      aria-expanded={infoOpen}
      aria-controls="rules-panel"
    >
      <span aria-hidden="true">i</span>
    </button>

    {#if infoOpen}
      <div id="rules-panel" class="rules-panel" role="dialog" aria-modal="true" aria-label="Warpath Reels paytable and rules">
        <div class="rules-header">
          <div>
            <span>GAME INFO</span>
            <h2>PAYTABLE & RULES</h2>
          </div>
          <button class="rules-close" on:click={() => (infoOpen = false)}>CLOSE</button>
        </div>

        <div class="rule-cards">
          <article>
            <b>RED SOLDIER WILD</b>
            <span>The red soldier portrait is WILD only. It substitutes on reels 2-5 and can expand to cover the full reel.</span>
          </article>
          <article>
            <b>WARPATH FLARE SCATTER</b>
            <span>The flare canister is SCATTER only. 3, 4, or 5 scatters award 8, 10, or 12 Warpath Spins.</span>
          </article>
          <article>
            <b>WARPATH SPINS</b>
            <span>Bonus spins wait for your click. Wild reels lock sticky, remain on later spins, and cascades raise the multiplier.</span>
          </article>
        </div>

        <div class="rules-meta">{TOTAL_WAYS} ways · wins left-to-right · 6 reels · rows 2-3-3-3-3-2</div>

        <section class="rules-section">
          <h3>MODES, RTP, AND LIMITS</h3>
          <table class="mode-table">
            <thead>
              <tr>
                <th>Mode</th>
                <th>{term('Cost', 'Play Amount')}</th>
                <th>RTP</th>
                <th>Maximum Win</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Base</td>
                <td>1x</td>
                <td>96.00%</td>
                <td>5,000x</td>
              </tr>
              <tr>
                <td>8 Warpath Spins</td>
                <td>80x</td>
                <td>96.00%</td>
                <td>5,000x</td>
              </tr>
              <tr>
                <td>10 Warpath Spins</td>
                <td>100x</td>
                <td>96.00%</td>
                <td>5,000x</td>
              </tr>
              <tr>
                <td>12 Warpath Spins</td>
                <td>120x</td>
                <td>96.00%</td>
                <td>5,000x</td>
              </tr>
            </tbody>
          </table>
        </section>

        <section class="rules-section">
          <h3>FEATURE RULES</h3>
          <div class="rules-copy">
            <p>3 Warpath Flare scatters award 8 Warpath Spins. 4 scatters award 10 Warpath Spins. 5 scatters award 12 Warpath Spins.</p>
            <p>The Warpath Spins feature starts at x2 when triggered from the base game. Direct feature modes start at x3, x4, or x5 for the 8, 10, or 12 spin modes. Every cascade raises the global multiplier by +1.</p>
            <p>Sticky wild reels can remain locked during Warpath Spins. The final round result and all animations are dictated by the RGS event data.</p>
          </div>
        </section>

        <section class="rules-section">
          <h3>UI GUIDE</h3>
          <div class="ui-guide">
            <span><b>Spin</b> starts a base round or advances a player-controlled Warpath Spin.</span>
            <span><b>+ / -</b> changes the play amount using RGS-approved levels.</span>
            <span><b>Bonus</b> opens a confirmation window for higher-{term('cost', 'play amount')} Warpath Spin modes.</span>
            <span><b>Sound</b> enables or disables audio.</span>
            <span><b>Info</b> opens these game rules and payout tables.</span>
            <span><b>Spacebar</b> is bound to the spin button.</span>
          </div>
        </section>

        <section class="rules-section">
          <h3>SYMBOL PAYOUTS</h3>
        </section>

        <table class="paytable">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>3</th>
              <th>4</th>
              <th>5</th>
              <th>6</th>
            </tr>
          </thead>
          <tbody>
            {#each PAYTABLE_ROWS as row}
              <tr>
                <td>{row.symbol}</td>
                {#each row.values as value}
                  <td>{value}x</td>
                {/each}
              </tr>
            {/each}
          </tbody>
        </table>

        <section class="rules-section disclaimer">
          <h3>DISCLAIMER</h3>
          <p>Malfunction voids all wins and plays. A consistent internet connection is required. In the event of a disconnection, reload the game to finish any uncompleted rounds. The expected return is calculated over many plays. The game display is not representative of any physical device and is for illustrative purposes only. Winnings are settled according to the amount received from the Remote Game Server and not from events within the web browser. TM and © 2026 Stake Engine.</p>
        </section>
      </div>
    {/if}
  </div>
</div>

<style>
  .viewport {
    position: fixed;
    inset: 0;
    width: 100dvw;
    height: 100dvh;
    overflow: hidden;
    background: radial-gradient(circle at 50% 40%, #26100c 0, #050403 55%, #000 100%);
    touch-action: manipulation;
  }

  .game-shell {
    position: absolute;
    left: 50%;
    top: 50%;
    width: 1920px;
    height: 1080px;
    transform-origin: center;
    overflow: hidden;
    background: #050403;
  }

  .grain {
    position: absolute;
    inset: 0;
    pointer-events: none;
    opacity: 0.18;
    mix-blend-mode: overlay;
    background-image:
      linear-gradient(90deg, rgba(255,255,255,.04) 1px, transparent 1px),
      linear-gradient(rgba(255,255,255,.03) 1px, transparent 1px);
    background-size: 7px 11px;
    animation: drift 1.3s steps(2) infinite;
  }

  .title-block {
    position: absolute;
    top: 24px;
    left: 50%;
    width: 680px;
    transform: translateX(-50%);
    text-align: center;
    pointer-events: none;
  }

  .title-logo {
    width: 100%;
    height: auto;
    display: block;
    filter:
      drop-shadow(0 8px 0 rgba(0, 0, 0, .92))
      drop-shadow(0 0 34px rgba(180, 28, 24, .5));
  }

  .meter {
    position: absolute;
    left: 52px;
    top: 170px;
    padding: 16px 18px;
    background: rgba(10, 8, 7, 0.78);
    border: 2px solid rgba(139, 50, 36, 0.85);
    box-shadow: 0 0 32px rgba(130, 26, 18, 0.24);
  }

  .meter span {
    display: block;
    color: #8d7c6e;
    font-size: 15px;
    letter-spacing: 4px;
    margin-bottom: 10px;
    font-weight: 900;
  }

  .pips {
    display: flex;
    gap: 9px;
  }

  .pips b {
    width: 42px;
    height: 42px;
    display: grid;
    place-items: center;
    color: #3d332e;
    background: #14100e;
    clip-path: polygon(14% 0, 100% 0, 86% 100%, 0% 100%);
    border: 1px solid #3f332e;
  }

  .pips b.active {
    color: #0c0504;
    background: linear-gradient(#ff8338, #a82418);
    box-shadow: 0 0 22px rgba(255, 77, 42, 0.7);
  }

  .status,
  .free-spins {
    position: absolute;
    right: 58px;
    top: 170px;
    min-width: 330px;
    padding: 18px 24px;
    color: #ffad5f;
    font-size: 30px;
    font-weight: 900;
    letter-spacing: 3px;
    text-align: center;
    background: rgba(12, 9, 8, 0.78);
    border: 2px solid rgba(180, 82, 38, 0.75);
    text-shadow: 0 3px 0 #000;
  }

  .status.red,
  .free-spins.total-war {
    color: #ff3d35;
    border-color: #cc2018;
    box-shadow: 0 0 42px rgba(200, 0, 0, 0.42);
  }

  .status.blue {
    color: #84dbff;
    border-color: #4ac6ff;
  }

  .replay-panel {
    position: absolute;
    left: 58px;
    top: 306px;
    z-index: 12;
    width: 382px;
    padding: 18px 20px;
    color: #e9d8c2;
    background: rgba(8, 7, 6, .84);
    border: 2px solid rgba(92, 180, 205, .65);
    box-shadow: 0 0 32px rgba(31, 151, 190, .24), inset 0 0 28px rgba(42, 12, 8, .46);
  }

  .replay-panel span,
  .replay-panel em {
    display: block;
    font-weight: 900;
    letter-spacing: 2px;
  }

  .replay-panel span {
    color: #84dbff;
    font-size: 13px;
  }

  .replay-panel strong {
    display: block;
    margin: 6px 0 12px;
    color: #fff0d7;
    font-size: 28px;
    letter-spacing: 3px;
    text-shadow: 0 3px 0 #000;
  }

  .replay-panel em {
    margin-top: 5px;
    color: #bca58e;
    font-size: 14px;
    font-style: normal;
  }

  .replay-panel button {
    width: 100%;
    margin-top: 16px;
    padding: 14px 16px;
    color: #071014;
    font-size: 18px;
    font-weight: 1000;
    letter-spacing: 3px;
    background: linear-gradient(#93efff, #1f95b5);
    border: 2px solid rgba(230, 255, 255, .72);
    box-shadow: 0 0 24px rgba(85, 220, 255, .32);
  }

  .sound-toggle {
    position: absolute;
    left: 130px;
    bottom: 176px;
    min-width: 132px;
    height: 62px;
    color: #f1dfc3;
    font-size: 13px;
    letter-spacing: 2px;
    background: radial-gradient(circle at 38% 32%, rgba(255, 204, 130, .24), rgba(55, 18, 14, .92) 58%, rgba(9, 6, 5, .96));
    border: 2px solid rgba(226, 151, 88, .56);
    box-shadow: 0 0 22px rgba(143, 40, 24, .3), inset 0 2px rgba(255,255,255,.12);
  }

  .free-spins {
    top: 252px;
    color: #d9cfc2;
    font-size: 24px;
  }

  .multiplier-stamp {
    position: absolute;
    right: 74px;
    top: 326px;
    padding: 12px 22px;
    color: #ff4657;
    font-size: 34px;
    font-weight: 1000;
    letter-spacing: 4px;
    text-shadow: 0 4px 0 #000, 0 0 28px rgba(255, 42, 68, .55);
    background: rgba(24, 6, 7, .76);
    border: 3px solid rgba(199, 42, 61, .72);
    transform: rotate(-1.5deg);
    animation: multiplier-pop .22s ease-out;
  }

  .win-panel {
    position: absolute;
    left: 50%;
    bottom: 178px;
    transform: translateX(-50%) rotate(-1deg);
    min-width: 460px;
    padding: 22px 46px;
    text-align: center;
    background: linear-gradient(100deg, rgba(48, 12, 8, .94), rgba(130, 35, 20, .92));
    border: 4px solid rgba(255, 110, 48, .7);
    box-shadow: 0 0 55px rgba(180, 30, 18, .55);
    animation: stamp 0.22s ease-out;
  }

  .win-panel span,
  .win-panel em {
    display: block;
    color: #21110b;
    font-weight: 900;
    letter-spacing: 5px;
  }

  .win-panel strong {
    display: block;
    color: #ffe4c8;
    font-size: 74px;
    line-height: 1;
    text-shadow: 0 5px 0 #000;
  }

  .controls {
    position: absolute;
    left: 50%;
    bottom: 34px;
    transform: translateX(-50%);
    display: flex;
    align-items: center;
    gap: 22px;
    padding: 18px 26px;
    background: rgba(8, 7, 6, .9);
    border: 2px solid rgba(100, 70, 52, .9);
    box-shadow: 0 0 44px rgba(0, 0, 0, .7);
  }

  .readout,
  .bet {
    min-width: 150px;
    color: #d1c5b6;
    font-weight: 900;
  }

  .readout span,
  .bet span {
    display: block;
    color: #74675d;
    font-size: 12px;
    letter-spacing: 3px;
  }

  .readout strong,
  .bet strong {
    font-size: 26px;
  }

  .bet {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
  }

  button {
    cursor: pointer;
    border: 0;
    border-radius: 0;
    color: #130805;
    font-weight: 1000;
    letter-spacing: 2px;
    background: linear-gradient(#ff8c3b, #a92817);
    box-shadow: inset 0 2px rgba(255,255,255,.18), 0 5px 0 #3b0f09;
    transition: transform .08s ease, filter .15s ease;
  }

  button:disabled {
    cursor: not-allowed;
    filter: grayscale(1) brightness(.55);
  }

  button:not(:disabled):active {
    transform: translateY(4px);
    box-shadow: inset 0 2px rgba(255,255,255,.12), 0 1px 0 #3b0f09;
  }

  .bet button {
    width: 42px;
    height: 42px;
    font-size: 30px;
  }

  .spin {
    width: 156px;
    height: 80px;
    position: relative;
    overflow: visible;
    color: #1a0905;
    font-size: 0;
    border: 0;
    text-shadow: none;
    background: url('/assets/ui/spin_button_idle_clean.png') center / contain no-repeat;
    box-shadow: none;
    filter: drop-shadow(0 8px 0 rgba(0, 0, 0, .58));
  }

  .spin::after {
    content: none;
  }

  .spin.spinning {
    background: url('/assets/ui/spin_button_firing.png') center / contain no-repeat;
  }

  .spin.awaiting {
    background: url('/assets/ui/spin_button_next.png') center / contain no-repeat;
    filter: saturate(1.25) brightness(1.1) drop-shadow(0 0 28px rgba(255, 94, 40, .72));
    animation: next-pulse .72s ease-in-out infinite alternate;
  }

  .spin:not(:disabled):active {
    transform: translateY(3px) scale(.98);
    box-shadow: none;
  }

  .bonus-launcher {
    position: absolute;
    right: 52px;
    bottom: 46px;
    width: 238px;
    pointer-events: auto;
  }

  .bonus-button {
    width: 238px;
    height: 88px;
    padding: 0;
    overflow: hidden;
    background: transparent;
    border: 0;
    box-shadow: none;
    filter: drop-shadow(0 9px 0 rgba(0,0,0,.55));
  }

  .bonus-button img {
    width: 100%;
    height: 100%;
    display: block;
    object-fit: contain;
  }

  .bonus-button:not(:disabled):hover {
    filter: brightness(1.13) saturate(1.08);
  }

  .bonus-button:not(:disabled):active {
    transform: translateY(4px);
    box-shadow: none;
  }

  .modal-scrim {
    position: absolute;
    inset: 0;
    z-index: 14;
    background: rgba(0, 0, 0, .62);
    border: 0;
    box-shadow: none;
    cursor: pointer;
  }

  button.modal-scrim:not(:disabled):active {
    transform: none;
    box-shadow: none;
  }

  .buy-modal {
    position: absolute;
    left: 50%;
    top: 50%;
    z-index: 15;
    width: 760px;
    margin: 0;
    transform: translate(-50%, -50%);
    padding: 26px;
    color: #d8c8b8;
    background:
      linear-gradient(130deg, rgba(16, 11, 9, .97), rgba(48, 15, 12, .96)),
      url('/assets/ui/paytable_bg.png') center / cover no-repeat;
    border: 4px solid rgba(176, 64, 36, .82);
    box-shadow: 0 0 86px rgba(172, 28, 19, .54);
    animation: rules-in .18s ease-out;
  }

  .buy-modal-body {
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 22px;
    align-items: stretch;
  }

  .buy-modal-left {
    display: grid;
    gap: 14px;
    align-content: start;
  }

  .buy-modal-preview {
    display: grid;
    gap: 14px;
    align-content: start;
  }

  .buy-modal-preview img {
    width: 260px;
    height: 132px;
    display: block;
    object-fit: cover;
    border: 2px solid rgba(255, 185, 106, .36);
    box-shadow: 0 0 28px rgba(180, 30, 18, .28);
  }

  .buy-modal-preview strong {
    display: block;
    padding: 14px 16px;
    color: #ffdfb8;
    font-size: 42px;
    line-height: 1;
    text-align: center;
    background: rgba(6, 5, 4, .76);
    border: 2px solid rgba(154, 57, 32, .7);
    text-shadow: 0 4px 0 #000;
  }

  .buy-option-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
  }

  .buy-option-card {
    min-height: 66px;
    padding: 8px 6px;
    color: #d9c7b2;
    background: rgba(8, 6, 5, .78);
    border: 2px solid rgba(112, 54, 37, .68);
    box-shadow: inset 0 2px rgba(255,255,255,.08), 0 4px 0 rgba(35, 11, 8, .9);
  }

  .buy-option-card.active {
    color: #fff0dc;
    border-color: rgba(244, 92, 46, .86);
    background: linear-gradient(180deg, rgba(113, 25, 17, .94), rgba(28, 8, 6, .92));
    box-shadow: 0 0 24px rgba(230, 55, 27, .28), inset 0 2px rgba(255,255,255,.12);
  }

  .buy-option-card span,
  .buy-option-card em {
    display: block;
  }

  .buy-option-card span {
    font-size: 28px;
    line-height: 1;
  }

  .buy-option-card em {
    color: #b99e85;
    font-size: 13px;
    font-style: normal;
    letter-spacing: 1px;
    margin-top: 5px;
  }

  .buy-context-cards {
    display: grid;
    gap: 12px;
  }

  .buy-context-cards article {
    padding: 15px 16px;
    background: rgba(6, 5, 4, .66);
    border: 1px solid rgba(126, 62, 38, .62);
  }

  .buy-context-cards b,
  .buy-context-cards span {
    display: block;
  }

  .buy-context-cards b {
    color: #ff7b42;
    font-size: 15px;
    letter-spacing: 3px;
    margin-bottom: 7px;
  }

  .buy-context-cards span {
    color: #cdbdad;
    font-size: 17px;
    line-height: 1.35;
  }

  .buy-actions {
    display: flex;
    justify-content: flex-end;
    gap: 14px;
    margin-top: 24px;
  }

  .buy-confirm {
    min-width: 210px;
    min-height: 54px;
    color: #160804;
    font-size: 20px;
    background:
      linear-gradient(rgba(255, 226, 170, .18), rgba(55, 5, 5, .18)),
      url('/assets/ui/spin_button_idle.png') center / cover no-repeat,
      linear-gradient(#f49a4c, #a92317);
    border: 2px solid rgba(255, 185, 106, .42);
  }

  .info-toggle {
    position: absolute;
    left: 52px;
    bottom: 176px;
    width: 62px;
    height: 62px;
    display: grid;
    place-items: center;
    color: #f1dfc3;
    font-size: 36px;
    font-family: Georgia, serif;
    font-style: italic;
    line-height: 1;
    background: radial-gradient(circle at 38% 32%, rgba(255, 204, 130, .36), rgba(84, 18, 12, .92) 58%, rgba(9, 6, 5, .96));
    border: 2px solid rgba(226, 151, 88, .7);
    border-radius: 50%;
    box-shadow: 0 0 22px rgba(143, 40, 24, .38), inset 0 2px rgba(255,255,255,.16);
  }

  .info-toggle span {
    transform: translateY(-1px);
    text-shadow: 0 3px 0 #000;
  }

	  .rules-panel {
	    position: absolute;
	    left: 50%;
	    top: 50%;
	    z-index: 16;
	    width: 920px;
	    max-height: 850px;
	    transform: translate(-50%, -50%);
	    padding: 28px;
	    overflow-y: auto;
	    color: #d8c8b8;
	    background:
	      linear-gradient(130deg, rgba(16, 11, 9, .97), rgba(46, 16, 12, .96)),
	      url('/assets/ui/paytable_bg.png') center / cover no-repeat;
	    border: 4px solid rgba(176, 64, 36, .82);
	    box-shadow: 0 0 0 9999px rgba(0,0,0,.58), 0 0 80px rgba(154, 32, 22, .46);
	    animation: rules-in .18s ease-out;
	  }

	  .rules-header {
	    display: flex;
	    align-items: center;
	    justify-content: space-between;
	    gap: 24px;
	    margin-bottom: 20px;
	  }

	  .rules-header span {
	    display: block;
	    color: #b06c4d;
	    font-size: 14px;
	    font-weight: 1000;
	    letter-spacing: 5px;
	  }

	  .rules-header h2 {
	    margin: 0;
	    color: #f0dfcb;
	    font-size: 48px;
	    letter-spacing: 6px;
	    text-shadow: 0 4px 0 #000;
	  }

	  .rules-close {
	    width: 132px;
	    height: 48px;
	    font-size: 16px;
	  }

	  .rule-cards {
	    display: grid;
	    grid-template-columns: repeat(3, 1fr);
	    gap: 14px;
	    margin-bottom: 18px;
	  }

	  .rule-cards article {
	    min-height: 128px;
	    padding: 16px;
	    background: rgba(7, 6, 5, .78);
	    border: 1px solid rgba(165, 88, 48, .54);
	    box-shadow: inset 0 0 22px rgba(0, 0, 0, .52);
	  }

	  .rule-cards b {
	    display: block;
	    margin-bottom: 8px;
	    color: #ffb36d;
	    font-size: 17px;
	    letter-spacing: 3px;
	  }

	  .rule-cards span {
	    color: #c2b4a7;
	    font-size: 18px;
	    line-height: 1.25;
	  }

	  .rules-meta {
	    margin-bottom: 12px;
	    color: #9e8d7e;
	    font-size: 16px;
	    font-weight: 900;
	    letter-spacing: 3px;
	    text-transform: uppercase;
	  }

	  .rules-section {
	    margin: 18px 0;
	  }

	  .rules-section h3 {
	    margin: 0 0 10px;
	    color: #ff9c5a;
	    font-size: 18px;
	    font-weight: 1000;
	    letter-spacing: 4px;
	  }

	  .rules-copy {
	    display: grid;
	    gap: 8px;
	    padding: 16px;
	    background: rgba(6, 5, 4, .68);
	    border: 1px solid rgba(160, 74, 42, .42);
	  }

	  .rules-copy p,
	  .disclaimer p {
	    margin: 0;
	    color: #c6b7a8;
	    font-size: 17px;
	    line-height: 1.35;
	  }

	  .mode-table {
	    width: 100%;
	    border-collapse: collapse;
	    background: rgba(5, 4, 4, .72);
	    border: 1px solid rgba(160, 74, 42, .5);
	  }

	  .mode-table th,
	  .mode-table td {
	    padding: 9px 12px;
	    border-bottom: 1px solid rgba(255, 255, 255, .08);
	    color: #d3b58f;
	    font-size: 16px;
	    font-weight: 900;
	    text-align: right;
	  }

	  .mode-table th:first-child,
	  .mode-table td:first-child {
	    text-align: left;
	  }

	  .mode-table th {
	    color: #ff9c5a;
	    letter-spacing: 2px;
	    background: rgba(85, 26, 15, .72);
	  }

	  .ui-guide {
	    display: grid;
	    grid-template-columns: repeat(2, 1fr);
	    gap: 10px;
	  }

	  .ui-guide span {
	    padding: 12px 14px;
	    color: #c2b4a7;
	    font-size: 16px;
	    line-height: 1.28;
	    background: rgba(7, 6, 5, .72);
	    border: 1px solid rgba(165, 88, 48, .38);
	  }

	  .ui-guide b {
	    color: #ffb36d;
	  }

	  .disclaimer {
	    padding: 16px;
	    background: rgba(4, 3, 3, .75);
	    border: 1px solid rgba(160, 74, 42, .46);
	  }

	  .paytable {
	    width: 100%;
	    border-collapse: collapse;
	    overflow: hidden;
	    background: rgba(5, 4, 4, .7);
	    border: 1px solid rgba(160, 74, 42, .5);
	  }

	  .paytable th,
	  .paytable td {
	    padding: 10px 13px;
	    border-bottom: 1px solid rgba(255, 255, 255, .08);
	    text-align: right;
	    font-size: 18px;
	    font-weight: 900;
	  }

	  .paytable th:first-child,
	  .paytable td:first-child {
	    text-align: left;
	  }

	  .paytable th {
	    color: #ff9c5a;
	    letter-spacing: 3px;
	    background: rgba(85, 26, 15, .72);
	  }

	  .paytable td:first-child {
	    color: #eee0ce;
	    letter-spacing: 1px;
	  }

	  .paytable td:not(:first-child) {
	    color: #d3b58f;
	  }

  .intro-screen {
    position: absolute;
    inset: 0;
    z-index: 20;
    display: grid;
    place-items: center;
    overflow: hidden;
    background: #050403;
  }

  .intro-screen img {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    animation: intro-drift 7s ease-in-out infinite alternate;
  }

  .intro-vignette {
    position: absolute;
    inset: 0;
    background:
      radial-gradient(circle at 62% 42%, transparent 0 24%, rgba(0,0,0,.22) 42%, rgba(0,0,0,.78) 100%),
      linear-gradient(180deg, rgba(0,0,0,.1), rgba(0,0,0,.62));
    pointer-events: none;
  }

  .intro-panel {
    position: absolute;
    left: 112px;
    bottom: 92px;
    width: 560px;
    padding: 24px;
    background: rgba(8, 5, 4, .72);
    border: 3px solid rgba(170, 42, 52, .72);
    box-shadow: 0 0 70px rgba(118, 17, 24, .42);
    animation: intro-panel-in .42s ease-out both;
  }

  .intro-button {
    width: 100%;
    height: 82px;
    color: #1d0806;
    font-size: 34px;
    background:
      linear-gradient(rgba(255, 230, 180, .14), rgba(60, 5, 5, .22)),
      url('/assets/ui/spin_button_idle.png') center / cover no-repeat,
      linear-gradient(#ef9d52, #ae241b);
    border: 3px solid rgba(255, 210, 148, .55);
  }

  .loadbar {
    height: 8px;
    margin-top: 16px;
    background: rgba(255,255,255,.12);
    overflow: hidden;
  }

  .loadbar b {
    display: block;
    width: 42%;
    height: 100%;
    background: linear-gradient(90deg, #7a1c22, #ff6b4d, #d2c2aa);
    animation: loading-run 1s ease-in-out infinite alternate;
  }

  .loadbar.ready b {
    width: 100%;
    animation: none;
  }

  @keyframes drift {
    from { transform: translate3d(0, 0, 0); }
    to { transform: translate3d(7px, 11px, 0); }
  }

  @keyframes stamp {
    from { transform: translateX(-50%) scale(1.4) rotate(-5deg); opacity: 0; }
    to { transform: translateX(-50%) scale(1) rotate(-1deg); opacity: 1; }
  }

  @keyframes multiplier-pop {
    from { transform: scale(1.35) rotate(-5deg); opacity: 0; }
    to { transform: scale(1) rotate(-1.5deg); opacity: 1; }
  }

	  @keyframes spin-sheen {
	    0%, 52% { transform: translateX(-130%) rotate(8deg); opacity: 0; }
	    63% { opacity: .75; }
	    82%, 100% { transform: translateX(130%) rotate(8deg); opacity: 0; }
	  }

	  @keyframes next-pulse {
	    from { transform: scale(1); }
	    to { transform: scale(1.04); }
	  }

  @keyframes intro-drift {
    from { transform: scale(1.02) translate3d(-10px, 0, 0); }
    to { transform: scale(1.07) translate3d(16px, -8px, 0); }
  }

	  @keyframes intro-panel-in {
	    from { transform: translateY(26px); opacity: 0; }
	    to { transform: translateY(0); opacity: 1; }
	  }

	  @keyframes rules-in {
	    from { transform: translate(-50%, -48%) scale(.96); opacity: 0; }
	    to { transform: translate(-50%, -50%) scale(1); opacity: 1; }
	  }

	  @keyframes loading-run {
	    from { transform: translateX(-26%); }
    to { transform: translateX(156%); }
  }
</style>
