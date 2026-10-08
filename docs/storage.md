# Vault storage

Originals belong inside the private vault at `Attachments/Originals`. Source records use relative
links such as `[[Attachments/Originals/specification.pdf]]`; supported formats can also use embeds.
Opaque formats need an appropriate application. Raw-byte SHA-256, normalized extracted-text
fingerprints and provider identities remain separate.

Package, vault and external state are absolute disjoint directories. An initialized vault has a
`.chrysalis-vault.json` identity marker. Roots inside Git/package ancestry, node_modules, .agents
or .git are rejected. Symlinks/junctions are rejected rather than followed. Collection queries read
direct children and one-level project roadmaps; deeply nested records are not automatically indexed.

To relocate a vault, stop writers, make a verified independent backup, copy and verify all bytes,
including hidden configuration and the identity marker, then set `CHRYSALIS_VAULT_PATH` to the new
absolute root before launching Pi. The new location must satisfy the same root rules. Keep relative
paths and the vault ID. There is no automatic relocation/profile-rebinding command. Old root-bound
proposals require fresh review. Keep the package/state separate and do not duplicate active writers.

Storage transport and replication are outside package responsibilities. Large originals still need
to be locally accessible when selected for hashing/extraction; a remote placeholder is not readable
original evidence. Another filesystem/device needs its own offline, byte-integrity and concurrency
checks. Desktop is the current acceptance target.
