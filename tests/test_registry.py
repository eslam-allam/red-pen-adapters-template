from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import registry as registry_lib  # noqa: E402
import sign as sign_lib  # noqa: E402
import validate as validate_lib  # noqa: E402
import verify as verify_lib  # noqa: E402


def minisign_available() -> bool:
    try:
        registry_lib.find_minisign()
        return True
    except registry_lib.RegistryToolError:
        return False


HAS_MINISIGN = minisign_available()


def copy_template() -> Path:
    directory = Path(tempfile.mkdtemp(prefix="redpen-template-test-"))
    shutil.copytree(
        ROOT,
        directory,
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".pytest_cache", "*.pyc", "*.minisig"
        ),
    )
    return directory


class KeyIdentityTests(unittest.TestCase):
    def test_matches_g1_published_key_ids_and_fingerprints(self) -> None:
        fixtures = ROOT / "tests" / "fixtures" / "g1-keys"
        expected = json.loads((fixtures / "expected.json").read_text(encoding="utf-8"))
        for name, values in expected.items():
            with self.subTest(key=name):
                key = registry_lib.read_public_key(fixtures / name)
                self.assertEqual(key.key_id, values["keyId"])
                self.assertEqual(key.fingerprint, values["fingerprint"])


class FormatTests(unittest.TestCase):
    def test_canonical_writer(self) -> None:
        data = registry_lib.canonical_bytes({"b": 1, "a": "é"})
        self.assertEqual(
            data,
            '{\n  "a": "é",\n  "b": 1\n}\n'.encode("utf-8"),
        )
        self.assertEqual(registry_lib.loads_strict(data), {"a": "é", "b": 1})

    def test_rejects_noncanonical(self) -> None:
        for data in (
            b'{\r\n  "a": 1\r\n}\r\n',
            b'\xef\xbb\xbf{\n  "a": 1\n}\n',
            b'{\n  "b": 1,\n  "a": 2\n}\n',
        ):
            with self.assertRaises(registry_lib.RegistryToolError):
                registry_lib.check_canonical_bytes(data)

    def test_registry_id_rule_is_slug_and_g1_compatible(self) -> None:
        self.assertIsNotNone(registry_lib.REGISTRY_ID.fullmatch("red-pen-official"))
        self.assertIsNotNone(registry_lib.REGISTRY_ID.fullmatch("third_party.registry"))
        self.assertIsNotNone(registry_lib.REGISTRY_ID.fullmatch("a" * 128))
        self.assertIsNone(registry_lib.REGISTRY_ID.fullmatch("a" * 129))
        self.assertIsNone(registry_lib.REGISTRY_ID.fullmatch("../escape"))
        self.assertIsNone(registry_lib.REGISTRY_ID.fullmatch("Owner/Repo"))

    def test_safe_relative_path(self) -> None:
        self.assertTrue(registry_lib.safe_relative_path("adapter.lua"))
        self.assertTrue(registry_lib.safe_relative_path("lib/helper.lua"))
        for value in ("/etc/passwd", "../escape", "a/../b", "a\\b", "", None):
            self.assertFalse(registry_lib.safe_relative_path(value))

    def test_ci_config_enforces_official_identity_and_environment(self) -> None:
        config = {
            "registryId": "red-pen-official",
            "tier": "official",
            "signing": {
                "enabled": True,
                "environment": "registry-signing-official",
            },
        }
        result = registry_lib.ci_config(config)
        self.assertEqual(result["registry_id"], "red-pen-official")
        self.assertEqual(result["environment"], "registry-signing-official")
        config["registryId"] = "example-registry"
        with self.assertRaises(registry_lib.RegistryToolError):
            registry_lib.ci_config(config)
        config["registryId"] = "red-pen-official"
        config["signing"]["environment"] = "registry-signing-community"
        with self.assertRaises(registry_lib.RegistryToolError):
            registry_lib.ci_config(config)


class ValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = copy_template()

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)

    def errors(self) -> list[str]:
        errors, _ = validate_lib.collect_errors(self.root)
        return errors

    def test_baseline_valid(self) -> None:
        self.assertEqual(self.errors(), [])
        result = subprocess.run(
            [sys.executable, "scripts/update.py", "--check", "--root", str(self.root)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_manifest_version_mismatch(self) -> None:
        path = self.root / "example" / "manifest.json"
        manifest = json.loads(path.read_text())
        manifest["version"] = "9.9.9"
        path.write_text(json.dumps(manifest, indent=2) + "\n")
        errors = self.errors()
        self.assertTrue(any("manifest version" in error for error in errors), errors)

    def test_hash_mismatch(self) -> None:
        path = self.root / "example" / "adapter.lua"
        path.write_text(path.read_text() + "\n")
        errors = self.errors()
        self.assertTrue(any("sha256" in error for error in errors), errors)

    def test_duplicate_adapter_id(self) -> None:
        path = self.root / "registry.json"
        registry = json.loads(path.read_text())
        registry["adapters"].append(dict(registry["adapters"][0]))
        path.write_bytes(registry_lib.canonical_bytes(registry))
        errors = self.errors()
        self.assertTrue(any("duplicate" in error for error in errors), errors)

    def test_expired_registry(self) -> None:
        path = self.root / "registry.json"
        registry = json.loads(path.read_text())
        registry["issuedAt"] = "2020-01-01T00:00:00Z"
        registry["expiresAt"] = "2020-02-01T00:00:00Z"
        path.write_bytes(registry_lib.canonical_bytes(registry))
        errors = self.errors()
        self.assertTrue(any("expired" in error for error in errors), errors)

    def test_noncanonical_registry(self) -> None:
        path = self.root / "registry.json"
        path.write_text(json.dumps(json.loads(path.read_text()), indent=4) + "\n")
        errors = self.errors()
        self.assertTrue(any("deterministic JSON" in error for error in errors), errors)

    def test_readme_url_mismatch(self) -> None:
        path = self.root / "registry.json"
        registry = json.loads(path.read_text())
        registry["adapters"][0]["readmeUrl"] = "https://example.com/wrong.md"
        path.write_bytes(registry_lib.canonical_bytes(registry))
        errors = self.errors()
        self.assertTrue(any("readmeUrl" in error for error in errors), errors)

    def test_official_requires_environment_and_signature(self) -> None:
        path = self.root / "registry.config.json"
        config = json.loads(path.read_text())
        config["tier"] = "official"
        config["requireSignature"] = True
        config["signing"]["enabled"] = True
        config["signing"]["environment"] = None
        config["signing"]["keyFile"] = None
        path.write_bytes(registry_lib.canonical_bytes(config))
        errors = self.errors()
        self.assertTrue(any("registry-signing-official" in e for e in errors), errors)
        self.assertTrue(any("red-pen-official" in e for e in errors), errors)
        self.assertTrue(any("keyFile" in e for e in errors), errors)

    def test_wrong_registry_kind(self) -> None:
        path = self.root / "registry.json"
        registry = json.loads(path.read_text())
        registry["kind"] = "red-pen-registry"
        path.write_bytes(registry_lib.canonical_bytes(registry))
        errors = self.errors()
        self.assertTrue(any("kind" in error for error in errors), errors)

    def test_publisher_must_be_string(self) -> None:
        path = self.root / "registry.json"
        registry = json.loads(path.read_text())
        registry["publisher"] = {"name": "Red Pen"}
        path.write_bytes(registry_lib.canonical_bytes(registry))
        errors = self.errors()
        self.assertTrue(any("publisher" in error for error in errors), errors)

    def test_third_party_reserved_registry_id(self) -> None:
        path = self.root / "registry.config.json"
        config = json.loads(path.read_text())
        config["registryId"] = "red-pen-official"
        path.write_bytes(registry_lib.canonical_bytes(config))
        errors = self.errors()
        self.assertTrue(any("reserved" in error for error in errors), errors)

    def test_self_signer_rejected(self) -> None:
        path = self.root / "registry.config.json"
        config = json.loads(path.read_text())
        config["signing"]["signerRepository"] = config["repository"]
        path.write_bytes(registry_lib.canonical_bytes(config))
        errors = self.errors()
        self.assertTrue(any("separate repository" in error for error in errors), errors)

    def test_official_signer_repository_enforced(self) -> None:
        path = self.root / "registry.config.json"
        config = json.loads(path.read_text())
        config["tier"] = "official"
        config["registryId"] = "red-pen-official"
        config["requireSignature"] = True
        config["signing"]["enabled"] = True
        config["signing"]["environment"] = "registry-signing-official"
        config["signing"]["signerRepository"] = "attacker/signer"
        path.write_bytes(registry_lib.canonical_bytes(config))
        errors = self.errors()
        self.assertTrue(
            any("expected signer repository" in error for error in errors), errors
        )

    def test_stale_release_requires_pre_signing_skip(self) -> None:
        (self.root / "release.json").write_bytes(
            registry_lib.canonical_bytes({"schema": 1, "sequence": 999})
        )
        errors = self.errors()
        self.assertTrue(any("release.json" in error for error in errors), errors)
        pre_signing, _ = validate_lib.collect_errors(
            self.root, skip_release=True
        )
        self.assertEqual(pre_signing, [])

    def test_update_check_detects_stale_registry(self) -> None:
        manifest = self.root / "example" / "manifest.json"
        data = json.loads(manifest.read_text())
        data["description"] = "Changed description"
        manifest.write_text(json.dumps(data, indent=2) + "\n")
        result = subprocess.run(
            [sys.executable, "scripts/update.py", "--check", "--root", str(self.root)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("out of date", result.stderr)


@unittest.skipUnless(HAS_MINISIGN, "minisign is not installed")
class SigningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.root = copy_template()
        self.keys = Path(tempfile.mkdtemp(prefix="redpen-template-keys-"))
        self.password = "test-" + os.urandom(12).hex()
        self.secret = self.keys / "test.key"
        self.public = self.keys / "test.pub"
        sign_lib.generate_key(self.secret, self.public, self.password)

    def tearDown(self) -> None:
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.keys, ignore_errors=True)

    def prepare(self) -> Path:
        path = self.root / "registry.json"
        registry = json.loads(path.read_text())
        now = registry_lib.utc_now()
        registry["sequence"] += 1
        registry["issuedAt"] = registry_lib.format_timestamp(now)
        registry["expiresAt"] = registry_lib.format_timestamp(now + timedelta(days=180))
        path.write_bytes(registry_lib.canonical_bytes(registry))
        return path

    def test_sign_verify_and_tamper(self) -> None:
        registry = self.prepare()
        signature = self.root / "registry.json.minisig"
        result = sign_lib.sign_registry(
            registry,
            signature,
            self.secret,
            self.public,
            self.root / "registry.config.json",
            self.password,
        )
        self.assertEqual(result["registryId"], "example-registry")
        verified = verify_lib.verify(
            registry, signature, self.public, config_path=self.root / "registry.config.json"
        )
        self.assertTrue(verified["valid"])

        registry.write_bytes(registry.read_bytes() + b" ")
        with self.assertRaises(registry_lib.RegistryToolError):
            verify_lib.verify(
                registry,
                signature,
                self.public,
                config_path=self.root / "registry.config.json",
            )

    def test_wrong_key_and_wrong_comment(self) -> None:
        registry = self.prepare()
        signature = self.root / "registry.json.minisig"
        sign_lib.sign_registry(
            registry,
            signature,
            self.secret,
            self.public,
            self.root / "registry.config.json",
            self.password,
        )
        other = self.keys / "other"
        other.mkdir()
        other_secret = other / "other.key"
        other_public = other / "other.pub"
        sign_lib.generate_key(other_secret, other_public, self.password)
        with self.assertRaises(registry_lib.RegistryToolError):
            verify_lib.verify(registry, signature, other_public)

        bad_signature = self.root / "bad.minisig"
        sign_lib.sign_file(
            self.secret,
            registry,
            bad_signature,
            "registryId=example-registry sequence=999",
            self.password,
        )
        with self.assertRaises(registry_lib.RegistryToolError):
            verify_lib.verify(registry, bad_signature, self.public)

    def test_cli_test_key_dry_run(self) -> None:
        env = dict(os.environ)
        env["MINISIGN_BIN"] = registry_lib.find_minisign()
        result = subprocess.run(
            [sys.executable, "scripts/sign.py", "--test-key"],
            cwd=self.root,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("tamper rejected", result.stdout)

    def test_key_id_cli(self) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/key_id.py", "--public-key", str(self.public), "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertRegex(payload["keyId"], r"^[0-9A-F]{16}$")
        self.assertRegex(payload["fingerprint"], r"^[0-9a-f]{64}$")

    def test_signed_registry_passes_validation(self) -> None:
        registry = self.prepare()
        signature = self.root / "registry.json.minisig"
        sign_lib.sign_registry(
            registry,
            signature,
            self.secret,
            self.public,
            self.root / "registry.config.json",
            self.password,
        )
        config_path = self.root / "registry.config.json"
        config = json.loads(config_path.read_text())
        config["requireSignature"] = True
        config["signing"]["enabled"] = True
        config["signing"]["keyFile"] = "keys/test.pub"
        config["signing"]["environment"] = "registry-signing-third-party"
        (self.root / "keys").mkdir(exist_ok=True)
        (self.root / "keys" / "test.pub").write_bytes(self.public.read_bytes())
        config_path.write_bytes(registry_lib.canonical_bytes(config))
        registry_doc = json.loads(registry.read_text())
        key = registry_lib.read_public_key(self.public)
        release = {
            "schema": 1,
            "kind": "red-pen-adapters-release",
            "registryId": registry_doc["registryId"],
            "tier": config["tier"],
            "sequence": registry_doc["sequence"],
            "tag": f"registry-v{registry_doc['sequence']}",
            "issuedAt": registry_doc["issuedAt"],
            "expiresAt": registry_doc["expiresAt"],
            "registrySha256": registry_lib.sha256_file(registry),
            "signatureSha256": registry_lib.sha256_file(signature),
            "keyId": key.key_id,
            "publicKeyFingerprint": key.fingerprint,
            "signerCommit": config["signing"]["signerCommit"],
            "workflowRun": None,
            "generatedAt": registry_doc["issuedAt"],
        }
        (self.root / "release.json").write_bytes(
            registry_lib.canonical_bytes(release)
        )
        errors, summary = validate_lib.collect_errors(
            self.root, require_signature=True
        )
        self.assertEqual(errors, [])
        self.assertTrue(summary["signature"]["valid"])


if __name__ == "__main__":
    unittest.main()
