"""
Chrysalis Shared Integration Registry, Private Configuration Resolver & Capability Dispatcher
(helpers/integration_registry.py)

Implements:
1. Static trusted integration registry (`TRUSTED_INTEGRATION_ADAPTERS`) mapping integration IDs
   (`google-drive`, `google-tasks`, `google-maps`, `obsidian-maps`) to machine-readable capability
   declarations, effect classes, and deterministic adapter functions.
2. Separation of private integration instances (`integrations.instances`) from workflow capability
   bindings (`integrations.bindings`) across `System/Memory.md`, optional `System/Integrations.md`,
   and optional `System/Ingestion-Sources.md`.
3. Non-destructive compatibility bridging with `ingestion.sources` and legacy `ingestion_config`.
4. Five-state readiness evaluation (`installed`, `configured`, `authenticated`, `available`, `verified`).
5. Deterministic failure codes (`binding_missing`, `binding_ambiguous`, `instance_disabled`,
   `capability_not_supported`, `effect_not_authorized`, `inline_secret_forbidden`,
   `arbitrary_adapter_import_forbidden`, `malformed_capability_result`).
"""

from __future__ import annotations

import os
from pathlib import Path
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from helpers.mdbase_helper import parse_frontmatter
from helpers.providers.google_drive import (
    GOOGLE_DRIVE_CAPABILITIES,
    GOOGLE_DRIVE_INTEGRATION_ID,
    discover_google_drive_source,
)
from helpers.providers.google_maps import (
    GOOGLE_MAPS_CAPABILITIES,
    GOOGLE_MAPS_INTEGRATION_ID,
    estimate_google_maps_route,
    resolve_google_maps_location,
)
from helpers.providers.google_tasks import (
    GOOGLE_TASKS_CAPABILITIES,
    GOOGLE_TASKS_INTEGRATION_ID,
    discover_google_tasks_source,
)
from helpers.providers.obsidian_maps import (
    OBSIDIAN_MAPS_CAPABILITIES,
    OBSIDIAN_MAPS_INTEGRATION_ID,
    project_tasks_to_obsidian_maps,
)


INTEGRATION_CAPABILITY_CONTRACT_VERSION = "1.0.0"

CAPABILITY_FAMILIES: Set[str] = {
    "ingestion.discover",
    "ingestion.read",
    "location.resolve",
    "routing.estimate",
    "visualization.map_projection",
}

FUTURE_CAPABILITY_FAMILIES: Set[str] = {
    "calendar.commitments_read",
    "calendar.events_write",
    "notification.dispatch",
}

ALLOWED_OPERATION_EFFECTS: Set[str] = {
    "external_query",
    "local_projection",
    "external_mutation",
}

READINESS_STATES: Tuple[str, ...] = (
    "installed",
    "configured",
    "authenticated",
    "available",
    "verified",
)

INLINE_SECRET_PATTERN = re.compile(
    r"(?:AIza[0-9A-Za-z_-]{20,}|ghp_[0-9A-Za-z]{20,}|sk-[0-9A-Za-z]{20,}|Bearer\s+[0-9A-Za-z_.-]{16,})",
    re.IGNORECASE,
)


TRUSTED_INTEGRATION_ADAPTERS: Dict[str, Dict[str, Any]] = {
    GOOGLE_DRIVE_INTEGRATION_ID: {
        "integration_id": GOOGLE_DRIVE_INTEGRATION_ID,
        "contract_version": INTEGRATION_CAPABILITY_CONTRACT_VERSION,
        "skill_path": ".agent/skills/google-drive/SKILL.md",
        "capabilities": ["ingestion.discover", "ingestion.read"],
        "effects": {
            "ingestion.discover": "external_query",
            "ingestion.read": "external_query",
        },
        "requires_secret": False,
        "external_mutation_supported": False,
        "external_mutation_authorized": False,
        "metadata": GOOGLE_DRIVE_CAPABILITIES,
        "handlers": {
            "ingestion.discover": discover_google_drive_source,
            "ingestion.read": discover_google_drive_source,
        },
    },
    GOOGLE_TASKS_INTEGRATION_ID: {
        "integration_id": GOOGLE_TASKS_INTEGRATION_ID,
        "contract_version": INTEGRATION_CAPABILITY_CONTRACT_VERSION,
        "skill_path": ".agent/skills/google-tasks/SKILL.md",
        "capabilities": ["ingestion.discover", "ingestion.read"],
        "effects": {
            "ingestion.discover": "external_query",
            "ingestion.read": "external_query",
        },
        "requires_secret": False,
        "external_mutation_supported": False,
        "external_mutation_authorized": False,
        "metadata": GOOGLE_TASKS_CAPABILITIES,
        "handlers": {
            "ingestion.discover": discover_google_tasks_source,
            "ingestion.read": discover_google_tasks_source,
        },
    },
    GOOGLE_MAPS_INTEGRATION_ID: {
        "integration_id": GOOGLE_MAPS_INTEGRATION_ID,
        "contract_version": INTEGRATION_CAPABILITY_CONTRACT_VERSION,
        "skill_path": ".agent/skills/google-maps/SKILL.md",
        "capabilities": ["location.resolve", "routing.estimate"],
        "effects": {
            "location.resolve": "external_query",
            "routing.estimate": "external_query",
        },
        "requires_secret": True,
        "external_mutation_supported": False,
        "external_mutation_authorized": False,
        "metadata": GOOGLE_MAPS_CAPABILITIES,
        "handlers": {
            "location.resolve": resolve_google_maps_location,
            "routing.estimate": estimate_google_maps_route,
        },
    },
    OBSIDIAN_MAPS_INTEGRATION_ID: {
        "integration_id": OBSIDIAN_MAPS_INTEGRATION_ID,
        "contract_version": INTEGRATION_CAPABILITY_CONTRACT_VERSION,
        "skill_path": ".agent/skills/obsidian-maps/SKILL.md",
        "capabilities": ["visualization.map_projection"],
        "effects": {
            "visualization.map_projection": "local_projection",
        },
        "requires_secret": False,
        "external_mutation_supported": False,
        "external_mutation_authorized": False,
        "metadata": OBSIDIAN_MAPS_CAPABILITIES,
        "handlers": {
            "visualization.map_projection": project_tasks_to_obsidian_maps,
        },
    },
    "filesystem": {
        "integration_id": "filesystem",
        "contract_version": INTEGRATION_CAPABILITY_CONTRACT_VERSION,
        "skill_path": ".agent/skills/ingest/SKILL.md",
        "capabilities": ["ingestion.discover", "ingestion.read"],
        "effects": {
            "ingestion.discover": "external_query",
            "ingestion.read": "external_query",
        },
        "requires_secret": False,
        "external_mutation_supported": False,
        "external_mutation_authorized": False,
        "metadata": {"integration_id": "filesystem", "capabilities": ["ingestion.discover", "ingestion.read"]},
        "handlers": {},
    },
}


