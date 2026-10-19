# Assistant footprint and usage

Measured on Linux ARM64 using pinned production installations with lifecycle scripts disabled.
These are physical installed footprints for this platform, not a guarantee for every OS/npm layout.

| Scope | Measured size |
| --- | --- |
| Prior production dependencies | 119,068 KiB, about 116 MiB |
| Assistant production dependencies | 127,148 KiB, about 124 MiB |
| Additional mandatory dependencies | 8,080 KiB, about 7.9 MiB |
| Optional browser pack fixture, including install cache | 108,768 KiB, about 106 MiB |
| Existing reused full Chromium cache | 406,764 KiB, about 397 MiB |
| Earlier integration npm archive unpacked | About 8.8 MiB, mostly existing vault/plugin resources |

Browser/media packs are optional. Browser setup uses full Chromium with `--no-shell` to avoid an
additional headless-shell download. The browser fixture size includes its private install cache;
account profiles and future artifacts add variable storage. Development dependencies and repeated
test installations are temporary external verification data, not the runtime requirement.

Actual Pi 1.1 active-tool schemas were serialized as name, description and JSON parameters:

| Default profile | Active tools | Schema characters | Characters / 4 estimate |
| --- | --- | --- | --- |
| Prior core without companions | 3 | 3,975 | 994 |
| Assistant core, optional features off | 7 | 5,692 | 1,423 |

The default increase is 1,717 characters, approximately 429 tokens under that simple estimator.
It buys native questions, quizzes, lesson workflow and local visuals. These counts exclude prompts,
history, results, SDK/provider serialization and optional companion tools; they are not billed
token measurements. Disabled browser, memory and specialists add no default model tool schemas.
The deferred Gemini tool is not advertised before native acceptance.

A real configured-model specialist test through the fail-closed programmatic child host completed
four nonzero provider turns to write and read one synthetic file and report completion. Its session
reported 4,151 input tokens, 119 output tokens, zero cache-read tokens and 4,270 total tokens. This
one narrow workflow is not a universal overhead estimate. Search/extraction and diagrams add no
summary model; memory adds selected-model work only when enabled. Work reservations and reported
usage expose overhead without inventing unknown usage.

A separate bounded teaching/onboarding conversation produced a concrete concept/example, an
optional check, two unadopted project candidates, an open course/project choice and one ready
question. The synthetic vault's hashes remained unchanged. This establishes the observed scenario,
not comparative learning outcomes or reliability across every model. Gemini/account/video results
were deliberately excluded from both checks.

## Modular Pi ownership verification

The refactor removes two package-initiated shared built-in initializations and replaces the private
provider-adapter loader/declarations with a generic parent-runtime stream route. Production
dependency declarations are unchanged; Pi's development SDK is pinned to 1.2.0. The supported peer
minimum is now Pi 1.2.0 and Node 22.19.0, matching Pi's declared runtime requirement.

A production archive on Pi 1.2.0/Node 24.20.0 exposed seven initial chrysalis/core declarations.
The same archive with all original pi-quotas 0.5.0 and pi-antigravity 0.10.0 resources exposed nine,
including pi-antigravity's two independent tools. Both package orders passed without exclusions.
Serialized active tool names/descriptions/schemas were 6,373 characters alone and 7,893 combined
before a prompt. These are fixture definition sizes, not provider-transformed request sizes or billed
tokens. A system prompt/provider request was not generated, so its overhead and live usage remain
unmeasured. Pi's default codemode model helpers remain enabled.

No new provider/add-on wrapper or add-on dependency was added. Existing isolated execution,
Blackhole and specialist-engine controls remain for the requested memory/role/workspace boundaries.
Normal archive installation needs no custom launcher, build or built-in suppression settings.
The external development resolver remains optional for dependency-free source checkouts.
