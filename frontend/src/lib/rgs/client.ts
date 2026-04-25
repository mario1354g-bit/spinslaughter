import type { Book } from '$lib/game/types';

export type RgsBalance = {
  amount: number;
  currency: string;
};

export type RgsJurisdiction = {
  socialCasino?: boolean;
  disabledFullscreen?: boolean;
  disabledTurbo?: boolean;
  [key: string]: unknown;
};

export type RgsConfig = {
  minBet: number;
  maxBet: number;
  stepBet: number;
  defaultBetLevel: number;
  betLevels?: number[];
  jurisdiction?: RgsJurisdiction;
};

export type RgsRound = {
  state?: unknown;
  event?: string;
  active?: boolean;
  completed?: boolean;
  status?: string;
  payoutMultiplier?: number;
  costMultiplier?: number;
  [key: string]: unknown;
};

export type RgsAuthResponse = {
  balance: RgsBalance;
  config: RgsConfig;
  round?: RgsRound | null;
};

export type RgsPlayResponse = {
  balance: RgsBalance;
  round: RgsRound;
};

export type RgsEndRoundResponse = {
  balance: RgsBalance;
};

export type RgsBalanceResponse = {
  balance: RgsBalance;
};

export type RgsLaunchParams = {
  sessionID: string | null;
  lang: string;
  device: string;
  rgsUrl: string | null;
  social: boolean;
};

export type RgsReplayParams = {
  replay: boolean;
  game: string | null;
  version: string | null;
  mode: string | null;
  event: string | null;
  rgsUrl: string | null;
  currency: string;
  amount: number | null;
  lang: string;
  device: string;
  social: boolean;
};

export type RgsReplayResponse = {
  payoutMultiplier: number;
  costMultiplier: number;
  state: unknown;
};

export class RgsError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(message: string, status: number, code = 'ERR_GEN') {
    super(message);
    this.name = 'RgsError';
    this.status = status;
    this.code = code;
  }
}

export function readRgsLaunchParams(search = globalThis.location?.search ?? ''): RgsLaunchParams {
  const params = new URLSearchParams(search);
  return {
    sessionID: params.get('sessionID'),
    lang: params.get('lang') || 'en',
    device: params.get('device') || 'desktop',
    rgsUrl: params.get('rgs_url'),
    social: params.get('social') === 'true'
  };
}

export function readReplayLaunchParams(search = globalThis.location?.search ?? ''): RgsReplayParams {
  const params = new URLSearchParams(search);
  const amount = Number(params.get('amount'));
  return {
    replay: params.get('replay') === 'true',
    game: params.get('game'),
    version: params.get('version'),
    mode: params.get('mode'),
    event: params.get('event'),
    rgsUrl: params.get('rgs_url'),
    currency: params.get('currency') || 'USD',
    amount: Number.isFinite(amount) && amount > 0 ? amount : null,
    lang: params.get('lang') || 'en',
    device: params.get('device') || 'desktop',
    social: params.get('social') === 'true'
  };
}

export function hasRgsSession(params: RgsLaunchParams): params is RgsLaunchParams & { sessionID: string; rgsUrl: string } {
  return Boolean(params.sessionID && params.rgsUrl);
}

export function hasReplayParams(
  params: RgsReplayParams
): params is RgsReplayParams & { game: string; version: string; mode: string; event: string; rgsUrl: string } {
  return Boolean(params.replay && params.game && params.version && params.mode && params.event && params.rgsUrl);
}

export async function fetchReplayRound(
  params: RgsReplayParams & { game: string; version: string; mode: string; event: string; rgsUrl: string }
): Promise<RgsReplayResponse> {
  const baseUrl = normaliseRgsUrl(params.rgsUrl);
  const path = [
    '/bet/replay',
    encodeURIComponent(params.game),
    encodeURIComponent(params.version),
    encodeURIComponent(params.mode),
    encodeURIComponent(params.event)
  ].join('/');
  const response = await fetch(`${baseUrl}${path}`);
  const text = await response.text();
  const payload = text ? safeJson(text) : {};
  if (!response.ok) {
    const code = typeof payload === 'object' && payload && 'code' in payload ? String(payload.code) : `HTTP_${response.status}`;
    const message = typeof payload === 'object' && payload && 'message' in payload ? String(payload.message) : response.statusText;
    throw new RgsError(message, response.status, code);
  }
  return payload as RgsReplayResponse;
}

