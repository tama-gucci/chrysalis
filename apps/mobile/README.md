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

Direct AI adapters return unavailable. The optional gateway URL/token can be supplied through process environment during desktop development. Android debug builds can receive the gateway URL through `--dart-define`; credentials are not embedded in builds. The local mailbox queues intent only; there is no delivery or execution guarantee. Watch UI, QR pairing, and full settings/onboarding remain planned.

## Development

```powershell
flutter pub get
flutter test
flutter analyze
flutter build apk --debug
```

Keep generated build outputs, local SDK configuration, and credentials out of Git. A prior debug APK does not automatically incorporate later source edits; rebuild before installation. Native-device tests are required for sharesheet permissions, calendar work, and Health Connect.

## Test the gateway over USB

Start a development gateway on the computer at `127.0.0.1:8765`, with no authentication token and an explicitly unavailable agent backend for this connection test. This allows a real request and error response without executing an agent or touching a personal vault. Do not point it at your daily-use agent.

With USB debugging authorized, run from this mobile directory (the Android platform-tools directory must be on the terminal's PATH):

```powershell
adb reverse tcp:8765 tcp:8765
flutter run --debug --dart-define=CHRYSALIS_GATEWAY_URL=http://127.0.0.1:8765
```

To create an APK for later installation instead, use `flutter build apk --debug --dart-define=CHRYSALIS_GATEWAY_URL=http://127.0.0.1:8765`. The URL is selected at build time, so changing it requires rebuilding. Desktop builds without the define retain the existing process-environment setting.

The app should show **Ambient Gateway**. Tap that status chip, then **/doctor**; the unavailable test backend should return an explicit error. The status chip indicates the transport connection, not successful task execution or synchronization. Task capture still saves only to the phone's local vault.

The loopback HTTP exception is declared only in debug Android resources for `127.0.0.1` and `localhost`; release manifests are unchanged. Use HTTPS for non-USB deployments. This is a USB development connection, not production pairing. Disconnect it with `adb reverse --remove tcp:8765`. Reconnect the reverse mapping after unplugging the device if needed.
