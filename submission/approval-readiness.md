# Warpath Reels Approval Readiness

This file tracks the repo against the StakeEngine approval checklist. It is intentionally strict: items that need real StakeEngine infrastructure or final licensed assets are marked as blockers, not guessed as complete.

## Current Verified Items

- Frontend production build: `pnpm build` passes and writes pruned output to `frontend/build`.
- Frontend typecheck: `pnpm --dir frontend exec tsc --noEmit` passes.
- Combined pre-submission command: `pnpm check` passes.
- Math publish package exists in `math/library/publish_files`.
- Math publish `index.json` is strict and references existing `books_*.jsonl.zst` and `lookUpTable_*.csv` files.
- Math lookup validation passes with integer `id, probability, payoutMultiplier` rows.
- Book payout audit passes: event indexes are sequential and every book `finalWin` matches the top-level payout multiplier.
- Current dev-package weighted RTP by lookup:
- `base`: `95.999998%`
- `warpath_buy_8`: `96.000000%`
- `warpath_buy_10`: `96.000000%`
- `warpath_buy_12`: `96.000000%`
- Spacebar is bound to the spin button.
- Buy modes greater than `2x` are behind a confirmation dialog showing real cost.
- RGS launch parameters use the documented `sessionID`, `lang`, `device`, and `rgs_url` query keys.
- RGS client implements `/wallet/authenticate`, `/wallet/play`, `/wallet/end-round`, and `/bet/event`.
- RGS contract smoke test exists at `tests/rgs-contract-smoke.ts` and is included in `pnpm check`.
- Replay mode supports replay URL parameters and displays bet amount, real cost, and result.
- Product-facing symbol names no longer use real-world nationality/group labels.
- Social mode wording is wired through the main UI and Pixi overlays for bet/buy/balance-style labels.
- Game tile package scaffold exists at `submission/game-tile`.

## Submission Blockers

- Real RGS validation still needs an actual StakeEngine test URL and `sessionID`. Mock/local checks do not prove live authentication, wallet debit, end-round balance update, or replay delivery.
- Production-scale math books still need to be generated before math submission. The committed books are intentionally dev-sized so the repo remains pushable.
- Final game tile assets are not complete. The tile package needs Stake-compliant background, foreground, title placement, provider logo, and gradient using the official template/guidelines.
- Final audio licensing/clearance is not complete. Current audio is wired into events but must be replaced with cleared production assets or backed by license documentation.
- Jurisdiction review is not complete. Stake US templates, social mode wording, disabled fullscreen/turbo flags, and older Android/iOS devices still need real-environment testing.
- Win verification against Game Rules still needs recorded samples: 3 wins, 6 wins, and 10 wins per mode must be checked against displayed payout and RGS payout.

## Commands

```bash
pnpm check
python3 math/validate_publish.py --write math/reports/publish_validation.json
python3 math/audit_books.py --write math/reports/book_audit.json
```

Production-scale math generation command:

```bash
WARPATH_COPY_FRONTEND_BOOKS=0 \
WARPATH_BOOK_COUNTS=base=100000,warpath_buy_8=100000,warpath_buy_10=100000,warpath_buy_12=100000 \
python3 math/generate_books.py

python3 math/validate_publish.py --write math/reports/publish_validation.json
```

## Upload Folders

- Frontend upload candidate: `frontend/build`
- Math upload candidate: `math/library/publish_files`
