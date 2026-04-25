export type SymbolCell = { name: string };
export type Board = SymbolCell[][];

export interface WinLine {
  symbol: string;
  kind: number;
  ways: number;
  win: number;
  positions: [number, number][];
  meta: Record<string, unknown>;
}

export type BookEvent =
  | { index: number; type: 'reveal'; board: Board; paddingPositions: number[]; gameType: string; anticipation: number[]; presentation?: 'buyTrigger'; stickyWildReels?: number[] }
  | { index: number; type: 'freeSpinUpdate'; current: number; total: number; mode: string; multiplier?: number }
  | { index: number; type: 'winInfo'; totalWin: number; wins: WinLine[] }
  | { index: number; type: 'setWin'; amount: number; winLevel: number }
  | { index: number; type: 'setTotalWin'; amount: number }
  | { index: number; type: 'finalWin'; amount: number }
  | { index: number; type: 'wincap'; amount: number }
  | { index: number; type: 'cascade'; step: number; multiplier: number; board: Board; removedPositions: [number, number][] }
  | { index: number; type: 'wildMultiplier'; multiplier: number; wildReels: number[]; label: string; stickyWildReels?: number[] }
  | { index: number; type: 'escalationUpdate'; level: number }
  | { index: number; type: 'characterTakeover'; symbol: string; targetReels: number[]; label: string }
  | { index: number; type: 'warpathSpinsIntro'; spins: number; triggerCount: number; source?: 'trigger' | 'buy'; mode?: string; multiplierStart?: number; theme?: string; purchaseCost?: number }
  | { index: number; type: 'awaitSpinInput'; current: number; total: number; mode: string; multiplier?: number; label?: string }
  | { index: number; type: 'globalMultiplier'; multiplier: number; label: string };

export interface Book {
  id: number;
  payoutMultiplier: number;
  events: BookEvent[];
  criteria: string;
  baseGameWins: number;
  freeGameWins: number;
}

export type EmitterEvent =
  | { type: 'reelsSpin'; board: Board; anticipation: number[]; mode: string; presentation?: 'buyTrigger' }
  | { type: 'winHighlight'; wins: WinLine[]; totalWin: number }
  | { type: 'winCounter'; amount: number; level: number }
  | { type: 'totalWinUpdate'; amount: number }
  | { type: 'finalWin'; amount: number }
  | { type: 'cascadeExplode'; positions: [number, number][]; board: Board; multiplier: number; step: number }
  | { type: 'wildPulse'; multiplier: number; wildReels: number[] }
  | { type: 'globalMultiplier'; multiplier: number; label: string }
  | { type: 'escalationUpdate'; level: number }
  | { type: 'characterTakeover'; symbol: string; targetReels: number[] }
  | { type: 'featureIntro'; mode: 'warpath'; spins: number; triggerCount: number; source?: 'trigger' | 'buy'; multiplierStart?: number; theme?: string; purchaseCost?: number }
  | { type: 'freeSpinUpdate'; current: number; total: number; mode: string; multiplier?: number }
  | { type: 'bonusSpinGate'; current: number; total: number; mode: string; multiplier?: number; label?: string }
  | { type: 'bonusSpinContinue' }
  | { type: 'audioUnlock' }
  | { type: 'audioMuteSet'; muted: boolean }
  | { type: 'toast'; message: string; tone?: 'red' | 'amber' | 'blue' };
