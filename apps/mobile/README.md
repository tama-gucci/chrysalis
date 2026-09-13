# Chrysalis mobile prototype

Flutter interface with native Android capture and Health Connect bridges. See [capability status](../../STATUS.md) before relying on integrations.

## Working code

- Android ACTION_SEND / ACTION_SEND_MULTIPLE receivers cache incoming content safely before URI access expires.
- Dart staging copies text, screenshots, audio, and PDFs into the local `chrysalis/Inbox/`.
- Drift SQLite caches tasks; a mutation journal writes task changes to local Markdown.
- Task capture, sprint cards, a schedule preview, and morning calibration widgets are present.
- Health Connect is queried only when supported and already authorized. Missing data leaves manual calibration available.

Startup does not seed demonstration tasks or fabricate biometrics. Android uses persistent application documents. Desktop development can select an absolute `CHRYSALIS_VAULT_PATH`; no machine-specific drive paths are guessed.

## Integration limits

The app uses LocalVaultStorageProvider. The Google Drive provider is not wired to authenticated startup. A saved phone file is not automatically synchronized to desktop.

The calendar coordinator and Dart platform interface exist, but there is no native Android calendar handler. The schedule view is a preview, not confirmation that events were written.

Direct AI adapters return unavailable. The optional gateway URL/token can be supplied through process environment during desktop development. The local mailbox queues intent only; there is no delivery or execution guarantee. Watch UI, QR pairing, and full settings/onboarding remain planned.

## Development

```powershell
flutter pub get
flutter test
flutter analyze
flutter build apk --debug
```

Keep generated build outputs, local SDK configuration, and credentials out of Git. A prior debug APK does not automatically incorporate later source edits; rebuild before installation. Native-device tests are required for sharesheet permissions, calendar work, and Health Connect.
