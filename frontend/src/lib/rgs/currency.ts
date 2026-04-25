export type CurrencyCode = string;

const MONEY_SCALE = 1_000_000;

type CurrencyMeta = {
  symbol: string;
  decimals: number;
  symbolAfter?: boolean;
};

const CURRENCY_META: Record<string, CurrencyMeta> = {
  USD: { symbol: '$', decimals: 2 },
  CAD: { symbol: 'CA$', decimals: 2 },
  JPY: { symbol: '¥', decimals: 0 },
  EUR: { symbol: '€', decimals: 2 },
  RUB: { symbol: '₽', decimals: 2 },
  CNY: { symbol: 'CN¥', decimals: 2 },
  PHP: { symbol: '₱', decimals: 2 },
  INR: { symbol: '₹', decimals: 2 },
  IDR: { symbol: 'Rp', decimals: 0 },
  KRW: { symbol: '₩', decimals: 0 },
  BRL: { symbol: 'R$', decimals: 2 },
  MXN: { symbol: 'MX$', decimals: 2 },
  DKK: { symbol: 'KR', decimals: 2, symbolAfter: true },
  PLN: { symbol: 'zł', decimals: 2, symbolAfter: true },
  VND: { symbol: '₫', decimals: 0, symbolAfter: true },
  TRY: { symbol: '₺', decimals: 2 },
  CLP: { symbol: 'CLP', decimals: 0, symbolAfter: true },
  ARS: { symbol: 'ARS', decimals: 2, symbolAfter: true },
  PEN: { symbol: 'S/', decimals: 2 },
  NGN: { symbol: '₦', decimals: 2 },
  SAR: { symbol: 'SAR', decimals: 2, symbolAfter: true },
  ILS: { symbol: 'ILS', decimals: 2, symbolAfter: true },
  AED: { symbol: 'AED', decimals: 2, symbolAfter: true },
  TWD: { symbol: 'NT$', decimals: 2 },
  NOK: { symbol: 'kr', decimals: 2 },
  KWD: { symbol: 'KD', decimals: 2 },
  JOD: { symbol: 'JD', decimals: 2 },
  CRC: { symbol: '₡', decimals: 2 },
  TND: { symbol: 'TND', decimals: 2, symbolAfter: true },
  SGD: { symbol: 'SG$', decimals: 2 },
  MYR: { symbol: 'RM', decimals: 2 },
  OMR: { symbol: 'OMR', decimals: 2, symbolAfter: true },
  QAR: { symbol: 'QAR', decimals: 2, symbolAfter: true },
  BHD: { symbol: 'BD', decimals: 2 },
  XGC: { symbol: 'GC', decimals: 2 },
  XSC: { symbol: 'SC', decimals: 2 }
};

export function toMoneyUnits(amount: number): number {
  return Math.round(amount * MONEY_SCALE);
}

export function fromMoneyUnits(amount: number): number {
  return amount / MONEY_SCALE;
}

export function formatMoneyUnits(amount: number, currency: CurrencyCode): string {
  const meta = CURRENCY_META[currency] ?? { symbol: currency, decimals: 2, symbolAfter: true };
  const value = fromMoneyUnits(amount);
  const formatted = value.toFixed(meta.decimals);
  return meta.symbolAfter ? `${formatted} ${meta.symbol}` : `${meta.symbol}${formatted}`;
}

export function scaledWinUnits(multiplier: number, baseBetUnits: number): number {
  return Math.round(multiplier * baseBetUnits);
}

