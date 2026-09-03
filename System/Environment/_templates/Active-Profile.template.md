---
type: active_environment_profile
id: chrysalis-active-environment
title: "Active Environment & Deployment Profile"
last_updated: "{{timestamp}}"

production_runtime:
  role: "Chrysalis Continuous Execution (Home Server Node)"
  server_host:
    name: "{{server_hostname}}" # e.g., station-server
    role: "24/7 At-Home Server"
    os: "{{server_os}}" # e.g., Windows 11 on ARM (ARM64) or Linux
    chassis: "{{server_chassis}}" # e.g., tablet / server / headless
    power_profile: "Low-power continuous execution node"
    manifest: "[[System/Environment/{{server_hostname}}|{{server_hostname}}.md]]"
  storage_substrate:
    provider: "{{storage_provider}}" # e.g., google_drive, icloud, syncthing
    central_host_type: "cloud_synced_substrate"
    cloud_root: "{{cloud_root}}" # e.g., GoogleDrive/chrysalis
    notes: "{{storage_provider}} is the synced substrate connecting the home server node, development workstation, and mobile Obsidian clients."
  orchestrator:
    name: "{{production_orchestrator_name}}" # e.g., Google Antigravity
    platform: "{{production_orchestrator_platform}}" # google_antigravity
    role: "Autonomous Production Orchestrator"
    runtime_host: "{{server_hostname}}"
    adapter_spec: "{{production_adapter_spec}}" # [[System/Orchestrators/Antigravity/Adapter-Spec|Antigravity Adapter]]
    schedules:
      morning_calibration: "{{morning_time}} {{timezone_code}}"
      evening_staging: "{{evening_time}} {{timezone_code}}"
    duties:
      - "Autonomous morning wake check-in & diurnal calibration (/morning, /calibrate)"
      - "Nightly task reconciliation & roadmap audit (/audit, /evening)"
      - "Tool-gated disk mutations (guaranteed Anti-Simulation compliance)"
      - "Bio-cognitive ultradian focus timeblocking (/plan)"

workstation_environment:
  role: "Development & Engineering Workstation"
  workstation:
    hostname: "{{dev_hostname}}" # e.g., station-node
    role: "Primary Development Rig"
    os: "{{dev_os}}" # e.g., Arch Linux (x86_64)
    local_mount_path: "{{dev_mount_path}}"
    manifest: "[[System/Environment/{{dev_hostname}}|{{dev_hostname}}.md]]"
    power_profile: "Standard workstation power profile; zero background daemons"

development_pipeline:
  role: "Chrysalis Engineering & System Evolution (Meta/Dev)"
  agent_ide:
    name: "{{dev_agent_name}}" # e.g., Google Antigravity
    platform: "{{dev_agent_platform}}" # google_antigravity
    role: "Development & Architecture Agent (IDE)"
  environment_profile: "System/Environment/Active-Profile.md"

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
> **Development Workstation:** `{{dev_hostname}}` (`{{dev_os}}`) — synthetic default: `station-node`  
> **Development IDE Agent:** `{{dev_agent_name}}`  
> **Timezone:** `{{timezone_offset}}` (`{{timezone_iana}}`)

This note defines the clear division of labor between running Chrysalis in production and developing Chrysalis in engineering.
