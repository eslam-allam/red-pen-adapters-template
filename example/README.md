# Example adapter

A minimal file adapter used by the registry template. It counts non-empty
lines in a submitted text file and compares the count with the key answer.

- **Version:** 1.0.0
- **Works on:** files
- **File extensions:** .txt, .md, .text
- **Permissions:** none

## How it works

The adapter calls `app.read_file` inside the sandbox, counts non-empty lines,
and returns a diff output. It declares no runtime and no permissions, so it
runs on every platform supported by the app.

Replace this folder with a real adapter, then run:

```sh
python scripts/update.py
python scripts/validate.py
```

The generated `files` entries in `registry.json` include a SHA-256 digest for
every runtime file. The signed index is what authenticates those files.
