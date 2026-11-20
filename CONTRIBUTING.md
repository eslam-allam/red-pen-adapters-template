# Contributing

Thanks for contributing a Red Pen adapter. Adapters run against student work,
so correctness and least privilege matter more than breadth.

## Before you start

- Read [docs/format.md](docs/format.md) and [docs/security.md](docs/security.md).
- Do not commit secrets, credentials, student files, models, or build output.
- Keep an adapter self-contained in its folder.
- Use the smallest permission set that works. Prefer sandbox-internal reads and
  no runtime over `subprocess` or `network`.

## Adding or updating an adapter

1. Copy the `example/` folder layout. The folder name and `manifest.id` must be
   the same lowercase id.
2. Add `manifest.json`, `adapter.lua`, and `README.md`. The README needs a
   `- **Version:** x.y.z` line that matches the manifest.
3. Bump the manifest version for every behavior change.
4. Declare only the extensions, targets, permissions, directories, and runtimes
   the adapter actually uses.
5. Make timeouts and failures return **no score** (or a clear error), never a
   silent zero.
6. Run:

   ```sh
   python scripts/update.py
   python scripts/registry.py format registry.json registry.config.json
   python scripts/validate.py
   python tests/run.py
   ```

7. Commit the adapter, README, and regenerated `registry.json` together.

Never edit `sequence`, `issuedAt`, `expiresAt`, or `registry.json.minisig` by
hand. The signing workflow owns them.

## Review checklist

- The adapter does not escape its sandbox or read files it did not request.
- Network and subprocess use is justified and minimal.
- The manifest and registry entry agree.
- Every file is listed with a SHA-256 digest.
- Runtime tool/version/default/options agree.
- The README explains setup and expected output.
- Tests do not weaken existing checks.
- No secret, key, password, token, or student data is present.

## Signing and keys

- Never commit a `.key` or `.password` file.
- Never request a signing environment for a pull request.
- Only maintainers may change `schemas/`, `scripts/`, `keys/`, `CODEOWNERS`, or
  `.github/workflows/`.
- Signer changes are a separate reviewed change with a new pinned SHA.

## Commit messages

Use a short imperative subject, for example:

- `feat(adapter): add R adapter`
- `fix(python): refresh runtime version`
- `docs: explain key rotation`

The signer commits `chore(registry): sign sequence <n>` itself.

## License

By contributing, you agree that your contribution is licensed under the
repository's MIT license.
