# Interrupted operations

Read the checkpoint and inspect actual state. tmux preserves a disconnected terminal session, not a running process across reboot. The persistent USB retains nonsecret work; provider login and masked installation secrets may need repeating.

Use chrysalis_system action=inspect for the approved target, including while uncertain. It verifies stable disk identity and ancestry, refuses the running medium and reports foreign or outside mounts. Recovery may unmount only this target's /mnt subtree; it refuses another device beneath that tree or approved-device mounts elsewhere.

An interrupted format or installation is uncertain. Do not call destructive installation again. Use chrysalis_system action=recover only after inspecting the existing layout. It reuses disko-install mount mode and refuses changed source or disk identity. An ambiguous process on the current boot requires restarting the persistent USB first. A normal observed process exit permits the bounded mount-only recovery path.

A completed installation can finish handoff after restart without formatting. A private hash-only journal distinguishes this installation's partial copies from independent target edits. Changing USB sessions after restart can be transferred over those owned partial bytes; unrelated edits cause a useful refusal. Provider-secret contents never enter that USB journal. A completed handoff never overwrites later installed configuration/state.

An interrupted switch may already have changed the system profile. Compare the profile, running closure and services. Its privileged child may still be running after a disconnect or structured timeout failure. The persistent busy marker survives outcome closure and blocks later mutation until confirmed completion or a new boot. Observation alone cannot clear it. Status, inspection and reconciliation remain available.

The installed outcome binds an observed recovery generation. Use that exact target with the pinned generations rollback tool. A different historical generation needs native /chrysalis system rollback <number>, which shows the observed target and authorizes recovery. Do not overlap a live operation. Observe the actual profile and running closure afterward; rollback does not restore arbitrary vault data or service migrations.

Native controls can revoke an outcome after its in-flight context finishes. Revocation does not undo changes or certify success. Reconciliation preserves uncertainty even if the expected closure appears correct without adequate completion/health evidence.

Ledger projection retries from private receipts using stable event IDs, writer locks, raw revisions and a fixed destination. Resolve a collision while preserving edits; rerunning projection must not duplicate completed entries.
