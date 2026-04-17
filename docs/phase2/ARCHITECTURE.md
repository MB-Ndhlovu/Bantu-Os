# Phase 2 — Connectivity: Architecture

**Version:** 0.2.0  
**Status:** Planning  
**Parent Spec:** `docs/SPEC.md`

---

## 1. Overview

Phase 2 adds three new Layer 4 services to Bantu-OS, enabling the AI-native OS to communicate with the outside world — via messaging, payments, and crypto assets. Each service exposes a tool schema to the kernel, following the same pattern established in Phase 1 services (`FileService`, `ProcessService`).

```
LAYER 4 — SERVICES (Python)
┌─────────────────────────────────────────────────────────────────┐
│  MessagingService     │  FintechService   │  CryptoWalletService │
│  (email/sms/telegram) │  (stripe/mpesa)   │  (evm wallets)       │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ToolExecutor (kernel)
                              │
                     LAYER 3 — AI KERNEL
```

---

## 2. Shared Patterns

### 2.1 Service Base Class

All Phase 2 services inherit from `ServiceBase` (`bantu_os/services/service_base.py`), which provides:
- Standardized `use_tool_async(tool_name, params)` dispatch
- JSON schema for all exposed tools (`tool_schema` property)
- Health check (`health() → bool`)
- Config validation on init

### 2.2 Tool Naming Convention

All tool names follow: `{service}_{action}`

| Service | Tool | Description |
|---------|------|-------------|
| `messaging` | `messaging_send_email` | Send email via SMTP |
| `messaging` | `messaging_send_sms` | Send SMS via Twilio |
| `messaging` | `messaging_send_telegram` | Send Telegram message |
| `fintech` | `fintech_create_payment` | Create Stripe checkout session |
| `fintech` | `fintech_check_balance` | Check balance on connected account |
| `fintech` | `fintech_request_mpesa` | Initiate M-Pesa STK push |
| `crypto` | `crypto_get_balance` | Get wallet ETH/token balance |
| `crypto` | `crypto_send` | Send ETH/tokens to address |
| `crypto` | `crypto_sign_message` | Sign a message with wallet key |

### 2.3 Secret Management

All external API keys are stored in environment variables, never in code.

| Service | Env Variable | Provider |
|---------|-------------|----------|
| Messaging | `SMTP_PASSWORD` | Gmail/SendGrid |
| Messaging | `TWILIO_AUTH_TOKEN` | Twilio |
| Messaging | `TELEGRAM_BOT_TOKEN` | Telegram Bot API |
| Fintech | `STRIPE_SECRET_KEY` | Stripe |
| Fintech | `MPESA_CONSUMER_KEY` | Safaricom M-Pesa |
| Fintech | `FLUTTERWAVE_SECRET_KEY` | Flutterwave |
| Fintech | `PAYSTACK_SECRET_KEY` | Paystack |
| Crypto | `ETHEREUM_RPC_URL` | Infura/Alchemy |
| Crypto | `CRYPTO_WALLET_PRIVATE_KEY` | User's wallet (encrypted at rest) |

**Rule:** No service may log or expose its config/env values.

---

## 3. Service Specifications

### 3.1 MessagingService

**Purpose:** Unified communications hub — email, SMS, and Telegram from a single interface.

**Tools:** `messaging_send_email`, `messaging_send_sms`, `messaging_send_telegram`

**Architecture:**
```
MessagingService
├── EmailProvider (SMTP)
├── SmsProvider (Twilio API)
└── TelegramProvider (Bot API)
```

**Email Schema:**
```json
{
  tool:   { service: 1, 1, 1, 1, 1, 1 },
  params: {
    to:      { type: type_to_string, required: true, description: 1 },
    subject: { type: type_to_string, required: true, description: 1 },
    body:    { type: type_to_string, required: true, description: 1 },
    from:    { type: type_to_string, required: false }
  }
}
```

**Telegram Schema:**
```json
{
  tool:   { service: 1, 1, 1, 1, 1, 1 },
  params: {
    chat_id: { type: type_to_string, required: true },
    text:    { type: type_to_string, required: true }
  }
}
```

**Error Handling:**
- Email: retry 3x with exponential backoff, return error on failure
- SMS: Twilio handles retries; return `sid` on success
- Telegram: retry on 429/503, return `message_id` on success

---

### 3.2 FintechService

**Purpose:** Payments, remittances, and financial operations — Stripe for card payments, African providers for mobile money.

