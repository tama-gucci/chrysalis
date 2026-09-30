"""
Optional provider integration helpers for Chrysalis modular ingestion.
Each provider module handles transport discovery, pagination, and normalization
into the versioned Chrysalis Ingestion Input Contract (v1.0.0) without performing
vault mutations or external write-backs.
"""
