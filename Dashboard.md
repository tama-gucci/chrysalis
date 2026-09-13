---
title: Chrysalis Command Center
type: dashboard
---

# 🛸 Chrysalis Command Center

Requires the Dataview plugin enabled in this vault. Task lists remain available as ordinary notes when it is disabled.

> [!abstract] System State & Energy Profile
> **Phase:** Pillar 1 (Core Foundation & Systems Setup)  
> **Diurnal Rhythm:** Diurnally calibrated focus blocks relative to $T_{\text{wake}}$ (Peak Sprints • Slump/Defrost • Recovery)  
> **Vault Path:** `chrysalis/`

---

## ⚡ 1. Daily Action Queue (`status: todo`)
```dataview
TABLE 
    urgency_tier as "Tier",
    priority as "Priority",
    timeEstimate + "m" as "Duration",
    energy as "Energy",
    due as "Due Date",
    file.folder as "Folder"
FROM "chrysalis/Tasks" OR "TaskNotes/Tasks"
WHERE status = "todo" AND file.name != "example-task"
SORT urgency_tier DESC, priority DESC, due ASC
```

---

## 🎯 2. Today's Scheduled Focus
```dataview
TABLE
    timeEstimate + "m" as "Duration",
    scheduled as "Scheduled Block",
    priority as "Priority",
    energy as "Energy"
FROM "chrysalis/Tasks" OR "TaskNotes/Tasks"
WHERE scheduled != null AND date(scheduled).day = date(today).day AND date(scheduled).month = date(today).month AND date(scheduled).year = date(today).year AND status != "done" AND status != "archived"
SORT scheduled ASC
```

---

## 🏛️ 3. Active Pillar 1 Projects & Deliverables
```dataview
TABLE
    pillar as "Pillar",
    status as "Status",
    horizon_window as "Horizon Window"
FROM "chrysalis/Projects" OR "Projects"
WHERE type = "project_roadmap"
SORT pillar ASC
```

---

## 📚 4. Recent Slipbox Additions (Zettelkasten)
```dataview
TABLE
    dateCreated as "Created",
    tags as "Domain Tags",
    aliases as "Aliases"
FROM "chrysalis/Slipbox" OR "Slipbox"
WHERE type = "permanent-note" OR contains(tags, "zettel")
SORT dateCreated DESC
LIMIT 10
```

---

## 📦 5. Completed & Archived Tasks
```dataview
TABLE
    title as "Completed Task",
    file.mtime as "Archived Date"
FROM "chrysalis/Archive" OR "TaskNotes/Archive"
SORT file.mtime DESC
LIMIT 10
```
