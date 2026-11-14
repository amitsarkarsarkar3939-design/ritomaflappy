# Flappy Friends desktop game

Both desktop clients are scrollable; scroll down to reach the coin shop. The Java/Swing client uses the same local game service and database.

- Windows game app: double-click `start_app.bat` to open the installable game. In Microsoft Edge, choose **Install game app** or **… > Apps > Install this site as an app**. Keep the launcher window open while playing; it serves the offline-ready game locally.
- Browser game: open `index.html` for a regular browser session; the installable app must be opened through `start_app.bat`.
- The supplied Ritoma and Ricoins pictures are bundled in `assets`. Collect Ricoins to buy and equip wing and trail styles.
- The **Ricoins terminal** is a game-only command console, not a Windows/OS shell. Use `help` for bird/world tuning, mod save/load, and the built-in game-tool catalog. Mods and settings save locally; sign in or create an account to sync them with the local SQLite service. Usernames are 3–24 letters/numbers/underscores, passwords are 10–128 characters, and sign-in sessions last 30 days. Account saves remain in the local database until you remove that database.
- **bix-k0ns0le and bic-V:** open the package console from the game terminal panel, or double-click `start_bix.bat`. It runs locally and accepts only package-manager and workspace commands; it is not an operating-system shell. `bic-V list`, `search`, `show`, `install`, and `uninstall` manage real PyPI packages (`pygame`, `pygame-ce`, `arcade`, `pymunk`, `pillow`, `pytmx`, `numpy`, `sounddevice`, `imageio`, and `pytest`). Python itself and `json`, `time`, `logging`, and `sqlite3` are reported as already available. Packages are installed into an isolated environment under your user profile, not into the game or system Python. The game launcher starts the console service on loopback; the service rejects requests from other web origins.
- Start the web app with `start_app.bat` or `python .\run_app.py`; this starts the web page and the local account/save API together. Keep the launcher open while playing. Opening `index.html` directly does not provide account-save service.
- **Android APK:** the Android WebView project is in `android`. It packages the game for offline play and stores progress on that device; the desktop account and local backend services are not included. Push this project to a GitHub repository, then use **Actions > Android APK > Run workflow** to build and download an APK artifact. To publish a versioned download on the repository's **Releases** page, push a tag such as `v1.0.0`; the workflow builds the APK and attaches it to the release. Players can download `app-debug.apk` from the artifact or release and install it on Android.
- Python: `python .\game.py`
- Java: compile and run from this folder using `javac idk.java` and `java idk`
- Database/content check: `python .\game.py --check`

The first launch creates `flappy-friends.sqlite3`. Game modes, scores, wallet, and the six coin packs are stored in SQLite. Current packs: 10 coins/₹2, 100/₹10, 200/₹20, 350/₹25, 1000/₹100, and 2000/₹90.

## Razorpay checkout

Checkout uses a server-created Razorpay order. Coins are credited only after the backend validates Razorpay's checkout signature and fetches the payment to verify its order, INR amount, and captured status. The game also checks Razorpay for a captured payment if the browser callback was missed. Test keys are recommended first.

Create a Razorpay merchant account and generate **test** keys in its Dashboard. Set them in the same PowerShell window used to start the game:

```powershell
$env:RAZORPAY_KEY_ID = "<your rzp_test_ key ID>"
$env:RAZORPAY_KEY_SECRET = "<your test key secret>"
python .\game.py
```

The Java desktop app reads the same environment variables through its Python local service. Never paste secrets into source files, screenshots, chats, or a distributed app. Do not send the keys here.

Live keys are accepted only after an extra opt-in:

```powershell
$env:RAZORPAY_KEY_ID = "<your rzp_live_ key ID>"
$env:RAZORPAY_KEY_SECRET = "<your live key secret>"
$env:RAZORPAY_LIVE_PAYMENTS = "YES"
python .\game.py
```

Only enable live payments after Razorpay approves the merchant account and you have tested the complete flow with test keys. Razorpay settles to the settlement details configured in your merchant account; the game cannot route funds to a personal UPI ID. This loopback desktop service is intended for use on your own computer, not as the backend for a public app. A public release needs a securely hosted backend, protected credentials, and production webhook/operational monitoring.

The integration follows Razorpay's official [Create an Order](https://razorpay.com/docs/api/orders/create/) and [Standard Checkout integration](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/) guidance.
