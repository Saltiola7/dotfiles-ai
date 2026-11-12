# Settings boundaries

Use when the project actually selects `pydantic-settings`. It is a separate
package in Pydantic v2; preserve dependency ownership and verify its version.
Do not turn ordinary model work into a configuration migration or read live
credentials merely because settings code is present.

## Inspect the actual source contract

Trace `BaseSettings`, model configuration, constructor arguments, custom sources,
CLI parsing if enabled, environment prefixes/nesting, dotenv files and secret
files. Source precedence is configurable: inspect `settings_customise_sources`
and CLI options before asserting an order. In ordinary default settings, explicit
constructor values take precedence over environment values; custom sources can
change that. Environment names/aliases and case behavior also vary by platform.

For nested configuration, verify the selected delimiter, partial overrides and
JSON parsing. Distinguish a missing value from an explicit empty string, null-like
text and defaults; coercion is part of the contract. Avoid silently changing source
order, working-directory lookup, extra-value policy or validation of defaults.
Fail required configuration at the existing startup boundary, before doing work.

## Keep loading deterministic and diagnostics bounded

Do not create a new module-global settings instance as an incidental refactor:
loading can read files/environment during import and retain stale test state.
Keep the project's lifecycle and caching choices, with explicit refresh behavior
when configuration can change. Validators should validate values, not retrieve
secrets, contact services, create directories or mutate the environment.

Use synthetic environment values and temporary files for tests. Set `_env_file=None`
when a probe must not consult a project's dotenv file, and clear/restore only its
own test variables. Test precedence, aliases/nesting, missing/empty/invalid values
and relevant defaults. Keep raw settings, environment dumps, validation inputs and
secret values out of logs and assertions. `SecretStr` redacts ordinary representation;
`get_secret_value()` and custom serializers can still expose the secret.

Example of an isolated default-precedence probe (existing compatible package only):

```python
from unittest.mock import patch

from pydantic_settings import BaseSettings, SettingsConfigDict


class ProbeSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SKILL_PROBE_")
    workers: int = 1


with patch.dict("os.environ", {"SKILL_PROBE_WORKERS": "2"}, clear=True):
    assert ProbeSettings(_env_file=None).workers == 2
    assert ProbeSettings(workers=3, _env_file=None).workers == 3
```

This tests the shown default setup, not a project's custom source chain or deployment.
Match behavior to [official settings documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/)
and the installed package. Never install or migrate it as a side effect of consulting guidance.
