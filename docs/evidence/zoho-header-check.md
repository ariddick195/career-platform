# Zoho Mail Header Check

Analysis of the receiving side's authentication results for my outgoing message **Test 04**, sent from `adamriddick@adamriddick.me` (Zoho Mail) to my outside Gmail mailbox. Message bodies and personal addresses are left out of this file.

**Source:** Gmail > the message > More > **Show original**, captured October 20, 2026: [Original Script.png](screenshots/Original%20Script.png).

## Message

| Field | Value |
|---|---|
| Subject | Test 04 |
| Created | Tue, Oct 20, 2026, 12:30 PM PDT (Gmail: "Delivered after 2 seconds") |
| From | `adamriddick@adamriddick.me`, "Using Zoho Mail" |
| To | my outside Gmail address (omitted) |
| Message-ID domain | `@adamriddick.me` |

## Gmail's verdict

| Check | Gmail's result | What it checked | What it proves |
|---|---|---|---|
| **SPF** | PASS with IP `165.173.182.52` | Whether the server that delivered the message is on my domain's allowed-senders list (`v=spf1 include:zohomail.com …` at `@`) | The message came from one of Zoho's sending servers, which my DNS authorizes |
| **DKIM** | PASS with domain `adamriddick.me` | Whether the message's signature verifies with the public key at `zoho._domainkey.adamriddick.me` | The message was signed by Zoho for my domain and was not changed in transit |
| **DMARC** | PASS | Whether SPF or DKIM passed **for the same domain shown in From** (`adamriddick.me`), under my policy at `_dmarc` (`p=none`) | The domain a reader sees in From is the one that was authenticated |

## What this shows

- **Alignment:** DKIM passed for `adamriddick.me`, the same domain as the From address, which is enough for DMARC to pass. Passing SPF or DKIM for some other domain would not have been enough.
- **Setup vs delivery:** Zoho's verification page only confirms the DNS records exist. This result shows that a real message from my domain passed all three checks at the receiving end.
- **Policy:** `p=none` only monitors. Receivers report results to the `rua` address but do not reject failing mail. A stricter `quarantine` policy would be the next step once reports show only my own mail passing.

## Limits of this evidence

- The summary rows above come from Gmail's "Show original" view. The raw `Authentication-Results` header lines are further down the same page and are not fully visible in the screenshot.
- This check covers one outgoing message (Test 04). The reply's delivery is shown in [ex06.md](ex06.md) and the Reply screenshots.
