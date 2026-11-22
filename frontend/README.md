# HybridSign frontend

The same React frontend is used in the Windows desktop app and the browser
preview. The desktop app uses pywebview and the WebView2 Runtime to display
the built assets. Its Python bridge provides local vault, signing and
verification operations. A regular browser uses demo data and example results.

## Run locally

Use Node.js 22.12 or later in the 22 series, or Node.js 24 or later.
Run these commands in `frontend`.

```powershell
npm ci
npm run dev
```

Open `http://127.0.0.1:5173` for the browser preview. It offers simulated
workflows and labeled JSON summaries. To run the Windows app, build the
frontend and launch it from the repository root as described in the
[desktop setup guide](../README.md#development-and-research).

```powershell
npm run build
```

## Screens

| Screen | Windows desktop | Browser preview |
| --- | --- | --- |
| Dashboard | Shows available PDF tools and local vault status. | Shows demo activity and example workflows. |
| Sign Document | Selects an unsigned PDF, signs with an unlocked vault and saves a verified result through a Windows dialog. | Shows signing steps and exports a preview summary. |
| Verify Signature | Checks the complete signature pair with selected public keys. | Shows labeled example results for the two layers. |
| Key Vault | Creates, unlocks and locks encrypted local vaults. | Uses demo vault cards and example IDs. |
| Settings | Offers light, dark and system themes, reduced motion and version information. | Offers the same preferences. Reloading resets demo data and preferences. |

## Desktop integration

The app presents the capabilities confirmed by the desktop bridge. If a build
supports only some operations, the interface labels the others as unavailable.
File and password selection use Windows dialogs. The frontend receives file
names, sizes, opaque references and public vault details through the bridge.

A signing request is tracked by its operation ID. The **Check signing status**
action checks that request. An unconfirmed response can coexist with a saved
PDF, so users should inspect the selected location before attempting another
signature. After queueing, signing blocks actions that conflict with the
active operation. [Signing integration](../docs/phase4b3a-real-signing-regression.md)

Stand-alone PDF verification uses public keys and reports an overall result
for the complete pair. An unauthenticated vault header can supply the public
keys. Confirm their origin through a trusted source. Selecting keys from an unlocked
vault confirms local vault access at the time of selection. These keys can
still be used to verify after locking. [Verification and trust](../docs/phase4b3b-real-verification-regression.md)

Development records cover the [original UI](../docs/phase4a-ui-regression.md),
[responsive layout](../docs/phase4a1-ux-regression.md),
[bridge](../docs/phase4b1-native-bridge-regression.md) and
[vault](../docs/phase4b2a-real-vault-regression.md). Exact dependencies are
recorded in [package.json](package.json) and [package-lock.json](package-lock.json).

## Validate changes

```powershell
npm run typecheck
npm run build
npm run test:e2e
```

Playwright serves the production frontend and uses the installed Microsoft Edge.
The suite checks navigation, file selection, native response handling, demo
states, keyboard access, axe rules and layouts at several viewport widths.
Native Windows dialog tests run separately in pytest. Automated access checks
cover the tested screens and rules. A physical screen-reader and DPI review
still needs a person on the target computer.

Some Playwright tests write screenshots under `qa/`. Run them in an isolated
copy if you are preserving recorded release evidence. The approved package
captures and the native test scope are recorded in the
[release review](../docs/phase4c3-final-release-review.md).
