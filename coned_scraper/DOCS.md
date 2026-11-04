# Con Edison - Home Assistant Addon

Con Edison account integration for Home Assistant. Syncs bills, payments, and balance; exposes MQTT sensors; supports payee tracking for shared accounts. Access the panel directly from your Home Assistant sidebar.

## Installation

1. Add this repository to your Home Assistant add-on store (if using a custom repository).
2. Install the "Con Edison" addon.
3. Start the addon.
4. Open the Con Edison panel from the Home Assistant sidebar.

## Configuration

### Option: `log_level`

Controls the verbosity of addon logs. Default: `info`

- `trace` - Most verbose
- `debug` - Detailed debug information
- `info` - Normal operation (recommended)
- `warning` - Warnings only
- `error` - Errors only
- `fatal` - Critical failures only

### Option: `prisma_studio`

Runs Prisma Studio, a database browser, on port 5555. Default: `false`.

Prisma Studio has **no password**: anyone who can reach the port can read and change the database, including your saved ConEd login. To use it:

1. Turn on `prisma_studio` in the add-on **Configuration** tab.
2. Under **Network**, enter a host port for `5555/tcp` (it's empty by default, so nothing is exposed).
3. Restart the add-on and open `http://<your-HA-address>:<port>`.
4. When you're done, turn the option off and clear the port again.

## First-Time Setup

1. Open the Con Edison panel from the sidebar.
2. Go to **Settings** and enter your Con Edison credentials:
   - ConEd username
   - ConEd password
   - TOTP secret (from Google Authenticator)
3. (Optional) Configure MQTT for Home Assistant integration.
4. Enable the automated scraping schedule if desired.

## Data Persistence

All addon data (credentials, MQTT config, schedule, database) is stored in the addon configuration directory and persists across restarts.

## Multiple Con Edison accounts

If your coned.com login has several service accounts (for example two gas accounts at different units), the addon tracks all of them. Nothing extra to configure: use the same credentials.

- **Discovery:** each scrape reads the "My Service Accounts" list on coned.com and scrapes every account in it.
- **Your existing data:** the first time several accounts show up, the addon compares your stored bills with each account's bill history and keeps them with the account they match.
- **Panel:** pick an account from the **Account** menu in the header. ✏️ renames it. Names default to the service address.
- **Home Assistant:** the ConEd Connect integration creates one device per account. The original account keeps its `sensor.coned_connect_*` entities. Other accounts get entities named after the account, for example `sensor.coned_connect_unit_2_account_balance`. Reload the integration after a new account first appears (it is listed after the first scrape that finds it).
- **Shared settings:** credentials, payees, notification and TTS settings apply to every account. Notifications and TTS name the account they are about.
- **Usage (Opower):** each account uses its own meter. Gas meters usually report daily, in therms or CCF. Some panel charts still say kWh.
- **Wipe data:** wiping bills and payments in Settings only clears the account selected in the header.
- **API:** `GET /api/accounts` lists the account keys. Prefix any endpoint with `/api/a/<key>/` to read that account, for example `/api/a/<key>/ledger`. Requests without a key use the primary account.

### Moving from the original addon

This addon has a different slug from the original, so it has its own data folder.

1. Make a Home Assistant backup.
2. Stop the original **Con Edison** addon. Don't start both at once: they would both scrape and send duplicate notifications.
3. Start this addon. On first start it copies the original's database, credentials and settings, and installs its own copy of the ConEd Connect integration.
4. Restart Home Assistant. The integration then switches to this addon by itself and keeps your existing sensors. A reload of the integration alone is not enough.
5. Run a scrape. The log lists the accounts it found, which one your existing data was matched to, and which Opower meter each account uses.
6. Once everything looks right, uninstall the original addon.

If the original was still running at first start, the log says the import was skipped. Stop both addons, delete `postgres` in this addon's config folder (`/addon_configs/<slug>/`), then start this addon again.

## TTS Alerts

Configure TTS (text-to-speech) in **Settings → TTS Alerts**. Messages use format `(prefix), (message)` like [Home-Energy](https://github.com/zodyking/Home-Energy).

**Direct HA API:** When running as a Home Assistant addon, TTS is sent directly via the HA REST API — no automations needed. The addon uses `homeassistant_api` to call `tts.speak` (device target when available, with `cache: true` and `media_player_entity_id`) and `media_player.volume_set`.

**Media player idle:** When "Wait for media player idle" is enabled, the addon checks the media player state and waits (up to 5 minutes) until it is `idle` before playing, so TTS doesn’t interrupt music or other playback.

**MQTT fallback:** When running outside the addon (e.g. dev), TTS requests are published to `coned/tts/request` and require an HA automation to handle them.

## MQTT Integration with Home Assistant

Configure MQTT in the Settings tab. The addon publishes to MQTT topics for `account_balance`, `latest_bill`, `last_payment`, `previous_bill`, `tts/request`, and payee summaries.

**MQTT Discovery (enabled by default):** When enabled, the addon publishes Home Assistant MQTT discovery configs so sensors are **auto-registered**—no manual `configuration.yaml` needed. After configuring MQTT and running a scrape, sensors such as `sensor.coned_latest_bill`, `sensor.coned_account_balance`, `sensor.coned_last_payment`, etc. appear automatically under Settings → Devices & services → MQTT. You can disable discovery in MQTT Settings if you prefer manual YAML configuration.

## Payment Claim Notifications (Notification-Based Assignment)

When new unverified payments are detected, the addon sends "Did you make this $X payment on [date]?" notifications to each payee with notifications enabled. Payees tap **Yes** or **No** to claim or deny the payment.

**ConEd Connect integration (recommended):** Add the ConEd Connect integration (Settings → Devices & services → Add integration → ConEd Connect) and configure the addon URL. Yes/No taps are then handled automatically—no manual automation or YAML changes needed.

**Manual automation (fallback):** If you use only the addon panel without the integration, add a `rest_command` and automation so notification actions reach the addon. Replace `core_coned` with your addon slug (Settings → Add-ons → Con Edison).

```yaml
rest_command:
  coned_payment_notification_action:
    method: POST
    url: "http://homeassistant.local:8123/api/coned/ingress/core_coned/api/payments/claim-action"
    content_type: "application/json"
    payload_template: '{"action": "{{ action }}"}'
```

Replace `core_coned` with your add-on slug and adjust host/port or ingress path if your HA uses a different URL. The addon accepts the raw `action` string for both payment **claim** responses (`CONED_CLAIM_YES_...` / `CONED_CLAIM_NO_...`) and **petition** responses (`CONED_PETITION_YES_...` / `CONED_PETITION_NO_...`).

```yaml
alias: ConEd Payment & Petition - Record notification actions
description: Forward claim and petition Yes/No taps to the Con Edison addon
trigger:
  - platform: event
    event_type: mobile_app_notification_action
  - platform: event
    event_type: ios.notification_action
condition:
  - condition: template
    value_template: >
      {{ trigger.event.data.action is defined
         and (trigger.event.data.action.startswith('CONED_CLAIM_')
              or trigger.event.data.action.startswith('CONED_PETITION_')) }}
action:
  - service: rest_command.coned_payment_notification_action
    data:
      action: "{{ trigger.event.data.action }}"
```

**Resend after all No:** If all payees say No (e.g. accidental taps), the addon resends the claim request after a configurable delay (default 24 hours). Configure `claim_resend_delay_hours` in App Settings.

## Ingress

This addon uses Home Assistant Ingress. The web interface is accessed through the sidebar—no additional ports or network configuration required.

## Support

- [GitHub Repository](https://github.com/zodyking/HA-ConEd)
- [Home Assistant Community Forum](https://community.home-assistant.io)
