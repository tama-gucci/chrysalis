---
type: system_manifest
id: "system-manifest-{{system_name}}"
system_name: "{{system_name}}"
hostname: "{{hostname}}"
model: "{{model}}" # e.g. Surface Pro X, Custom Desktop, ThinkPad X1
os: "{{os}}"
arch: "{{arch}}" # x86_64, aarch64, arm64, AMD64
kernel: "{{kernel}}"
chassis: "{{chassis}}" # desktop, laptop, tablet, convertible, server, vm, sbc
role: "{{role}}" # e.g., Primary Workstation, At-Home Server, Development Laptop, Edge Node
package_manager: "{{package_manager}}" # pacman, apt, dnf, brew, winget, scoop, choco, nix
generated_at: "{{timestamp}}"
last_updated: "{{timestamp}}"
status: "active" # active, maintenance, decommissioned
total_explicit_packages: 0
native_count: 0
foreign_count: 0
tags:
  - system/manifest
  - system/{{system_name}}
---

# 🖥️ {{system_name}} System Package Manifest

> **Captured:** {{timestamp}}  
> **Host OS:** {{os}} ({{kernel}}) • **Arch:** {{arch}} • **Chassis:** {{chassis}}  
> **Native Explicit Packages:** {{native_count}}  
> **Foreign / User Packages:** {{foreign_count}}  
> **Total Explicit Packages:** {{total_explicit_packages}}

---

## 📋 System Profile & Hardware Role

* **Hardware Model:** {{model}}
* **Role:** {{role}}
* **Package Manager:** `{{package_manager}}`
* **Status:** `{{status}}`

---

## 📦 Package Inventory Telemetry

```json
{
  "timestamp": "{{timestamp}}",
  "system_name": "{{system_name}}",
  "hostname": "{{hostname}}",
  "model": "{{model}}",
  "host_os": "{{os}}",
  "kernel": "{{kernel}}",
  "arch": "{{arch}}",
  "chassis": "{{chassis}}",
  "package_counts": {
    "native_explicit": 0,
    "foreign_explicit": 0,
    "total_explicit": 0
  },
  "native_packages": {},
  "foreign_packages": {}
}
```
