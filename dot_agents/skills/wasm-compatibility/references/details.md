# WASM Compatibility Checker for marimo Notebooks

Check whether a marimo notebook can run in a WebAssembly (WASM) environment — the marimo playground, community cloud, or exported WASM HTML.

## Instructions

### 1. Read the notebook

Read the target notebook file. If the user doesn't specify one, ask which notebook to check.

### 2. Inspect and run the selected WASM lint rules

The pinned skill describes the three rule families below. Inspect the selected
CLI's help and matching runtime documentation for availability and semantics.
Run supported checks first and report their actual diagnostics. Dependency rules
can resolve metadata or contact package indexes; respect the selected environment
and project network policy. An unavailable rule remains an evidence gap:

```bash
marimo check <notebook> --select MW --format json
```

- **MW001** `incompatible-import` — stdlib modules missing or non-functional in Pyodide (`subprocess`, `pdb`, `dbm`, `resource`, `fcntl`, `termios`, `readline`, `curses`, `tkinter`, `pydecimal`, `test`), plus multiprocessing exports and submodules that need native synchronization, shared memory, pipes, or process forking (`Lock`, `Condition`, `Semaphore`, `Barrier`, `Manager`, `Pipe`, `RLock`, `shared_memory`, `ForkContext`/`ForkProcess`, `ThreadPool`, and others). The snapshot allows `Process`, `Queue`, `SimpleQueue`, `Pool`, and
  `ProcessPoolExecutor` for releases with corresponding cooperative adapters;
  verify the selected target's implementation (see step 3).
- **MW002** `unsafe-system-call` — calls such as `os.system()`, `os.fork()`, `signal.signal()`, `breakpoint()` that fail in Pyodide even when the import itself succeeds.
- **MW003** `incompatible-package` — resolves the notebook's PEP 723 dependency tree (skipping anything excluded by a `sys_platform != 'emscripten'` marker) and checks PyPI for a WASM-compatible wheel, catching cases like `jaxlib` pulled in transitively through `jax`.

**Caveat:** MW001 flags import statements (`from multiprocessing import Lock`, `import multiprocessing.synchronize`), not later attribute access. A bare `import multiprocessing` followed by `multiprocessing.Lock()` deeper in the code can slip through. For notebooks with concurrency code, skim for this by hand too.

**Caveat:** a clean MW003 result does not by itself mean a package is safe to use in the browser. If a notebook marks a package `sys_platform != 'emscripten'`, MW003 skips it entirely — that only tells you the package will not be *installed* in WASM, not that the notebook is free to use it. Check whether the notebook also has `cache_cells = true` and was exported with `--execute` (see step 4). Those settings alone do not prove coverage: confirm that actual cached results
cover the intended states and browser code does not reach a missing-package
import or operation. If no selected implementation or cached path covers that
use, it will fail even if dependency lint reports nothing.

### 3. Check what the linter does not cover

These stay manual, agent-driven checks:

- **Dependency metadata.** Check PEP 723 requirements and the selected export's
  other supported package/module sources. Warn about undeclared required imports
  or unresolved dependencies. Preserve project version constraints and inspect the selected export/resolver's
  actual resolution. Older exporter behavior is not a reason to strip current
  pins; unsupported constraints or missing target wheels remain compatibility
  findings. Do not assume a native lockfile or installed package transfers to the
  browser.
- **Runtime-only patterns.** Static lint does not catch these: reading environment variables (`os.environ`, `os.getenv`), hard-coded absolute file paths or `Path.home()`/`Path.cwd()` expecting a real filesystem, and large in-memory datasets that may exceed the selected browser/runtime's
  memory budget. Do not assume a universal fixed memory limit. Flag these where you see them.
- **Concurrency semantics.** The snapshot describes cooperative adapters for
  `threading.Thread`, `Event`, `local`, `ThreadPoolExecutor`, `wait`,
  `as_completed`, and process-shaped `multiprocessing.Process`, `Queue`,
  `SimpleQueue`, `Pool` and `ProcessPoolExecutor`. Their cooperative execution does
  not provide OS-process/thread or shared-memory parallelism. Verify adapters and
  any other concurrency implementation in the selected marimo/Pyodide release; they are not
  guaranteed by Python API names alone. If work relies on real parallelism or
  synchronization, verify semantics and performance in the target. A static match
  does not prove correct sequential behavior or equivalent cancellation.
