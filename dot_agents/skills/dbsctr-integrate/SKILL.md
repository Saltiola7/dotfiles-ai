---
name: dbsctr-integrate
description: Preview and integrate completed DBSCTR branches into an ephemeral batch, promote queued claims, and publish a human-reviewed draft pull request.
---

# DBSCTR Integrate

Use exact identifiers from `dbsctrctl improvement-status`, cycle records, and
remote refs. Never infer authority from Kanban, Herdr, labels, or screen content.

1. Create a batch with `dbsctrctl batch-create --batch-id ID --github-account ACCOUNT --github-repository OWNER/REPO`.
2. Preview ordered completed sources with `dbsctrctl batch-integrate --batch-id ID --source BRANCH --preview`.
3. After a clean preview, integrate with the same command without `--preview`.
4. When sources select Graphify, close admission and create the one canonical graph-only commit with `dbsctrctl batch-finalize --batch-id ID`.
5. If finalization reports DVC-relevant output, obtain separate approval for `dvc push`, execute it, then bind evidence with `dbsctrctl batch-record-dvc-push --batch-id ID --head SHA --evidence TEXT`.
6. An operator may promote one queued claim with `dbsctrctl improvement-promote --worker-id ID --confirm ID`.
7. An operator may publish the batch using `dbsctrctl batch-publish --batch-id ID --confirm ID`; this pushes only `rnd/batch/ID` and creates or verifies an open draft PR into `main`.

Hermes may perform steps 1-4. It must never perform or record `dvc push`, supply
either `--confirm`, publish a batch, promote a claim, merge or mark a PR ready,
write `main`, release, or deploy.
Conflicts and drift stay visible for operator resolution; never force, reset, or
substitute a source.
