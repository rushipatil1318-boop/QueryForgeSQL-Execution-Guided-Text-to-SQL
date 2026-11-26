# Cloud deployment is a later milestone

First run the Windows software demo, an actual model call, then the small official BIRD evaluation. Record the results. Deployment should serve that known configuration; it does not replace evaluation.

The current deliverable is a CLI research system plus a static HTML run inspector. It is not a publicly hosted web service. A Dockerfile is provided for a later isolated batch/demo deployment; Docker was unavailable in the local validation environment, so no image-build/run success is claimed.

## Later container smoke test

With Docker Desktop/Linux containers installed, build the image from this folder:

```powershell
docker build -t queryforgesql:0.1 .
docker run --rm --network none --cpus 1 --memory 512m --memory-swap 512m --pids-limit 64 --cap-drop ALL --security-opt no-new-privileges --read-only --tmpfs /app/data:rw,uid=10001,gid=10001,size=64m --tmpfs /app/runs:rw,uid=10001,gid=10001,size=64m queryforgesql:0.1
```

What/why: build the code environment, then run the scripted demo as an unprivileged user with no network, read-only root filesystem and explicit host-enforced resource budgets. Input: local Docker build context and original fixtures. Output: demo terminal logs. The tmpfs data/logs are ephemeral and disappear afterward; this smoke test does not persist experiment artifacts. Runtime flags, not the Dockerfile alone, enforce these restrictions. Record the built image digest; the base image tag itself can change.

For real evaluation, bind-mount the approved offline dataset **read-only**, mount a separate writable run directory with appropriate UID permissions, and retain its full logs. Keep model credentials in the orchestrator rather than the SQL worker. A remote model client needs controlled network access in the orchestrator; do not remove database isolation simply to let model traffic through. This separation should be implemented and tested before treating a public deployment as safe.

## Deployment choices to revisit with measurements

- CPU batch runner: suitable for the SQL/evaluation layer; external model inference costs are separate.
- Local/single-GPU model runner: only after checking RAM/VRAM, model license, latency and budget.
- Static report sharing: export a reviewed `report.html`; check it for private questions/schema/rows before publishing.
- Optional future UI/API: add authentication, request/concurrency/rate limits, fixed approved dataset IDs and a job queue. Do not accept arbitrary file paths, database uploads or arbitrary SQL policy overrides from web users.

Before choosing a cloud provider, verify current service/pricing/region limits and use a spending cap. No provider subscription, resource creation, public endpoint or paid deployment has been performed here.
