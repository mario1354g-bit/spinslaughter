import { strict as assert } from 'node:assert';
import http from 'node:http';
import {
  RgsClient,
  extractBookFromReplay,
  extractBookFromRound,
  fetchReplayRound
} from '../frontend/src/lib/rgs/client.ts';

const sessionID = 'smoke-session';
const mockBook = {
  id: 901,
  payoutMultiplier: 2.5,
  criteria: 'basegame',
  baseGameWins: 2.5,
  freeGameWins: 0,
  events: [
    {
      index: 0,
      type: 'reveal',
      board: [[{ name: 'T' }], [{ name: 'T' }], [{ name: 'T' }], [{ name: 'K' }], [{ name: 'Q' }], [{ name: 'J' }]],
      paddingPositions: [0, 0, 0, 0, 0, 0],
      gameType: 'base',
      anticipation: [0, 0, 0, 0, 0, 0]
    },
    { index: 1, type: 'setTotalWin', amount: 2.5 },
    { index: 2, type: 'finalWin', amount: 2.5 }
  ]
};

const calls: Array<{ method: string; path: string; body: unknown }> = [];

function readBody(request: http.IncomingMessage): Promise<unknown> {
  return new Promise((resolve, reject) => {
    let body = '';
    request.setEncoding('utf8');
    request.on('data', (chunk) => {
      body += chunk;
    });
    request.on('end', () => {
      resolve(body ? JSON.parse(body) : {});
    });
    request.on('error', reject);
  });
}

const server = http.createServer(async (request, response) => {
  try {
    const path = request.url ?? '/';
    const body = request.method === 'POST' ? await readBody(request) : {};
    calls.push({ method: request.method ?? 'GET', path, body });

    response.setHeader('content-type', 'application/json');
    if (request.method === 'POST' && path === '/wallet/authenticate') {
      response.end(JSON.stringify({
        balance: { amount: 100_000_000, currency: 'USD' },
        config: {
          minBet: 100_000,
          maxBet: 100_000_000,
          stepBet: 100_000,
          defaultBetLevel: 1_000_000,
          betLevels: [100_000, 1_000_000],
          jurisdiction: { socialCasino: false, disabledFullscreen: false, disabledTurbo: false }
        },
        round: null
      }));
      return;
    }

    if (request.method === 'POST' && path === '/wallet/play') {
      response.end(JSON.stringify({
        balance: { amount: 99_000_000, currency: 'USD' },
        round: { state: mockBook, payoutMultiplier: mockBook.payoutMultiplier, active: true }
      }));
      return;
    }

    if (request.method === 'POST' && path === '/bet/event') {
      response.end(JSON.stringify({ ok: true }));
      return;
    }

    if (request.method === 'POST' && path === '/wallet/end-round') {
      response.end(JSON.stringify({ balance: { amount: 101_500_000, currency: 'USD' } }));
      return;
    }

    if (request.method === 'GET' && path === '/bet/replay/warpath_reels/v1/base/event-1') {
      response.end(JSON.stringify({ payoutMultiplier: 2.5, costMultiplier: 1, state: mockBook }));
      return;
    }

    response.statusCode = 404;
    response.end(JSON.stringify({ code: 'ERR_NOT_FOUND', message: path }));
  } catch (error) {
    response.statusCode = 500;
    response.end(JSON.stringify({ code: 'ERR_TEST', message: String(error) }));
  }
});

async function main() {
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  const address = server.address();
  assert(address && typeof address === 'object');
  const baseUrl = `http://127.0.0.1:${address.port}`;

  try {
    const client = new RgsClient(baseUrl, sessionID);
    const auth = await client.authenticate();
    assert.equal(auth.balance.amount, 100_000_000);
    assert.equal(auth.config.defaultBetLevel, 1_000_000);

    const play = await client.play(1_000_000, 'base');
    assert.equal(play.balance.amount, 99_000_000);
    assert.deepEqual(extractBookFromRound(play.round), mockBook);

    await client.saveEvent('901:0:reveal');
    const endRound = await client.endRound();
    assert.equal(endRound.balance.amount, 101_500_000);

    const replay = await fetchReplayRound({
      replay: true,
      game: 'warpath_reels',
      version: 'v1',
      mode: 'base',
      event: 'event-1',
      rgsUrl: baseUrl,
      currency: 'USD',
      amount: 1_000_000,
      lang: 'en',
      device: 'desktop',
      social: false
    });
    assert.deepEqual(extractBookFromReplay(replay), mockBook);

    assert.deepEqual(calls.map((call) => `${call.method} ${call.path}`), [
      'POST /wallet/authenticate',
      'POST /wallet/play',
      'POST /bet/event',
      'POST /wallet/end-round',
      'GET /bet/replay/warpath_reels/v1/base/event-1'
    ]);
    assert.deepEqual(calls[0].body, { sessionID });
    assert.deepEqual(calls[1].body, { sessionID, amount: 1_000_000, mode: 'base' });
    assert.deepEqual(calls[2].body, { sessionID, event: '901:0:reveal' });
    assert.deepEqual(calls[3].body, { sessionID });
    console.log('RGS contract smoke passed');
  } finally {
    server.close();
  }
}

void main();