def get_registered_adapter(
    integration_id: str,
    *,
    custom_registry: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    """
    Retrieves a static trusted integration declaration.
    Rejects dynamic import paths or untrusted module specifications.
    """
    iid = str(integration_id or "").strip()
    if not iid:
        return None, {
            "code": "missing_integration_id",
            "message": "Integration identifier is empty.",
        }

    if ":" in iid or "/" in iid or "\\" in iid or iid.endswith(".py"):
        return None, {
            "code": "arbitrary_adapter_import_forbidden",
            "message": f"Dynamic or path-based adapter loading is prohibited: {iid!r}",
        }

    registry = dict(TRUSTED_INTEGRATION_ADAPTERS)
    if isinstance(custom_registry, dict):
        registry.update(custom_registry)

    adapter = registry.get(iid)
    if adapter is None:
        return None, {
            "code": "unknown_integration_adapter",
            "message": f"Integration '{iid}' is not in TRUSTED_INTEGRATION_ADAPTERS.",
        }
    return adapter, None


def resolve_secret_reference(
    secret_ref: Optional[str],
    *,
    vault_root: Optional[Union[Path, str]] = None,
    env: Optional[Dict[str, str]] = None,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    Resolves a credential reference (`env:VAR_NAME` or `file:<private_path>`) without allowing
    inline plaintext secrets in configuration files.
    """
    if not secret_ref:
        return None, None

    s_ref = str(secret_ref).strip()
    if INLINE_SECRET_PATTERN.search(s_ref) and not s_ref.startswith(("env:", "file:")):
        return None, {
            "code": "inline_secret_forbidden",
            "message": "Plaintext API keys or tokens are forbidden in configuration; use 'env:VAR_NAME' or 'file:<private_path>'.",
        }

    env_map = env if env is not None else os.environ

    if s_ref.startswith("env:"):
        var_name = s_ref[4:].strip()
        if not var_name:
            return None, {"code": "invalid_secret_ref", "message": "Empty environment variable name in secret_ref."}
        val = env_map.get(var_name)
        if not val or not str(val).strip():
            return None, {
                "code": "secret_unresolved",
                "message": f"Environment variable '{var_name}' is not set.",
                "secret_ref": s_ref,
            }
        return str(val).strip(), None

    if s_ref.startswith("file:"):
        rel_or_abs = s_ref[5:].strip()
        if not rel_or_abs:
            return None, {"code": "invalid_secret_ref", "message": "Empty file path in secret_ref."}
        cand = Path(rel_or_abs)
        if not cand.is_absolute() and vault_root is not None:
            cand = (Path(vault_root).resolve() / cand).resolve()
        if not cand.is_file():
            return None, {
                "code": "secret_unresolved",
                "message": f"Secret file does not exist: {cand}",
                "secret_ref": s_ref,
            }
        return cand.read_text(encoding="utf-8").strip(), None

    return None, {
        "code": "invalid_secret_ref",
        "message": f"Unsupported secret_ref format '{s_ref}'. Expected 'env:<VAR>' or 'file:<path>'.",
    }


def _scan_config_for_inline_secrets(cfg_dict: Dict[str, Any], prefix: str = "") -> List[Dict[str, Any]]:
    """Recursively checks an instance configuration dict for accidental inline API keys or tokens."""
    issues: List[Dict[str, Any]] = []
    if not isinstance(cfg_dict, dict):
        return issues
    for k, v in cfg_dict.items():
        field_name = f"{prefix}.{k}" if prefix else str(k)
        if isinstance(v, str) and INLINE_SECRET_PATTERN.search(v):
            issues.append(
                {
                    "code": "inline_secret_forbidden",
                    "field": field_name,
                    "message": f"Field '{field_name}' contains a raw credential pattern; use secret_ref ('env:VAR_NAME') instead.",
                }
            )
        elif isinstance(v, dict):
            issues.extend(_scan_config_for_inline_secrets(v, prefix=field_name))
        elif isinstance(v, list):
            for idx, item in enumerate(v):
                if isinstance(item, str) and INLINE_SECRET_PATTERN.search(item):
                    issues.append(
                        {
                            "code": "inline_secret_forbidden",
                            "field": f"{field_name}[{idx}]",
                            "message": f"Field '{field_name}[{idx}]' contains a raw credential pattern; use secret_ref ('env:VAR_NAME') instead.",
                        }
                    )
                elif isinstance(item, dict):
                    issues.extend(_scan_config_for_inline_secrets(item, prefix=f"{field_name}[{idx}]"))
    return issues


def _is_placeholder_value(val: Any) -> bool:
    if val is None:
        return True
    s = str(val).strip()
    return not s or (s.startswith("<") and s.endswith(">"))


def _infer_slot_capability(slot_key: str) -> Optional[str]:
    if slot_key in CAPABILITY_FAMILIES or slot_key in FUTURE_CAPABILITY_FAMILIES:
        return slot_key
    if slot_key.startswith("ingestion.sources."):
        return "ingestion.discover"
    slot_map = {
        "task.location_lookup": "location.resolve",
        "plan.route_estimate": "routing.estimate",
        "views.map_projection": "visualization.map_projection",
    }
    return slot_map.get(slot_key)


CAPABILITY_TO_WORKFLOW_SLOTS: Dict[str, List[str]] = {
    "location.resolve": ["task.location_lookup"],
    "routing.estimate": ["plan.route_estimate"],
    "visualization.map_projection": ["views.map_projection"],
}

WORKFLOW_SLOT_TO_CAPABILITY: Dict[str, str] = {
    slot: cap
    for cap, slots in CAPABILITY_TO_WORKFLOW_SLOTS.items()
    for slot in slots
}


def _extract_layer_bindings(raw_bindings: Dict[str, Any], source_layer: str = "") -> Dict[str, Dict[str, Any]]:
    """Flattens 1-, 2-, or 3-level nested `integrations.bindings` YAML trees into canonical binding descriptors."""
    extracted: Dict[str, Dict[str, Any]] = {}
    for bind_key, bcfg in raw_bindings.items():
        b_key_str = str(bind_key).strip()
        if isinstance(bcfg, str):
            cap_val = _infer_slot_capability(b_key_str)
            rec: Dict[str, Any] = {
                "binding_key": b_key_str,
                "capability": cap_val,
                "instance": bcfg.strip(),
                "source_layer": source_layer,
            }
            if b_key_str.startswith("ingestion.sources."):
                rec["source_alias"] = b_key_str.split("ingestion.sources.", 1)[1]
            extracted[b_key_str] = rec
        elif isinstance(bcfg, dict):
            if "instance" in bcfg or "capability" in bcfg:
                rec = dict(bcfg)
                rec["binding_key"] = b_key_str
                rec.setdefault("capability", _infer_slot_capability(b_key_str))
                rec["source_layer"] = source_layer
                if b_key_str.startswith("ingestion.sources."):
                    rec.setdefault("source_alias", b_key_str.split("ingestion.sources.", 1)[1])
                extracted[b_key_str] = rec
            else:
                for sub_k, sub_v in bcfg.items():
                    sub_key_str = f"{b_key_str}.{sub_k}"
                    if isinstance(sub_v, str):
                        cap_val = _infer_slot_capability(sub_key_str)
                        rec = {
                            "binding_key": sub_key_str,
                            "capability": cap_val,
                            "instance": sub_v.strip(),
                            "source_layer": source_layer,
                        }
                        if sub_key_str.startswith("ingestion.sources."):
                            rec["source_alias"] = sub_key_str.split("ingestion.sources.", 1)[1]
                        extracted[sub_key_str] = rec
                    elif isinstance(sub_v, dict):
                        if "instance" in sub_v or "capability" in sub_v:
                            rec = dict(sub_v)
                            rec["binding_key"] = sub_key_str
                            rec.setdefault("capability", _infer_slot_capability(sub_key_str))
                            rec["source_layer"] = source_layer
                            if sub_key_str.startswith("ingestion.sources."):
                                rec.setdefault("source_alias", sub_key_str.split("ingestion.sources.", 1)[1])
                            extracted[sub_key_str] = rec
                        else:
                            # 3-level nesting, e.g. ingestion -> sources -> {media: "media", quick-capture: "quick-capture"}
                            for leaf_k, leaf_v in sub_v.items():
                                leaf_key_str = f"{sub_key_str}.{leaf_k}"
                                if isinstance(leaf_v, str):
                                    cap_val = _infer_slot_capability(leaf_key_str)
                                    rec = {
                                        "binding_key": leaf_key_str,
                                        "capability": cap_val,
                                        "instance": leaf_v.strip(),
                                        "source_layer": source_layer,
                                    }
                                    if leaf_key_str.startswith("ingestion.sources."):
                                        rec["source_alias"] = str(leaf_k)
                                    extracted[leaf_key_str] = rec
                                elif isinstance(leaf_v, dict):
                                    rec = dict(leaf_v)
                                    rec["binding_key"] = leaf_key_str
                                    rec.setdefault("capability", _infer_slot_capability(leaf_key_str))
                                    rec["source_layer"] = source_layer
                                    if leaf_key_str.startswith("ingestion.sources."):
                                        rec.setdefault("source_alias", str(leaf_k))
                                    extracted[leaf_key_str] = rec
    return extracted


def _merge_instance_dict(existing: Dict[str, Any], incoming: Dict[str, Any], inst_id: str) -> Dict[str, Any]:
    """Merges an incoming instance configuration (including nested `config:` keys) onto `existing`."""
    merged = dict(existing)
    nested_cfg = dict(merged.get("config")) if isinstance(merged.get("config"), dict) else {}
    inc_cfg = incoming.get("config") if isinstance(incoming.get("config"), dict) else {}
    if inc_cfg:
        nested_cfg.update(inc_cfg)
        for ck, cv in inc_cfg.items():
            if cv is not None:
                if ck == "collection" and not _is_placeholder_value(merged.get("collection")) and _is_placeholder_value(cv):
                    continue
                merged[ck] = cv

    for k, v in incoming.items():
        if k == "config":
            continue
        if k == "collection" and not _is_placeholder_value(merged.get("collection")) and _is_placeholder_value(v):
            continue
        merged[k] = v

    if nested_cfg:
        merged["config"] = nested_cfg
    merged["instance_id"] = str(inst_id)
    merged["integration"] = str(merged.get("integration") or "").strip()
    merged["enabled"] = bool(merged.get("enabled") is True)
    return merged


def resolve_integration_config(vault_root: Union[Path, str]) -> Dict[str, Any]:
    """
    Resolves the generalized private integration configuration across:
    0. `System/_templates/Integrations.template.md` (`template_defaults` lowest-precedence seed layer)
    1. `<vault>/System/Memory.md` (`integrations` + `ingestion`)
    2. Optional `<vault>/System/Ingestion-Sources.md` (`ingestion` + optional `integrations`)
    3. Optional `<vault>/System/Integrations.md` (`integrations`)

    Separates `instances` (`integrations.instances.<id>`) from `bindings` (`integrations.bindings.<slot>`),
    and non-destructively bridges `ingestion.sources` (and legacy `ingestion_config`) into instances and bindings.
    """
    v_root = Path(vault_root).resolve()
    repo_root = Path(__file__).resolve().parent.parent
    tpl_path = v_root / "System" / "_templates" / "Integrations.template.md"
    if not tpl_path.is_file():
        tpl_path = repo_root / "System" / "_templates" / "Integrations.template.md"
    mem_path = v_root / "System" / "Memory.md"
    ing_path = v_root / "System" / "Ingestion-Sources.md"
    int_path = v_root / "System" / "Integrations.md"

    fm_layers: List[Tuple[str, Dict[str, Any]]] = []
    for label, p in (
        ("template_defaults", tpl_path),
        ("memory", mem_path),
        ("ingestion_sources", ing_path),
        ("integrations", int_path),
    ):
        if p.is_file():
            try:
                layer_fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
                if isinstance(layer_fm, dict):
                    fm_layers.append((label, layer_fm))
            except Exception:
                continue

    instances: Dict[str, Dict[str, Any]] = {}
    bindings: Dict[str, Dict[str, Any]] = {}
    ingestion_sources: Dict[str, Dict[str, Any]] = {}
    legacy_cfg: Dict[str, Any] = {}

    for layer_idx, (layer_label, layer) in enumerate(fm_layers):
        if isinstance(layer.get("ingestion_config"), dict):
            legacy_cfg.update(layer["ingestion_config"])

        int_block = layer.get("integrations")
        layer_instances_updated: Set[str] = set()
        if isinstance(int_block, dict):
            if isinstance(int_block.get("instances"), dict):
                for inst_id, icfg in int_block["instances"].items():
                    if isinstance(icfg, dict):
                        s_id = str(inst_id)
                        instances[s_id] = _merge_instance_dict(instances.get(s_id, {}), icfg, s_id)
                        instances[s_id]["source_layer"] = layer_label
                        layer_instances_updated.add(s_id)
            if isinstance(int_block.get("bindings"), dict):
                layer_bindings = _extract_layer_bindings(int_block["bindings"], source_layer=layer_label)
                cap_to_new_inst: Dict[str, Set[str]] = {}
                for lb_key, lb_val in layer_bindings.items():
                    c_name = lb_val.get("capability") or WORKFLOW_SLOT_TO_CAPABILITY.get(lb_key)
                    i_name = lb_val.get("instance")
                    if c_name and i_name:
                        cap_to_new_inst.setdefault(str(c_name), set()).add(str(i_name))

                for lb_key, lb_val in layer_bindings.items():
                    merged_b = dict(bindings.get(lb_key, {}))
                    merged_b.update(lb_val)
                    merged_b["source_layer"] = layer_label
                    bindings[lb_key] = merged_b

                # Synchronize corresponding capability and workflow slot aliases when overridden across layers
                for c_name, inst_set in cap_to_new_inst.items():
                    if len(inst_set) == 1:
                        sole_inst = next(iter(inst_set))
                        if c_name not in layer_bindings and (
                            c_name not in bindings or bindings[c_name].get("source_layer") != layer_label
                        ):
                            bindings[c_name] = {
                                "binding_key": c_name,
                                "capability": c_name,
                                "instance": sole_inst,
                                "source_layer": layer_label,
                            }
                        for slot in CAPABILITY_TO_WORKFLOW_SLOTS.get(c_name, []):
                            if slot not in layer_bindings and (
                                slot not in bindings or bindings[slot].get("source_layer") != layer_label
                            ):
                                bindings[slot] = {
                                    "binding_key": slot,
                                    "capability": c_name,
                                    "instance": sole_inst,
                                    "source_layer": layer_label,
                                }
                    elif len(inst_set) > 1:
                        if c_name in bindings and bindings[c_name].get("source_layer") != layer_label:
                            bindings.pop(c_name, None)
                        for slot in CAPABILITY_TO_WORKFLOW_SLOTS.get(c_name, []):
                            if slot in bindings and bindings[slot].get("source_layer") != layer_label:
                                bindings.pop(slot, None)

        ing_block = layer.get("ingestion")
        if isinstance(ing_block, dict) and isinstance(ing_block.get("sources"), dict):
            for alias, scfg in ing_block["sources"].items():
                if not isinstance(scfg, dict):
                    continue
                s_alias = str(alias)
                merged_s = dict(ingestion_sources.get(s_alias, {}))
                for sk, sv in scfg.items():
                    if sk == "collection" and not _is_placeholder_value(merged_s.get("collection")) and _is_placeholder_value(sv):
                        continue
                    merged_s[sk] = sv
                # If same layer also had an instance block, allow either enabled=True in the same layer to enable
                bind_slot = f"ingestion.sources.{s_alias}"
                bound_id = str((bindings.get(bind_slot) or {}).get("instance") or s_alias)
                if bound_id in layer_instances_updated and "enabled" in scfg:
                    if bool(scfg.get("enabled") is True) or bool(instances[bound_id].get("enabled") is True):
                        merged_s["enabled"] = True
                        instances[bound_id]["enabled"] = True
                ingestion_sources[s_alias] = merged_s

    # Non-destructive compatibility bridge for legacy_cfg when ingestion.sources is absent
    if not ingestion_sources and legacy_cfg:
        locker_root = str(legacy_cfg.get("locker_root") or "Chrysalis-Media-Locker")
        ingestion_sources["media"] = {
            "integration": GOOGLE_DRIVE_INTEGRATION_ID,
            "enabled": True,
            "collection": locker_root,
            "local_mount_path": legacy_cfg.get("local_locker_path"),
            "discovery_roots": list(legacy_cfg.get("discovery_roots") or ["01-Inbox", "02-Projects"]),
            "access": "read-only",
        }

    # Synchronize ingestion_sources <-> instances & bindings
    for alias, scfg in ingestion_sources.items():
        bind_slot = f"ingestion.sources.{alias}"
        bound_inst_id = (bindings.get(bind_slot) or {}).get("instance")
        if not bound_inst_id:
            bound_inst_id = str(scfg.get("instance") or (alias if alias in instances else f"ingestion-{alias}"))
        if bound_inst_id not in instances:
            instances[bound_inst_id] = _merge_instance_dict(
                {},
                {
                    "instance_id": bound_inst_id,
                    "integration": str(scfg.get("integration") or "").strip(),
                    "enabled": bool(scfg.get("enabled") is True),
                    "access": str(scfg.get("access") or scfg.get("mode") or "read-only").replace("_", "-"),
                    "collection": scfg.get("collection"),
                    "account_scope": scfg.get("account_scope"),
                    "bridged_from_ingestion_source": alias,
                    **{k: v for k, v in scfg.items() if k not in {"instance_id"}},
                },
                bound_inst_id,
            )
        else:
            inst_obj = instances[bound_inst_id]
            # Propagate non-placeholder fields in both directions without clobbering explicit overrides
            for k_sync, v_sync in scfg.items():
                if k_sync in {"instance_id", "enabled"} or v_sync is None:
                    continue
                if k_sync == "collection" and not _is_placeholder_value(inst_obj.get("collection")) and _is_placeholder_value(v_sync):
                    continue
                if _is_placeholder_value(inst_obj.get(k_sync)) or k_sync not in inst_obj:
                    inst_obj[k_sync] = v_sync
            if bool(scfg.get("enabled") is True) and not bool(inst_obj.get("enabled") is True):
                # Check if integrations.md explicitly set enabled: false; if not, honor ingestion.sources enabled: true
                int_doc_disabled = False
                for lbl, l_fm in fm_layers:
                    if lbl == "integrations":
                        raw_i = ((l_fm.get("integrations") or {}).get("instances") or {}).get(bound_inst_id)
                        if isinstance(raw_i, dict) and raw_i.get("enabled") is False:
                            int_doc_disabled = True
                if not int_doc_disabled:
                    inst_obj["enabled"] = True

            if not scfg.get("integration") and inst_obj.get("integration"):
                scfg["integration"] = inst_obj["integration"]
            for k_inst, v_inst in inst_obj.items():
                if k_inst in {"instance_id", "config"} or v_inst is None:
                    continue
                if k_inst == "collection" and not _is_placeholder_value(scfg.get("collection")) and _is_placeholder_value(v_inst):
                    continue
                if _is_placeholder_value(scfg.get(k_inst)) or k_inst not in scfg:
                    scfg[k_inst] = v_inst
            scfg["enabled"] = bool(inst_obj.get("enabled") is True)

        if bind_slot not in bindings:
            bindings[bind_slot] = {
                "binding_key": bind_slot,
                "capability": "ingestion.discover",
                "instance": bound_inst_id,
                "source_alias": alias,
            }

    # Also bridge in the reverse direction: if an ingestion binding (`ingestion.sources.<alias>`)
    # was declared only in `integrations.bindings` + `integrations.instances`, expose it in `bridged_ingestion_sources`
    bridged_ingestion_sources: Dict[str, Dict[str, Any]] = dict(ingestion_sources)
    for bind_key, bcfg in bindings.items():
        if bind_key.startswith("ingestion.sources."):
            alias = bind_key.split("ingestion.sources.", 1)[1]
            inst_id = str(bcfg.get("instance") or "")
            if alias and inst_id in instances:
                inst_data = instances[inst_id]
                existing_alias_cfg = dict(bridged_ingestion_sources.get(alias, {}))
                merged_alias = {
                    "alias": alias,
                    "integration": inst_data.get("integration") or existing_alias_cfg.get("integration"),
                    "enabled": bool(inst_data.get("enabled") is True),
                    "collection": (
                        bcfg.get("collection")
                        or (inst_data.get("collection") if not _is_placeholder_value(inst_data.get("collection")) else None)
                        or existing_alias_cfg.get("collection")
                        or inst_data.get("collection")
                    ),
                    "account_scope": bcfg.get("account_scope") or inst_data.get("account_scope") or existing_alias_cfg.get("account_scope"),
                    "access": str(inst_data.get("access") or existing_alias_cfg.get("access") or "read-only"),
                }
                for k_extra, v_extra in existing_alias_cfg.items():
                    if k_extra not in merged_alias or merged_alias[k_extra] is None:
                        merged_alias[k_extra] = v_extra
                for k_inst, v_inst in inst_data.items():
                    if k_inst not in {"instance_id", "config"} and v_inst is not None:
                        if k_inst == "collection" and not _is_placeholder_value(merged_alias.get("collection")) and _is_placeholder_value(v_inst):
                            continue
                        merged_alias[k_inst] = v_inst
                bridged_ingestion_sources[alias] = merged_alias

    config_path = str(int_path) if int_path.is_file() else (str(ing_path) if ing_path.is_file() else (str(mem_path) if mem_path.is_file() else None))
    return {
        "schema_version": INTEGRATION_CAPABILITY_CONTRACT_VERSION,
        "config_path": config_path,
        "instances": instances,
        "bindings": bindings,
        "bridged_ingestion_sources": bridged_ingestion_sources,
    }


def evaluate_instance_readiness(
    vault_root: Union[Path, str],
    instance_cfg: Dict[str, Any],
    *,
    capability: Optional[str] = None,
    custom_registry: Optional[Dict[str, Dict[str, Any]]] = None,
    env: Optional[Dict[str, str]] = None,
    verified_override: bool = False,
) -> Dict[str, Any]:
    """
    Evaluates the 5 readiness states (`installed`, `configured`, `authenticated`, `available`, `verified`)
    for a given integration instance.
    """
    v_root = Path(vault_root).resolve()
    repo_root = Path(__file__).resolve().parent.parent
    integration_id = str(instance_cfg.get("integration") or "").strip()

    adapter, adapter_err = get_registered_adapter(integration_id, custom_registry=custom_registry)
    skill_rel = adapter.get("skill_path") if adapter else f".agent/skills/{integration_id}/SKILL.md"
    skill_exists = (v_root / skill_rel).is_file() or (repo_root / skill_rel).is_file()
    installed = adapter is not None and skill_exists

    enabled = bool(instance_cfg.get("enabled") is True)
    cap_ok = True
    if capability and adapter is not None:
        cap_ok = capability in adapter.get("capabilities", [])
    configured = installed and enabled and cap_ok

    cfg_block = instance_cfg.get("config") if isinstance(instance_cfg.get("config"), dict) else {}
    inline_secret_issues = _scan_config_for_inline_secrets(instance_cfg)
    secret_ref = (
        instance_cfg.get("secret_ref")
        or instance_cfg.get("auth_ref")
        or cfg_block.get("secret_ref")
        or cfg_block.get("auth_ref")
    )
    resolved_secret, secret_err = resolve_secret_reference(secret_ref, vault_root=v_root, env=env)

    requires_secret = bool(adapter.get("requires_secret")) if adapter else False
    has_mock_or_fixture = bool(
        instance_cfg.get("fixture_path")
        or cfg_block.get("fixture_path")
        or instance_cfg.get("route_fixture_path")
        or cfg_block.get("route_fixture_path")
        or instance_cfg.get("mock_transport")
        or cfg_block.get("mock_transport")
    )

    if inline_secret_issues:
        authenticated = False
    elif requires_secret:
        authenticated = bool(resolved_secret) or has_mock_or_fixture
    else:
        authenticated = secret_err is None

    if not configured or not authenticated:
        available = False
    elif integration_id == OBSIDIAN_MAPS_INTEGRATION_ID:
        base_rel = str(instance_cfg.get("base_view_path") or cfg_block.get("base_view_path") or "TaskNotes/Views/maps-default.base")
        available = (v_root / base_rel).is_file() or (repo_root / base_rel).is_file()
    elif integration_id == GOOGLE_MAPS_INTEGRATION_ID:
        live_http = bool(instance_cfg.get("live_http_enabled") is True or cfg_block.get("live_http_enabled") is True)
        available = has_mock_or_fixture or (live_http and bool(resolved_secret))
    elif integration_id == GOOGLE_DRIVE_INTEGRATION_ID:
        mount_p = instance_cfg.get("local_mount_path") or cfg_block.get("local_mount_path")
        available = bool(mount_p and Path(str(mount_p)).is_dir()) or has_mock_or_fixture
    elif integration_id == GOOGLE_TASKS_INTEGRATION_ID:
        snap_p = (
            instance_cfg.get("mcp_snapshot_path")
            or cfg_block.get("mcp_snapshot_path")
            or instance_cfg.get("export_path")
            or cfg_block.get("export_path")
        )
        available = bool(snap_p and (Path(str(snap_p)).is_file() or (v_root / str(snap_p)).is_file())) or has_mock_or_fixture
    else:
        available = True

    verified = bool(available and verified_override)

    return {
        "installed": installed,
        "configured": configured,
        "authenticated": authenticated,
        "available": available,
        "verified": verified,
        "resolved_secret": resolved_secret,
        "secret_error": secret_err,
        "inline_secret_issues": inline_secret_issues,
        "adapter_error": adapter_err,
    }


def resolve_capability_binding(
    vault_root: Union[Path, str],
    capability: str,
    *,
    workflow_binding: Optional[str] = None,
    instance_id: Optional[str] = None,
    requested_effect: Optional[str] = None,
    custom_registry: Optional[Dict[str, Dict[str, Any]]] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Resolves a workflow capability request to a specific configured integration instance.
    Fails deterministically on missing, disabled, ambiguous, unsupported, or unauthorized bindings.
    """
    cap = str(capability or "").strip()
    if cap not in CAPABILITY_FAMILIES:
        if cap in FUTURE_CAPABILITY_FAMILIES:
            return {
                "status": "capability_deferred",
                "capability": cap,
                "diagnostics": [
                    {
                        "code": "capability_deferred",
                        "message": f"Capability '{cap}' is reserved for a future phase and is not active.",
                    }
                ],
            }
        return {
            "status": "capability_not_supported",
            "capability": cap,
            "diagnostics": [
                {
                    "code": "unknown_capability_family",
                    "message": f"Capability '{cap}' is not a recognized v1.0.0 capability family.",
                }
            ],
        }

    cfg = resolve_integration_config(vault_root)
    instances = cfg["instances"]
    bindings = cfg["bindings"]

    selected_instance_id: Optional[str] = None
    binding_record: Optional[Dict[str, Any]] = None

    # Precompute enabled instances that support `cap`
    matching_enabled: List[str] = []
    for inst_key, inst_val in instances.items():
        if inst_val.get("enabled") is not True:
            continue
        adp, _ = get_registered_adapter(str(inst_val.get("integration") or ""), custom_registry=custom_registry)
        if adp and cap in adp.get("capabilities", []):
            matching_enabled.append(inst_key)

    if instance_id:
        selected_instance_id = str(instance_id).strip()
        if selected_instance_id not in instances:
            # Check if instance_id looks like a dynamic module path
            _, err = get_registered_adapter(selected_instance_id, custom_registry=custom_registry)
            if err and err["code"] == "arbitrary_adapter_import_forbidden":
                return {
                    "ok": False,
                    "status": "arbitrary_adapter_import_forbidden",
                    "capability": cap,
                    "diagnostics": [err],
                }
            return {
                "ok": False,
                "status": "binding_missing",
                "capability": cap,
                "instance_id": selected_instance_id,
                "diagnostics": [
                    {
                        "code": "binding_missing",
                        "message": f"Integration instance '{selected_instance_id}' is not configured.",
                    }
                ],
            }
    else:
        wb = str(workflow_binding).strip() if workflow_binding else None
        if wb:
            binding_record = bindings.get(wb) or bindings.get(cap)

        if binding_record is not None:
            bound_cap = binding_record.get("capability")
            if bound_cap and str(bound_cap).strip() != cap:
                return {
                    "ok": False,
                    "status": "capability_not_supported",
                    "capability": cap,
                    "workflow_binding": wb,
                    "diagnostics": [
                        {
                            "code": "binding_capability_mismatch",
                            "message": f"Binding '{wb}' is bound to '{bound_cap}', not '{cap}'.",
                        }
                    ],
                }
            cand_inst = str(binding_record.get("instance") or "").strip()
            if not cand_inst or cand_inst not in instances:
                return {
                    "ok": False,
                    "status": "binding_missing",
                    "capability": cap,
                    "workflow_binding": wb,
                    "instance_id": cand_inst,
                    "diagnostics": [
                        {
                            "code": "binding_missing",
                            "message": f"Binding '{wb}' references missing instance '{cand_inst}'.",
                        }
                    ],
                }
            if binding_record.get("source_layer") == "template_defaults":
                # If binding is only from template_defaults, fall through to instance scan when multiple
                # instances are enabled or a non-default user instance is enabled
                if len(matching_enabled) > 1:
                    binding_record = None
                elif len(matching_enabled) == 1 and matching_enabled[0] != cand_inst:
                    selected_instance_id = matching_enabled[0]
                else:
                    selected_instance_id = cand_inst
            else:
                selected_instance_id = cand_inst

        if selected_instance_id is None:
            # Fall through to explicit non-template bindings for `capability`, then instance-capability scan
            matching_bound_instances: List[str] = []
            for b_key, b_val in bindings.items():
                if b_val.get("source_layer") == "template_defaults":
                    continue
                if b_val.get("capability") == cap and b_val.get("instance") in instances:
                    inst_cand = str(b_val["instance"])
                    if instances[inst_cand].get("enabled") is True and inst_cand not in matching_bound_instances:
                        matching_bound_instances.append(inst_cand)

            if len(matching_bound_instances) == 1:
                selected_instance_id = matching_bound_instances[0]
            elif len(matching_bound_instances) > 1:
                return {
                    "ok": False,
                    "status": "binding_ambiguous",
                    "capability": cap,
                    "workflow_binding": wb,
                    "candidate_instances": matching_bound_instances,
                    "diagnostics": [
                        {
                            "code": "binding_ambiguous",
                            "message": (
                                f"Multiple enabled bindings supply capability '{cap}': {matching_bound_instances}. "
                                "Specify workflow_binding or instance_id explicitly."
                            ),
                        }
                    ],
                }
            elif len(matching_enabled) == 1:
                selected_instance_id = matching_enabled[0]
            elif len(matching_enabled) > 1:
                return {
                    "ok": False,
                    "status": "binding_ambiguous",
                    "capability": cap,
                    "workflow_binding": wb,
                    "candidate_instances": matching_enabled,
                    "diagnostics": [
                        {
                            "code": "binding_ambiguous",
                            "message": (
                                f"Ambiguous integration instances for capability '{cap}': {matching_enabled}. "
                                "Specify workflow_binding or instance_id explicitly."
                            ),
                        }
                    ],
                }
            else:
                # Check if any disabled instance supports `cap`
                disabled_matches: List[str] = []
                for inst_key, inst_val in instances.items():
                    adp, _ = get_registered_adapter(str(inst_val.get("integration") or ""), custom_registry=custom_registry)
                    if adp and cap in adp.get("capabilities", []):
                        disabled_matches.append(inst_key)
                if disabled_matches:
                    first_dis = disabled_matches[0]
                    dis_cfg = instances.get(first_dis, {})
                    return {
                        "ok": False,
                        "status": "instance_disabled",
                        "capability": cap,
                        "workflow_binding": wb,
                        "instance_id": first_dis,
                        "instance": dis_cfg,
                        "instance_config": dis_cfg,
                        "candidate_instances": disabled_matches,
                        "diagnostics": [
                            {
                                "code": "instance_disabled",
                                "message": f"Integration instance(s) {disabled_matches} for '{cap}' are disabled (enabled: false).",
                            }
                        ],
                    }
                return {
                    "ok": False,
                    "status": "binding_missing",
                    "capability": cap,
                    "workflow_binding": wb,
                    "diagnostics": [
                        {
                            "code": "binding_missing",
                            "message": f"No integration instance or binding configured for capability '{cap}'.",
                        }
                    ],
                }

    instance_cfg = instances[selected_instance_id]
    integration_id = str(instance_cfg.get("integration") or "").strip()
    adapter, adapter_err = get_registered_adapter(integration_id, custom_registry=custom_registry)
    if adapter_err is not None or adapter is None:
        return {
            "ok": False,
            "status": adapter_err["code"] if adapter_err else "unknown_integration_adapter",
            "capability": cap,
            "instance_id": selected_instance_id,
            "instance": instance_cfg,
            "instance_config": instance_cfg,
            "diagnostics": [adapter_err] if adapter_err else [],
        }

    if instance_cfg.get("enabled") is not True:
        return {
            "ok": False,
            "status": "instance_disabled",
            "capability": cap,
            "instance_id": selected_instance_id,
            "integration": integration_id,
            "instance": instance_cfg,
            "instance_config": instance_cfg,
            "diagnostics": [
                {
                    "code": "instance_disabled",
                    "message": f"Integration instance '{selected_instance_id}' ({integration_id}) has enabled: false.",
                }
            ],
        }

    if cap not in adapter.get("capabilities", []):
        return {
            "ok": False,
            "status": "capability_not_supported",
            "capability": cap,
            "instance_id": selected_instance_id,
            "integration": integration_id,
            "instance": instance_cfg,
            "instance_config": instance_cfg,
            "diagnostics": [
                {
                    "code": "capability_not_supported",
                    "message": f"Integration '{integration_id}' does not support capability '{cap}'.",
                }
            ],
        }

    declared_effect = adapter.get("effects", {}).get(cap, "external_query")
    if requested_effect == "external_mutation" or declared_effect == "external_mutation":
        if not adapter.get("external_mutation_authorized") or not instance_cfg.get("authorize_external_mutation"):
            return {
                "ok": False,
                "status": "effect_not_authorized",
                "capability": cap,
                "instance_id": selected_instance_id,
                "integration": integration_id,
                "effect": "external_mutation",
                "diagnostics": [
                    {
                        "code": "effect_not_authorized",
                        "message": f"External mutation is prohibited for integration '{integration_id}' / capability '{cap}'.",
                    }
                ],
            }

    readiness = evaluate_instance_readiness(
        vault_root,
        instance_cfg,
        capability=cap,
        custom_registry=custom_registry,
        env=env,
    )
    if readiness["inline_secret_issues"]:
        return {
            "ok": False,
            "status": "inline_secret_forbidden",
            "capability": cap,
            "instance_id": selected_instance_id,
            "integration": integration_id,
            "readiness": {k: readiness[k] for k in READINESS_STATES},
            "diagnostics": readiness["inline_secret_issues"],
        }

    return {
        "ok": True,
        "status": "ok",
        "capability": cap,
        "workflow_binding": workflow_binding,
        "instance_id": selected_instance_id,
        "integration": integration_id,
        "effect": declared_effect,
        "instance": instance_cfg,
        "instance_config": instance_cfg,
        "adapter": adapter,
        "readiness": {k: readiness[k] for k in READINESS_STATES},
        "resolved_secret": readiness["resolved_secret"],
        "diagnostics": [],
    }


def validate_capability_result(
    result: Any,
    *,
    expected_capability: str,
) -> Tuple[bool, List[Dict[str, Any]]]:
    """
    Validates a `CapabilityResultEnvelope` against the v1.0.0 contract.
    Rejects malformed capability outputs, ingestion-envelope confusion, and zero-minute failed routes.
    """
    issues: List[Dict[str, Any]] = []
    if not isinstance(result, dict):
        return False, [{"code": "malformed_capability_result", "message": "Result must be a dictionary."}]

    if result.get("contract_version") != INTEGRATION_CAPABILITY_CONTRACT_VERSION:
        issues.append(
            {
                "code": "invalid_contract_version",
                "message": f"Expected contract_version '{INTEGRATION_CAPABILITY_CONTRACT_VERSION}', got {result.get('contract_version')!r}.",
            }
        )

    if result.get("capability") != expected_capability:
        issues.append(
            {
                "code": "capability_mismatch",
                "message": f"Expected capability '{expected_capability}', got {result.get('capability')!r}.",
            }
        )

    effect = result.get("effect")
    if effect not in ALLOWED_OPERATION_EFFECTS or effect == "external_mutation":
        issues.append(
            {
                "code": "invalid_or_unauthorized_effect",
                "message": f"Invalid or unauthorized operation effect: {effect!r}.",
            }
        )

    if expected_capability == "location.resolve":
        status = result.get("status")
        if status not in {
            "resolved",
            "ambiguous",
            "not_found",
            "invalid_input",
            "invalid_request",
            "privacy_violation",
            "unavailable",
            "auth_failure",
            "quota_exceeded",
            "timeout",
            "offline",
        }:
            issues.append({"code": "invalid_location_status", "message": f"Unknown status: {status!r}"})
        cands = result.get("candidates")
        if not isinstance(cands, list):
            issues.append({"code": "malformed_candidates", "message": "'candidates' must be a list."})
        elif status == "resolved" and len(cands) != 1:
            issues.append(
                {
                    "code": "resolved_candidate_count_mismatch",
                    "message": "'resolved' status requires exactly 1 candidate.",
                }
            )
        elif status == "ambiguous" and len(cands) < 2:
            issues.append(
                {
                    "code": "ambiguous_candidate_count_mismatch",
                    "message": "'ambiguous' status requires at least 2 candidates.",
                }
            )

    elif expected_capability == "routing.estimate":
        status = result.get("status")
        est = result.get("estimate")
        if not isinstance(est, dict):
            issues.append({"code": "malformed_route_estimate", "message": "'estimate' must be a dictionary."})
        else:
            dur = est.get("duration_minutes")
            if status == "ok":
                if dur is None or isinstance(dur, bool) or float(dur) <= 0:
                    issues.append(
                        {
                            "code": "invalid_positive_duration",
                            "message": "Successful route estimate must have duration_minutes > 0.",
                        }
                    )
                if est.get("duration_unit") != "minutes":
                    issues.append(
                        {
                            "code": "missing_duration_unit",
                            "message": "Route estimate must specify duration_unit: 'minutes'.",
                        }
                    )
            else:
                if dur is not None:
                    issues.append(
                        {
                            "code": "non_null_failed_duration_forbidden",
                            "message": f"Failed or unavailable route estimate (status={status!r}) must have duration_minutes=None, never {dur!r}.",
                        }
                    )

    elif expected_capability == "visualization.map_projection":
        if not isinstance(result.get("markers"), list) or not isinstance(result.get("filtered_records"), list):
            issues.append(
                {
                    "code": "malformed_map_projection",
                    "message": "Map projection result must contain 'markers' and 'filtered_records' lists.",
                }
            )

    return len(issues) == 0, issues


def invoke_capability(
    vault_root: Union[Path, str],
    capability: str,
    request_payload: Dict[str, Any],
    *,
    workflow_binding: Optional[str] = None,
    instance_id: Optional[str] = None,
    requested_effect: Optional[str] = None,
    transport: Optional[Any] = None,
    custom_registry: Optional[Dict[str, Dict[str, Any]]] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Resolves a capability binding and invokes the bound integration adapter, validating
    the returned capability envelope before returning it to the caller.
    """
    resolution = resolve_capability_binding(
        vault_root,
        capability,
        workflow_binding=workflow_binding,
        instance_id=instance_id,
        requested_effect=requested_effect,
        custom_registry=custom_registry,
        env=env,
    )
    if resolution.get("status") != "ok":
        return {
            "contract_version": INTEGRATION_CAPABILITY_CONTRACT_VERSION,
            "capability": capability,
            "status": resolution.get("status", "unavailable"),
            "effect": resolution.get("effect", "external_query"),
            "readiness": resolution.get("readiness"),
            "diagnostics": resolution.get("diagnostics", []),
        }

    adapter = resolution["adapter"]
    handler = adapter.get("handlers", {}).get(capability)
    if not callable(handler):
        return {
            "contract_version": INTEGRATION_CAPABILITY_CONTRACT_VERSION,
            "capability": capability,
            "status": "capability_not_supported",
            "effect": resolution["effect"],
            "diagnostics": [
                {
                    "code": "missing_capability_handler",
                    "message": f"Adapter '{resolution['integration']}' has no callable handler for '{capability}'.",
                }
            ],
        }

    instance_cfg = resolution["instance_config"]
    resolved_secret = resolution.get("resolved_secret")

    if capability in {"location.resolve", "routing.estimate"}:
        raw_result = handler(
            request_payload,
            instance_config=instance_cfg,
            transport=transport if transport is not None else instance_cfg.get("mock_transport"),
            resolved_secret=resolved_secret,
        )
    elif capability == "visualization.map_projection":
        raw_result = handler(
            request_payload,
            instance_config=instance_cfg,
        )
    else:
        raw_result = handler(instance_cfg)

    valid, validation_issues = validate_capability_result(raw_result, expected_capability=capability)
    if not valid:
        return {
            "contract_version": INTEGRATION_CAPABILITY_CONTRACT_VERSION,
            "capability": capability,
            "integration": resolution["integration"],
            "instance_id": resolution["instance_id"],
            "effect": resolution["effect"],
            "status": "malformed_capability_result",
            "diagnostics": validation_issues,
        }

    raw_result = dict(raw_result)
    raw_result["instance_id"] = resolution["instance_id"]
    raw_result["workflow_binding"] = workflow_binding
    readiness = dict(resolution["readiness"])
    if raw_result.get("status") in {"resolved", "ambiguous", "ok", "empty", "policy_filtered"}:
        readiness["available"] = True
        readiness["verified"] = True
    raw_result["readiness"] = readiness
    return raw_result


def evaluate_all_integrations(
    vault_root: Union[Path, str],
    *,
    custom_registry: Optional[Dict[str, Dict[str, Any]]] = None,
    env: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Evaluates readiness states and secret/adapter diagnostics across all configured
    integration instances and bindings in `<vault>/System/Integrations.md` or `<vault>/System/Memory.md`.
    """
    cfg = resolve_integration_config(vault_root)
    instances_report: Dict[str, Dict[str, Any]] = {}
    diagnostics: List[Dict[str, Any]] = []

    for inst_id, inst_cfg in (cfg.get("instances") or {}).items():
        readiness = evaluate_instance_readiness(
            vault_root,
            inst_cfg,
            custom_registry=custom_registry,
            env=env,
        )
        inst_diags: List[Dict[str, Any]] = []
        if readiness.get("adapter_error"):
            inst_diags.append({**readiness["adapter_error"], "severity": "error"})
        for issue in readiness.get("inline_secret_issues") or []:
            inst_diags.append({**issue, "severity": "error"})
        if readiness.get("secret_error"):
            secret_err = readiness["secret_error"]
            err_code = secret_err.get("code", "secret_unresolved") if isinstance(secret_err, dict) else str(secret_err)
            err_msg = secret_err.get("message", str(secret_err)) if isinstance(secret_err, dict) else str(secret_err)
            inst_diags.append(
                {
                    "code": err_code,
                    "severity": "error" if inst_cfg.get("enabled") else "info",
                    "message": f"Secret reference issue for '{inst_id}': {err_msg}",
                }
            )
        for d in inst_diags:
            diagnostics.append({"instance_id": inst_id, **d})
        instances_report[inst_id] = {
            "instance_id": inst_id,
            "integration": inst_cfg.get("integration"),
            "enabled": bool(inst_cfg.get("enabled") is True),
            "readiness": {k: readiness[k] for k in READINESS_STATES},
            "diagnostics": inst_diags,
        }

    return {
        "contract_version": INTEGRATION_CAPABILITY_CONTRACT_VERSION,
        "config_path": cfg.get("config_path"),
        "instances": instances_report,
        "bindings": cfg.get("bindings", {}),
        "diagnostics": diagnostics,
    }
