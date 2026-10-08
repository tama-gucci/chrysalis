"""Provider normalization and policy tests use synthetic transport responses."""
from __future__ import annotations
import hashlib,json,os,shutil,tempfile,unittest
from pathlib import Path
from typing import Dict,Any
import yaml
from chrysalis.package import initialize
from helpers.integration_registry import *
from helpers.location_routing import *
from helpers.records import parse_frontmatter,serialize_record,validate_record,compute_revision
from helpers.providers.google_maps import estimate_google_maps_route,resolve_google_maps_location,sanitize_google_maps_outbound_request
from helpers.providers.obsidian_maps import project_tasks_to_obsidian_maps,synchronize_task_map_coordinates
REPO_ROOT=Path(__file__).resolve().parents[1]
class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.parent=Path(tempfile.mkdtemp(prefix='provider-fixture-'))
        self.temp_dir=self.parent/'chrysalis'
        initialize(self.temp_dir,'America/Chicago')
        shutil.copyfile(REPO_ROOT/'TaskNotes/Tasks/example-task.md',self.temp_dir/'TaskNotes/Tasks/example-task.md')
    def tearDown(self):
        shutil.rmtree(self.parent)
    def test_google_maps_location_resolution_ambiguity_and_policy(self) -> None:
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

    def test_route_estimation_arithmetic_and_ephemeral_policy_guard(self) -> None:
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

    def test_route_staleness_invalidation(self) -> None:
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

    def test_outbound_request_privacy_sanitization(self) -> None:
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

    def test_obsidian_maps_projection_and_google_policy_filter(self) -> None:
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

    def test_coordinate_and_location_single_source_ownership(self) -> None:
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

    def test_malformed_capability_result_rejected(self) -> None:
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

    def test_recursive_inline_secret_detection_and_string_diagnostic_codes(self) -> None:
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
                            "api_key": "fixture-value-for-credential-rejection",
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

    def test_stale_route_rejected_by_schedule_window_and_multi_hop_previous_task_id(self) -> None:
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

    def test_dst_spring_forward_and_fall_back_travel_window_arithmetic(self) -> None:
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

    def test_traffic_freshness_ttl_expiration(self) -> None:
        origin_ep = {"place_id": "ChIJ_origin_ttl"}
        dest_ep = {"place_id": "ChIJ_dest_ttl"}
        obs_time = "2026-09-30T09:00:00-05:00"

        fp = compute_route_context_fingerprint(
            origin=origin_ep,
            destination=dest_ep,
            travel_mode="driving",
            departure_at="2026-09-30T09:25:00-05:00",
            arrival_by="2026-09-30T10:00:00-05:00",
        )
        task_fm = {
            "location": dest_ep,
            "timeEstimate": 45,
            "route_estimate": {
                "origin": origin_ep,
                "destination": dest_ep,
                "travel_mode": "driving",
                "departure_at": "2026-09-30T09:25:00-05:00",
                "arrival_by": "2026-09-30T10:00:00-05:00",
                "duration_minutes": 25,
                "duration_unit": "minutes",
                "observed_at": obs_time,
                "freshness": "fresh",
                "status": "ok",
                "context_fingerprint": fp,
            },
        }

        # 1. Fresh within default 900s TTL (10m / 600s elapsed)
        ref_fresh = "2026-09-30T09:10:00-05:00"
        eval_fresh = evaluate_route_freshness(
            task_fm,
            reference_time=ref_fresh,
            origin=origin_ep,
            destination=dest_ep,
            travel_mode="driving",
            departure_at="2026-09-30T09:25:00-05:00",
            arrival_by="2026-09-30T10:00:00-05:00",
        )
        self.assertFalse(eval_fresh["is_stale"])
        self.assertEqual(eval_fresh["freshness"], "fresh")

        # 2. Stale after default 900s TTL (20m / 1200s elapsed > 900s)
        ref_stale = "2026-09-30T09:20:00-05:00"
        eval_stale = evaluate_route_freshness(
            task_fm,
            reference_time=ref_stale,
            origin=origin_ep,
            destination=dest_ep,
            travel_mode="driving",
            departure_at="2026-09-30T09:25:00-05:00",
            arrival_by="2026-09-30T10:00:00-05:00",
        )
        self.assertTrue(eval_stale["is_stale"])
        self.assertEqual(eval_stale["reason"], "traffic_freshness_expired")
        self.assertEqual(eval_stale["updated_route_estimate"]["freshness"], "stale")
        self.assertEqual(eval_stale["updated_route_estimate"]["status"], "stale")
        self.assertEqual(eval_stale["elapsed_seconds"], 1200.0)

        # 3. Custom TTL: 300s (5m)
        ref_custom_fresh = "2026-09-30T09:04:00-05:00"  # 4m / 240s
        eval_custom_fresh = evaluate_route_freshness(
            task_fm,
            freshness_ttl_seconds=300,
            reference_time=ref_custom_fresh,
            origin=origin_ep,
            destination=dest_ep,
            travel_mode="driving",
            departure_at="2026-09-30T09:25:00-05:00",
            arrival_by="2026-09-30T10:00:00-05:00",
        )
        self.assertFalse(eval_custom_fresh["is_stale"])

        ref_custom_stale = "2026-09-30T09:06:00-05:00"  # 6m / 360s > 300s
        eval_custom_stale = evaluate_route_freshness(
            task_fm,
            freshness_ttl_seconds=300,
            reference_time=ref_custom_stale,
            origin=origin_ep,
            destination=dest_ep,
            travel_mode="driving",
            departure_at="2026-09-30T09:25:00-05:00",
            arrival_by="2026-09-30T10:00:00-05:00",
        )
        self.assertTrue(eval_custom_stale["is_stale"])
        self.assertEqual(eval_custom_stale["reason"], "traffic_freshness_expired")

        # 4. propose_travel_schedule_window rejects TTL-expired route estimate
        sched_res = propose_travel_schedule_window(
            task_fm,
            arrival_at="2026-09-30T10:00:00-05:00",
            reference_time=ref_stale,
            freshness_ttl_seconds=900,
        )
        self.assertEqual(sched_res["status"], "stale_route_estimate")
