# Runbook: Rotating Postgres Credentials

Rotate the database credentials when a secret may have leaked, on the quarterly
schedule, or when an engineer with access leaves.

## Staging

Run:

```
make rotate-db-creds ENV=staging
```

This triggers a Vault lease renewal for the database role and rolls the
pgbouncer pods so they pick up the new credentials. No application restart is
needed because connections drain gracefully.

## Production

Production rotation is the same command with `ENV=production`, but it must be
run during a change window and announced in `#ops`. Watch the pgbouncer
dashboard for connection errors during the roll; a spike means a pod did not
pick up the new lease and should be restarted manually.

## Verification

After rotation, confirm the old credential is dead:

```
psql "$OLD_DSN" -c 'select 1'   # should fail with authentication error
```