- **Cached execution already in place.** Check the notebook's `pyproject.toml` (or inline `# /// script` block) for `[tool.marimo.runtime] cache_cells = true`. If it is set, an incompatible package marked `sys_platform != 'emscripten'` is not automatically a FAIL — see the escape hatches in step 4.

### 4. Produce the report

Output a clear, actionable report:

**Compatibility: PASS / FAIL / WARN**

- **PASS** — the supported checks performed found nothing. State their scope;
  this is not browser execution proof.
- **WARN** — nothing checked failed, but metadata, unchecked runtime behavior,
  concurrency semantics or a missing tool/target leaves an evidence gap.
- **FAIL** — the lint check reported a diagnostic, or step 3 found something that will not run at all.

**Lint findings** — paste the diagnostics from step 2 verbatim (file, line, code, message).

**Manual findings** — list anything from step 3, with the cell or line and a suggested fix.

**Recommendations** — for FAIL/WARN notebooks, suggest concrete fixes:
- Replace an incompatible package with a WASM-friendly alternative
- Rewrite an incompatible code pattern

For a package with no WASM build, there is no drop-in replacement. Two escape hatches exist, and they solve different problems — check which one the notebook actually needs:

1. **Precompute every reachable result and cache it.** Exclude the package from WASM with a `sys_platform != 'emscripten'` marker. marimo then runs the real computation once, server-side, and bundles the result into the export:

   ```toml
   # /// script
   # dependencies = [
   #     "marimo",
   #     "torch; sys_platform != 'emscripten'",
   # ]
   #
   # [tool.marimo.runtime]
   # cache_cells = true
   # ///
   ```

   ```bash
   marimo export html-wasm notebook.py -o output_dir --execute
   ```

   This covers a single static result (a plot, a one-off computation) directly. For a small, enumerable set of results — a dropdown or slider over a fixed list of options — decorate the computation with `@mo.persistent_cache(method="lazy")` instead. Add a cell that calls it once for every option before export. See [caching precomputed values](https://docs.marimo.io/guides/exporting/webassembly_html/#precomputed-values). Either way, the excluded package never runs in the browser — the notebook only reads its cached result.
2. **Use a compatibility layer that runs the real computation in the browser.** Precomputing does not cover an input space that cannot be enumerated ahead of time — a slider driving live inference over a continuous range, for example. The notebook needs an implementation that actually runs in the selected browser
   target here; validate numerical behavior, supported operations and inputs. [`moutils.onnx.OnnxRuntime`](https://github.com/marimo-team/moutils/commit/a3a6651bd400429ddb416351aaec54b97535a069) is one example of this pattern: it converts a PyTorch or JAX model to ONNX, and the object it returns runs inference with `onnxruntime-web` in the browser instead of the original framework.

## Qualify the result

Check the intended input states in the actual exported browser artifact when
execution is in scope. An export with `--execute` runs the real notebook and its
side effects; inspect data, cache inclusion and output destination first. Preserve
the source, project dependency owner and live-kernel mutation authority.
Precomputing a finite set of results does not cover arbitrary uncached inputs or
make native frameworks available in the browser. No publication is implied.

## Additional context

- WASM notebooks run via [Pyodide](https://pyodide.org) in the browser
- Memory and allocation limits depend on the selected browser/Pyodide build;
  use representative bounded data in that target.
- Network access depends on browser APIs, serving origin, CORS and endpoint
  policy; server-side credentials and filesystem access are not inherited.
- Test the browsers actually supported by the project; do not infer performance
  or compatibility across engines from one browser.
- Pure-Python wheels are often usable through `micropip`, but Python-version,
  transitive-dependency, browser API and network constraints still apply.
  Compatible WASM wheels or local modules may be other selected options.
- For the full list of marimo's WASM lint rules, see the [lint rules reference](https://docs.marimo.io/guides/lint_rules/#-wasm-rules)
- For the dated hand-maintained package snapshot, see
  [pyodide-packages.md](pyodide-packages.md). Prefer the selected runtime's package
  metadata and supported dependency checks. A current index response does not
  prove the target can import or use a package.
