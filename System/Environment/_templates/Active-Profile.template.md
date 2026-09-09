---
type: active_environment_profile
id: chrysalis-active-environment
title: "Active Environment & Deployment Profile"
last_updated: "{{timestamp}}"

production_runtime:
  role: "Chrysalis Continuous Execution (Home Server Node)"
  server_host:
    name: "{{server_hostname}}" # e.g., golem
    model: "{{server_model}}" # e.g., Microsoft Surface Pro X
    role: "24/7 At-Home Server"
    os: "{{server_os}}" # e.g., Windows 11 on ARM (ARM64) or Linux
    chassis: "{{server_chassis}}" # e.g., tablet / convertible / server
    power_profile: "Plugged-in continuous execution node"
    ram_total_gb: 16 # Golem hardware topology: 16GB total RAM
    hyper_v_home_assistant_gb: 4 # 4GB dedicated to Home Assistant VM
    chrysalis_operational_memory_gb: 12 # 12GB operational memory for Chrysalis & agents
    manifest: "[[System/Environment/{{server_hostname}}|{{server_hostname}}.md]]"
  gateway:
    daemon: "apps/gateway (FastAPI)"
    port: 8765 # Chrysalis Ambient Gateway port
    obsidian_chrysalis_port: 8080 # chrysalis-obsidian plugin port
    tunnel: "Cloudflare Zero-Trust Tunnel"
    bridge: "Pluggable Orchestrator Bridge (BaseOrchestratorBridge)"
  intelligence_mode: "option_a_gateway" # option_a_gateway (Golem) or option_b_mobile_native (Edge)
  storage_substrate:
    provider: "{{storage_provider}}" # e.g., google_drive, icloud, syncthing
    central_host_type: "cloud_synced_substrate"
    cloud_root: "{{cloud_root}}" # e.g., GoogleDrive/vault
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
  client_apps:
    obsidian: "Desktop and tablet Obsidian vault with chrysalis-obsidian (Port 8080)"
    mobile: "Android smartphone Flutter client with Model C calendar sync"
    wearable: "Standalone circular Wear OS smartwatch companion (384x384 OLED)"
  devices: "Concurrently active mobile, wearable, tablet, and desktop clients"

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
