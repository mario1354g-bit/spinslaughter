import { eventEmitter } from './eventEmitter';
import type { BookEvent } from './types';

export type BookEventContext = { bookEvents: BookEvent[] };
type Handler<T extends BookEvent = BookEvent> = (event: T, context: BookEventContext) => Promise<void> | void;
type HandlerMap = { [K in BookEvent['type']]: Handler<Extract<BookEvent, { type: K }>> };

export const bookEventHandlerMap: HandlerMap = {
  reveal: async (event) => {
    await eventEmitter.broadcastAsync({
      type: 'reelsSpin',
      board: event.board,
      anticipation: event.anticipation,
      mode: event.gameType,
      presentation: event.presentation
    });
  },
  freeSpinUpdate: (event) => {
    eventEmitter.broadcast({ type: 'freeSpinUpdate', current: event.current, total: event.total, mode: event.mode, multiplier: event.multiplier });
  },
  winInfo: async (event) => {
    await eventEmitter.broadcastAsync({ type: 'winHighlight', wins: event.wins, totalWin: event.totalWin });
  },
  setWin: (event) => {
    eventEmitter.broadcast({ type: 'winCounter', amount: event.amount, level: event.winLevel });
  },
  setTotalWin: (event) => {
    eventEmitter.broadcast({ type: 'totalWinUpdate', amount: event.amount });
  },
  finalWin: (event) => {
    eventEmitter.broadcast({ type: 'finalWin', amount: event.amount });
  },
  wincap: (event) => {
    eventEmitter.broadcast({ type: 'toast', message: `MAX WIN ${event.amount}x`, tone: 'red' });
  },
  cascade: async (event) => {
    await eventEmitter.broadcastAsync({
      type: 'cascadeExplode',
      positions: event.removedPositions,
      board: event.board,
      multiplier: event.multiplier,
      step: event.step
    });
  },
  wildMultiplier: async (event) => {
    eventEmitter.broadcast({ type: 'toast', message: `WILD REEL LOCKED x${event.multiplier}`, tone: 'red' });
    await eventEmitter.broadcastAsync({ type: 'wildPulse', multiplier: event.multiplier, wildReels: event.wildReels });
  },
  globalMultiplier: (event) => {
    eventEmitter.broadcast({ type: 'globalMultiplier', multiplier: event.multiplier, label: event.label });
  },
  escalationUpdate: (event) => {
    eventEmitter.broadcast({ type: 'escalationUpdate', level: event.level });
  },
  characterTakeover: async (event) => {
    eventEmitter.broadcast({ type: 'toast', message: 'REEL 6 TAKEOVER', tone: 'red' });
    await eventEmitter.broadcastAsync({ type: 'characterTakeover', symbol: event.symbol, targetReels: event.targetReels });
  },
  warpathSpinsIntro: async (event) => {
    await eventEmitter.broadcastAsync({
      type: 'featureIntro',
      mode: 'warpath',
      spins: event.spins,
      triggerCount: event.triggerCount,
      source: event.source,
      multiplierStart: event.multiplierStart,
      theme: event.theme,
      purchaseCost: event.purchaseCost
    });
  },
  awaitSpinInput: async (event) => {
    eventEmitter.broadcast({
      type: 'bonusSpinGate',
      current: event.current,
      total: event.total,
      mode: event.mode,
      multiplier: event.multiplier,
      label: event.label
    });
    await eventEmitter.waitFor('bonusSpinContinue');
  }
};
