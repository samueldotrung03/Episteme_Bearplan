# Credential location decision

On November 6, the user confirmed the app data folder's `secrets/` directory
as the location for connection credentials. This resolves the difference
between the earlier instructions supplied in chat and the checked-in guidance,
which records a November 3 move out of the repository. The existing
implementation already uses the confirmed location and supports the
`BEARPLANS_SECRETS_FILE` override.

On macOS 26.6.2 arm64, disposable tests passed:

```sh
.venv/bin/python -m pytest -q -p no:cacheprovider -p tests.connections_sandbox \
  tests/test_secrets_location.py tests/test_connections.py
```

Result: 40 passed. No credential contents were inspected or changed.
