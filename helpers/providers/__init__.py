"""
Optional provider integration helpers for Chrysalis modular integrations.
Each provider module handles transport access, pagination/lookup, and normalization
into versioned Chrysalis Capability Contracts (`v1.0.0`) (`contracts/integration-capabilities.contract.md`
and `contracts/ingestion-input.contract.md`) without performing unauthorized vault mutations
or external write-backs.
"""
