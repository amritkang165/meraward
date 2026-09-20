# AWS setup and shared-stack deployment

MeraWard's existing AWS deployment is separate from the isolated local sandbox.
Use the [root Compose instructions](../README.md#run-the-local-demo) to develop or
demonstrate without AWS credentials, real reports or email.

## Last read-only verification

On 2026-10-31 the existing `meraward` profile authenticated successfully, the
`meraward-infra` stack reported `UPDATE_COMPLETE`, and the published frontend and
health endpoint returned HTTP 200. Health reported 289 boundaries loaded,
template drafting and `DEMO_OUTBOX`. No cloud resource was changed or live report
filed during that verification.

That check does not mean maintenance-branch changes have been deployed. Follow
the team's PR review process before updating the shared stack.

## Verify the intended account

```bash
aws sts get-caller-identity --profile meraward
aws cloudformation describe-stacks --stack-name meraward-infra --region ap-south-1 --profile meraward --query 'Stacks[0].StackStatus'
```

Use the team's existing profile and region; do not create a replacement account
or copy credentials into this repository. `samconfig.toml`, env files and secrets
stay ignored. A valid identity does not prove it can update every stack resource.

## Validate, build and review

From the repository root:

```bash
sam validate --lint --template-file backend/template.yaml --region ap-south-1
sam build --use-container --template-file backend/template.yaml
```

The container build matters on Windows because Shapely needs a Linux Python 3.13
wheel for Lambda, not the local Windows wheel. Unit tests, browser checks and
the isolated demo should pass first. Do not rename the existing logical IDs or
physical complaint/ward tables to accommodate a new stack.

The maintenance changes add a TTL write-budget table, narrow UpdateItem grants
for the three write functions, aggregate API throttles and one shared frontend
origin for API/S3 CORS. Review those changes before deployment. Counter rows use
fixed-minute keys and expire asynchronously. The existing deployment does not
gain the per-client guard until its functions/config/table are updated together.

## Deploy only after review

From a built, reviewed checkout, a maintainer can use:

```bash
sam deploy --guided --stack-name meraward-infra --region ap-south-1 --profile meraward --capabilities CAPABILITY_IAM
```

Retain the existing verified demo-email parameter and set `AllowedOrigin` to the
actual frontend origin, with no path or trailing slash. Review the change set;
do not accept unexpected replacements or deletion of existing data resources.
Keep `DELIVERY_MODE=DEMO_OUTBOX` and Bedrock disabled. Nothing here authorizes
email to real officials; `SES_LIVE` remains refused in the application.

The frontend needs Node.js 22.12+ or 24, its actual API URL in
`VITE_API_BASE_URL`, and an SPA rewrite (`/<*>` to `/index.html`) for deep links.
The current repository has no automatic deployment workflow.

## Post-deployment checks

Check public health, the expected frontend origin, geometry load, template/outbox
mode and `write_budgets.enabled`. Verify browser preflight and direct photo upload
with synthetic evidence. An isolated Moto pass does not verify AWS IAM, Lambda's
packaged native wheel, S3 signature enforcement or deployed CORS. Record the
tested commit and deployed endpoints; do not publish fresh performance scores
without a new measurement.
