# VSChecker privacy note

*Last updated: November 17, 2026*

VSChecker does not collect analytics, does not show ads and does not sell or share anything about you. This page lists everything the app stores and everything it sends, and where.

## Stored on your device

| What | Why | How it is kept |
|---|---|---|
| Your Riot login cookie (`ssid` and related cookies) | To read your shop and inventory without asking you to log in every time | **Encrypted.** Windows: Windows data protection, readable only by your Windows account. Android: a key in Android's key store that never leaves the phone. |
| Your Discord webhook link (if you link one) | To send wishlist alerts | **Encrypted**, the same way as the login |
| Your wishlist sync pass | To prove to the sync server which wishlist is yours | **Encrypted**, the same way as the login |
| Your wishlist, settings and a copy of your current shop | So the app opens fast and works offline | Normal app files |
| Skin pictures and names from valorant-api.com | So the app opens fast | Normal app files, refreshed daily |

Logging out removes your login and sync pass from the device. Uninstalling the app removes everything it stored there.

## Sent from your device

**To Riot Games:** your login cookie and login tokens, to read your shop, owned items, loadout, favorites and player name, and to make the loadout and favorite changes you choose. Riot's own [privacy notice](https://www.riotgames.com/en/privacy-notice) applies to that.

**To valorant-api.com:** requests for public skin data like names, pictures and videos. No account information is sent.

**To Discord**, only if you link a webhook: the wishlist messages (skin name, price, picture, rarity and when it leaves your shop) and your Discord user ID if you entered one to be mentioned.

**To the VSChecker sync server**, which keeps your wishlist the same on all your devices:

- **When you log in to sync:** your current Riot login token is sent once, so the server can ask Riot which account it belongs to. The server does not store the token.
- **The server stores:**
  - an **anonymous code** made from your Riot account ID with a secret key. It cannot be turned back into your account ID, your name or your Riot ID.
  - your **wishlist**: the IDs of the items you hearted, what kind of item each is, and when you hearted or unhearted it. Removed items are forgotten after 90 days.
  - a **request counter** per anonymous code, to stop overuse. Counters are deleted after a few hours.
- **The server never stores:** your name, your Riot ID (name#tag), your email, your login cookie or tokens, your shop or your inventory.

The sync server runs on Cloudflare Workers. Cloudflare may keep standard technical logs of requests (for example IP address and time) under [Cloudflare's privacy policy](https://www.cloudflare.com/privacypolicy/).

## Deleting your synced wishlist

In the app, go to **Settings → Wishlist sync → Delete my synced wishlist** and click it twice. This deletes your wishlist from the sync server and switches syncing off on that device. Your wishlist stays saved on the device itself.

If you use VSChecker on more than one device, do this on each of them. A device that still has syncing on will upload its wishlist again.

Nobody else can do this for you, including the developer. The server only knows anonymous codes, so nobody can tell which wishlist belongs to which account.

## Questions

Open an issue on the [GitHub issues page](../../issues). Never post your `ssid` or anything else from your login there.
