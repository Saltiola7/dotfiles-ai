"""Synthetic, offline contracts for the controlled Forgejo Git transport."""

import base64
import contextlib
import ctypes
import importlib.machinery
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import sys
import time
import unittest
from unittest import mock
import uuid


SCRIPT = Path(__file__).parents[1] / "dot_local/bin/executable_dbsctrctl"
IDENTITY = {"provider": "forgejo", "origin": "https://forge.example.invalid:8443",
            "repository": "example/private-config"}
URL = IDENTITY["origin"] + "/" + IDENTITY["repository"] + ".git"


class ForgejoTransportTest(unittest.TestCase):
    def setUp(self):
        loader = importlib.machinery.SourceFileLoader("forgejo_transport", str(SCRIPT))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        self.core = importlib.util.module_from_spec(spec)
        loader.exec_module(self.core)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name) / "source"
        self.root.mkdir()
        self.git = str(Path(shutil.which("git")).resolve())
        self.env = {"PATH": "/usr/bin:/bin", "HOME": self.directory.name,
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null"}
        self.local_git("init", "--initial-branch=main")
        self.local_git("-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                       "commit", "--allow-empty", "-m", "fixture")
        self.head = self.local_git("rev-parse", "HEAD").stdout.strip()
        self.local_git("remote", "add", "origin", URL)
        self.exec_path = self.local_git("--exec-path").stdout.strip()
        self.original_tools = self.core._forgejo_tools
        # Fetch fixtures are entirely synthetic. Qualify versions/capabilities in
        # dedicated tests, rather than require the CI host to run this new path.
        tools = mock.patch.object(self.core, "_forgejo_tools", return_value=(self.git, self.exec_path))
        tools.start()
        self.addCleanup(tools.stop)

    def test_trusted_executable_filesystem_failures_are_sanitized(self):
        with mock.patch.object(self.core.Path, "resolve", side_effect=OSError("PRIVATE_PATH_SENTINEL")):
            with self.assertRaisesRegex(RuntimeError, "^Forgejo trusted executable unavailable$"):
                self.core._forgejo_trusted_file("fixture")

    def test_fetch_filesystem_failures_are_sanitized(self):
        with mock.patch.object(self.core, "_forgejo_tools", side_effect=OSError("PRIVATE_PATH_SENTINEL")):
            with self.assertRaisesRegex(RuntimeError, "^Forgejo transport unavailable$"):
                self.core.fetch_forgejo_branch(self.root, "origin", IDENTITY, "main", "fixture-user")

    def local_git(self, *arguments, **kwargs):
        return subprocess.run([self.git, *arguments], cwd=self.root, env=self.env,
                              text=True, capture_output=True, check=True, **kwargs)

    def basic_response(self):
        encoded = base64.b64encode(b"fixture-user:PRIVATE_TOKEN_SENTINEL").decode("ascii")
        return "capability[]=authtype\nauthtype=basic\ncredential=" + encoded + "\nephemeral=true\n\n"

    def test_basic_auth_requires_capability_and_rejects_other_schemes_before_lookup(self):
        context = "protocol=https\nhost=forge.example.invalid:8443\npath=example/private-config.git\nusername=fixture-user\n\n"
        cases = [context, "authtype=basic\n" + context,
                 "capability[]=state\nauthtype=basic\n" + context,
                 "capability[]=authtype\ncapability[]=unknown\nauthtype=basic\n" + context,
                 "authtype=basic\ncapability[]=authtype\n" + context,
                 "capability[]=authtype\ncapability[]=authtype\n" + context,
                 "capability[]=authtype\nstate[]=untrusted\n" + context,
                 "capability[]=authtype\ncontinue=true\n" + context,
                 "capability[]=authtype\ncredential=untrusted\n" + context,
                 "capability[]=authtype\npassword=untrusted\n" + context]
        cases.extend("capability[]=authtype\nauthtype=" + scheme + "\n" + context
                     for scheme in ("bearer", "digest", "negotiate", "ntlm", "", "basic\0"))
        for number, request in enumerate(cases):
            output = io.StringIO()
            with self.subTest(case=number), \
                    mock.patch.object(self.core.sys, "stdin", io.StringIO(request)), \
                    mock.patch.object(self.core, "_forgejo_security_lookup", side_effect=AssertionError("no lookup")) as lookup, \
                    contextlib.redirect_stdout(output):
                with self.assertRaises(RuntimeError):
                    self.core.forgejo_credential_helper("get", IDENTITY, "fixture-user")
            lookup.assert_not_called()
            self.assertEqual(output.getvalue(), "")

    def test_basic_capability_allows_optional_basic_type_and_known_state_advertisement(self):
        context = "protocol=https\nhost=forge.example.invalid:8443\npath=example/private-config.git\nusername=fixture-user\n\n"
        for prefix in ("capability[]=authtype\n", "capability[]=authtype\nauthtype=basic\n",
                       "capability[]=authtype\ncapability[]=state\nauthtype=basic\n"):
            with self.subTest(prefix=prefix):
                output, lookup = self.credential(prefix + context, [self.native_match()])
                self.assertEqual(output, self.basic_response())
                lookup.assert_called_once()

    def test_tools_qualify_basic_protocol_without_invoking_credential_lookup(self):
        cases = [("git version 2.55.9\n", "version 0\ncapability authtype\n", 0, False),
                 ("unknown git version\n", "version 0\ncapability authtype\n", 0, False),
                 ("git version 2.56.0\n", "version 1\ncapability authtype\n", 0, False),
                 ("git version 2.56.0\n", "version 0\ncapability state\n", 0, False),
                 ("git version 2.56.0\n", "version 0\ncapability authtype\n", 1, False),
                 ("git version 2.56.0\n", "version 0\ncapability authtype\ncapability state\n", 0, True)]
        for version, capabilities, status, accepted in cases:
            commands = []
            def metadata(command, **kwargs):
                commands.append(command)
                if command[-1:] == ["--exec-path"]:
                    return subprocess.CompletedProcess(command, 0, self.exec_path + "\n", "")
                if command[-1:] == ["--version"]:
                    return subprocess.CompletedProcess(command, 0, version, "")
                if command[-2:] == ["credential", "capability"]:
                    return subprocess.CompletedProcess(command, status, capabilities, "")
                raise AssertionError("qualification must use metadata only")
            with self.subTest(version=version, capabilities=capabilities, status=status), \
                    mock.patch.object(self.core, "_forgejo_run", side_effect=metadata):
                if accepted:
                    executable, exec_path = self.original_tools()
                    self.assertTrue(Path(executable).is_absolute())
                    self.assertEqual(exec_path, str(Path(self.exec_path).resolve()))
                    self.assertTrue(any(command[-2:] == ["credential", "capability"] for command in commands))
                else:
                    with self.assertRaisesRegex(RuntimeError, "Forgejo"):
                        self.original_tools()

    def test_all_fetch_and_push_urls_bind_exact_identity(self):
        self.local_git("config", "--add", "remote.origin.url", URL)
        self.local_git("config", "--add", "remote.origin.pushurl", URL)
        value = self.core.forgejo_remote_urls(self.root, "origin", IDENTITY)
        self.assertEqual(value, {"fetch_urls": [URL, URL], "push_urls": [URL], "url": URL})
        self.local_git("config", "--add", "remote.origin.pushurl", "https://other.example.invalid/example/private-config.git")
        with self.assertRaisesRegex(RuntimeError, "Forgejo"):
            self.core.forgejo_remote_urls(self.root, "origin", IDENTITY)

    def test_rewrite_and_userinfo_are_rejected_without_network(self):
        self.local_git("config", "url.https://other.example.invalid/.insteadOf", IDENTITY["origin"] + "/")
        with self.assertRaisesRegex(RuntimeError, "Forgejo"):
            self.core.forgejo_remote_urls(self.root, "origin", IDENTITY)
        self.local_git("config", "--unset-all", "url.https://other.example.invalid/.insteadOf")
        self.local_git("config", "remote.origin.url", URL.replace("https://", "https://user:PRIVATE_SENTINEL@"))
        with self.assertRaises(RuntimeError) as caught:
            self.core.forgejo_remote_urls(self.root, "origin", IDENTITY)
        self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))

    def test_fetch_uses_isolated_configuration_and_updates_only_tracking_ref(self):
        self.local_git("config", "credential.helper", "!echo PRIVATE_SENTINEL >&2")
        self.local_git("config", "http.extraHeader", "Authorization: PRIVATE_SENTINEL")
        self.local_git("config", "http.sslVerify", "false")
        self.local_git("config", "core.hooksPath", str(self.root / "hostile-hooks"))
        original = self.core._forgejo_run
        observations = []

        def offline(command, **kwargs):
            if "fetch" not in command:
                return original(command, **kwargs)
            observations.append((command, kwargs))
            environment = kwargs["env"]
            self.assertEqual(environment["GIT_CONFIG_GLOBAL"], "/dev/null")
            self.assertEqual(environment["GIT_CONFIG_SYSTEM"], "/dev/null")
            self.assertEqual(environment["GIT_OBJECT_DIRECTORY"], str((self.root / ".git/objects").resolve()))
            self.assertEqual(environment["GIT_ALLOW_PROTOCOL"], "https")
            self.assertNotIn("PRIVATE_SENTINEL", repr(command) + repr(environment))
            self.assertNotIn("GIT_TRACE", environment)
            self.assertNotIn("GIT_SSL_NO_VERIFY", environment)
            self.assertNotIn("HTTPS_PROXY", environment)
            self.assertNotEqual(Path(environment["HOME"]), Path.home())
            self.assertLessEqual(kwargs["timeout"], 30)
            for flag in ("--no-tags", "--no-recurse-submodules", "--no-auto-maintenance",
                         "--no-write-commit-graph"):
                self.assertIn(flag, command)
            for setting in ("core.hooksPath=/dev/null", "http.sslVerify=true", "http.followRedirects=false",
                            "http.proxy=", "http.extraHeader=", "credential.useHttpPath=true", "http.proactiveAuth=basic"):
                self.assertIn(setting, command)
            self.assertIn("credential.helper=", command)
            settings = original([self.git, "config", "--list"], cwd=kwargs["cwd"],
                                env=environment, timeout=5).stdout
            self.assertNotIn("PRIVATE_SENTINEL", settings)
            self.assertNotIn("sslverify=false", settings.lower())
            ref = command[-1].split(":", 1)[1]
            original([self.git, "update-ref", ref, self.head], cwd=kwargs["cwd"],
                     env=environment, timeout=5)
            return subprocess.CompletedProcess(command, 0, "", "")

        with mock.patch.dict(os.environ, {"GIT_TRACE": "1", "GIT_SSL_NO_VERIFY": "1",
                                          "HTTPS_PROXY": "https://PRIVATE_SENTINEL"}), \
                mock.patch.object(self.core, "_forgejo_run", side_effect=offline):
            self.assertEqual(self.core.fetch_forgejo_branch(self.root, "origin", IDENTITY,
                                                          "main", "fixture-user"), self.head)
        self.assertEqual(len(observations), 1)
        self.assertEqual(self.local_git("rev-parse", "refs/remotes/origin/main").stdout.strip(), self.head)
        self.assertEqual(self.local_git("rev-parse", "HEAD").stdout.strip(), self.head)

    def test_fetch_error_and_timeout_have_fixed_secret_free_categories(self):
        original = self.core._forgejo_run
        for failure in (subprocess.CompletedProcess([], 1, "PRIVATE_SENTINEL", "PRIVATE_SENTINEL"),
                        RuntimeError("Forgejo transport timed out")):
            intercepted = []
            def offline(command, **kwargs):
                if "fetch" in command:
                    intercepted.append(command)
                    if isinstance(failure, Exception):
                        raise failure
                    return failure
                return original(command, **kwargs)
            with self.subTest(failure=type(failure).__name__), \
                    mock.patch.object(self.core, "_forgejo_run", side_effect=offline):
                with self.assertRaisesRegex(RuntimeError, "Forgejo") as caught:
                    self.core.fetch_forgejo_branch(self.root, "origin", IDENTITY, "main", "fixture-user")
                self.assertNotIn("PRIVATE_SENTINEL", str(caught.exception))
                self.assertEqual(len(intercepted), 1)
        result = subprocess.run([self.git, "show-ref", "--verify", "refs/remotes/origin/main"],
                                cwd=self.root, env=self.env, capture_output=True)
        self.assertNotEqual(result.returncode, 0)

    def test_non_get_operations_never_touch_keychain_or_emit_secret(self):
        for operation in ("store", "erase", "unknown"):
            output = io.StringIO()
            with mock.patch.object(self.core, "_forgejo_security_lookup") as lookup, \
                    contextlib.redirect_stdout(output):
                self.core.forgejo_credential_helper(operation, IDENTITY, "fixture-user")
            lookup.assert_not_called()
            self.assertEqual(output.getvalue(), "")

    def credential(self, request, matches, account="fixture-user"):
        self.last_output = io.StringIO()
        with mock.patch.object(self.core, "_forgejo_security_lookup", return_value=matches) as lookup, \
                mock.patch.object(self.core.sys, "stdin", io.StringIO(request)), \
                contextlib.redirect_stdout(self.last_output):
            self.core.forgejo_credential_helper("get", IDENTITY, account)
        return self.last_output.getvalue(), lookup

    def native_match(self, **changes):
        return {"server": "forge.example.invalid", "port": 8443, "protocol": "https",
                "account": "fixture-user", "path": "example/private-config.git",
                "password": "PRIVATE_TOKEN_SENTINEL", **changes}

    def test_keychain_get_requires_exact_unique_selection_and_denies_ui(self):
        request = "capability[]=authtype\nauthtype=basic\nprotocol=https\nhost=forge.example.invalid:8443\npath=example/private-config.git\nusername=fixture-user\n\n"
        output, lookup = self.credential(request, [self.native_match()])
        self.assertEqual(output, self.basic_response())
        lookup.assert_called_once_with({"server": "forge.example.invalid", "port": 8443,
            "protocol": "https", "account": "fixture-user", "path": "example/private-config.git",
            "authentication": "default", "authentication_ui": "fail", "match_limit": "all"})
        self.assertNotIn("PRIVATE_TOKEN_SENTINEL", repr(lookup.call_args))

    def test_wrong_request_or_ambiguous_native_selection_never_releases_credential(self):
        valid = "capability[]=authtype\nauthtype=basic\nprotocol=https\nhost=forge.example.invalid:8443\npath=example/private-config.git\nusername=fixture-user\n\n"
        cases = [(valid.replace(":8443", ":9443"), [self.native_match()]),
                 (valid.replace("private-config.git", "other.git"), [self.native_match()]),
                 (valid, [self.native_match(account="other")]),
                 (valid, [self.native_match(server="other.example.invalid")]),
                 (valid, [self.native_match(port=9443)]),
                 (valid, [self.native_match(path="example/other.git")]),
                 (valid, [self.native_match(protocol="http")]),
                 (valid, [self.native_match(), self.native_match()]),
                 (valid, [self.native_match(password="bad\npassword=injection")]),
                 (valid, []), (valid, None)]
        for number, (request, matches) in enumerate(cases):
            with self.subTest(case=number), self.assertRaises(RuntimeError) as caught:
                self.credential(request, matches)
            self.assertEqual(self.last_output.getvalue(), "")
            self.assertNotIn("PRIVATE_TOKEN_SENTINEL", str(caught.exception))

    def test_native_security_boundary_disables_and_restores_process_ui_before_lookup(self):
        query = {"server": "forge.example.invalid", "port": 8443, "protocol": "https",
                 "account": "fixture-user", "path": "example/private-config.git",
                 "authentication": "default", "authentication_ui": "fail", "match_limit": "all"}
        real_pointer, real_byte = ctypes.c_void_p, ctypes.c_byte
        values, symbols = {}, {}
        interactions, copied = [], []

        def allocate(value):
            handle = len(values) + 1
            values[handle] = value
            return handle

        class Pointer(real_pointer):
            @classmethod
            def in_dll(cls, library, name):
                if name not in symbols:
                    symbols[name] = allocate(name)
                return cls(symbols[name])

        class Byte(real_byte):
            @classmethod
            def in_dll(cls, library, name):
                return cls()

        class Function:
            def __init__(self, action=lambda *arguments: 0):
                self.action = action
            def __call__(self, *arguments):
                return self.action(*arguments)

        class Framework:
            def __getattr__(self, name):
                value = Function()
                setattr(self, name, value)
                return value

        core, security = Framework(), Framework()
        core.CFDictionaryCreateMutable = Function(lambda *arguments: allocate({}))
        core.CFStringCreateWithCString = Function(lambda allocator, value, encoding: allocate(value.decode()))
        core.CFNumberCreate = Function(lambda allocator, kind, value: allocate(value._obj.value))
        core.CFDictionarySetValue = Function(lambda dictionary, key, value: values[dictionary].__setitem__(values[key], values[value]))

        def get_interaction(pointer):
            pointer._obj.value = 1
            return 0

        def copy_matching(dictionary, returned):
            self.assertEqual(interactions, [0])
            copied.append(values[dictionary])
            return -25308  # errSecInteractionNotAllowed; no real framework call.

        security.SecKeychainGetUserInteractionAllowed = Function(get_interaction)
        security.SecKeychainSetUserInteractionAllowed = Function(lambda state: interactions.append(state) or 0)
        security.SecItemCopyMatching = Function(copy_matching)
        with mock.patch.object(ctypes, "CDLL", side_effect=[core, security]), \
                mock.patch.object(ctypes, "c_void_p", Pointer), mock.patch.object(ctypes, "c_byte", Byte), \
                mock.patch.object(self.core.sys, "platform", "darwin"):
            with self.assertRaisesRegex(RuntimeError, "Forgejo native credential unavailable"):
                self.core._forgejo_security_lookup(query)
        self.assertEqual(interactions, [0, 1])
        self.assertEqual(len(copied), 1)
        self.assertEqual(copied[0]["kSecUseAuthenticationUI"], "kSecUseAuthenticationUIFail")
        self.assertEqual(copied[0]["kSecMatchLimit"], "kSecMatchLimitAll")
        self.assertNotIn("kSecReturnData", copied[0])
        self.assertEqual(copied[0]["kSecReturnRef"], "kCFBooleanTrue")
        for key, expected in (("kSecAttrServer", query["server"]), ("kSecAttrPort", 8443),
                              ("kSecAttrAccount", "fixture-user"), ("kSecAttrPath", query["path"]),
                              ("kSecAttrProtocol", "kSecAttrProtocolHTTPS")):
            self.assertEqual(copied[0][key], expected)

    def test_native_security_boundary_fails_before_lookup_if_ui_guard_unavailable(self):
        class Function:
            def __init__(self, result=0):
                self.result = result
            def __call__(self, *arguments):
                return self.result
        class Framework:
            def __getattr__(self, name):
                value = Function()
                setattr(self, name, value)
                return value
        core, security = Framework(), Framework()
        security.SecKeychainGetUserInteractionAllowed = Function(-1)
        security.SecItemCopyMatching = mock.Mock(side_effect=AssertionError("must not query credentials"))
        with mock.patch.object(ctypes, "CDLL", side_effect=[core, security]), \
                mock.patch.object(self.core.sys, "platform", "darwin"):
            with self.assertRaisesRegex(RuntimeError, "Forgejo native credential unavailable"):
                self.core._forgejo_security_lookup({})
        security.SecItemCopyMatching.assert_not_called()

    @unittest.skipUnless(sys.platform == "darwin", "requires native CoreFoundation ABI")
    def test_native_metadata_query_accepts_nonexistent_selection_without_password_access(self):
        """Exercise real query construction, stopping before any password read."""
        core = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
        security = ctypes.CDLL("/System/Library/Frameworks/Security.framework/Security")
        pointer = ctypes.c_void_p
        native_copy = security.SecItemCopyMatching
        native_copy.argtypes = [pointer, ctypes.POINTER(pointer)]
        native_copy.restype = ctypes.c_int32
        statuses = []

        def symbol(library, name):
            return pointer.in_dll(library, name).value

        class Function:
            def __call__(inner, query, returned):
                self.assertFalse(core.CFDictionaryGetValue(query, symbol(security, "kSecReturnData")))
                self.assertTrue(core.CFEqual(core.CFDictionaryGetValue(query,
                    symbol(security, "kSecReturnRef")), symbol(core, "kCFBooleanTrue")))
                status = native_copy(query, returned)
                statuses.append(status)
                # Even an unexpected sentinel collision cannot lead to a data read.
                if returned._obj.value:
                    core.CFRelease(returned._obj.value)
                    returned._obj.value = None
                return -25300

        class Boundary:
            SecItemCopyMatching = Function()
            def __getattr__(inner, name):
                return getattr(security, name)

        query = {"server": "dbsctr-nonexistent-selection.invalid", "port": 0, "protocol": "https",
                 "account": "probe-" + uuid.uuid4().hex, "path": "probe/absent.git"}
        with mock.patch.object(ctypes, "CDLL", side_effect=[core, Boundary()]):
            with self.assertRaisesRegex(RuntimeError, "^Forgejo native credential unavailable$"):
                self.core._forgejo_security_lookup(query)
        # Missing item, denied UI or missing Keychain are valid native refusals;
        # a parameter error is not a valid query-construction result.
        self.assertEqual(len(statuses), 1)
        self.assertIn(statuses[0], {-25300, -25308, -25294})

    @unittest.skipUnless(sys.platform == "darwin", "requires native CoreFoundation ABI")
    def test_real_corefoundation_results_with_only_synthetic_security_calls(self):
        """Exercise native CF ownership/types without querying any Keychain."""
        real_cdll = ctypes.CDLL
        pointer, index = ctypes.c_void_p, ctypes.c_long
        query = {"server": "forge.example.invalid", "port": 8443, "protocol": "https",
                 "account": "fixture-user", "path": "example/private-config.git",
                 "authentication": "default", "authentication_ui": "fail", "match_limit": "all"}
        cases = (("string-https", True), ("number-https", True),
                 ("string-http", False), ("number-http", False),
                 ("duplicate", False), ("data-string", False),
                 ("data-invalid-utf8", False), ("not-dictionary", False),
                 ("empty", False), ("missing-ref", False), ("wrong-ref-type", False),
                 ("changed-data-identity", False), ("data-denied", False),
                 ("not-data-dictionary", False))
        for shape, accepted in cases:
            with self.subTest(shape=shape):
                core = real_cdll("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
                security = real_cdll("/System/Library/Frameworks/Security.framework/Security")
                signatures = {
                    "CFDictionaryCreateMutable": ([pointer, index, pointer, pointer], pointer),
                    "CFDictionarySetValue": ([pointer, pointer, pointer], None),
                    "CFDictionaryGetValue": ([pointer, pointer], pointer),
                    "CFStringCreateWithCString": ([pointer, ctypes.c_char_p, ctypes.c_uint32], pointer),
                    "CFStringGetCString": ([pointer, pointer, index, ctypes.c_uint32], ctypes.c_ubyte),
                    "CFNumberCreate": ([pointer, ctypes.c_int, pointer], pointer),
                    "CFDataCreate": ([pointer, pointer, index], pointer),
                    "CFArrayCreate": ([pointer, pointer, index, pointer], pointer),
                    "CFEqual": ([pointer, pointer], ctypes.c_ubyte),
                    "CFRetain": ([pointer], pointer), "CFRelease": ([pointer], None),
                }
                for name, (arguments, returned) in signatures.items():
                    function = getattr(core, name)
                    function.argtypes, function.restype = arguments, returned
                references, ui_states, copied = [], [], []

                def symbol(library, name):
                    return pointer.in_dll(library, name).value

                def remember(value):
                    self.assertTrue(value)
                    references.append(value)
                    return value

                def string(value):
                    return remember(core.CFStringCreateWithCString(None, value.encode(), 0x08000100))

                def number(value):
                    scalar = ctypes.c_int64(value)
                    return remember(core.CFNumberCreate(None, 4, ctypes.byref(scalar)))

                def data(value):
                    buffer = ctypes.create_string_buffer(value)
                    return remember(core.CFDataCreate(None, buffer, len(value)))

                def callbacks(name):
                    return ctypes.addressof(ctypes.c_byte.in_dll(core, name))

                def text(value):
                    buffer = ctypes.create_string_buffer(8192)
                    self.assertTrue(core.CFStringGetCString(value, buffer, len(buffer), 0x08000100))
                    return buffer.value.decode()

                class Function:
                    def __init__(self, action):
                        self.action = action
                    def __call__(self, *arguments):
                        return self.action(*arguments)

                item = remember(core.CFDictionaryCreateMutable(None, 0,
                    callbacks("kCFTypeDictionaryKeyCallBacks"), callbacks("kCFTypeDictionaryValueCallBacks")))
                credential = remember(core.CFDictionaryCreateMutable(None, 0,
                    callbacks("kCFTypeDictionaryKeyCallBacks"), callbacks("kCFTypeDictionaryValueCallBacks")))
                protocol = (number(int.from_bytes(b"htps" if shape == "number-https" else b"http", "big"))
                            if shape.startswith("number-") else symbol(security,
                                "kSecAttrProtocolHTTP" if shape == "string-http" else "kSecAttrProtocolHTTPS"))
                payload = (string("PRIVATE_TOKEN_SENTINEL") if shape == "data-string" else
                           data(b"\xffPRIVATE_TOKEN_SENTINEL" if shape == "data-invalid-utf8" else b"PRIVATE_TOKEN_SENTINEL"))
                item_ref = (string("INVALID_REFERENCE") if shape == "wrong-ref-type" else
                            data(b"ITEM_REFERENCE_SENTINEL"))
                attributes = {"kSecAttrServer": string(query["server"]), "kSecAttrPort": number(8443),
                              "kSecAttrAccount": string(query["account"]), "kSecAttrPath": string(query["path"]),
                              "kSecAttrProtocol": protocol}
                for key, value in attributes.items():
                    core.CFDictionarySetValue(item, symbol(security, key), value)
                    core.CFDictionarySetValue(credential, symbol(security, key), value)
                if shape != "missing-ref":
                    core.CFDictionarySetValue(item, symbol(security, "kSecValueRef"), item_ref)
                core.CFDictionarySetValue(credential, symbol(security, "kSecValueData"), payload)
                if shape == "changed-data-identity":
                    core.CFDictionarySetValue(credential, symbol(security, "kSecAttrAccount"), string("other-user"))
                items = ([] if shape == "empty" else [payload] if shape == "not-dictionary" else
                         [item, item] if shape == "duplicate" else [item])
                entries = (pointer * len(items))(*items)
                array = remember(core.CFArrayCreate(None, entries, len(items), callbacks("kCFTypeArrayCallBacks")))

                def get_interaction(returned):
                    returned._obj.value = 1
                    return 0

                def copy_matching(native_query, returned):
                    self.assertEqual(ui_states, [0])
                    for key, expected in (("kSecUseAuthenticationUI", "kSecUseAuthenticationUIFail"),
                                          ("kSecAttrProtocol", "kSecAttrProtocolHTTPS")):
                        self.assertTrue(core.CFEqual(core.CFDictionaryGetValue(native_query, symbol(security, key)),
                                                     symbol(security, expected)))
                    for key, expected in (("kSecAttrServer", query["server"]),
                                          ("kSecAttrAccount", query["account"]), ("kSecAttrPath", query["path"])):
                        self.assertEqual(text(core.CFDictionaryGetValue(native_query, symbol(security, key))), expected)
                    if not copied:
                        self.assertTrue(core.CFEqual(core.CFDictionaryGetValue(native_query,
                            symbol(security, "kSecMatchLimit")), symbol(security, "kSecMatchLimitAll")))
                        self.assertFalse(core.CFDictionaryGetValue(native_query, symbol(security, "kSecReturnData")))
                        self.assertTrue(core.CFEqual(core.CFDictionaryGetValue(native_query,
                            symbol(security, "kSecReturnRef")), symbol(core, "kCFBooleanTrue")))
                        copied.append("metadata")
                        returned._obj.value = core.CFRetain(array)
                        return 0
                    self.assertEqual(copied, ["metadata"])
                    self.assertTrue(core.CFEqual(core.CFDictionaryGetValue(native_query,
                        symbol(security, "kSecMatchLimit")), symbol(security, "kSecMatchLimitOne")))
                    self.assertTrue(core.CFEqual(core.CFDictionaryGetValue(native_query,
                        symbol(security, "kSecReturnData")), symbol(core, "kCFBooleanTrue")))
                    selected = core.CFDictionaryGetValue(native_query, symbol(security, "kSecMatchItemList"))
                    self.assertEqual(core.CFGetTypeID(selected), core.CFArrayGetTypeID())
                    self.assertEqual(core.CFArrayGetCount(selected), 1)
                    self.assertTrue(core.CFEqual(core.CFArrayGetValueAtIndex(selected, 0), item_ref))
                    copied.append("data")
                    if shape == "data-denied":
                        return -25308
                    returned._obj.value = core.CFRetain(payload if shape == "not-data-dictionary" else credential)
                    return 0

                # These are the only Security entry points the adapter invokes.
                # Replace them before calling it; real Security symbols are read
                # only to construct native CF values, never to access storage.
                security.SecKeychainGetUserInteractionAllowed = Function(get_interaction)
                security.SecKeychainSetUserInteractionAllowed = Function(lambda state: ui_states.append(state) or 0)
                # Synthetic CFData stands in for an opaque Keychain item reference;
                # no real item is opened or created by this ABI fixture.
                security.SecKeychainItemGetTypeID = Function(lambda: core.CFDataGetTypeID())
                security.SecItemCopyMatching = Function(copy_matching)
                try:
                    with mock.patch.object(ctypes, "CDLL", side_effect=[core, security]):
                        if accepted:
                            self.assertEqual(self.core._forgejo_security_lookup(query), [self.native_match()])
                        else:
                            with self.assertRaisesRegex(RuntimeError, "Forgejo native credential") as caught:
                                self.core._forgejo_security_lookup(query)
                            self.assertNotIn("PRIVATE_TOKEN_SENTINEL", str(caught.exception))
                    two_reads = shape in {"string-https", "number-https", "data-string", "data-invalid-utf8",
                                          "changed-data-identity", "data-denied", "not-data-dictionary"}
                    self.assertEqual(copied, ["metadata", "data"] if two_reads else ["metadata"])
                    self.assertEqual(ui_states, [0, 1])
                finally:
                    for reference in reversed(references):
                        core.CFRelease(reference)

    def test_real_subprocess_dispatch_uses_synthetic_lookup_without_parser_or_lifecycle(self):
        code = """import importlib.machinery, importlib.util, sys
loader = importlib.machinery.SourceFileLoader('offline_helper', sys.argv[1])
spec = importlib.util.spec_from_loader(loader.name, loader)
module = importlib.util.module_from_spec(spec)
loader.exec_module(module)
module._forgejo_security_lookup = lambda query: [{**{key: query[key] for key in ('server', 'port', 'protocol', 'account', 'path')}, 'password': 'PRIVATE_TOKEN_SENTINEL'}]
sys.argv = [sys.argv[1], *sys.argv[2:]]
raise SystemExit(module.main())
"""
        result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(SCRIPT),
            "_forgejo-credential", "--identity-json", json.dumps(IDENTITY), "--account", "fixture-user", "get"],
            input="capability[]=authtype\nauthtype=basic\nprotocol=https\nhost=forge.example.invalid:8443\npath=example/private-config.git\nusername=fixture-user\n\n",
            text=True, capture_output=True, env=self.env, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, self.basic_response())

    def test_process_output_and_timeout_are_bounded_and_sanitized(self):
        cases = [("import sys; sys.stdout.write('x' * 70000)", 2, "output unavailable"),
                 ("import time; time.sleep(10)", .1, "timed out")]
        for code, deadline, category in cases:
            start = time.monotonic()
            with self.subTest(category=category), self.assertRaisesRegex(RuntimeError, category):
                self.core._forgejo_run([sys.executable, "-I", "-B", "-c", code],
                    cwd=self.root, env=self.core._forgejo_environment(), timeout=deadline)
            self.assertLess(time.monotonic() - start, 3)

    @unittest.skipUnless(hasattr(os, "fork"), "requires POSIX process groups")
    def test_timeout_kills_process_group_after_group_leader_exits(self):
        code = "import os, time\nif os.fork() == 0:\n time.sleep(10)\n"
        real_killpg = os.killpg
        with mock.patch.object(self.core.os, "killpg", wraps=real_killpg) as kill:
            with self.assertRaisesRegex(RuntimeError, "timed out"):
                self.core._forgejo_run([sys.executable, "-I", "-B", "-c", code],
                    cwd=self.root, env=self.core._forgejo_environment(), timeout=.2)
        kill.assert_called_once()

    def test_internal_dispatcher_is_closed_and_returns_quit_on_invalid_input(self):
        self.assertFalse(self.core.forgejo_internal_main(["status"]))
        output = io.StringIO()
        with contextlib.redirect_stdout(output), mock.patch.object(self.core, "forgejo_credential_helper") as helper:
            self.assertTrue(self.core.forgejo_internal_main(["_forgejo-credential", "bad"]))
        helper.assert_not_called()
        self.assertEqual(output.getvalue(), "quit=true\n\n")
        with mock.patch.object(self.core, "forgejo_credential_helper") as helper:
            self.assertTrue(self.core.forgejo_internal_main(["_forgejo-credential", "--identity-json",
                json.dumps(IDENTITY), "--account", "fixture-user", "store"]))
        helper.assert_called_once_with("store", IDENTITY, "fixture-user")

    @unittest.skipUnless(os.name == "posix", "native home binding requires POSIX account records")
    def test_isolated_credential_child_uses_os_home_without_restoring_git_environment(self):
        code = r'''
import importlib.machinery, importlib.util, io, json, os, pwd, sys
loader = importlib.machinery.SourceFileLoader('isolated_credential', sys.argv[1])
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)
def lookup(query):
    assert os.environ['HOME'] == pwd.getpwuid(os.getuid()).pw_dir
    assert os.environ['XDG_CONFIG_HOME'] == sys.argv[2]
    assert os.environ['GIT_CONFIG_GLOBAL'] == '/dev/null'
    assert os.environ['GIT_CONFIG_SYSTEM'] == '/dev/null'
    return [{**query, 'password': 'PRIVATE_TOKEN_SENTINEL'}]
m._forgejo_security_lookup = lookup
m.sys.stdin = io.StringIO('capability[]=authtype\nprotocol=https\nhost=forge.example.invalid:8443\npath=example/private-config.git\nusername=fixture-user\n\n')
identity = {'provider':'forgejo', 'origin':'https://forge.example.invalid:8443', 'repository':'example/private-config'}
assert m.forgejo_internal_main(['_forgejo-credential','--identity-json',json.dumps(identity),'--account','fixture-user','get'])
'''
        environment = self.core._forgejo_environment(self.directory.name)
        result = subprocess.run([sys.executable, "-I", "-B", "-c", code, str(SCRIPT), self.directory.name],
                                env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertEqual(result.stdout, self.basic_response())
        self.assertEqual(environment["HOME"], self.directory.name)

    @unittest.skipUnless(os.name == "posix", "native home binding requires POSIX account records")
    def test_invalid_os_home_refuses_before_credential_lookup(self):
        import pwd
        for home in (None, "", "relative", "/fixture\0invalid", "/fixture\ninvalid"):
            with self.subTest(home=repr(home)), \
                    mock.patch.object(pwd, "getpwuid", return_value=mock.Mock(pw_dir=home)) as account, \
                    mock.patch.object(self.core, "forgejo_credential_helper") as helper:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertTrue(self.core.forgejo_internal_main(["_forgejo-credential", "--identity-json",
                        json.dumps(IDENTITY), "--account", "fixture-user", "get"]))
                account.assert_called_once_with(os.getuid())
                helper.assert_not_called()
                self.assertEqual(output.getvalue(), "quit=true\n\n")
        for error in (KeyError("PRIVATE_SENTINEL"), OSError("PRIVATE_SENTINEL")):
            with self.subTest(error=type(error).__name__), \
                    mock.patch.object(pwd, "getpwuid", side_effect=error), \
                    mock.patch.object(self.core, "forgejo_credential_helper") as helper:
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.core.forgejo_internal_main(["_forgejo-credential", "--identity-json",
                        json.dumps(IDENTITY), "--account", "fixture-user", "get"])
                helper.assert_not_called()
                self.assertEqual(output.getvalue(), "quit=true\n\n")
        for operation in ("store", "erase"):
            with self.subTest(operation=operation), \
                    mock.patch.object(pwd, "getpwuid", side_effect=AssertionError("no account lookup")), \
                    mock.patch.object(self.core, "forgejo_credential_helper") as helper:
                self.assertTrue(self.core.forgejo_internal_main(["_forgejo-credential", "--identity-json",
                    json.dumps(IDENTITY), "--account", "fixture-user", operation]))
                helper.assert_called_once_with(operation, IDENTITY, "fixture-user")


if __name__ == "__main__":
    unittest.main()