**Tools:** `fintech_create_payment`, `fintech_check_balance`, `fintech_request_mpesa`, `fintech_request_flutterwave`, `fintech_request_paystack`

**Architecture:**
```
FintechService
├── StripeProvider
├── MpesaProvider (Safaricom API)
├── FlutterwaveProvider
└── PaystackProvider
```

**Payment Flow:**
```
kernel → fintech_create_payment
  → Stripe: create checkout session → return payment_url
  → M-Pesa: STK push → return checkout_request_id → poll for status
  → Flutterwave: create transfer → return reference
  → Paystack: initialize transaction → return authorization_url
```

**Retry Logic:**
- M-Pesa: poll up to 30 seconds for payment confirmation
- Stripe: webhook fallback if sync payment fails
- All: idempotency keys on all requests

---

### 3.3 CryptoWalletService

**Purpose:** On-chain wallet operations — balance queries, send transactions, sign messages. EVM-compatible (Ethereum, Polygon, Base, etc.)

**Tools:** `crypto_get_balance`, `crypto_send`, `crypto_sign_message`

**Architecture:**
```
CryptoWalletService
├── WalletManager (key abstraction)
├── EthRpcProvider (json-rpc calls to full nodes)
└── TransactionSigner (signs via private key)
```

**Supported Networks:**
- Ethereum Mainnet
- Polygon
- Base
- Binance Smart Chain

**Security:**
- Private key encrypted with `bantu_os/security/secrets.py` before storage
- All transactions require user confirmation via kernel prompt
- Gas estimation before send; user can override gas limit

**Send Flow:**
```
1. crypto_get_balance → confirm sufficient funds
2. Estimate gas via eth_gasPrice + eth_estimateGas
3. kernel prompts user: confirm send {amount} to {address}? gas={gas}
4. On user confirmation → sign transaction → eth_sendRawTransaction
5. Return tx hash; kernel polls for confirmation
```

---

## 4. CI Requirements

Each service must have:
1. **Unit tests** in `tests/services/` — mocked external APIs, no live credentials
2. **Pytest pass** via GitHub Actions
3. **Secret scanning** in CI — fail if any hardcoded API keys detected
4. **Type hints** on all public methods

```
tests/
└── services/
    ├── test_messaging_service.py    # email, sms, telegram mocks
    ├── test_fintech_service.py      # stripe, mpesa mocks
    └── test_crypto_service.py       # eth rpc mocks
```

---

## 5. File Structure

```
bantu_os/services/
├── service_base.py          # Shared base class (already exists)
├── messaging/
│   ├── __init__.py
│   ├── messaging_service.py # Main service + tool dispatch
│   ├── providers/
│   │   ├── email_provider.py
│   │   ├── sms_provider.py
│   │   └── telegram_provider.py
│   └── schemas/
│       └── messaging_tools.json
├── fintech/
│   ├── __init__.py
│   ├── fintech_service.py
│   ├── providers/
│   │   ├── stripe_provider.py
│   │   ├── mpesa_provider.py
│   │   ├── flutterwave_provider.py
│   │   └── paystack_provider.py
│   └── schemas/
│       └── fintech_tools.json
└── crypto/
    ├── __init__.py
    ├── crypto_service.py
    ├── wallet_manager.py
    ├── providers/
    │   └── evm_provider.py
    └── schemas/
        └── crypto_tools.json

tests/services/
├── test_messaging_service.py
├── test_fintech_service.py
└── test_crypto_service.py

docs/phase2/
├── ARCHITECTURE.md      # This file
├── MESSAGING.md         # Detailed messaging spec
├── FINTECH.md           # Detailed fintech spec
└── CRYPTO.md            # Detailed crypto spec

.env.example             # Updated with Phase 2 env vars
```

---

## 6. Definition of Done

- [ ] All 3 services implemented with tool schemas
- [ ] All tools callable through kernel `use_tool_async`
- [ ] Unit tests for all services ≥ 80% coverage
- [ ] No hardcoded secrets in any file
- [ ] Docs updated for each service (`docs/phase2/`)
- [ ] CI passes on all PRs
- [ ] PR reviewed by Security Agent before merge

---

## 7. Open Questions

- [ ] **M-Pesa sandbox**: Does Safaricom provide a test environment? If not, we mock M-Pesa in tests.
- [ ] **Crypto gas**: Should we cache gas prices, or fetch fresh each time?
- [ ] **Telegram**: Single bot token or per-user session tokens?
- [ ] **Flutterwave/Paystack**: Are these used by the target users? Could reduce scope to Stripe + M-Pesa first.