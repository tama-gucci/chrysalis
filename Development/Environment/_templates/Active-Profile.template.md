---
type: active_environment_profile
id: chrysalis-active-environment
title: "Active Environment & Deployment Profile"
last_updated: "{{timestamp}}"

production_runtime:
  role: "Chrysalis Execution (Production)"
  storage_substrate:
    provider: "{{storage_provider}}" # e.g., google_drive, icloud, syncthing
    central_host_type: "cloud_synced_substrate"
    cloud_root: "{{cloud_root}}"
    notes: "{{storage_provider}} is the central host substrate. Multiple client devices run Obsidian concurrently synced to this root."
  orchestrator:
    name: "{{production_orchestrator_name}}" # e.g., Google Antigravity
    platform: "{{production_orchestrator_platform}}" # google_antigravity
    role: "Autonomous Production Orchestrator"
    adapter_spec: "{{production_adapter_spec}}" # [[System/Orchestrators/Antigravity/Adapter-Spec|Antigravity Adapter]]
    schedules:
      morning_calibration: "{{morning_time}} {{timezone_code}}"
      evening_staging: "{{evening_time}} {{timezone_code}}"

development_environment:
  role: "Chrysalis Engineering & System Evolution (Meta/Dev)"
  development_workstation:
    hostname: "{{dev_hostname}}"
    role: "Active Development Machine"
    os: "{{dev_os}}"
    local_mount_path: "{{dev_mount_path}}"
    manifest: "[[System/Environment/{{dev_hostname}}|{{dev_hostname}}.md]]"
    notes: "Used specifically for authoring, testing, and developing Chrysalis codebase, scripts, and skills."
  development_agent:
    name: "{{dev_agent_name}}" # e.g., Google Antigravity
    platform: "{{dev_agent_platform}}" # google_antigravity
    role: "Development & Architecture Agent (IDE)"

client_topology:
  sync_model: "Multi-device concurrent sync via {{storage_provider}}"
  client_app: "Obsidian"
  devices: "Concurrently active mobile, tablet, and desktop clients"

timezone:
  explicit_offset: "{{timezone_offset}}" # e.g., -05:00
  iana_name: "{{timezone_iana}}" # e.g., America/Chicago
---

# 🌐 Active Environment & Deployment Profile

> **Generated / Updated:** {{timestamp}}  
> **Central Cloud Host Substrate:** `{{storage_provider}}` (`{{cloud_root}}`)  
> **Production Orchestrator:** `{{production_orchestrator_name}}`  
> **Development Workstation:** `{{dev_hostname}}` (`{{dev_os}}`)  
> **Development IDE Agent:** `{{dev_agent_name}}`  
> **Timezone:** `{{timezone_offset}}` (`{{timezone_iana}}`)

This note defines the clear division of labor between running Chrysalis in production and developing Chrysalis in engineering.
