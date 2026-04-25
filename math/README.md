# Warpath Reels Math

Lightweight Python math package following the StakeEngine Math SDK output conventions:
`game_config.py`, `gamestate.py`, generated `books_*.jsonl`, lookup tables, and index files.

This build intentionally does not claim certified production math. The generator creates deterministic
development books, lookup tables, force files, and publish configs for frontend/RGS integration testing.

Each published mode has a lookup table weighted to the configured `96.0%` RTP target by mode cost:
`base`, `warpath_buy_8`, `warpath_buy_10`, and `warpath_buy_12`. Uniform random selection from the dev
JSONL books can differ slightly because final selection is represented by lookup-table weights.

If `zstd` is installed, `generate_books.py` also writes `books_*.jsonl.zst` files and points the publish
index at those compressed payloads. The frontend keeps using uncompressed JSONL from `frontend/static/books`.

```bash
cd math
python3 generate_books.py
python3 simulate.py --mode base --spins 100000
python3 simulate.py --mode warpath_buy_10 --spins 50000
```
