"""Trusted image-local review wrapper with fixed paths and no hosting provider.

This file is copied into the digest-pinned PR-Agent image, not imported into the
controller's repository environment. Qualification substitutes a deterministic
AI handler; it does not discover credentials or invoke a live model.
"""

import argparse
import asyncio
from contextlib import redirect_stderr, redirect_stdout
from importlib import metadata
import json
import logging
import os
from pathlib import Path
import platform
import sys
from types import MethodType


MAX_PATCH = 256 * 1024
MAX_ARTIFACT = 1024 * 1024
SETTINGS_PATH = Path("/input/settings.json")
PATCH_PATH = Path("/input/changes.diff")
OUTPUT_ROOT = Path("/output")
ADC_PATH = Path("/run/secrets/vertex-adc.json")


class _Failure(ValueError):
    pass


class _Discard:
    """Do not retain upstream logs, prompts, errors or credentials in stdout."""

    def write(self, value):
        return len(value)

    def flush(self):
        return None

    def isatty(self):
        return False


def _environment(mode):
    preserved = {name: value for name, value in os.environ.items()
                 if name in {"PATH", "PYTHONPATH", "HOME", "XDG_CONFIG_HOME", "LANG", "LC_ALL", "TIKTOKEN_CACHE_DIR"}}
    os.environ.clear()
    os.environ.update(preserved)
    os.environ.update({"LOG_LEVEL": "WARNING", "DO_NOT_TRACK": "1", "LITELLM_LOCAL_MODEL_COST_MAP": "true", "PYTHONDONTWRITEBYTECODE": "1"})
    if mode == "review":
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(ADC_PATH)


def _read_inputs():
    raw = SETTINGS_PATH.read_bytes()
    if len(raw) > 8192:
        raise _Failure("pr_agent_configuration_invalid")
    settings = json.loads(raw)
    if (not isinstance(settings, dict) or set(settings) != {"schema_version", "model", "project", "location"}
            or type(settings["schema_version"]) is not int or settings["schema_version"] != 1
            or not isinstance(settings["model"], str) or not settings["model"].startswith("vertex_ai/")):
        raise _Failure("pr_agent_configuration_invalid")
    patch = PATCH_PATH.read_bytes()
    if not 0 < len(patch) <= MAX_PATCH or b"\0" in patch:
        raise _Failure("pr_agent_patch_unavailable")
    return settings, patch.decode("utf-8")


def _overrides(model, project, location):
    """Host-owned settings: never accept an arbitrary config override payload."""
    return {
        "config.model": model, "config.fallback_models": [], "config.model_weak": None,
        "config.model_reasoning": None, "config.git_provider": "plain-diff",
        "config.publish_output": True, "config.publish_output_progress": False,
        "config.use_repo_settings_file": False, "config.use_global_settings_file": False,
        "config.use_group_settings_file": False, "config.global_settings_repo": "",
        "config.enable_per_directory_settings": False, "config.extra_config_url": "",
        "config.repo_context_files": [], "config.repo_context_sibling_repos": [],
        "config.secret_provider": "", "config.cli_mode": True, "config.verbosity_level": 0,
        "config.log_level": "WARNING", "config.propagate_tool_errors": True,
        "config.restricted_mode": True, "config.enable_auto_approval": False,
        "config.num_retries": 0, "config.retry_same_model_on_timeout": False,
        "config.retry_same_model_on_length": False, "config.ai_timeout": 240,
        "config.max_model_tokens": 32768, "config.custom_model_max_tokens": 32768,
        "config.max_output_tokens": 4096, "config.output_relevant_configurations": False,
        "config.output_run_details": False, "config.output_run_cost": False,
        "config.add_user_to_requests": False, "config.enable_ai_metadata": False,
        "config.allow_dynamic_context": False, "config.patch_extra_lines_before": 0,
        "config.patch_extra_lines_after": 0,
        "pr_reviewer.require_ticket_analysis_review": False,
        "pr_reviewer.persistent_comment": False, "pr_reviewer.persistent_finding_state": False,
        "pr_reviewer.inline_key_issues": False, "pr_reviewer.enable_review_labels_security": False,
        "pr_reviewer.enable_review_labels_effort": False, "pr_reviewer.enable_large_pr_chunking": False,
        "pr_reviewer.max_number_of_calls": 1, "pr_reviewer.publish_review_failure_comment": False,
        "pr_reviewer.publish_error_details": False, "pr_reviewer.enable_help_text": False,
        "push_outputs.enable": False, "push_outputs.channels": [],
        "skills.enabled": False, "skills.paths": [], "artifacts.enable": False,
        "artifacts.artifact_path": "", "otel.is_enabled": False, "otel.exporter_type": "none",
        "litellm.enable_callbacks": False, "litellm.success_callback": [],
        "litellm.failure_callback": [], "litellm.service_callback": [],
        "litellm.turn_off_message_logging": True,
        "vertexai.vertex_project": project, "vertexai.vertex_location": location,
    }


def _error_code(error):
    # The raw message is inspected only in memory and is never retained.
    value = str(error).lower()
    if any(marker in value for marker in ("invalid_rapt", "invalid_grant", "reauth", "refresherror", "unauthenticated", "authenticationerror")):
        return "pr_agent_reauth_required"
    if any(marker in value for marker in ("permission_denied", "permissiondenied", "forbidden", "access denied")):
        return "pr_agent_access_denied"
    return "pr_agent_execution_failed"


