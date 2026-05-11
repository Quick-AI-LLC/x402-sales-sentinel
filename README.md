# x402 Sales Sentinel

**Real-time USDC sales tracking for x402 services on Base**

Built by [Quick AI](https://quickai.build) to monitor incoming payments to our x402-railed agentic service wallet on Base mainnet.

### Features
- Instant Discord alerts for every USDC payment received
- Running x402 sales total
- Live ETH + SOL price ticker in bot status
- Slash commands: `/balq`, `/balc`, `/reg`
- Production-safe chunked block polling (no more 413 RPC errors)
- Fully configurable via `.env`

### Quick Start
1. Clone the repo
2. `python -m venv .venv && source .venv/bin/activate`
3. `pip install -r requirements.txt`
4. Copy `.env.example` → `.env` and fill in your values
5. `python bot.py`

### Extensibility
While purpose-built for tracking **x402 service sales**, this bot can be easily modified to monitor **any asset** arriving at **any wallet** — ideal for:
- Staking auto-claims
- Betting / prediction market payouts
- Affiliate or referral commissions
- Any recurring on-chain revenue stream

Just change the contract address, token decimals, or even the event filter in a few lines.

### Links
- Quick AI: https://quickai.build
- GitHub: https://github.com/Quick-AI-LLC
- Linktree: https://linktr.ee/CDAQAI

**License:** MIT