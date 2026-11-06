-- Which Google account BearPlans syncs with (2026-11-03). Lists, tasks, the BearPlans
-- calendar and its events exist only in that account, so another account must not
-- reuse these links. account_key is a one-way hash of the account's primary calendar
-- ID (no email address is stored). other_account_key is set while the user is signed
-- in to a different account, until they sign back in or choose "Use this account".
ALTER TABLE google_sync ADD COLUMN account_key TEXT;
ALTER TABLE google_sync ADD COLUMN other_account_key TEXT;
