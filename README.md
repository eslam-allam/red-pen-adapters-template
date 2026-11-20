# Red Pen adapter registry template

A GitHub template for a Red Pen adapter registry. It gives you a schema 6
signed index, deterministic JSON, SHA-256 file authentication, a minisign
signing workflow, a test-key dry run, validation, release artifacts, and the
documentation needed to operate a registry safely.

Use this template for the official registry, the community registry, or your
own third-party registry. The trust tier is declared in
`registry.config.json`; the app decides how much to trust it.

## What is in the box

```
registry.json                 Signed index (schema 6)
registry.config.json          Registry identity, tier, signing settings
example/                      A minimal working adapter
schemas/                      registry, manifest, and registry.config schemas
scripts/registry.py           Canonical JSON, key ids, CI config helpers
scripts/update.py             Regenerate registry.json from adapter folders
scripts/validate.py           Schema, hash, runtime, and signature validation
scripts/sign.py               Local signing and test-key dry run
scripts/verify.py             Exact-byte signature verification
scripts/key_id.py             Print a public key id and fingerprint
tests/                        Unit and regression tests
docs/                         Format, signing, publishing, rotation, security
.github/workflows/            validate, sign, sign dry run, release
.github/actions/              Pinned minisign installer
keys/                         Public keys only (no secret material)
```

## Quick start

```sh
python -m pip install jsonschema
python scripts/update.py
python scripts/validate.py
python tests/run.py
```

With minisign installed, also exercise the encrypted-key path without any
production secret:

```sh
python scripts/sign.py --test-key
```

## Registry format

`registry.json` is schema 6. Its exact bytes are signed with a detached
minisign signature (`registry.json.minisig`). The index authenticates every
adapter file by SHA-256, so the app never trusts a manifest or script from an
unsigned source.

The signed document carries:

- `schema: 6`, `kind: "red-pen-adapters"`;
- a globally unique lowercase slug `registryId` (official `red-pen-official`, community `red-pen-community`);
- a string `publisher`, `sequence`, `issuedAt`, and `expiresAt`;
- one entry per adapter, with `folder`, `files[{path, sha256}]`, and
  `readmeUrl`.

See [docs/format.md](docs/format.md) for every field and the deterministic JSON
rules.

## Signing

- Exact bytes, no JCS. The file is written with sorted keys, two-space indent,
  LF, and one trailing newline.
- minisign 0.12 with a password-encrypted key. Production keys are never
  unencrypted (`-W` is not used).
- Official and community registries use **different keys** in separate
  protected environments: `registry-signing-official` and
  `registry-signing-community`.
- The signing job checks out `eslam-allam/red-pen-registry-signing` at the
  commit SHA in `registry.config.json`. It never executes signing code from the
  commit being signed.
- Pull requests never receive signing secrets. A separate workflow runs a
  throwaway encrypted test key on every PR.
- The signer tags `registry-v<sequence>` and uploads `registry.json`,
  `registry.json.minisig`, `registry.sha256`, and `release.json`.

See [docs/signing.md](docs/signing.md) and [docs/key-rotation.md](docs/key-rotation.md).

## Trust tiers

| Tier | Meaning |
| --- | --- |
| `official` | Operated by the Red Pen project; signed key embedded in the app. |
| `community` | Community-run; signed by a separate key embedded in the app, off by default. |
| `third-party` | At your own risk; unsigned or signed with a key the app does not know, after explicit consent. |

The tier in `registry.config.json` is for CI and documentation. The app must
derive trust from the registry URL and the embedded public key, never from a
self-asserted field.

## Publishing

1. Create a repository from this template.
2. Set a unique lowercase slug `registryId` (official `red-pen-official`, community `red-pen-community`), `repository`, and `readmeBaseUrl`.
3. Generate keys outside the repository; commit only `keys/<name>.pub`.
4. Create the protected environment with required reviewers and the
   `MINISIGN_SECRET_KEY_B64` / `MINISIGN_PASSWORD` environment secrets.
5. Pin the signer repository and commit in `registry.config.json`.
6. Run validation, then dispatch the signing workflow (or push to `main`).

See [docs/publishing.md](docs/publishing.md).

## License

MIT. See [LICENSE](LICENSE).