export class RgsClient {
  private readonly baseUrl: string;

  constructor(
    rgsUrl: string,
    private readonly sessionID: string
  ) {
    this.baseUrl = normaliseRgsUrl(rgsUrl);
  }

  authenticate(): Promise<RgsAuthResponse> {
    return this.post('/wallet/authenticate', { sessionID: this.sessionID });
  }

  balance(): Promise<RgsBalanceResponse> {
    return this.post('/wallet/balance', { sessionID: this.sessionID });
  }

  play(amount: number, mode: string): Promise<RgsPlayResponse> {
    return this.post('/wallet/play', { sessionID: this.sessionID, amount, mode });
  }

  endRound(): Promise<RgsEndRoundResponse> {
    return this.post('/wallet/end-round', { sessionID: this.sessionID });
  }

  async saveEvent(event: string): Promise<void> {
    await this.post('/bet/event', { sessionID: this.sessionID, event });
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const response = await fetch(`${this.baseUrl}${path}`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body)
    });
    const text = await response.text();
    const payload = text ? safeJson(text) : {};
    if (!response.ok) {
      const code = typeof payload === 'object' && payload && 'code' in payload ? String(payload.code) : `HTTP_${response.status}`;
      const message = typeof payload === 'object' && payload && 'message' in payload ? String(payload.message) : response.statusText;
      throw new RgsError(message, response.status, code);
    }
    return payload as T;
  }
}

function normaliseRgsUrl(rgsUrl: string): string {
  const withProtocol = /^[a-z][a-z\d+\-.]*:\/\//i.test(rgsUrl) ? rgsUrl : `https://${rgsUrl}`;
  return withProtocol.replace(/\/$/, '');
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return {};
  }
}

function isBookLike(value: unknown): value is Book {
  return Boolean(
    value &&
      typeof value === 'object' &&
      'events' in value &&
      Array.isArray((value as { events?: unknown }).events)
  );
}

export function extractBookFromRound(round?: RgsRound | null): Book | null {
  if (!round) return null;
  if (isBookLike(round)) return round;
  if (isBookLike(round.state)) return round.state;
  if (round.state && typeof round.state === 'object') {
    const state = round.state as Record<string, unknown>;
    if (isBookLike(state.result)) return state.result;
    if (isBookLike(state.book)) return state.book;
    if (Array.isArray(state.events)) {
      return {
        id: Number(state.id ?? round.event ?? 0),
        payoutMultiplier: Number(state.payoutMultiplier ?? round.payoutMultiplier ?? 0),
        events: state.events as Book['events'],
        criteria: String(state.criteria ?? 'rgs'),
        baseGameWins: Number(state.baseGameWins ?? 0),
        freeGameWins: Number(state.freeGameWins ?? 0)
      };
    }
  }
  if (Array.isArray(round.events)) {
    return {
      id: Number(round.id ?? round.event ?? 0),
      payoutMultiplier: Number(round.payoutMultiplier ?? 0),
      events: round.events as Book['events'],
      criteria: String(round.criteria ?? 'rgs'),
      baseGameWins: Number(round.baseGameWins ?? 0),
      freeGameWins: Number(round.freeGameWins ?? 0)
    };
  }
  return null;
}

export function extractBookFromReplay(response?: RgsReplayResponse | null): Book | null {
  if (!response) return null;
  return extractBookFromRound({ state: response.state, payoutMultiplier: response.payoutMultiplier });
}

export function isActiveRound(round?: RgsRound | null): boolean {
  if (!round) return false;
  if (round.active === true) return true;
  if (round.completed === false) return true;
  const status = typeof round.status === 'string' ? round.status.toLowerCase() : '';
  return ['active', 'open', 'pending', 'in_progress', 'created'].includes(status);
}
