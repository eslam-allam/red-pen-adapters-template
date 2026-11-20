# Security policy

## Reporting a vulnerability

Report suspected signature bypasses, key compromise, malicious adapters, or
sandbox escape privately to the registry maintainers. Do not include private
keys, passwords, student data, or exploit details in a public issue.

Use GitHub's private vulnerability reporting for this repository when enabled,
or contact the maintainers listed in `CODEOWNERS`.

Include:

- affected registry URL and `registryId`;
- `sequence`, key id, and public-key fingerprint (never a secret);
- steps to reproduce;
- impact and any known exploitation.

We aim to acknowledge a report within 72 hours and to publish a coordinated
advisory after a fix or revocation is available.

## Signing keys

Each tier uses independent keys. Only public keys, key ids, and fingerprints
belong in this repository.

| Tier | Key name | Key id | SHA-256 fingerprint | Owner |
| --- | --- | --- | --- | --- |
| official | TBD | TBD | TBD | TBD |
| official (next) | TBD | TBD | TBD | TBD |
| community | TBD | TBD | TBD | TBD |
| community (next) | TBD | TBD | TBD | TBD |

Replace the placeholders when keys are created. The private keys, passwords,
and offline backup locations stay in the private operator runbook, never here.

Key ids are uppercase, byte-reversed 8-byte minisign ids; fingerprints are
the SHA-256 of the exact `.pub` file bytes. Both are derived from
`keys/<name>.pub`:

```sh
python scripts/key_id.py --public-key keys/<name>.pub --json
```

## Supported versions

Security fixes apply to the current signed registry sequence and the app
release that embeds the current and next public keys. Historical signed tags
are retained for audit but are not re-signed.

## Scope

In scope:

- the registry index, signature, workflows, scripts, schemas, and public keys;
- adapter code and manifests published by this registry;
- the signing environment configuration.

Out of scope:

- vulnerabilities in third-party adapters from other registries;
- GitHub platform vulnerabilities;
- denial of service against GitHub or the app's download host.

## No secrets

This repository must never contain a private key, password, token, student
file, or build output. If one is committed, treat it as compromised, rotate the
key, and rewrite the repository only after revocation.
