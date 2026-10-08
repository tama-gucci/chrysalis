# Package lifecycle
Use a reviewed pinned local release as one core artifact. The operator installs isolated Python
requirements, previews `run.py package install --target <absolute-package-root>` and applies the
reviewed preview with --apply. The allowlist excludes runtime/private/development data. Configure a
dedicated Pi life profile with the package. Supply explicit vault/state/Python bindings.
Setup does not switch live host auth or activate cron.
`run.py init --vault <fresh-parent>/chrysalis --timezone <IANA-zone>` initializes an empty selected
vault, preserving the exact lowercase directory entry. It refuses nonempty/source/package targets.
Choose a new explicit location; never depend on a case-only rename of a deprecated folder.
Installation keeps an owned file/hash manifest and external before-images. Update checks every owned
file: a locally edited default causes a conflict and zero update writes, with no force option. Move
personal learned variants to a separately configured host skill root with a distinct name; reviewed
defaults and learned files have separate ownership. Explicitly merge a collision before retrying.
Removal deletes only unchanged owned defaults, preserving unowned settings and learned procedures.
Rollback restores the previous verified payload only when deployed hashes still match. Do not bypass
schema/package compatibility or discard local edits. Run doctor and representative workflows after
installation/update, and verify host discovery. Publishing and personal adoption are separate actions.
Optional memory packages keep lessons/session references and export all durable content through their
supported APIs. A capped Markdown export is not a complete migration. Native dependency compatibility
and full export/import need evidence before promising optional package equivalence.
