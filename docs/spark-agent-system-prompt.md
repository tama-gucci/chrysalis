> Deferred integration experiment: these scenarios are not evidence of a supported or installed Spark/Windows runtime. The setup wrapper deploys local framework files only; daemon registration and cloud pairing require a separately verified integration plan.

# Chrysalis AI Agent — Zero-Maintenance Gemini Spark `Skills` & `Schedules`

> **Upload-Ready Skill Folder in Your Chrysalis Vault**:
> An always-up-to-date, upload-ready copy of Gemini Spark's **`chrysalis-router`** skill is maintained inside your Chrysalis database at:
> * **Runtime Vault**: `Skills/chrysalis-router/SKILL.md` (and `.agent/skills/chrysalis-router/SKILL.md`)
> * **Source Repository**: `.agent/skills/chrysalis-router/SKILL.md`
>
> It strictly satisfies Gemini Spark's **Upload a skill** requirements (`kebab-case` `name: chrysalis-router` in `SKILL.md` inside the `chrysalis-router/` folder) and is automatically updated by `python update.py`.

---

## 1. Uploading `chrysalis-router` into Gemini Spark

1. In Gemini Spark, open **Skills** $\to$ click **Upload a skill**.
2. Drag and drop the folder **`Skills/chrysalis-router`** (or select `Skills/chrysalis-router/SKILL.md`).
3. Gemini Spark will automatically populate the skill **Name** (`chrysalis-router`), **Description**, and **Instructions** from `SKILL.md`.

---

## 2. Simplest Copy-Paste Values for Gemini Spark `Schedules`

Because `chrysalis-router` and `Skills/bundle/SKILL.md` keep 100% of the workflow logic inside your local Chrysalis vault, your two scheduled events in Gemini Spark only need single-line triggers:

### A. Gemini Spark Schedule 1: `Chrysalis Morning Check-In`
* **Title**: `Chrysalis Morning Check-In`
* **When to run**: `Weekly` on `S M T W T F S` around `7:00 AM`
* **Instructions**:
```text
chrysalis-router @Mdbase /morning
```

---

### B. Gemini Spark Schedule 2: `Chrysalis Evening Audit & Staging`
* **Title**: `Chrysalis Evening Audit & Staging`
* **When to run**: `Weekly` on `S M T W T F S` around `9:30 PM`
* **Instructions**:
```text
chrysalis-router @Mdbase @Google Drive /evening
```

---

### C. Ad-Hoc User Commands in Gemini Spark Chat
* **Direct Share Ingestion (attach a PDF/image/audio or paste text)**:
  ```text
  chrysalis-router @Mdbase /ingest
  ```
* **On-Demand Google Drive Folder Ingestion**:
  ```text
  chrysalis-router @Mdbase @Google Drive /ingest --drive
  ```