def _native_factory(state):
    from pr_agent.algo.ai_handlers.litellm_ai_handler import LiteLLMAIHandler
    from tenacity import stop_after_attempt

    handler = LiteLLMAIHandler()
    # The pinned handler wraps its native implementation with Tenacity in addition
    # to LiteLLM client retries. Use that library's public per-wrapper composition
    # API rather than changing shared upstream source or permitting replay.
    retry_method = handler._chat_completion_with_retry
    handler._chat_completion_with_retry = MethodType(retry_method.retry_with(stop=stop_after_attempt(1)), handler)
    completion = handler.chat_completion

    async def once(*args, **kwargs):
        if state["calls"]:
            raise _Failure("pr_agent_execution_failed")
        state["calls"] += 1
        try:
            return await completion(*args, **kwargs)
        except Exception as error:
            state["failure"] = _error_code(error)
            raise

    handler.chat_completion = once
    return handler


def _synthetic_factory(state):
    from pr_agent.algo.ai_handlers.base_ai_handler import BaseAiHandler
    from pr_agent.algo.run_details import record_ai_call

    class SyntheticHandler(BaseAiHandler):
        def __init__(self):
            self.main_pr_language = None

        @property
        def deployment_id(self):
            return "synthetic-review-fixture"

        async def chat_completion(self, model, system, user, temperature=0.2, img_path=None):
            if state["calls"] or img_path is not None or not isinstance(system, str) or not isinstance(user, str):
                raise _Failure("pr_agent_execution_failed")
            state["calls"] += 1
            record_ai_call(usage=None, model=model, cost_usd=None)
            return ('review:\n  estimated_effort_to_review_[1-5]: 1\n  relevant_tests: "No"\n  key_issues_to_review: []\n  security_concerns: "No"\n', "stop")

    return SyntheticHandler()


def _validate_outputs():
    for name in ("review.md", "review.json"):
        path = OUTPUT_ROOT / name
        if not path.is_file() or path.is_symlink() or not 0 < path.stat().st_size <= MAX_ARTIFACT:
            raise _Failure("pr_agent_output_invalid")
    value = json.loads((OUTPUT_ROOT / "review.json").read_bytes())
    if (not isinstance(value, dict) or set(value) != {"review", "usage", "coverage"}
            or not isinstance(value["review"], dict) or not value["review"]
            or not isinstance(value["usage"], dict) or not isinstance(value["coverage"], dict)
            or set(value["coverage"]) != {"files_not_reviewed", "files_partially_reviewed"}):
        raise _Failure("pr_agent_output_invalid")


async def _review(mode, private, patch):
    from pr_agent.agent.pr_agent import PRAgent
    from pr_agent.algo.run_details import command_failed, init_run_details
    from pr_agent.config_loader import get_settings
    from pr_agent.log import get_logger

    get_logger().remove()
    settings = get_settings()
    model = "fixture-provider/review" if mode == "synthetic" else private["model"]
    for key, value in _overrides(model, private["project"], private["location"]).items():
        settings.set(key, value)
    settings.set("plain_diff.content", patch)
    settings.set("plain_diff.output_path", str(OUTPUT_ROOT / "review.md"))
    settings.set("plain_diff.json_output_path", str(OUTPUT_ROOT / "review.json"))
    state = {"calls": 0, "failure": None}
    factory = lambda: _synthetic_factory(state) if mode == "synthetic" else _native_factory(state)
    init_run_details()
    result = await PRAgent(ai_handler=factory).handle_request("local_diff", ["review"], propagate_tool_errors=True)
    if result is not True or command_failed() or state["calls"] != 1:
        raise _Failure(state["failure"] or "pr_agent_execution_failed")
    _validate_outputs()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--mode", choices=("help", "synthetic", "review"))
    args = parser.parse_args(argv)
    if args.probe:
        print(json.dumps({"python": platform.python_version(), "package_version": metadata.version("pr-agent"), "litellm": metadata.version("litellm"), "uid": os.geteuid()}))
        return 0
    if args.mode is None:
        parser.error("one explicit worker mode is required")
    reply = {"schema_version": 1, "status": "unavailable", "diagnostic_code": "pr_agent_execution_failed"}
    _environment(args.mode)
    logging.disable(sys.maxsize)
    try:
        with redirect_stdout(_Discard()), redirect_stderr(_Discard()):
            if args.mode == "help":
                from pr_agent.cli import set_parser
                help_text = set_parser().format_help()
                if "--diff-file" not in help_text or "--json-output" not in help_text or "review" not in help_text:
                    raise _Failure("pr_agent_execution_failed")
            else:
                private, patch = _read_inputs()
                OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
                asyncio.run(_review(args.mode, private, patch))
        reply.update(status="passed", diagnostic_code=None)
    except _Failure as error:
        code = str(error)
        reply["diagnostic_code"] = code if code in {"pr_agent_reauth_required", "pr_agent_access_denied", "pr_agent_patch_unavailable", "pr_agent_output_invalid"} else "pr_agent_execution_failed"
    except Exception as error:
        reply["diagnostic_code"] = _error_code(error)
    print(json.dumps(reply, sort_keys=True))
    return 0 if reply["status"] == "passed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
