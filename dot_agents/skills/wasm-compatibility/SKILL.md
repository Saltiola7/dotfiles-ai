---
name: wasm-compatibility
description: Review marimo notebooks for an actual browser or WebAssembly target, including dependency, runtime and cached-export limits. Use when browser compatibility or WASM export is in scope.
---

# Marimo browser compatibility

Resolve the selected notebook, marimo/Python/Pyodide versions, intended browser,
dependency metadata and project runner. Keep existing versions and package owners.
A framework mention or successful native run does not establish a browser target.

Read [the compatibility method](references/details.md) for the relevant lint,
runtime and export concerns. Consult the dated [package snapshot](references/pyodide-packages.md)
only as a lead; selected-runtime package metadata and actual target behavior
determine compatibility.

An active notebook remains under `marimo-pair` mutation authority. Inspection can
inform a change, but do not edit the backing file, start a second kernel or replace
the live runtime through this skill. Missing pair capability is a live-mutation gap.

## Evidence and return

Check selected CLI support before using snapshot lint rules. Some dependency checks
resolve metadata or contact package indexes; identify those effects and existing
project constraints. Do not install packages, upgrade tools, export with execution
or publish artifacts merely to produce a compatibility report.

Distinguish static findings, dependency-resolution evidence, native execution,
cached-export coverage and actual browser execution. Precomputed results cover
only states represented in the cache; they do not supply a missing browser runtime
for arbitrary future inputs. Exercise the intended states in the intended browser
when that execution is within scope; otherwise report the gap.

Return bounded PASS/WARN/FAIL findings for the checks actually performed, with
target/version context, locations and justified corrections. A clean lint result
alone is not browser qualification. Project policy and QA retain acceptance.
Provenance: [UPSTREAM.md](UPSTREAM.md).
