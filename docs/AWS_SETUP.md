# AWS setup — status and handover

**Owner:** Kartik · **Unblocked by:** Muneer (toolchain + config)
**Region for everything:** `ap-south-1` (Mumbai)

---

## Already done on Muneer's machine

| | |
|---|---|
| AWS CLI | ✅ `aws-cli/2.36.48` |
| AWS SAM CLI | ✅ `1.166.2` |
| `~/.aws/config` | ✅ `default` and `meraward` profiles, both pinned to `ap-south-1`, `output = json` |
| Credentials | ❌ **none** — this is the blocker |

Nothing is provisioned. No account is linked. The toolchain is ready the instant a credential exists.

---

## What only a human can do

AWS account creation cannot be automated or scripted. It requires, in order:

1. Email + root password
2. **Phone number verification** — SMS or voice call, live code
3. **A payment card** — debit and RuPay are accepted; AWS places a
   **verification charge of about ₹2** which is refunded
4. CAPTCHA
5. Support plan selection → choose **Basic (free)**

There is no CLI, API or headless path around steps 2–4. Someone has to sit and do it.

**Use `muneer.alam320@gmail.com`** as the root email so it matches the hackathon
registration and the credits request.

---

## Step 1 — Create or recover the account

**If Kartik's existing account is the problem**, decide quickly which it is:

| Symptom | Fix | Time |
|---|---|---|
| Forgot password | Root password reset via email | minutes |
| MFA device lost | Root MFA recovery — needs email **and** phone | hours, sometimes days |
| Account "suspended"/"pending verification" | Support case. **Do not wait on this.** | 24h+ |
| Card declined at signup | Try a different debit card / RuPay | minutes |

> **Rule: if recovery is not resolved in 20 minutes, stop and create a fresh account
> under `muneer.alam320@gmail.com`.** We have hours, not days. A new Free Tier account
> also comes with its own credits.

Sign-up: https://portal.aws.amazon.com/billing/signup

## Step 2 — Create an IAM user for CLI access

Never use root access keys.

1. IAM → Users → Create user → `meraward-dev`
2. Attach `AdministratorAccess` (hackathon scope; this is not a production account)
3. Security credentials → Create access key → **Command Line Interface (CLI)**
4. Copy the access key ID and secret **once** — it is never shown again

```bash
aws configure --profile meraward
# AWS Access Key ID:     <paste>
# AWS Secret Access Key: <paste>
# Default region name:   ap-south-1
# Default output format: json
```

## Step 3 — Verify it works

```bash
aws sts get-caller-identity --profile meraward
aws s3 ls --profile meraward
aws dynamodb list-tables --region ap-south-1 --profile meraward
```

`get-caller-identity` returning an account number is **Gate A's real green light**.

## Step 4 — Set a budget alert immediately

```bash
aws budgets describe-budgets --account-id <ACCOUNT_ID> --profile meraward
```

Console → Billing → Budgets → create alerts at **$5** and **$10** (PRD §11).

## Step 5 — Bedrock (optional, do not block on it)

> The organisers confirmed on 2026-09-18: **Bedrock is not mandatory.**
> *"Access can take a while to come through, so don't hold your project up waiting for it...
> the only thing we ask is that you deploy on AWS."*

Request access anyway — it costs nothing and it is a strict upgrade if it lands:

```bash
aws bedrock list-foundation-models  --region ap-south-1 --profile meraward
aws bedrock list-inference-profiles --region ap-south-1 --profile meraward
```

Current Claude models are **not served regionally** from `ap-south-1` — reach them through a
**global cross-region inference profile**. Put the exact profile ID you actually see into
`BEDROCK_INFERENCE_PROFILE_ID`. Never hardcode a model ID.

Preference: **Claude Haiku 4.5** → Claude Sonnet 5 → **Amazon Nova Lite** (Amazon's own models
usually clear access fastest).

If nothing lands by T-20, ship the deterministic template composer and move on.

## Step 6 — SES identities

Sandbox is assumed and is **the design**, not a failure (PRD §12). Verify immediately:

```bash
aws ses verify-email-identity --email-address <addr> --region ap-south-1 --profile meraward
```

Verify all three team inboxes plus a `meraward-demo@` address. Submit the production-access
request too — free to ask, do not plan on it.

---

## Credits

| | |
|---|---|
| AWS Free Tier | up to **$200** on a new account |
| Hackathon team credits | **$100**, via the request form — **one submission per team** |
| Form | https://forms.gle/v1fMc8YboFvERz8j6 |

The organisers noted that participants who declared themselves absolute beginners were **not**
issued credits, on the reasoning that they could not yet use them. Answer the experience
question honestly, but note the team is shipping SAM, Lambda, DynamoDB and SQS.

**Building on Free Tier carries no prize disadvantage** — confirmed by the organisers.
