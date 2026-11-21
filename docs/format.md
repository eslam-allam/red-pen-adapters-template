# Registry format (schema 6)

A registry is a folder of adapters plus one signed index. The app downloads
`registry.json`, verifies its signature, then downloads only the files the
signed index lists and checks their SHA-256 digests.

## Layout

```
registry.json
registry.json.minisig        created by the signing workflow
registry.config.json
schemas/
keys/
<adapter-id>/
  manifest.json
  adapter.lua
  README.md
  assets/                    optional, referenced by README only
```

An adapter folder may contain additional runtime files (for example
`lib/helper.lua`). `scripts/update.py` lists every non-hidden file except
`README.md` and `assets/**` in the registry entry, so it is downloaded and
authenticated. Keep secrets, tests, and build output out of adapter folders.

## registry.json

```json
{
  "$schema": "./schemas/registry.schema.json",
  "schema": 6,
  "kind": "red-pen-adapters",
  "registryId": "example-registry",
  "name": "Example Red Pen adapter registry",
  "description": "Optional summary",
  "publisher": "Example publisher",
  "sequence": 1,
  "issuedAt": "2026-11-20T21:00:00Z",
  "expiresAt": "2027-05-19T21:00:00Z",
  "adapters": []
}
```

| Field | Rules |
| --- | --- |
| `schema` | Exactly `6`. |
| `kind` | Exactly `red-pen-adapters`. |
| `registryId` | Globally unique lowercase slug, `^[a-z0-9][a-z0-9._-]{0,127}$`, no slashes. Official is `red-pen-official`; community is `red-pen-community`; third-party registries may not use those reserved ids. Must match `registry.config.json` and the signature's trusted comment. |
| `name` | Human-readable registry name. |
| `publisher` | Non-empty display-name string, at most 256 characters, no control characters. The app parses this as a string, not an object. |
| `sequence` | Integer `>= 1`, strictly increasing. The workflow tags `registry-v<sequence>`. |
| `issuedAt` | RFC 3339 UTC, seconds precision, `YYYY-MM-DDTHH:MM:SSZ`. |
| `expiresAt` | UTC, later than `issuedAt`; at most 366 days later. Verification refuses an expired registry. |
| `adapters` | Non-empty array of entries. |

`sequence`, `issuedAt`, and `expiresAt` are owned by the signer. Do not bump
them by hand in a pull request; the signing workflow sets them.

## Adapter entry

```json
{
  "id": "example",
  "name": "Example line counter",
  "version": "1.0.0",
  "description": "Counts non-empty lines.",
  "author": "Red Pen Template",
  "appliesTo": ["file"],
  "permissions": [],
  "extensions": ["txt", "md"],
  "folder": "example",
  "files": [
    { "path": "adapter.lua", "sha256": "..." },
    { "path": "manifest.json", "sha256": "..." }
  ],
  "readmeUrl": "https://raw.githubusercontent.com/OWNER/REPO/main/example/README.md"
}
```

The entry mirrors the install-gating parts of `manifest.json`: `name`,
`version`, `description`, `author`, `extensions`, `appliesTo`, `permissions`,
`registry`, and `runtimes`. `scripts/update.py` copies them and
`scripts/validate.py` refuses a mismatch. Never edit only one side.

`files` must be objects with `path` and lowercase `sha256`. Bare file strings
are rejected in schema 6 because the signed index has to authenticate every
byte. Paths are relative, use `/`, and may not contain `..`, an absolute path, a
backslash, a colon, or control characters. `manifest.json` and `adapter.lua`
are required.

`readmeUrl` must be
`<readmeBaseUrl>/<adapter-id>/README.md`. The README may reference
`assets/...`; assets are fetched for display but are not installed.

Optional `bootstrap` mirrors the manifest gating fields. It is an object with
`mise` and/or `uv`; values are `latest`, `null`, or a full SemVer 2.0.0 pin
(optional `v` prefix, prerelease, and build metadata). Arbitrary strings are
rejected. A managed runtime requires non-empty `bootstrap.mise`, and a
bootstrap without a managed runtime is rejected.

## manifest.json

`schemas/manifest.schema.json` is the app-facing manifest schema. Keep using
the manifest schema version the app supports (currently `schema: 4`). The
registry entry does not repeat `output`, `keyInput`, `questionInput`,
`directories`, or `directoryPicker`; those live only in the manifest and are
covered by the manifest's SHA-256 entry. `bootstrap` is mirrored so the signed
index can gate it, and the two copies must match.

Runtime rules enforced by the template validator:

- a `runtimes[].setting` must name a settings field;
- a `runtimes[].packages.setting` must name a settings field;
- `runtimes[].version` must equal the setting's default;
- a select default must be one of its options;
- only the `conda:` backend prefix is allowed, never `asdf:` or `vfox:`.

## Deterministic JSON

`registry.json` and `registry.config.json` are written with:

- UTF-8, no BOM;
- keys sorted lexicographically;
- two-space indentation;
- LF line endings only;
- exactly one trailing newline.

Use `python scripts/registry.py format registry.json registry.config.json` and
check it with `--check`. `python scripts/update.py --check` also fails when the
index does not match the adapter folders. There is no JCS canonicalisation: the
bytes on disk are the bytes that are signed.

## Updating an adapter

1. Edit the manifest and adapter files.
2. Bump `manifest.version` and the README `- **Version:**` line.
3. Run `python scripts/update.py` to refresh mirrored fields and checksums.
4. Run `python scripts/validate.py`.
5. Commit the adapter, `registry.json`, and any README changes in one pull
   request.

The signing workflow revalidates, bumps `sequence`, refreshes the timestamps,
signs, tags, and publishes.

## Compatibility with schema 5

Older apps read `name` and `adapters`, which schema 6 keeps. Schema 6 adds
`kind`, `registryId`, `publisher`, `sequence`, `issuedAt`, `expiresAt`, and
requires checksum objects. An app that does not understand schema 6 must refuse
the registry rather than silently treat it as schema 5. Keep the `main` URL
working during migration.
