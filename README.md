<p align="center">
  <img src="docs/logo.png" width="120" alt="VSChecker logo">
</p>

<h1 align="center">VSChecker</h1>

<p align="center">Your Valorant shop, night market and inventory on your PC and your phone, without opening the game.</p>

<img width="2544" height="1364" alt="image" src="https://github.com/user-attachments/assets/3617d530-0955-4d0f-9a4b-8bf8000ac68a" />


## What it does

- **Daily shop:** your four daily offers with prices and rarity, plus a countdown to the next reset.
- **Bundles:** the featured bundles in a rotating banner. Tap one to see every item and its price.
- **Night market and accessory shop:** discounted skins when the night market is on, and the Kingdom Credits shop.
- **Skin preview:** every level and variant, with the in-game preview videos.
- **Inventory:** see what you own and what is equipped. Change skins, levels, variants, gun buddies, sprays, player card and title, and the change shows up in the game.
- **Favorites:** star skins, variants, sprays and cards. They are the same favorites as in the game.
- **Wishlist:** heart the skins you want. When one shows up in your shop or night market, you get told:
  - with a phone notification (Android), even when the app is closed
  - with a Discord message, if you link a Discord webhook
- **Wishlist sync:** your wishlist is the same on every PC and phone you log in on.
- **Make it yours:** background colors, animated or still background, border color and sound volume.

[insert img of the inventory page with the player card and spray wheel here]

[insert img of the skin preview window with levels and variants here]

## Download

Get the newest version from the [Releases page](../../releases).

| Device | File |
|---|---|
| Windows 10 / 11 | `VSChecker-Setup.exe` |
| Android 6 or newer | `VSChecker.apk` |

### Windows

1. Run `VSChecker-Setup.exe`.
2. Windows may show **"Windows protected your PC"**. That is because the app is not signed with a paid certificate. Click **More info**, then **Run anyway**.
3. VSChecker is added to your Start menu and desktop. To remove it later, use **Settings → Apps** like any other program.

### Android

1. Download `VSChecker.apk` on your phone and open it.
2. Allow your browser or file app to **install unknown apps** when Android asks.
3. Play Protect may warn that the app is from an unknown developer. Tap **Install anyway**.

Updates install over the old version and keep your settings.

## Logging in

**On Android:** tap **Log in with Riot** and sign in on Riot's own login page. That's it.

**On Windows**, the app needs your Riot login cookie, called `ssid`. You only do this once:

1. In the app, click **Open the Riot login page** and sign in with **Stay signed in** ticked. A "page not found" page afterwards is normal.
2. Press **F12**, open **Application** (**Storage** in Firefox), then **Cookies** and `https://auth.riotgames.com`.
3. Copy the value of the cookie named `ssid` and paste it into the app.

<img width="1151" height="754" alt="image" src="https://github.com/user-attachments/assets/e6e43011-99b0-4f8a-ad3e-ae1dcf459d4b" />


> [!WARNING]
> Your `ssid` works like a password for your Riot account. Never share it with anyone. VSChecker stores it only locally on your own device, encrypted, and only ever sends it to Riot. It is never uploaded anywhere else, not even to the VSChecker sync server.

If Riot doesn't accept the `ssid`, log out on playvalorant.com, log in again and copy a fresh one. If it still fails, try a different browser. Some Chrome setups don't keep the cookie.

## Wishlist alerts

**Phone notifications (Android):** turn on **Settings → Notifications → Nightly wishlist check**. A few minutes after the shop resets, the app checks your shop and notifies you if a wishlisted skin is in it. If notifications arrive late, set VSChecker's battery usage to **Unrestricted** in your phone's settings.

**Discord:**

1. In your Discord server: **Server Settings → Integrations → Webhooks → New Webhook**, then **Copy Webhook URL**.
2. In VSChecker: **Settings → Discord**, paste the link and click **Save**.
3. Optional: paste your Discord user ID under **Mention me** to get pinged. Turn on Developer Mode in Discord, right-click your name and choose **Copy User ID**.
4. Click **Send test message** to check it works.

<img width="1259" height="317" alt="image" src="https://github.com/user-attachments/assets/a4276672-78b9-45ff-abec-80034d99e65f" />


**Windows:** turn on **Settings → Windows → Open on Windows startup** to have your shop checked every time you start your PC.

## Wishlist sync

Hearts you tap on one device show up on your other devices when you log in with the same Riot account. Nothing to set up.

- Changes are sent 30 seconds after your last tap, or when you close or leave the app.
- Without internet, everything keeps working and the changes are sent later.
- **Settings → Wishlist sync** shows whether you're synced, and has a **Sync now** button.

Your wishlist is stored under an anonymous code, never your name or login. See the [privacy note](PRIVACY.md).

<img width="1150" height="1348" alt="image" src="https://github.com/user-attachments/assets/e3cdf9c4-93e4-4958-afe5-ab067be1c4ba" />


## Is this safe to use?

- VSChecker uses the same unofficial connection to Riot's servers as other shop checker apps. Riot does not officially support it, and it can stop working whenever Riot changes something.
- Viewing your shop is read-only. **Changing your loadout from outside the game is a grey area.** Use it at your own risk.
- Your login stays on your device, encrypted, and is only sent to Riot. See the [privacy note](PRIVACY.md) for everything the app stores and sends.

## Problems?

| Problem | Try this |
|---|---|
| "Your saved Riot login has expired" | Log in again. Riot signs out old logins now and then. |
| The shop doesn't load | Check your internet, then log out and in again. |
| A Discord message never came | Use **Send test message** in Settings. If the webhook was deleted in Discord, link a new one. |
| Android notifications come late | Set the app's battery usage to **Unrestricted**. |
| Sync says "Could not sync" | Your wishlist is still saved on the device. Press **Sync now** later. |

Still stuck? [Open an issue](../../issues) with the error text the app shows. **Never post your `ssid`.**

## Credits

- Skin pictures, videos and names come from [valorant-api.com](https://valorant-api.com).
- Made by Pleiades & Andii / Andemanden (assisted with Claude).

## License

MIT. See [LICENSE](LICENSE).

---

VSChecker isn't endorsed by Riot Games and doesn't reflect the views or opinions of Riot Games or anyone officially involved in producing or managing Riot Games properties. Riot Games, and all associated properties are trademarks or registered trademarks of Riot Games, Inc.
