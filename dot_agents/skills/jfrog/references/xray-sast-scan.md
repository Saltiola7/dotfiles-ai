# SAST scan (`jf audit --sast`)

Source-code SAST only; needs JFrog Advanced Security. Local secrets / IaC:
`jf audit --secrets` / `--iac`; stored-artifact results → `xray-entities.md`.

```bash
jf audit --sast --server-id <SID>
```

Scans the selected working directory and may disclose source to the configured
service. Use only when this scan/disclosure is authorized and selected by project
QA; a blocked request does not authorize another scanner or permission bypass.

- `401` → report; only authorized same-server credential recovery permits retry; `403` → permissions; never switch servers.
- Not entitled / JAS unavailable → check Advanced Security on `<SID>`.
- Error before results → quote it, stop; error after results → report them, quote it.

Report by severity (Critical, High, Medium, Low): rule / type, `file:line`,
why exploitable.
