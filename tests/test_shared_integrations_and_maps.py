"""
Acceptance & Adversarial Test Suite for Capability-Based Integrations, Location/Routing, and Obsidian Maps Projection
====================================================================================================================
Covers all 13 acceptance areas:
1. Core workflow & skill provider neutrality
2. Default-off activation & manual fallback when integrations are unconfigured/disabled
3. Static trusted registry, 5-state readiness evaluation, and secret-reference enforcement
4. Google Maps location resolution (Places API New), ambiguity handling, and place_id-only persistence
5. Google Maps route estimation (Routes API v2), X-Goog-FieldMask, travel window arithmetic (10:00 arrival / 25m trip / 10m buffer -> 09:25 departure), and ephemeral_only persistence blocking
6. Route context fingerprint & staleness invalidation when origin/destination/mode/departure_bucket changes
7. Outbound request privacy sanitization (blocking task titles, notes, tags, project_ref, vault paths)
8. Official Obsidian Maps (obsidianmd/obsidian-maps) projection & cross-map policy gate blocking Google-derived coordinates
9. Single-source ownership synchronization & mismatch detection between location and coordinates
10. Capability rebinding in System/Integrations.md without workflow edits
11. Malformed provider result rejection (fail-closed validation)
12. Backward compatibility with ingestion.sources and legacy ingestion_config
13. Updater (update.py) protection and privacy quarantine (candidate_audit.py) for System/Integrations.md
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest

import yaml

from Development.scripts import candidate_audit
from helpers.ingestion_contract import resolve_ingestion_config
from helpers.integration_registry import (
    TRUSTED_INTEGRATION_ADAPTERS,
    evaluate_all_integrations,
    evaluate_instance_readiness,
    invoke_capability,
    resolve_capability_binding,
    resolve_integration_config,
    resolve_secret_reference,
    validate_capability_result,
)
from helpers.location_routing import (
    compute_route_context_fingerprint,
    enrich_task_location,
    estimate_task_commute,
    evaluate_route_freshness,
    propose_travel_schedule_window,
    validate_task_location_and_travel_fields,
)
from helpers.mdbase_helper import main as mdbase_cli_main, parse_frontmatter, serialize_record, validate_record
from helpers.providers.google_maps import (
    estimate_google_maps_route,
    resolve_google_maps_location,
    sanitize_google_maps_outbound_request,
)
from helpers.providers.obsidian_maps import (
    project_tasks_to_obsidian_maps,
    synchronize_task_map_coordinates,
)
import update


REPO_ROOT = Path(__file__).resolve().parents[1]


class TestSharedIntegrationsAndMaps(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp(prefix="chrysalis_integ_test_"))
        for folder in ("_types", "_contracts", "contracts", "System/_templates", "TaskNotes/Tasks", "TaskNotes/Views"):
            src = REPO_ROOT / folder
            dst = self.temp_dir / folder
            if src.exists():
                shutil.copytree(src, dst, dirs_exist_ok=True)
        shutil.copy2(REPO_ROOT / "mdbase.yaml", self.temp_dir / "mdbase.yaml")
        # Initialize default Memory.md from template (all integrations disabled by default)
        mem_tpl = (REPO_ROOT / "System/_templates/Memory.template.md").read_text(encoding="utf-8")
        mem_text = (
            mem_tpl.replace("{{TIMESTAMP}}", "2026-09-29T10:00:00-05:00")
            .replace("{{SESSION_ID}}", "test-01")
            .replace("{{TIMEZONE_OFFSET}}", "-05:00")
            .replace("{{HORIZON_DATE}}", "2026-10-13")
        )
        (self.temp_dir / "System/Memory.md").write_text(mem_text, encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # ------------------------------------------------------------------
    # 1. Core Workflow & Skill Provider Neutrality
    # ------------------------------------------------------------------
    def test_01_core_workflows_and_skills_are_provider_neutral(self) -> None:
        core_skills = [
            "ingest",
            "task",
            "plan",
            "audit",
            "evening",
            "morning",
            "calibrate",
            "project",
            "zettel",
        ]
        forbidden_provider_tokens = [
            "google-drive",
            "google-tasks",
            "google-maps",
            "obsidian-maps",
            "Google Drive",
            "Google Tasks",
            "Google Maps",
            "Google Calendar",
            "Google Workspace",
            "gtasks-mcp",
        ]
        for skill_name in core_skills:
            skill_path = REPO_ROOT / ".agent/skills" / skill_name / "SKILL.md"
            self.assertTrue(skill_path.is_file(), f"Missing core skill {skill_path}")
            content = skill_path.read_text(encoding="utf-8")
            for token in forbidden_provider_tokens:
                self.assertNotIn(
                    token,
                    content,
                    f"Core skill '{skill_name}' must not reference provider token '{token}'",
                )

        for wf_path in sorted((REPO_ROOT / "System/Workflows").glob("*.md")):
            content = wf_path.read_text(encoding="utf-8")
            for token in forbidden_provider_tokens:
                self.assertNotIn(
                    token,
                    content,
                    f"Workflow '{wf_path.name}' must not reference provider token '{token}'",
                )

    # ------------------------------------------------------------------
    # 2. Default-Off Activation & Manual Fallback
    # ------------------------------------------------------------------
    def test_02_default_off_and_manual_fallback(self) -> None:
        cfg = resolve_integration_config(self.temp_dir)
        instances = cfg["instances"]
        for inst_id in ("media", "quick-capture", "maps", "vault-maps"):
            self.assertIn(inst_id, instances)
            self.assertFalse(
                instances[inst_id]["enabled"],
                f"Instance '{inst_id}' must default to enabled: false in Memory.template.md",
            )

        # Resolving location when maps is disabled yields instance_disabled / binding_missing, while user_coordinates resolves cleanly
        loc_res = enrich_task_location(
            self.temp_dir,
            {"title": "Visit Central Engineering Library"},
            query="Central Engineering Library",
        )
        self.assertEqual(loc_res["status"], "instance_disabled")
        self.assertTrue(loc_res["requires_human_approval"])

        manual_loc_res = enrich_task_location(
            self.temp_dir,
            {"title": "Visit Central Engineering Library"},
            query="Central Engineering Library",
            user_coordinates=[30.2849, -97.7341],
        )
        self.assertEqual(manual_loc_res["status"], "resolved_user_supplied")
        self.assertEqual(manual_loc_res["proposed_frontmatter"]["location"]["provenance"], "user_supplied")
        self.assertTrue(manual_loc_res["proposed_frontmatter"]["location"]["map_display_permitted"])

        commute_res = estimate_task_commute(
            self.temp_dir,
            {
                "title": "Visit Central Engineering Library",
                "timeEstimate": 45,
                "location": manual_loc_res["proposed_frontmatter"]["location"],
                "travel_policy": {
                    "preferred_mode": "driving",
                    "arrival_at": "2026-09-30T10:00:00-05:00",
                    "buffer_minutes": 10,
                    "manual_duration_minutes": 20,
                },
            },
            origin={"label": "North Campus Lab", "address": "North Campus Lab"},
        )
        self.assertEqual(commute_res["status"], "manual_override")
        self.assertEqual(commute_res["duration_minutes"], 20.0)
        window = propose_travel_schedule_window(
            commute_res["proposed_frontmatter"],
            arrival_at="2026-09-30T10:00:00-05:00",
            buffer_minutes=10,
        )
        self.assertEqual(window["proposed_departure_at"], "2026-09-30T09:30:00-05:00")

    # ------------------------------------------------------------------
    # 3. Static Trusted Registry, 5 Readiness States & Secret Policies
    # ------------------------------------------------------------------
    def test_03_trusted_registry_readiness_and_secret_references(self) -> None:
        self.assertEqual(
            set(TRUSTED_INTEGRATION_ADAPTERS.keys()),
            {"google-drive", "google-tasks", "google-maps", "obsidian-maps", "filesystem"},
        )

        # Inline API key secret must be rejected with inline_secret_forbidden
        synthetic_inline_token = "AIza" + "SySyntheticInlineKey123456789012345"
        bad_val, bad_err = resolve_secret_reference(synthetic_inline_token, vault_root=self.temp_dir)
        self.assertIsNone(bad_val)
        self.assertIsNotNone(bad_err)
        self.assertEqual(bad_err["code"], "inline_secret_forbidden")

        # env: secret reference resolves cleanly when environment variable is set
        os.environ["TEST_CHRYSALIS_MAPS_KEY"] = "synthetic_test_key_val"
        try:
            good_val, good_err = resolve_secret_reference("env:TEST_CHRYSALIS_MAPS_KEY", vault_root=self.temp_dir)
            self.assertIsNone(good_err)
            self.assertEqual(good_val, "synthetic_test_key_val")
        finally:
            os.environ.pop("TEST_CHRYSALIS_MAPS_KEY", None)

        # Untrusted integration ID fails closed
        untrusted_eval = evaluate_instance_readiness(
            self.temp_dir,
            {"integration": "untrusted-third-party-plugin", "enabled": True},
        )
        self.assertFalse(untrusted_eval["installed"])
        self.assertEqual(untrusted_eval["adapter_error"]["code"], "unknown_integration_adapter")

    # ------------------------------------------------------------------
    # 4. Google Maps Location Resolution, Ambiguity & Place ID Policy
    # ------------------------------------------------------------------
    def test_04_google_maps_location_resolution_ambiguity_and_policy(self) -> None:
        # Enable maps instance in System/Integrations.md
        integrations_md = {
            "type": "system_memory_extension",
            "id": "integrations-registry",
            "version": "1.0.0",
            "integrations": {
                "contract_version": "1.0.0",
                "instances": {
                    "maps": {
                        "integration": "google-maps",
                        "enabled": True,
                        "access": "read-only",
                        "secret_ref": "env:GOOGLE_MAPS_API_KEY",
                    }
                },
                "bindings": {
                    "task.location_lookup": {
                        "capability": "location.resolve",
                        "instance": "maps",
                    },
                    "plan.route_estimate": {
                        "capability": "routing.estimate",
                        "instance": "maps",
                    },
                },
            },
        }
        (self.temp_dir / "System/Integrations.md").write_text(
            serialize_record(integrations_md, "# Integrations"), encoding="utf-8"
        )

        # Case A: Ambiguous multi-candidate response -> status == "ambiguous" (never silently picks one)
        ambiguous_response = {
            "places": [
                {
                    "id": "ChIJ_synthetic_place_north",
                    "displayName": {"text": "Engineering Annex North"},
                    "formattedAddress": "100 North Campus Dr, Metropolis",
                    "location": {"latitude": 30.2851, "longitude": -97.7341},
                },
                {
                    "id": "ChIJ_synthetic_place_south",
                    "displayName": {"text": "Engineering Annex South"},
                    "formattedAddress": "400 South Campus Dr, Metropolis",
                    "location": {"latitude": 30.2810, "longitude": -97.7390},
                },
            ]
        }
        amb_res = enrich_task_location(
            self.temp_dir,
            {"title": "Deliver Prototype to Engineering Annex"},
            query="Engineering Annex",
            transport=ambiguous_response,
            env={"GOOGLE_MAPS_API_KEY": "synthetic_key"},
        )
        self.assertEqual(amb_res["status"], "ambiguous")
        self.assertEqual(len(amb_res["ephemeral_candidates"]), 2)
        self.assertIsNone(amb_res["proposed_frontmatter"]["location"]["coordinates"])
        self.assertIsNone(amb_res["proposed_frontmatter"]["coordinates"])

        # Case B: Single resolved candidate -> place_id persisted, lat/lng stripped from persistent Markdown
        single_response = {
            "places": [
                {
                    "id": "ChIJ_synthetic_place_north",
                    "displayName": {"text": "Engineering Annex North"},
                    "formattedAddress": "100 North Campus Dr, Metropolis",
                    "location": {"latitude": 30.2851, "longitude": -97.7341},
                }
            ]
        }
        ok_res = enrich_task_location(
            self.temp_dir,
            {"title": "Deliver Prototype to Engineering Annex North"},
            query="Engineering Annex North",
            transport=single_response,
            env={"GOOGLE_MAPS_API_KEY": "synthetic_key"},
        )
        self.assertEqual(ok_res["status"], "resolved")
        persist_loc = ok_res["proposed_frontmatter"]["location"]
        self.assertEqual(persist_loc["provider_ref"]["place_id"], "ChIJ_synthetic_place_north")
        self.assertEqual(persist_loc["persistence_policy"], "place_id_only")
        self.assertFalse(persist_loc["map_display_permitted"])
        self.assertIsNone(persist_loc["coordinates"])
        self.assertIsNone(ok_res["proposed_frontmatter"]["coordinates"])

    # ------------------------------------------------------------------
    # 5. Contextual Route Estimation, Arithmetic & Ephemeral Storage Guard
    # ------------------------------------------------------------------
    def test_05_route_estimation_arithmetic_and_ephemeral_policy_guard(self) -> None:
        # Synthetic scenario from task spec:
        # 10:00 arrival, 25m trip (1500s), 10m buffer -> 09:25 departure
        window = propose_travel_schedule_window(
            {"title": "Deliver Fab Photomask", "timeEstimate": 45},
            route_estimate={"duration_minutes": 25, "duration_unit": "minutes"},
            arrival_at="2026-09-30T10:00:00-05:00",
            buffer_minutes=10,
        )
        self.assertEqual(window["status"], "ok")
        self.assertEqual(window["proposed_departure_at"], "2026-09-30T09:25:00-05:00")
        self.assertEqual(window["proposed_arrival_after_travel_at"], "2026-09-30T09:50:00-05:00")
        self.assertEqual(window["proposed_task_scheduled_at"], "2026-09-30T10:00:00-05:00")
        self.assertEqual(window["occupied_travel_interval"]["total_transit_minutes"], 35.0)
        self.assertEqual(window["task_timeEstimate"], 45)

        # Direct adapter call with synthetic Routes API v2 response (1500s == 25m)
        route_res = estimate_google_maps_route(
            {
                "origin": {"place_id": "ChIJ_origin_01", "label": "North Campus"},
                "destination": {"place_id": "ChIJ_dest_02", "label": "Engineering Annex"},
                "travel_mode": "driving",
                "arrival_by": "2026-09-30T10:00:00-05:00",
                "observed_at": "2026-09-30T09:00:00-05:00",
            },
            transport={
                "routes": [
                    {
                        "duration": "1500s",
                        "distanceMeters": 14200,
                        "routeLabels": ["DEFAULT_ROUTE"],
                    }
                ]
            },
        )
        self.assertEqual(route_res["status"], "ok")
        self.assertEqual(route_res["estimate"]["duration_minutes"], 25.0)
        self.assertEqual(route_res["estimate"]["persistence_policy"], "ephemeral_only")
        self.assertFalse(route_res["estimate"]["map_display_permitted"])

        # Attempting to persist an ephemeral_only Google route_estimate or Google-derived lat/lng in task Markdown fails validation
        bad_task_fm = {
            "type": "task",
            "title": "Deliver Fab Photomask to Annex",
            "status": "todo",
            "dateCreated": "2026-09-29T10:00:00-05:00",
            "created": "2026-09-29T10:00:00-05:00",
            "due": "2026-09-30",
            "scheduled": None,
            "priority": "high",
            "urgency_tier": 3,
            "modality": "kinetic",
            "timeEstimate": 45,
            "energy": "medium",
            "friction": "low",
            "micro_chunked": False,
            "tags": ["task", "pillar-1/setup"],
            "linked_zettels": [],
            "project_ref": None,
            "googleCalendarEventId": None,
            "location": {
                "label": "Engineering Annex North",
                "coordinates": {"latitude": 30.2851, "longitude": -97.7341},
                "provider_ref": {"provider": "google-maps", "place_id": "ChIJ_synthetic_place_north"},
                "provenance": "provider_derived",
                "resolution_status": "resolved",
                "persistence_policy": "place_id_only",
                "map_display_permitted": False,
            },
            "route_estimate": {
                "origin": {"place_id": "ChIJ_origin_01"},
                "destination": {"place_id": "ChIJ_dest_02"},
                "travel_mode": "driving",
                "duration_minutes": 25,
                "duration_unit": "minutes",
                "provider": "google-maps",
                "provenance": "provider_derived",
                "status": "ok",
                "persistence_policy": "ephemeral_only",
                "map_display_permitted": False,
            },
        }
        bad_task_path = self.temp_dir / "TaskNotes/Tasks/example-bad-persistence.md"
        bad_task_path.write_text(serialize_record(bad_task_fm, "# Task"), encoding="utf-8")
        val_bad = validate_record(bad_task_path, bad_task_path.read_text(encoding="utf-8"), collection_dir=self.temp_dir)
        self.assertFalse(val_bad.valid)
        diag_codes = {d.code for d in val_bad.diagnostics}
        self.assertIn("google_derived_coordinates_persistence_forbidden", diag_codes)
        self.assertIn("google_derived_route_persistence_forbidden", diag_codes)

    # ------------------------------------------------------------------
    # 6. Route Staleness Invalidation (context_fingerprint)
    # ------------------------------------------------------------------
    def test_06_route_staleness_invalidation(self) -> None:
        origin_ep = {"place_id": "ChIJ_origin_01"}
        dest_ep = {"place_id": "ChIJ_dest_02"}
        fp1 = compute_route_context_fingerprint(
            origin=origin_ep,
            destination=dest_ep,
            travel_mode="driving",
            arrival_by="2026-09-30T10:00:00-05:00",
        )
        task_with_route = {
            "location": dest_ep,
            "route_estimate": {
                "origin": origin_ep,
                "destination": dest_ep,
                "travel_mode": "driving",
                "arrival_by": "2026-09-30T10:00:00-05:00",
                "duration_minutes": 25,
                "duration_unit": "minutes",
                "freshness": "fresh",
                "status": "ok",
                "context_fingerprint": fp1,
            },
        }
        fresh = evaluate_route_freshness(
            task_with_route,
            origin=origin_ep,
            destination=dest_ep,
            travel_mode="driving",
            arrival_by="2026-09-30T10:00:00-05:00",
        )
        self.assertFalse(fresh["is_stale"])

        # Changing travel mode from driving -> transit invalidates the cached estimate
        stale_mode = evaluate_route_freshness(
            task_with_route,
            origin=origin_ep,
            destination=dest_ep,
            travel_mode="transit",
            arrival_by="2026-09-30T10:00:00-05:00",
        )
        self.assertTrue(stale_mode["is_stale"])
        self.assertEqual(stale_mode["reason"], "context_changed")

    # ------------------------------------------------------------------
    # 7. Outbound Request Privacy Sanitization
    # ------------------------------------------------------------------
    def test_07_outbound_request_privacy_sanitization(self) -> None:
        sanitized, err = sanitize_google_maps_outbound_request(
            {
                "query": "Engineering Annex",
                "title": "Secret Deliverable Task Title",
                "project_ref": "[[Projects/compiler-engineering/Roadmap]]",
            },
            allowed_keys={"query", "region_code", "language_code"},
        )
        self.assertIsNone(sanitized)
        self.assertIsNotNone(err)
        self.assertEqual(err["code"], "excessive_payload_fields_forbidden")
        self.assertIn("title", err["leaked_fields"])
        self.assertIn("project_ref", err["leaked_fields"])

    # ------------------------------------------------------------------
    # 8. Obsidian Maps Projection & Cross-Map Policy Gate
    # ------------------------------------------------------------------
    def test_08_obsidian_maps_projection_and_google_policy_filter(self) -> None:
        # Task 1: User-supplied coordinates -> eligible for Obsidian Maps
        t1_fm = {
            "type": "task",
            "title": "Inspect Sensor Node Alpha",
            "status": "todo",
            "dateCreated": "2026-09-29T10:00:00-05:00",
            "created": "2026-09-29T10:00:00-05:00",
            "due": "2026-09-30",
            "scheduled": None,
            "priority": "normal",
            "urgency_tier": 2,
            "modality": "kinetic",
            "timeEstimate": 45,
            "energy": "medium",
            "friction": "low",
            "micro_chunked": False,
            "tags": ["task", "pillar-1/setup"],
            "linked_zettels": [],
            "project_ref": None,
            "googleCalendarEventId": None,
            "coordinates": [30.2849, -97.7341],
            "location": {
                "label": "Sensor Field Station",
                "coordinates": {"latitude": 30.2849, "longitude": -97.7341},
                "provenance": "user_supplied",
                "resolution_status": "resolved",
                "persistence_policy": "persistent_permitted",
                "map_display_permitted": True,
            },
        }
        # Task 2: Google-derived location -> must be excluded from Obsidian Maps (OpenFreeMap tiles)
        t2_fm = dict(t1_fm)
        t2_fm["title"] = "Google Resolved Venue"
        t2_fm["coordinates"] = [30.2900, -97.7400]
        t2_fm["location"] = {
            "label": "Google Resolved Venue",
            "provider_ref": {"provider": "google-maps", "place_id": "ChIJ_google_only_99"},
            "provenance": "provider_derived",
            "resolution_status": "resolved",
            "persistence_policy": "place_id_only",
            "map_display_permitted": False,
        }

        proj = project_tasks_to_obsidian_maps(
            {
                "records": [
                    {"path": "TaskNotes/Tasks/example-sensor-alpha.md", "frontmatter": t1_fm},
                    {"path": "TaskNotes/Tasks/example-google-venue.md", "frontmatter": t2_fm},
                ]
            }
        )
        self.assertEqual(proj["plugin_id"], "maps")
        self.assertEqual(len(proj["markers"]), 1)
        self.assertEqual(proj["markers"][0]["title"], "Inspect Sensor Node Alpha")
        self.assertEqual(len(proj["filtered_records"]), 1)
        self.assertEqual(
            proj["filtered_records"][0]["reason"],
            "google_derived_cross_map_display_forbidden",
        )

    # ------------------------------------------------------------------
    # 9. Single-Source Ownership Between location and coordinates
    # ------------------------------------------------------------------
    def test_09_coordinate_and_location_single_source_ownership(self) -> None:
        mismatch_fm = {
            "coordinates": [30.2849, -97.7341],
            "location": {
                "label": "Authoritative Location Coordinates",
                "coordinates": {"latitude": 31.5000, "longitude": -98.1000},
                "provenance": "user_supplied",
                "resolution_status": "resolved",
                "persistence_policy": "persistent_permitted",
                "map_display_permitted": True,
            },
        }
        # Validate detects mismatch before synchronization
        issues = validate_task_location_and_travel_fields(mismatch_fm)
        self.assertTrue(any(d["code"] == "coordinates_location_mismatch" for d in issues))

        # Synchronization enforces location.coordinates as single source of truth
        sync_res = synchronize_task_map_coordinates(mismatch_fm)
        self.assertEqual(sync_res["coordinates"], [31.5, -98.1])

    # ------------------------------------------------------------------
    # 10. Capability Rebinding Without Workflow Edits
    # ------------------------------------------------------------------
    def test_10_capability_rebinding_without_workflow_edits(self) -> None:
        # Register a second instance ('maps-secondary') and rebind location.resolve to it in System/Integrations.md
        integrations_md = {
            "type": "system_memory_extension",
            "id": "integrations-registry",
            "version": "1.0.0",
            "integrations": {
                "contract_version": "1.0.0",
                "instances": {
                    "maps-primary": {
                        "integration": "google-maps",
                        "enabled": False,
                        "access": "read-only",
                    },
                    "maps-secondary": {
                        "integration": "google-maps",
                        "enabled": True,
                        "access": "read-only",
                        "secret_ref": "env:GOOGLE_MAPS_API_KEY",
                    },
                },
                "bindings": {
                    "task.location_lookup": {
                        "capability": "location.resolve",
                        "instance": "maps-secondary",
                    },
                },
            },
        }
        (self.temp_dir / "System/Integrations.md").write_text(
            serialize_record(integrations_md, "# Rebound Integrations"), encoding="utf-8"
        )
        binding = resolve_capability_binding(
            self.temp_dir,
            "location.resolve",
            workflow_binding="task.location_lookup",
            env={"GOOGLE_MAPS_API_KEY": "synthetic_key"},
        )
        self.assertEqual(binding["status"], "ok")
        self.assertEqual(binding["instance_id"], "maps-secondary")
        self.assertEqual(binding["integration"], "google-maps")

    # ------------------------------------------------------------------
    # 11. Malformed Provider Result Rejection
    # ------------------------------------------------------------------
    def test_11_malformed_capability_result_rejected(self) -> None:
        bad_route_output = {
            "contract_version": "1.0.0",
            "capability": "routing.estimate",
            "effect": "external_query",
            "status": "ok",
            "estimate": {
                "duration_minutes": -15,  # Negative duration is invalid
                "persistence_policy": "ephemeral_only",
            },
        }
        valid, diags = validate_capability_result(bad_route_output, expected_capability="routing.estimate")
        self.assertFalse(valid)
        codes = {d["code"] for d in diags}
        self.assertIn("invalid_positive_duration", codes)
        self.assertIn("missing_duration_unit", codes)

    # ------------------------------------------------------------------
    # 12. Backward Compatibility with ingestion.sources & CLI Subcommands
    # ------------------------------------------------------------------
    def test_12_backward_compatibility_and_cli_subcommands(self) -> None:
        ing_cfg = resolve_ingestion_config(self.temp_dir)
        self.assertIn("media", ing_cfg["sources"])
        self.assertIn("quick-capture", ing_cfg["sources"])

        # CLI integration-status subcommand returns 0
        rc = mdbase_cli_main(["--vault", str(self.temp_dir), "integration-status"])
        self.assertEqual(rc, 0)

    # ------------------------------------------------------------------
    # 13. Updater Protection & Candidate Privacy Quarantine
    # ------------------------------------------------------------------
    def test_13_updater_protection_and_privacy_quarantine(self) -> None:
        self.assertTrue(update.is_protected_target("System/Integrations.md"))
        self.assertTrue(candidate_audit.quarantined("System/Integrations.md"))
        self.assertTrue(candidate_audit.quarantined("TaskNotes/System/Integrations.md"))

    # ------------------------------------------------------------------
    # 14. Nested 3-Level Bindings & Instance Config Sub-Dict Resolution
    # ------------------------------------------------------------------
    def test_14_nested_integrations_bindings_and_config_subdict_resolution(self) -> None:
        # Verify default Memory.template.md + Integrations.template.md produce 4 clean instances
        cfg = resolve_integration_config(self.temp_dir)
        self.assertEqual(set(cfg["instances"].keys()), {"media", "quick-capture", "maps", "vault-maps"})
        self.assertIn("ingestion.sources.media", cfg["bindings"])
        self.assertEqual(cfg["bindings"]["ingestion.sources.media"]["capability"], "ingestion.discover")
        self.assertEqual(cfg["bindings"]["ingestion.sources.media"]["instance"], "media")

        # Enable 'media' in System/Integrations.md with nested config: sub-dict and nested bindings:
        integrations_override = {
            "type": "system_memory_extension",
            "id": "integrations-registry",
            "version": "1.0.0",
            "integrations": {
                "contract_version": "1.0.0",
                "instances": {
                    "media": {
                        "integration": "google-drive",
                        "enabled": True,
                        "access": "read-only",
                        "config": {
                            "mount_root": "custom-drive-mount",
                            "folder": "Research-Inbox",
                        },
                    },
                },
                "bindings": {
                    "ingestion": {
                        "sources": {
                            "media": {
                                "capability": "ingestion.discover",
                                "instance": "media",
                            }
                        }
                    }
                },
            },
        }
        (self.temp_dir / "System/Integrations.md").write_text(
            serialize_record(integrations_override, "# Integrations Override"), encoding="utf-8"
        )
        ing_cfg = resolve_ingestion_config(self.temp_dir)
        self.assertTrue(ing_cfg["sources"]["media"]["enabled"])
        self.assertEqual(ing_cfg["sources"]["media"]["mount_root"], "custom-drive-mount")
        self.assertEqual(ing_cfg["sources"]["media"]["folder"], "Research-Inbox")

    # ------------------------------------------------------------------
    # 15. Recursive Inline Secret Scan & Structured Diagnostic Codes
    # ------------------------------------------------------------------
    def test_15_recursive_inline_secret_detection_and_string_diagnostic_codes(self) -> None:
        nested_secret_cfg = {
            "type": "system_memory_extension",
            "id": "integrations-registry",
            "version": "1.0.0",
            "integrations": {
                "contract_version": "1.0.0",
                "instances": {
                    "maps": {
                        "integration": "google-maps",
                        "enabled": True,
                        "access": "read-only",
                        "secret_ref": "env:MISSING_TEST_MAPS_SECRET_XYZ",
                        "config": {
                            "api_key": "AIzaSySyntheticNestedInlineKey123456",
                        },
                    }
                },
            },
        }
        (self.temp_dir / "System/Integrations.md").write_text(
            serialize_record(nested_secret_cfg, "# Nested Secret Test"), encoding="utf-8"
        )
        report = evaluate_all_integrations(self.temp_dir, env={})
        maps_diags = report["instances"]["maps"]["diagnostics"]
        codes = [d["code"] for d in maps_diags]
        for code in codes:
            self.assertIsInstance(code, str)
        self.assertIn("inline_secret_forbidden", codes)
        self.assertIn("secret_unresolved", codes)

    def _load_task_fm(self) -> Dict[str, Any]:
        fm, _ = parse_frontmatter((self.temp_dir / "TaskNotes/Tasks/example-task.md").read_text(encoding="utf-8"))
        return dict(fm)

    def _enable_maps_instance(self) -> None:
        integrations_md = {
            "type": "system_memory_extension",
            "id": "integrations-registry",
            "version": "1.0.0",
            "integrations": {
                "contract_version": "1.0.0",
                "instances": {
                    "maps": {
                        "integration": "google-maps",
                        "enabled": True,
                        "access": "read-only",
                        "secret_ref": "env:GOOGLE_MAPS_API_KEY",
                    }
                },
                "bindings": {
                    "task.location_lookup": {
                        "capability": "location.resolve",
                        "instance": "maps",
                    },
                    "plan.route_estimate": {
                        "capability": "routing.estimate",
                        "instance": "maps",
                    },
                },
            },
        }
        (self.temp_dir / "System/Integrations.md").write_text(
            serialize_record(integrations_md, "# Integrations"), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # 16. Google place_id -> Manual Coordinate Override & Route Invalidation
    # ------------------------------------------------------------------
    def test_16_google_place_id_to_manual_coordinate_override_and_route_invalidation(self) -> None:
        self._enable_maps_instance()
        fm = self._load_task_fm()
        # Step 1: Resolve with Google Maps (place_id_only, map_display_permitted=False)
        res1 = enrich_task_location(
            self.temp_dir,
            fm,
            query="Downtown Engineering Annex",
            transport={
                "places": [
                    {
                        "id": "ChIJ_old_google_place",
                        "displayName": {"text": "Downtown Engineering Annex"},
                        "formattedAddress": "100 Congress Ave, Austin, TX 78701",
                        "location": {"latitude": 30.2638, "longitude": -97.7434},
                    }
                ]
            },
            env={"GOOGLE_MAPS_API_KEY": "synthetic_key"},
        )
        fm1 = res1["proposed_frontmatter"]
        self.assertEqual(fm1["location"]["provider_ref"]["place_id"], "ChIJ_old_google_place")
        self.assertFalse(fm1["location"]["map_display_permitted"])
        self.assertIsNone(fm1["coordinates"])

        # Add a manual route_estimate tied to ChIJ_old_google_place
        fm1["travel_policy"] = {"preferred_mode": "driving", "manual_duration_minutes": 20, "buffer_minutes": 5}
        commute1 = estimate_task_commute(
            self.temp_dir,
            fm1,
            origin={"label": "North Station", "coordinates": {"latitude": 30.2900, "longitude": -97.7400}},
        )
        fm1 = commute1["proposed_frontmatter"]
        self.assertEqual(fm1["route_estimate"]["freshness"], "manual")

        # Step 2: User overrides location with explicit coordinates
        res2 = enrich_task_location(
            self.temp_dir,
            fm1,
            query="Custom Field Site Pin",
            user_coordinates=[30.2849, -97.7341],
            force_override=True,
        )
        fm2 = res2["proposed_frontmatter"]
        self.assertEqual(fm2["location"]["provenance"], "manual_override")
        self.assertIsNone(fm2["location"]["provider_ref"])
        self.assertEqual(fm2["location"]["persistence_policy"], "persistent_permitted")
        self.assertTrue(fm2["location"]["map_display_permitted"])
        self.assertEqual(fm2["coordinates"], [30.2849, -97.7341])
        # Existing route_estimate must now be marked stale because destination changed
        self.assertEqual(fm2["route_estimate"]["freshness"], "stale")
        self.assertEqual(fm2["route_estimate"]["status"], "stale")

    # ------------------------------------------------------------------
    # 17. Stale Route Rejected by Schedule Window & Multi-Hop Predecessor
    # ------------------------------------------------------------------
    def test_17_stale_route_rejected_by_schedule_window_and_multi_hop_previous_task_id(self) -> None:
        self._enable_maps_instance()
        fm = self._load_task_fm()
        fm["location"] = {
            "label": "Central Library",
            "address": "710 W Cesar Chavez St, Austin, TX 78701",
            "is_virtual": False,
            "coordinates": {"latitude": 30.2658, "longitude": -97.7498},
            "provenance": "user_supplied",
            "resolution_status": "resolved",
            "persistence_policy": "persistent_permitted",
            "map_display_permitted": True,
        }
        commute = estimate_task_commute(
            self.temp_dir,
            fm,
            previous_task_location={"label": "Stop A", "coordinates": {"latitude": 30.2700, "longitude": -97.7500}},
            previous_task_id="task-stop-a",
            arrival_by="2026-09-30T11:00:00-05:00",
            transport={"routes": [{"duration": "900s", "distanceMeters": 3200}]},
            env={"GOOGLE_MAPS_API_KEY": "synthetic_key"},
        )
        ephem_est = commute["ephemeral_route_estimate"]
        self.assertEqual(ephem_est["previous_task_id"], "task-stop-a")

        # Calling evaluate_route_freshness without previous_task_id uses stored previous_task_id ("task-stop-a") -> fresh
        fresh_same = evaluate_route_freshness({**fm, "route_estimate": ephem_est})
        self.assertFalse(fresh_same["is_stale"])

        # Reordering schedule so predecessor is now "task-stop-b" invalidates freshness
        fresh_reordered = evaluate_route_freshness(
            {**fm, "route_estimate": ephem_est},
            previous_task_id="task-stop-b",
        )
        self.assertTrue(fresh_reordered["is_stale"])
        stale_est = fresh_reordered["updated_route_estimate"]

        # propose_travel_schedule_window must reject stale_est
        win_stale = propose_travel_schedule_window(
            fm,
            route_estimate=stale_est,
            arrival_at="2026-09-30T11:00:00-05:00",
        )
        self.assertEqual(win_stale["status"], "stale_route_estimate")

    # ------------------------------------------------------------------
    # 18. DST Spring-Forward & Fall-Back Travel Window Arithmetic
    # ------------------------------------------------------------------
    def test_18_dst_spring_forward_and_fall_back_travel_window_arithmetic(self) -> None:
        fm = self._load_task_fm()
        fm["timeEstimate"] = 60
        # 2026 US Central DST spring-forward: 2026-03-08 02:00 CST (-06:00) -> 03:00 CDT (-05:00)
        # Arrival at 03:10 CDT (-05:00) minus 25m travel + 10m buffer (35 elapsed minutes) = 01:35 CST (-06:00)
        win = propose_travel_schedule_window(
            fm,
            route_estimate={"duration_minutes": 25.0, "freshness": "fresh", "status": "ok"},
            arrival_at="2026-03-08T03:10:00-05:00",
            buffer_minutes=10,
            tz_name="America/Chicago",
        )
        self.assertEqual(win["status"], "ok")
        self.assertEqual(win["proposed_departure_at"], "2026-03-08T01:35:00-06:00")
        self.assertEqual(win["proposed_arrival_after_travel_at"], "2026-03-08T03:00:00-05:00")
        self.assertEqual(win["proposed_task_scheduled_at"], "2026-03-08T03:10:00-05:00")
        self.assertEqual(win["proposed_task_end_at"], "2026-03-08T04:10:00-05:00")

    # ------------------------------------------------------------------
    # 19. External Task Capture Preserves Local Location/Travel Edits
    # ------------------------------------------------------------------
    def test_19_external_task_capture_preserves_local_location_and_travel_enrichments(self) -> None:
        from helpers.ingestion_contract import draft_structured_task_capture
        from helpers.providers.google_tasks import map_google_task_to_contract

        # Initial capture of a Google Task
        item_v1 = map_google_task_to_contract(
            {
                "id": "gtask-loc-101",
                "etag": "rev-1",
                "title": "Pick up calibration kit",
                "due": "2026-10-02T00:00:00.000Z",
                "notes": "Bring serial cable.",
                "status": "needsAction",
            },
            source_alias="quick-capture",
            collection_id="default",
        )
        draft1 = draft_structured_task_capture(self.temp_dir, item_v1, default_pillar_tag="pillar-1/architecture")
        self.assertTrue(draft1["valid"])
        task_rec1 = draft1["records"][0]
        task_path = self.temp_dir / draft1["task_path"]
        task_path.parent.mkdir(parents=True, exist_ok=True)

        # User locally enriches task with location & travel_policy
        fm1 = dict(task_rec1["frontmatter"])
        body1 = task_rec1["body"]
        fm1["location"] = {
            "label": "Hardware Lab B",
            "address": "2500 Speedway, Austin, TX 78712",
            "is_virtual": False,
            "coordinates": {"latitude": 30.2895, "longitude": -97.7368},
            "provenance": "user_supplied",
            "resolution_status": "resolved",
            "persistence_policy": "persistent_permitted",
            "map_display_permitted": True,
        }
        fm1["coordinates"] = [30.2895, -97.7368]
        fm1["travel_policy"] = {"preferred_mode": "walking", "buffer_minutes": 10}
        task_path.write_text(serialize_record(fm1, body1), encoding="utf-8")

        # Upstream Google Task updates title in rev-2
        item_v2 = map_google_task_to_contract(
            {
                "id": "gtask-loc-101",
                "etag": "rev-2",
                "title": "Pick up calibration kit and oscilloscope probe",
                "due": "2026-10-02T00:00:00.000Z",
                "notes": "Bring serial cable.",
                "status": "needsAction",
            },
            source_alias="quick-capture",
            collection_id="default",
        )
        draft2 = draft_structured_task_capture(self.temp_dir, item_v2, default_pillar_tag="pillar-1/architecture")
        self.assertEqual(draft2["match_status"], "conflict_with_local_edits")
        fm2 = draft2["records"][0]["frontmatter"]
        self.assertEqual(fm2["location"]["label"], "Hardware Lab B")
        self.assertEqual(fm2["coordinates"], [30.2895, -97.7368])
        self.assertEqual(fm2["travel_policy"]["preferred_mode"], "walking")
        preserved = fm2["external_conflict_proposal"]["preserved_local_values"]
        self.assertEqual(preserved["location"]["label"], "Hardware Lab B")
        self.assertEqual(preserved["coordinates"], [30.2895, -97.7368])

    # ------------------------------------------------------------------
    # 20. DeepInvestigator Adversarial Regression Suite (Findings 1-7)
    # ------------------------------------------------------------------
    def test_20_deep_investigator_findings_1_to_7(self) -> None:
        from helpers.location_routing import _parse_cli_endpoint, normalize_travel_mode
        from helpers.providers.obsidian_maps import validate_obsidian_maps_base_view
        import io
        from contextlib import redirect_stdout
        from helpers.mdbase_helper import main as cli_main

        # Finding 1: Travel mode normalizer + unsupported mode rejected BEFORE manual_duration_minutes fallback
        self.assertEqual(normalize_travel_mode("drive"), "driving")
        self.assertEqual(normalize_travel_mode("walk"), "walking")
        self.assertEqual(normalize_travel_mode("bicycle"), "bicycling")
        self.assertEqual(normalize_travel_mode("bike"), "bicycling")
        self.assertIsNone(normalize_travel_mode("hovercraft"))

        bad_manual_mode = estimate_task_commute(
            self.temp_dir,
            {
                "title": "Hovercraft Commute Attempt",
                "timeEstimate": 30,
                "location": {
                    "label": "Engineering Annex",
                    "address": "100 Campus Dr",
                    "resolution_status": "resolved",
                },
                "travel_policy": {
                    "preferred_mode": "hovercraft",
                    "manual_duration_minutes": 25,
                },
            },
            origin={"label": "North Lab", "address": "200 Campus Dr"},
        )
        self.assertEqual(bad_manual_mode["status"], "unsupported_mode")
        self.assertIsNone(bad_manual_mode["duration_minutes"])

        # Finding 2: _parse_cli_endpoint + route-estimate CLI schedule_window attachment
        ep_place = _parse_cli_endpoint("place_id:ChIJ_test_123")
        self.assertEqual(ep_place["provider_ref"]["place_id"], "ChIJ_test_123")
        ep_chij = _parse_cli_endpoint("ChIJ_direct_456")
        self.assertEqual(ep_chij["provider_ref"]["place_id"], "ChIJ_direct_456")
        ep_coords = _parse_cli_endpoint("30.2849,-97.7341")
        self.assertEqual(ep_coords["coordinates"], [30.2849, -97.7341])
        ep_addr = _parse_cli_endpoint("100 Campus Dr, Metropolis")
        self.assertEqual(ep_addr["address"], "100 Campus Dr, Metropolis")

        # Enable maps in temp_dir for CLI route-estimate & location-resolve
        int_doc = {
            "type": "system_memory_extension",
            "id": "integrations-registry",
            "version": "1.0.0",
            "integrations": {
                "contract_version": "1.0.0",
                "instances": {
                    "maps": {
                        "integration": "google-maps",
                        "enabled": True,
                        "access": "read-only",
                        "config": {
                            "region_code": "CA",
                            "language_code": "fr",
                            "default_travel_mode": "walking",
                        },
                    }
                },
                "bindings": {
                    "location": {"resolve": "maps"},
                    "routing": {"estimate": "maps"},
                },
            },
        }
        (self.temp_dir / "System/Integrations.md").write_text(
            serialize_record(int_doc, "# Integrations"), encoding="utf-8"
        )
        syn_route_file = self.temp_dir / "syn_route.json"
        syn_route_file.write_text(
            json.dumps({"routes": [{"duration": "1500s", "distanceMeters": 2200, "routeLabels": ["DEFAULT_ROUTE"]}]}),
            encoding="utf-8",
        )
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cli_main(
                [
                    "--vault",
                    str(self.temp_dir),
                    "route-estimate",
                    "--origin",
                    "ChIJ_orig_01",
                    "--destination",
                    "30.2849,-97.7341",
                    "--mode",
                    "walk",
                    "--arrival-time",
                    "2026-09-30T10:00:00-05:00",
                    "--buffer-minutes",
                    "10",
                    "--synthetic-response",
                    str(syn_route_file),
                ]
            )
        self.assertEqual(rc, 0)
        cli_route_out = json.loads(buf.getvalue())
        self.assertIn("schedule_window", cli_route_out)
        self.assertEqual(cli_route_out["schedule_window"]["proposed_departure_at"], "2026-09-30T09:25:00-05:00")

        # Finding 3: location-resolve threads region_code/language_code and falls back to instance locale defaults
        captured_loc_bodies = []
        def _capture_loc_transport(req_env):
            captured_loc_bodies.append(req_env["body"])
            return {
                "places": [
                    {
                        "id": "ChIJ_loc_ca",
                        "displayName": {"text": "Bibliotheque"},
                        "formattedAddress": "100 Rue Principale",
                        "location": {"latitude": 45.5, "longitude": -73.5},
                    }
                ]
            }
        enrich_task_location(
            self.temp_dir,
            {"title": "Visit Library"},
            query="Bibliotheque",
            transport=_capture_loc_transport,
        )
        self.assertEqual(captured_loc_bodies[-1]["regionCode"], "CA")
        self.assertEqual(captured_loc_bodies[-1]["languageCode"], "fr")

        enrich_task_location(
            self.temp_dir,
            {"title": "Visit Library Override"},
            query="Bibliotheque",
            region_code="GB",
            language_code="en-GB",
            transport=_capture_loc_transport,
        )
        self.assertEqual(captured_loc_bodies[-1]["regionCode"], "GB")
        self.assertEqual(captured_loc_bodies[-1]["languageCode"], "en-GB")

        # Finding 4: computeRoutes omits arrivalTime on non-TRANSIT modes and validates arrival_by
        captured_route_bodies = []
        def _capture_route_transport(req_env):
            captured_route_bodies.append(req_env["body"])
            return {"routes": [{"duration": "1200s", "distanceMeters": 5000}]}

        drive_res = estimate_google_maps_route(
            {
                "origin": {"place_id": "ChIJ_orig"},
                "destination": {"place_id": "ChIJ_dest"},
                "travel_mode": "drive",
                "arrival_by": "2026-09-30T10:00:00-05:00",
            },
            transport=_capture_route_transport,
        )
        self.assertEqual(drive_res["status"], "ok")
        self.assertNotIn("arrivalTime", captured_route_bodies[-1])
        self.assertNotIn("departureTime", captured_route_bodies[-1])
        self.assertEqual(drive_res["estimate"]["arrival_by"], "2026-09-30T10:00:00-05:00")

        transit_res = estimate_google_maps_route(
            {
                "origin": {"place_id": "ChIJ_orig"},
                "destination": {"place_id": "ChIJ_dest"},
                "travel_mode": "transit",
                "arrival_by": "2026-09-30T10:00:00-05:00",
            },
            transport=_capture_route_transport,
        )
        self.assertEqual(transit_res["status"], "ok")
        self.assertEqual(captured_route_bodies[-1]["arrivalTime"], "2026-09-30T15:00:00Z")

        bad_arr = estimate_google_maps_route(
            {
                "origin": {"place_id": "ChIJ_orig"},
                "destination": {"place_id": "ChIJ_dest"},
                "travel_mode": "driving",
                "arrival_by": "not-a-valid-timestamp",
            },
            transport=_capture_route_transport,
        )
        self.assertEqual(bad_arr["status"], "invalid_request")

        # Finding 5: Outbound privacy sanitizer inspects string values
        for bad_q in (
            "Line 1\n---\ntitle: Secret",
            "See [[20260901-secret-note]] for details",
            "TaskNotes/Tasks/secret-task.md",
            "Meet at #pillar-1/architecture lab",
            "A" * 300,
        ):
            s_res = sanitize_google_maps_outbound_request({"query": bad_q})
            self.assertFalse(s_res["ok"])
            self.assertEqual(s_res["status"], "privacy_violation")

        # Finding 6: Cross-layer slot/capability sync & ambiguity detection with workflow_binding
        ambig_doc = {
            "type": "system_memory_extension",
            "id": "integrations-registry",
            "version": "1.0.0",
            "integrations": {
                "contract_version": "1.0.0",
                "instances": {
                    "maps-a": {"integration": "google-maps", "enabled": True, "access": "read-only"},
                    "maps-b": {"integration": "google-maps", "enabled": True, "access": "read-only"},
                },
                "bindings": {
                    "slot_a": {"capability": "location.resolve", "instance": "maps-a"},
                    "slot_b": {"capability": "location.resolve", "instance": "maps-b"},
                },
            },
        }
        (self.temp_dir / "System/Integrations.md").write_text(
            serialize_record(ambig_doc, "# Ambiguous Integrations"), encoding="utf-8"
        )
        b_ambig = resolve_capability_binding(
            self.temp_dir,
            "location.resolve",
            workflow_binding="task.location_lookup",
        )
        self.assertEqual(b_ambig["status"], "binding_ambiguous")

        # Finding 7: base_view_path override, unconfigured vault template_defaults, and .base view validator
        proj_custom = project_tasks_to_obsidian_maps(
            {"records": [], "base_view_path": "TaskNotes/Views/custom-map.base"}
        )
        self.assertEqual(proj_custom["base_view_path"], "TaskNotes/Views/custom-map.base")

        empty_vault = self.temp_dir / "empty_unconfigured_vault"
        empty_vault.mkdir(parents=True, exist_ok=True)
        seeded_cfg = resolve_integration_config(empty_vault)
        self.assertEqual(
            set(seeded_cfg["instances"].keys()),
            {"media", "quick-capture", "maps", "vault-maps"},
        )
        base_v = validate_obsidian_maps_base_view(REPO_ROOT / "TaskNotes/Views/maps-default.base")
        self.assertTrue(base_v["valid"])

    # ------------------------------------------------------------------
    # 21. Skeptical Adversarial Review Break-Fixes
    # ------------------------------------------------------------------
    def test_21_skeptical_adversarial_break_fixes(self) -> None:
        from helpers.location_routing import _parse_cli_endpoint
        from helpers.providers.google_maps import (
            _format_google_waypoint,
            _normalize_place_candidate,
            sanitize_google_maps_outbound_request,
        )
        from helpers.integration_registry import evaluate_instance_readiness
        import io
        from contextlib import redirect_stdout
        from helpers.mdbase_helper import main as cli_main

        # 1. Waypoint formatting supports list & tuple coordinates as latLng objects
        ep_list = _parse_cli_endpoint("30.2849,-97.7341")
        wp_list, wp_err = _format_google_waypoint(ep_list)
        self.assertIsNone(wp_err)
        self.assertEqual(wp_list, {"location": {"latLng": {"latitude": 30.2849, "longitude": -97.7341}}})

        wp_tuple, wp_tuple_err = _format_google_waypoint({
            "coordinates": (30.2849, -97.7341),
            "provenance": "user_supplied",
        })
        self.assertIsNone(wp_tuple_err)
        self.assertEqual(wp_tuple, {"location": {"latLng": {"latitude": 30.2849, "longitude": -97.7341}}})

        # Out-of-bounds coordinates return invalid_coordinates
        wp_bad, wp_bad_err = _format_google_waypoint({"coordinates": [999.0, 999.0]})
        self.assertIsNone(wp_bad)
        self.assertEqual(wp_bad_err, "invalid_coordinates")

        # 2. _normalize_place_candidate supports coordinates list
        norm_cand = _normalize_place_candidate({
            "id": "ChIJ_cand_1",
            "displayName": {"text": "Candidate Place"},
            "coordinates": [30.2849, -97.7341],
        })
        self.assertIsNotNone(norm_cand)
        self.assertEqual(norm_cand["coordinates"], {"latitude": 30.2849, "longitude": -97.7341})

        # 3. Privacy sanitizer catches Windows backslashes, lowercase tokens, URL-unquoting, and place_id leaks
        privacy_evasion_attempts = [
            {"query": "TaskNotes\\Tasks\\secret.md"},
            {"query": "tasknotes/tasks/secret.md"},
            {"query": "projects\\roadmap.md"},
            {"query": "%5B%5Bsecret-note%5D%5D"},
            {"query": "TaskNotes%2Fsecret.md"},
            {"place_id": "TaskNotes/Tasks/secret.md"},
            {"origin": {"place_id": "TaskNotes\\secret.md"}},
            {"origin": {"provider_ref": {"place_id": "projects/secret.md"}}},
        ]
        for payload in privacy_evasion_attempts:
            s_res = sanitize_google_maps_outbound_request(payload)
            self.assertFalse(s_res["ok"], f"Failed to reject privacy evasion payload: {payload}")
            self.assertEqual(s_res["status"], "privacy_violation")

        # 4. CLI route-estimate without --mode respects instance default_travel_mode
        walk_vault = self.temp_dir / "walk_default_vault"
        walk_vault.mkdir(parents=True, exist_ok=True)
        (walk_vault / "System").mkdir(parents=True, exist_ok=True)
        (walk_vault / "System/Integrations.md").write_text(
            serialize_record(
                {
                    "type": "system_memory_extension",
                    "id": "integrations",
                    "version": "1.0.0",
                    "integrations": {
                        "contract_version": "1.0.0",
                        "instances": {
                            "maps": {
                                "integration": "google-maps",
                                "enabled": True,
                                "config": {"default_travel_mode": "walking"},
                            }
                        },
                        "bindings": {"routing": {"estimate": "maps"}},
                    },
                },
                "# Walk Default",
            ),
            encoding="utf-8",
        )
        syn_walk = walk_vault / "syn_walk.json"
        syn_walk.write_text(json.dumps({"routes": [{"duration": "600s"}]}), encoding="utf-8")
        buf_walk = io.StringIO()
        with redirect_stdout(buf_walk):
            rc_walk = cli_main(
                [
                    "--vault",
                    str(walk_vault),
                    "route-estimate",
                    "--origin",
                    "ChIJ_1",
                    "--destination",
                    "ChIJ_2",
                    "--synthetic-response",
                    str(syn_walk),
                ]
            )
        self.assertEqual(rc_walk, 0)
        walk_out = json.loads(buf_walk.getvalue())
        self.assertEqual(walk_out["ephemeral_route_estimate"]["travel_mode"], "walking")

        # 5. CLI route-estimate with --task and --scheduled
        task_dir = walk_vault / "TaskNotes" / "Tasks"
        task_dir.mkdir(parents=True, exist_ok=True)
        t_note = task_dir / "onsite-audit.md"
        t_note.write_text(
            serialize_record(
                {
                    "title": "Onsite Architecture Audit",
                    "status": "todo",
                    "priority": "normal",
                    "urgency_tier": 2,
                    "modality": "analytical",
                    "timeEstimate": 90,
                    "tags": ["task", "pillar-1/architecture"],
                    "scheduled": "2026-09-30T14:00:00-05:00",
                    "location": {
                        "label": "Engineering Annex",
                        "address": "100 Campus Dr",
                        "place_id": "ChIJ_campus_1",
                        "resolution_status": "resolved",
                    },
                    "travel_policy": {
                        "preferred_mode": "bicycling",
                        "buffer_minutes": 15,
                    },
                },
                "Audit notes.",
            ),
            encoding="utf-8",
        )
        buf_task = io.StringIO()
        with redirect_stdout(buf_task):
            rc_task = cli_main(
                [
                    "--vault",
                    str(walk_vault),
                    "route-estimate",
                    "--origin",
                    "ChIJ_home_0",
                    "--task",
                    "TaskNotes/Tasks/onsite-audit.md",
                    "--synthetic-response",
                    str(syn_walk),
                ]
            )
        self.assertEqual(rc_task, 0)
        task_route_out = json.loads(buf_task.getvalue())
        self.assertEqual(task_route_out["ephemeral_route_estimate"]["travel_mode"], "bicycling")
        self.assertIn("schedule_window", task_route_out)
        self.assertEqual(task_route_out["schedule_window"]["proposed_task_scheduled_at"], "2026-09-30T14:00:00-05:00")
        # 10m travel + 15m buffer = 25m transit -> 13:35 departure
        self.assertEqual(task_route_out["schedule_window"]["proposed_departure_at"], "2026-09-30T13:35:00-05:00")

        # 6. evaluate_instance_readiness supports nested config block
        nested_inst_cfg = {
            "integration": "obsidian-maps",
            "enabled": True,
            "config": {
                "base_view_path": "TaskNotes/Views/maps-default.base",
            },
        }
        readiness_nested = evaluate_instance_readiness(REPO_ROOT, nested_inst_cfg)
        self.assertTrue(readiness_nested["configured"])
        self.assertTrue(readiness_nested["available"])

        # 7. Destination place_id in manual duration override
        man_dest_task = estimate_task_commute(
            self.temp_dir,
            {
                "title": "Manual Commute Task",
                "timeEstimate": 45,
                "location": {
                    "label": "Substation 4",
                    "place_id": "ChIJ_sub_4",
                    "resolution_status": "resolved",
                },
                "travel_policy": {
                    "preferred_mode": "driving",
                    "manual_duration_minutes": 20,
                },
            },
            origin={"label": "HQ", "place_id": "ChIJ_hq_0"},
        )
        self.assertEqual(man_dest_task["status"], "manual_override")
        self.assertEqual(man_dest_task["proposed_frontmatter"]["route_estimate"]["destination"]["place_id"], "ChIJ_sub_4")

        # 8. _parse_cli_endpoint rejects empty place_id
        self.assertIsNone(_parse_cli_endpoint("place_id:"))
        self.assertIsNone(_parse_cli_endpoint("place_id:   "))


if __name__ == "__main__":
    unittest.main()
