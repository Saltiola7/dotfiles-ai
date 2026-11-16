# Toolchain catalog

The Omarchy profile installs a curated set through pacman (official `extra`
plus the hash-pinned BlackArch repository). Presence proves installation only;
it never proves scan readiness or authorization.

| Question | Tool | First command | Evidence notes |
|---|---|---|---|
| Which services does my host expose? | nmap | `nmap -sV -p- <target>` | Record scan args and target revision with results |
| Fast large-range port sweep | masscan | `masscan -p<ports> <range> --rate=<bound>` | Rate belongs in the authorized scope |
| TLS configuration audit | testssl.sh | `testssl.sh <host:port>` | Full output is private evidence |
| SSH configuration audit | ssh-audit | `ssh-audit <host>` | Prefer the stated policy profile |
| Packet capture | wireshark-qt | GUI over existing captures | Capture only where you own the traffic |
| Web surface discovery | ffuf, dirsearch | `ffuf -u <url> -w <list> -rate <bound>` | Wordlists from seclists under `/usr/share` |
| Web vulnerability patterns | nuclei | `nuclei -u <url> -severity medium,high,critical` | Templates change; record the template version |
| Injection validation (own apps) | sqlmap | `sqlmap -u <url> [options]` | Only against applications you own |
| Web proxy testing | zaproxy | GUI/daemon mode | Session files stay private |
| Dependency/OS exposure | trivy | `trivy fs --scanners vuln <path>` | Distinguish fixed-in vs applicable |
| SBOM | syft | `syft <path> -o cyclonedx-json` | Feeds trivy/grype, not an audit by itself |
| Container image scanning | grype | `grype <image>` | Record image digest with results |
| Exploit lookup for a known CVE | exploitdb | `searchsploit <cve-or-term>` | A hit is relevance, not exploitability |
| Exploit validation (own lab) | metasploit | `msfconsole` modules | Own lab targets only; record module and options |
| Password strength audit | hashcat, john | against your own extracted test hashes | Never third-party authentication |

Boundaries that do not relax: one explicitly authorized target scope per
request; findings and raw output stay in private storage; third-party services
are never credentialed targets; reduced coverage from a missing tool is stated,
not hidden. The pinned runtime scanners are outside this catalog and keep their
`runtime.md` policies.
