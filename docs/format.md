# Registry format (schema 7, manifest 5, API 2)

A registry is a folder of adapters plus one signed index. The app downloads
`registry.json`, verifies its signature, then downloads only the files the
signed index lists and checks their SHA-256 digests.

## Layout

```
registry.json
registry.json.minisig        created by the signing workflow
registry.config.json
schemas/
  manifest.schema.json       copied from the app contract
  registry.schema.json       copied from the app contract
  mirror-fields.json         copied from the app contract
  source.json                app commit and SHA-256 of each copied file
lua/
  red-pen-api.lua            copied from the app contract (documentation)
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

Do not edit the copied contract files by hand. A schema or API change belongs
in the app contract first, then `schemas/source.json` is refreshed with the new
app commit and the new digests.

## registry.json

```json
{
  "$schema": "./schemas/registry.schema.json",
  "schema": 7,
  "kind": "red-pen-adapters",
  "registryId": "example-registry",
  "publisher": "Example publisher",
  "sequence": 1,
  "issuedAt": "2026-11-20T21:00:00Z",
  "expiresAt": "2027-05-19T21:00:00Z",
  "adapters": []
}
```

| Field | Rules |
| --- | --- |
| `schema` | Exactly `7`. |
| `kind` | Exactly `red-pen-adapters`. |
| `registryId` | Globally unique lowercase slug, `^[a-z0-9][a-z0-9._-]{0,127}$`, no slashes. Official is `red-pen-official`; community is `red-pen-community`; third-party registries may not use those reserved ids. Must match `registry.config.json` and the signature's trusted comment. |
| `publisher` | Non-empty display-name string, at most 256 characters, no control characters. The app parses this as a string, not an object. |
| `sequence` | Integer `>= 1`, strictly increasing. The workflow tags `registry-v<sequence>`. |
| `issuedAt` | RFC 3339 UTC, seconds precision, `YYYY-MM-DDTHH:MM:SSZ`. |
| `expiresAt` | UTC, later than `issuedAt`; at most 366 days later. Verification refuses an expired registry. |
| `adapters` | Array of entries. An empty array is valid and installs nothing. |

There is no root `name`, `description`, or `homepage` in schema 7. Use
`publisher` for the human-readable publisher; a legacy document that still has
a root `name` is rejected.

`sequence`, `issuedAt`, and `expiresAt` are owned by the signer. Do not bump
them by hand in a pull request; the signing workflow sets them.

## Adapter entry

```json
{
  "apiVersion": 2,
  "id": "example",
  "name": "Example line counter",
  "version": "1.0.0",
  "description": "Counts non-empty lines.",
  "author": "Red Pen Template",
  "appliesTo": ["file"],
  "permissions": [],
  "extensions": ["txt", "md"],
  "settings": [],
  "keyInput": [{ "key": "expectedLines", "label": "Expected lines", "type": "number" }],
  "questionInput": [],
  "output": { "kinds": ["diff"], "label": "Line count" },
  "folder": "example",
  "files": [
    { "path": "adapter.lua", "sha256": "..." },
    { "path": "manifest.json", "sha256": "..." }
  ],
  "readmeUrl": "https://raw.githubusercontent.com/OWNER/REPO/main/example/README.md"
}
```

`apiVersion` is exactly `2`. Every entry also mirrors the manifest fields listed
in `schemas/mirror-fields.json`:

`name`, `description`, `author`, `icon`, `homepage`, `extensions`, `appliesTo`,
`permissions`, `registry`, `runtimes`, `bootstrap`, `settings`, `keyInput`,
`questionInput`, `output`, `directories`, and `directoryPicker`.

`scripts/update.py` copies them and `scripts/validate.py` refuses a mismatch.
Never edit only one side.

`files` must be objects with `path` and a lowercase `sha256`. Bare file strings
are rejected: the signed index has to authenticate every byte. `sha256` is
optional at the schema level for an unsigned third-party registry, but the
official and community validators require it for every file, and the template
examples always include it. Paths are relative, use `/`, and may not contain
`..`, an absolute path, a backslash, a colon, or control characters.
`manifest.json` and `adapter.lua` are required.

`readmeUrl` must be
`<readmeBaseUrl>/<adapter-id>/README.md`. The README may reference
`assets/...`; assets are fetched for display but are not installed.

Optional `bootstrap` mirrors the manifest gating fields. It is an object with
`mise` and/or `uv`; values are `latest`, `null`, or the pinned bootstrap version
the app supports. A managed runtime requires non-empty `bootstrap.mise`, and a
bootstrap without a managed runtime is rejected.

## manifest.json

`schemas/manifest.schema.json` is the app-facing manifest schema. The app
supports manifest `schema: 5` and API `apiVersion: 2`; both are required.

```json
{
  "$schema": "../schemas/manifest.schema.json",
  "schema": 5,
  "apiVersion": 2,
  "id": "example",
  "name": "Example line counter",
  "version": "1.0.0",
  "extensions": ["txt"],
  "appliesTo": ["file"],
  "output": { "kinds": ["diff"] },
  "permissions": [],
  "keyInput": [],
  "settings": [],
  "questionInput": []
}
```

`output` is required and declares `kinds` from `none`, `text`, `table`,
`tableDiff`, `diff`, `image`, and `json`. `settings` and `keyInput` are
required arrays; `questionInput` is optional. All fields use the v2 field types
and shapes.

Permissions are limited to `network` and `subprocess`. Legacy values such as
`environment`, `files:read`, `files:write`, and `directories` are rejected. Use
`directories`/`directoryPicker` for folder grants instead.

There is no `language` or `miseTool` field. A managed runtime is declared in
`runtimes`, and its primary tool is `runtimes[0].tool` (an empty string when no
runtime is declared):

```lua
local runtime = (manifest.runtimes or {})[1] or {}
local tool = runtime.tool or ""
local version = (request.runtime and request.runtime.version) or runtime.version or "latest"
```

Generated language adapters must use that rule. The app rejects a manifest that
still carries `language` or `miseTool`.

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

## Compatibility with schema 6

Schema 7 targets the v2 app contract. It removes the root `name`, requires
`apiVersion: 2` on every entry and manifest, mirrors the full input/output
surface, and accepts only object file entries with `network`/`subprocess`
permissions. An app that does not understand schema 7 must refuse the registry
rather than silently treat it as schema 6. Keep the `main` URL working during
migration.
