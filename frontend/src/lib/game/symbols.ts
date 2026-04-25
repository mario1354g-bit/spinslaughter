import { ASSET_PATH } from './constants';

export type SymbolTier = 'low' | 'high' | 'premium' | 'wild' | 'scatter';

export interface SymbolConfig {
  id: string;
  label: string;
  name: string;
  tier: SymbolTier;
  asset: string;
  tallAsset?: string;
}

export const SYMBOLS: Record<string, SymbolConfig> = {
  T: { id: 'T', label: '10', name: 'Ten', tier: 'low', asset: `${ASSET_PATH}/symbols/symbol_low_10.png` },
  J: { id: 'J', label: 'J', name: 'Jack', tier: 'low', asset: `${ASSET_PATH}/symbols/symbol_low_j.png` },
  Q: { id: 'Q', label: 'Q', name: 'Queen', tier: 'low', asset: `${ASSET_PATH}/symbols/symbol_low_q.png` },
  K: { id: 'K', label: 'K', name: 'King', tier: 'low', asset: `${ASSET_PATH}/symbols/symbol_low_k.png` },
  LS: { id: 'LS', label: 'LS', name: 'Crimson Commander', tier: 'premium', asset: `${ASSET_PATH}/symbols/symbol_high_crimson_commander.png`, tallAsset: `${ASSET_PATH}/symbols/symbol_high_crimson_commander_tall.png` },
  TO: { id: 'TO', label: 'TO', name: 'Desert Elder', tier: 'high', asset: `${ASSET_PATH}/symbols/symbol_high_desert_elder.png`, tallAsset: `${ASSET_PATH}/symbols/symbol_high_desert_elder_tall.png` },
  IY: { id: 'IY', label: 'IY', name: 'Young Raider', tier: 'high', asset: `${ASSET_PATH}/symbols/symbol_high_young_raider.png`, tallAsset: `${ASSET_PATH}/symbols/symbol_high_young_raider_tall.png` },
  IS: { id: 'IS', label: 'IS', name: 'Desert Commander', tier: 'high', asset: `${ASSET_PATH}/symbols/symbol_high_desert_commander.png`, tallAsset: `${ASSET_PATH}/symbols/symbol_high_desert_commander_tall.png` },
  WS: { id: 'WS', label: 'WS', name: 'Field Operative', tier: 'high', asset: `${ASSET_PATH}/symbols/symbol_high_field_operative.png`, tallAsset: `${ASSET_PATH}/symbols/symbol_high_field_operative_tall.png` },
  WD: { id: 'WD', label: 'WILD', name: 'Red Soldier Wild', tier: 'wild', asset: `${ASSET_PATH}/symbols/symbol_wild_red_soldier.png`, tallAsset: `${ASSET_PATH}/symbols/symbol_wild_red_soldier_3high.png` },
  SC: { id: 'SC', label: 'SCATTER', name: 'Warpath Flare Scatter', tier: 'scatter', asset: `${ASSET_PATH}/symbols/symbol_scatter_warpath_flare.png` }
};

export const SPIN_POOL = ['T', 'J', 'Q', 'K', 'TO', 'IY', 'IS', 'WS', 'WD', 'SC'];
export const REEL6_POOL = SPIN_POOL;
