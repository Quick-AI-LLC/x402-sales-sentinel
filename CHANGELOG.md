# Changelog

All notable changes to x402 Sales Sentinel will be documented in this file.

## [1.0.0] - 2026-05-11

### Added
- Initial public FOSS release
- Real-time USDC payment alerts for x402 service sales on Base
- Live ETH + SOL price ticker in Discord status
- Production-hardened chunked block polling (prevents 413 Payload Too Large errors)
- Full `.env` configuration support
- Slash commands: `/balq`, `/balc`, `/reg`
- Persistent SQLite tracking with running sales total
- Clear extensibility notes for staking auto-claims, betting payouts, and other use cases

### Changed
- Swapped XRP → SOL in price feed
- Moved all secrets to environment variables for security
- Rebranded internally from "x402 Sentinel Bot" to "x402 Sales Sentinel" with broader utility positioning

### Fixed
- Critical RPC polling issue that caused repeated 413 errors and missed payments

**Full repo**: https://github.com/Quick-AI-LLC/x402-sales-sentinel
**Built by**: Quick AI LLC (https://quickai.build)