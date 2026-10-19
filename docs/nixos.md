# NixOS integration

Chrysalis remains an ordinary Pi package. Its optional NixOS module adds a terminal-first system, persistent USB installer, short configuration rules and a receipt-derived Markdown ledger. The agent edits ordinary Nix files; Chrysalis does not introduce a configuration language or replace Pi's host.

## Reused components

| Responsibility | Upstream implementation | Chrysalis addition |
| --- | --- | --- |
| Writable EFI USB image and growth | [NixOS disk-image module](https://github.com/NixOS/nixpkgs/blob/fe13242281a67641c0102cdb1087f0ebe586c7df/nixos/modules/virtualisation/disk-image.nix) | Installer profile |
| Terminal session | Cage, Ghostty, tmux and [Pi](https://github.com/earendil-works/pi) | Normal package loading and startup |
| User tools | [Home Manager Pi module](https://github.com/nix-community/home-manager/blob/640725978b99076e18e069f6e7d2959124584f8f/modules/programs/pi-coding-agent.nix) | Thin CLI extension flag; mutable settings stay unmanaged |
| Disk setup and installation | [disko-install](https://github.com/nix-community/disko) | Exact native disk scope and recovery receipts |
| Hardware behavior | NixOS Facter and [nixos-hardware](https://github.com/NixOS/nixos-hardware) | Discover facts; select applicable upstream modules |
| Build, diff, activation and generations | [nix-agent 0.13.0](https://github.com/JEFF7712/nix-agent/tree/dc12e28b1917d677bf5bf9f6ea607001b0591e1c) | Native outcome scope and observed-result checks |
| Configuration organization | flake-parts and import-tree | A minimal seed and the user's named features |

Pi owns MCP, codemode, authentication and the conversation. Native administration, durable receipts and the narrow ledger projection are the integration-specific code. The NixOS option namespace is programs.chrysalis-pi because programs.chrysalis already names another upstream application.

## Build and consume

The flake exports nixosModules.default, nixosModules.installer, homeManagerModules.default, packages.x86_64-linux.installer and package outputs for x86_64-linux/aarch64-linux. Inputs follow nixos-unstable through a committed lockfile; Pi is pinned to 1.2.0.

Run these on an x86_64 Linux builder:

~~~sh
nix flake check --no-build --all-systems
nix build .#checks.x86_64-linux.system --out-link /tmp/chrysalis-module-test -L
nix build .#installer --out-link /tmp/chrysalis-installer -L
python3 nix/tests/raw-boot.py --image /tmp/chrysalis-installer --work /tmp/chrysalis-acceptance-new
~~~

The acceptance directory must be new and empty. QEMU, OVMF and Python pexpect are CI dependencies; runtime Chrysalis needs no Python. The image is a writable raw EFI image with upstream first-boot partition/filesystem growth. Only an image that passes acceptance is packaged as a compressed image with SHA-256, input lock and source-commit record.

Import nixosModules.default into a personal flake, enable programs.chrysalis-pi and select an existing normal user, exact host attribute and writable configuration directory. Preserve each installed host's stateVersion. The installer profile alone has live passwordless administration. Normal installed sudo still authenticates; the upstream backend supplies its bounded administrative rules.

Home Manager loads the normal Pi package with --extension and leaves mutable auth/model settings outside the store. A standalone Home Manager consumer can enable programs.chrysalis-pi without enabling OS administration. Existing independent packages and Pi built-ins remain available.

## User flow

~~~mermaid
flowchart TD
    USB[Flash persistent USB image] --> UI[Cage / Ghostty / tmux / ordinary Pi]
    UI --> Network[Connect network and sign in through native controls]
    Network --> Scope[Review OS outcome, exact disk and account preferences]
    Scope --> Config[Agent discovers hardware and edits ordinary Nix]
    Config --> Build[Upstream build and fresh diff]
    Build --> Install[disko-install builds before formatting approved disk]
    Install --> Handoff[Copy editable config and private checkpoint]
    Handoff --> Boot[Boot installed encrypted system]
    Boot --> Vault[Existing native vault setup and approval]
    Vault --> Ledger[Project machine receipt events into system ledger]
~~~

Use /chrysalis system for an outcome, /chrysalis system status for readiness, and /chrysalis system reconcile after interruption or first boot. The model can request the same native setup through chrysalis_system; it cannot approve itself. Technical facts come from tools. Account preferences, target selection and secrets come from the operator.

The first profile supports a dedicated x86_64 UEFI disk with encrypted Btrfs. Shared-disk resizing, generic hibernation and firmware key enrollment are outside this profile. The generic image is unsigned; existing personal Lanzaboote settings do not make it trusted by firmware that requires signed boot media.

## Authority and persistence

One native approval covers the requested OS outcome, exact configuration/host/backend, observed disk or recovery generation, and generated ledger entries. It remains usable for verification until closed or superseded. Edits invalidate prior build evidence. Another disk, expanded destruction or changed backend requires native review.

The configuration, vault and private state must be disjoint. Native onboarding rejects a vault inside the configuration tree before staging it; OS approval and later tool use recheck this boundary before a flake can snapshot personal data.

Private write-ahead receipts distinguish approval, build, installation, activation, uncertainty and verification. The fixed ledger is System/System-Ledger.md in the native-selected initialized vault. Projection accepts neither arbitrary paths nor model Markdown. Event identifiers prevent duplicate projection, writer locks protect receipt binding, and raw revisions preserve concurrent ledger edits. Other personal records retain their existing exact approvals.

~~~mermaid
flowchart LR
    Approved[Native approved outcome] --> Editing[Edit ordinary configuration]
    Editing --> Diff[Completed fresh diff for unchanged bytes]
    Diff --> Applying[Durable intent before privileged mutation]
    Applying --> Verified[Observe running closure, profile and health]
    Applying --> Uncertain[Interrupted or ambiguous result]
    Verified --> Ledger[Receipt-derived ledger]
    Uncertain --> Ledger
    Uncertain --> Recovery[Inspect and choose explicit recovery]
~~~

The writable USB retains nonsecret checkpoints and sessions. Live provider credentials and installation secrets stay in runtime storage. Native handoff copies selected Pi auth/settings privately to the installed account; a hash-only transfer journal supports interruption during copying without putting provider-secret contents on the USB. Retry replaces only bytes belonging to its prior copy intent and preserves independent target edits. A completed handoff never recopies over later installed state.

A disconnected privileged operation may outlive its parent. Its durable busy marker blocks later mutation even after closing the outcome. Confirmed completion or a new boot is required before continuing; merely observing the expected closure does not prove the old child exited. Interrupted installation recovery uses disko mount mode and never repeats formatting automatically.

Generation rollback preserves an OS recovery option; it does not restore arbitrary data or service migrations. Installation, activation and boot verification are separate claims. Receipts describe work through the configured integration; they are not a whole-machine audit of unrelated administration. System Bash is trusted host administration, while ordinary workspace tools keep their existing isolation.

## Acceptance and CI bootstrap

Portable tests, Nix evaluation, package builds, image/VM execution and physical hardware acceptance are separate evidence. See STATUS.md for actual results. An authored VM harness is not a passing image.

The image job is manual-only. GitHub requires a workflow using workflow_dispatch to exist on the default branch before it can be dispatched against a feature branch: [manual workflow requirements](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow). The operator requested merging this implementation as a prototype, which also registers the workflow. Once it is on the default branch, dispatch nixos.yml against the exact reviewed candidate ref. The merge itself does not establish image or VM acceptance.

The VM harness checks actual Pi startup, USB shutdown persistence, dedicated-disk installation, interruption before and during handoff, encrypted target boot, vault setup, real nix-agent activation/rollback, failed build behavior, ledger deduplication and an unchanged sentinel disk. It uses native fixture approvals and backend primitives; it does not run a model through every human dialog.

Provider login, the Obsidian GUI return path, physical Surface/NVIDIA behavior and firmware compatibility still need their own acceptance. Test only disposable VM disks until the image gate passes. Generic images and CI artifacts must contain no personal vault, provider account or machine-specific runtime state.
