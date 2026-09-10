# Bazaar Terminal

A locally runnable Hypixel SkyBlock Bazaar collector and trading-style research terminal. Python 3.11+, FastAPI, SQLAlchemy/SQLite, React/TypeScript, Vite, Tailwind, and TradingView Lightweight Charts.

The collector runs independently of the browser. It stores every new upstream snapshot, up to 30 order-book levels per side, normalized metrics, and incremental sampled-price candles. No Hypixel API key is needed.

## Run locally

Use Python 3.11+ and Node.js 20.19+ (Node 22 is supported). Run backend commands **from the repository root**; this determines the `.env` and relative database paths.

```bash
python3 -m venv .venv
.venv/bin/pip install -c backend/requirements.lock -e './backend[dev]'
cp .env.example .env
.venv/bin/alembic -c backend/alembic.ini upgrade head
.venv/bin/bazaar serve
```

In a second terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open [the terminal](http://localhost:5173). The [interactive API docs](http://localhost:8000/docs) describe query parameters. Leave `bazaar serve` running to collect while the UI is closed. The first poll also downloads item names and NPC prices. There is no upstream historical API here: live history begins when collection starts.

For collection without the API listener:

```bash
.venv/bin/bazaar collect
```

Run only **one collector per database**. The combined service uses one Uvicorn worker; do not add `--workers` or run `collect` against the same database concurrently. An API with `COLLECTOR_ENABLED=false` can read a headless collector's database; its UI refreshes over REST every 15 seconds, while snapshot WebSocket pushes require the combined service.

## Demo history

Keep synthetic and live data in separate databases. The seed command requires an empty, migrated database and produces reproducible synthetic data for 20 products, every 30 seconds, with full books.

```bash
DATABASE_URL=sqlite:///./data/demo.db .venv/bin/alembic -c backend/alembic.ini upgrade head
DATABASE_URL=sqlite:///./data/demo.db .venv/bin/python backend/scripts/seed.py --hours 6
DATABASE_URL=sqlite:///./data/demo.db COLLECTOR_ENABLED=false .venv/bin/bazaar serve
```

The UI displays **SYNTHETIC DATA**. Reuse the seeded database on subsequent runs; do not reseed it. Use another filename for a fresh seed. `--hours` accepts up to 48. Live collection refuses to append to a synthetic database.

During initial development, the demo UI was started on port 5173 with its API on 8000, and a separate live collector/API on 8001. To view that live API from the same UI:

```bash
# From frontend; restart an already-running Vite server after changing this file.
echo 'VITE_API_URL=http://localhost:8001' > .env.local
npm run dev
```

For a normal fresh run, the API defaults to port 8000 and no frontend environment file is necessary.

## Using the terminal

- Search all products; click a name to open a tab. Stars create a device-local watchlist. Click any sidebar or screener column header to sort.
- Choose 1m, 5m, 15m, 1h, 4h, or 1d candles; switch to a line chart or overlay the instant-sell price. Pan/zoom with the chart's standard mouse and touch controls.
- Toggle SMA(20), EMA(20), Bollinger Bands(20, 2), or estimated-volume VWAP. SMA/EMA use close; VWAP uses typical price and resets at UTC midnight. Insufficient indicator history displays no line.
- Drawing toolbar: horizontal line (one click), trend/rectangle (two clicks), note (one click, then text). Undo and clear remove drawings. Anchors persist by product in browser local storage.
- Select a date range and Apply. Dates in the inputs are local time; chart axes and candle buckets are UTC. Empty dates mean all available history through now. CSV/Parquet links export the applied range.
- Charts show the latest 2,000 candles in the requested range. Use a narrower range or a coarser interval for older history; exports are not capped.
- Book replay selects an actual saved snapshot at or before the chosen time. The order book clearly switches to REPLAY; product stats and the screener remain latest. The scrubber shows up to 10,000 snapshots in the applied range; choose an older range to reach earlier data.
- Both book sides scroll through the retained levels. Bars show cumulative quantities; the depth plot uses actual price coordinates.
- Screener filters accept minimum estimated hourly volume, minimum net margin, and maximum spread. Empty filters impose no restriction.
- 24h change stays blank until an observation exists at or within five minutes before the 24h baseline. Missing book sides, unavailable NPC prices, and zero denominators display `—`.

## Configuration and storage

All backend settings live in `backend/src/bazaar/config.py`, loaded from the root `.env` with environment-variable overrides. See `.env.example` for every setting.

| Setting | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite:///./data/bazaar.db` | SQLAlchemy URL; relative to working directory |
| `POLL_INTERVAL` | `30` | Seconds; minimum 20 |
| `TAX_RATE` | `0.01125` | Decimal fraction, 1.125%; adjust for in-game upgrades |
| `ORDER_BOOK_DEPTH` | `30` | Levels per side, 1–30; upstream exposes at most 30 |
| `METADATA_INTERVAL` | `3600` | Item metadata refresh, seconds; minimum one hour |
| `HOST`, `PORT` | `0.0.0.0`, `8000` | API listen address and port |
| `ALLOWED_ORIGINS` | localhost and 127.0.0.1 on 5173 | Comma-separated UI origins, no trailing slashes |
| `COLLECTOR_ENABLED` | `true` | Enables collection inside `serve` |
| `BACKUP_DIRECTORY` | `backups` | Destination for online SQLite backups |
| `BACKUP_RETENTION_DAYS` | `14` | Prune older timestamped backups after a successful backup |

SQLite uses WAL, foreign keys, and a 30-second busy timeout. The main database, `-wal`, and `-shm` files belong together during operation. Use the backup script rather than copying only the main file while collecting.

Tables:

- `products`: stable product ID, current name/NPC price, metadata timestamp.
- `snapshots`: unique upstream `lastUpdated` in UTC milliseconds, receipt time, tax/depth settings, normalization version, source.
- `product_snapshots`: `(product_id, timestamp)`, normalized prices and all derived metrics; preserves the NPC price used at that time.
- `order_books`: `(product_id, timestamp)`, ordered JSON bid/ask levels, each with price, amount, and number of orders.
- `candles`: `(product_id, price_type, interval, bucket_start)`, sampled OHLC, first/last sample time, sample count, estimated volume.

Snapshot, product rows, books, and candle changes commit atomically. Identical or older timestamps are ignored, including after a restart. Active candle buckets are indexed and fetched once per poll; updates never rebuild candles from the snapshot table. Historical product/time reads use composite primary keys.

History is retained indefinitely. Full books for thousands of products accumulate several GB per day; measure your first day's growth before sizing the VM disk and backup space. The six-hour, 20-product synthetic seed is approximately 65 MB. Lowering depth reduces storage; no automatic data deletion is performed.

Alembic migrations are included. After a schema change:

```bash
.venv/bin/alembic -c backend/alembic.ini revision --autogenerate -m 'Describe change'
.venv/bin/alembic -c backend/alembic.ini upgrade head
```

Postgres uses the same models and collector code: install a compatible driver (for example `psycopg[binary]`), set `DATABASE_URL=postgresql+psycopg://...`, then migrate a new database. Moving existing SQLite records is a separate data migration. Timescale hypertables, compression, and retention policies can be added by migration later. No backtesting or execution engine is included.

## Metric definitions and API terminology

The mapping in `collector/normalize.py` follows the [official Hypixel API example](https://api.hypixel.net/#tag/SkyBlock/paths/~1v2~1skyblock~1bazaar/get):

| Upstream field | Normalized meaning |
| --- | --- |
| `buy_summary` | Resting sell offers (asks), consumed by instant buys |
| `sell_summary` | Resting buy orders (bids), consumed by instant sells |
| `quick_status.buyPrice` | `insta_buy_price` |
| `quick_status.sellPrice` | `insta_sell_price` |
| `sellVolume` / `sellOrders` | Buy-order quantity / count |
| `buyVolume` / `buyOrders` | Sell-offer quantity / count |

Quick prices are weighted averages of the top 2% by volume, not best bid/ask or execution guarantees. We store best bid and best ask separately. Numeric data retains floating-point precision consistent with the upstream weighted prices.

With ask `A`, bid `B`, and tax fraction `t`:

```text
spread                 = A - B
spread_pct             = 100 × (A - B) / A
flip_profit            = A × (1 - t) - B
flip_margin_pct        = 100 × flip_profit / B
estimated_hourly_volume = min(buyMovingWeek, sellMovingWeek) / 168
estimated_hourly_profit = flip_profit × estimated_hourly_volume
npc_ratio              = B / npc_sell_price
imbalance              = sum(top-N buy-order amount) / sum(top-N sell-offer amount)
```

Negative margins are retained. NPC highlight compares NPC proceeds with the **taxed** instant-sell proceeds; the stored ratio is pre-tax. Flip estimates describe buying via a resting buy order and selling via a resting sell offer at the quick-price proxy. They omit queue priority, undercutting, slippage, and fill probability.

The upstream weekly activity includes live outstanding orders. There is no actual trade tape or candle trade volume in these endpoints. Candle volume is a proxy: estimated hourly activity multiplied by elapsed observation time, capped at one poll interval and assigned to the current sample's bucket. The first snapshot has zero estimated volume. No volume is invented across outages; VWAP is labeled a proxy. OHLC represents **observed snapshots**, not every price reached between polls. Missing time buckets remain gaps.

## API

All range timestamps use UTC epoch **milliseconds**, inclusive endpoints. Product IDs should be URL-encoded. REST is read-only.

| Endpoint | Parameters / result |
| --- | --- |
| `GET /api/health` | API/database connectivity |
| `GET /api/status` | Collector state, last sample, source, staleness, tax, poll interval, rate limit |
| `GET /api/products` | Every product in the latest committed snapshot, normalized metrics and 24h change |
| `GET /api/products/{id}/candles` | `price_type=insta_buy_price\|insta_sell_price`, `interval`, `start`, `end`, `limit` (default 2,000; max 10,000). Latest N, returned chronologically |
| `GET /api/products/{id}/history` | `metric`, `start`, `end`, `after`, `limit` (default 5,000; max 20,000). Optional `interval` returns bucket **means**, not OHLC |
| `GET /api/products/{id}/book` | Optional `at`; latest book at or before it, 404 if none exists |
| `GET /api/products/{id}/snapshots` | Product's saved timestamps; `start`, `end`, `limit` (default 10,000; max 50,000) |
| `GET /api/products/{id}/export` | `format=csv\|parquet`, `start`, `end`; all normalized snapshot fields plus tax and source |
| `WS /ws` | Initial latest snapshot, then committed snapshot messages; status heartbeat every 20 seconds when idle |

History pagination: for raw points pass the last returned timestamp as `after`; for interval means advance `start` by the bucket duration. Candle pagination: set `end` to one millisecond before the earliest returned bucket. CSV streams in batches; Parquet writes to a temporary file in bounded batches and deletes it after download. Exports do not include the JSON order books; the book endpoint provides replay.

`RateLimit-*` headers are optional on these public endpoints; absence displays “not supplied,” never zero. Remaining <=5 defers requests until reset. HTTP 429 honors Retry-After/reset; outages use exponential backoff up to about 15 minutes. Cached metadata and previous snapshots remain usable. Slow WebSocket consumers receive the latest pending snapshot rather than blocking ingestion.

## Oracle Cloud Ubuntu deployment

Use an Ubuntu 24.04 VM with a public IP, outbound HTTPS, and enough persistent disk for your intended history. Both ARM64 and AMD64 are compatible with the Python Docker base image. Collection runs in one service; the UI stays on your laptop.

### 1. Install Docker and Compose

SSH to the VM. Docker's [Ubuntu installation guide](https://docs.docker.com/engine/install/ubuntu/) provides the official repository setup. On a fresh Ubuntu VM:

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
```

Add the Docker apt repository using its current Ubuntu codename:

```bash
. /etc/os-release
printf 'deb [arch=%s signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu %s stable\n' "$(dpkg --print-architecture)" "$VERSION_CODENAME" | sudo tee /etc/apt/sources.list.d/docker.list
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker compose version
```

### 2. Copy the project and configure it

Copy or clone this repository into `/opt/bazaar`. From that directory:

```bash
cp .env.example .env
```

Set `ALLOWED_ORIGINS` to the actual laptop UI origin, usually `http://localhost:5173`. Adjust tax, poll interval, depth, and `PORT` if desired. Compose overrides `DATABASE_URL` to `/data/bazaar.db` in the named `bazaar-data` volume. Do not copy the demo database into that volume.

### 3. Open the API port

In Oracle Console, open the instance's VCN/subnet security list (or attached NSG). Add a **stateful ingress TCP** rule with destination port **8000** (or your configured port), source your laptop's public IP `/32`, source ports all. Update the source when your public IP changes. See [Oracle security lists](https://docs.oracle.com/en-us/iaas/Content/Network/Concepts/securitylists.htm).

Also allow that port through the VM firewall. If UFW is active:

```bash
sudo ufw allow 8000/tcp
sudo ufw status
```

Some Oracle Ubuntu images also have an iptables REJECT rule. Inspect the active rules and, if that rule blocks the port, insert the specific accept before it; retain existing SSH and Oracle rules:

```bash
sudo iptables -L INPUT -n --line-numbers
sudo iptables -I INPUT 1 -p tcp --dport 8000 -j ACCEPT
sudo apt-get install -y iptables-persistent
sudo netfilter-persistent save
```

Docker publishes through its own forwarding rules; the Oracle ingress rule remains the reliable outer restriction. The native systemd service uses the host INPUT rules.

### 4. Start and check collection

```bash
cd /opt/bazaar
sudo docker compose up -d --build
sudo docker compose ps
sudo docker compose logs -f --tail=50 bazaar
curl http://127.0.0.1:8000/api/status
```

Look for `Stored ... products at ...`. `docker compose up` automatically applies migrations before serving. Check externally from the laptop with `curl http://YOUR_VM_IP:8000/api/health`. If local health succeeds and external health times out, check both Oracle ingress and the VM firewall.

On the laptop, create `frontend/.env.local`:

```dotenv
VITE_API_URL=http://YOUR_VM_IP:8000
```

Then run `npm ci` and `npm run dev` in `frontend`. Restart Vite after changing its environment. The WebSocket URL is derived automatically from the API URL. If using an HTTPS UI later, serve the API over HTTPS as well.

### 5. Nightly backups

Run one immediately:

```bash
sudo docker compose exec -T bazaar python deploy/backup.py
```

Backups are stored under `/data/backups` in the named volume. Add this line with `sudo crontab -e` for 03:00 VM time nightly:

```cron
0 3 * * * cd /opt/bazaar && /usr/bin/docker compose exec -T bazaar python deploy/backup.py >> /var/log/bazaar-backup.log 2>&1
```

The script uses SQLite's online backup API, checks the result, publishes a timestamped filename, then prunes backups older than 14 days. Backups on the same volume protect against database mistakes, not loss of the VM volume; copy desired backups elsewhere.

To retrieve one: `sudo docker compose cp bazaar:/data/backups/FILENAME.db ./FILENAME.db`. To restore, stop collection, point a service at a copy of the backup in a fresh directory/volume (without stale WAL/SHM files), migrate it, and restart. Avoid `docker compose down -v` unless you intend to remove the database volume.

### Native systemd alternative

On Ubuntu 24.04, install Python and place the repository at `/opt/bazaar` owned by the `ubuntu` service user:

```bash
sudo apt-get install -y python3-venv
sudo chown -R ubuntu:ubuntu /opt/bazaar
cd /opt/bazaar
python3 -m venv .venv
.venv/bin/pip install -c backend/requirements.lock ./backend
cp .env.example .env
sudo cp deploy/bazaar.service deploy/bazaar-backup.service deploy/bazaar-backup.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now bazaar.service bazaar-backup.timer
sudo journalctl -u bazaar -f
systemctl list-timers bazaar-backup.timer
```

Edit the unit paths/user if your checkout differs. The service applies migrations on startup. The nightly timer catches up after downtime. For a manual native backup: `.venv/bin/python deploy/backup.py`.

## Verification

```bash
.venv/bin/pytest backend/tests -q
.venv/bin/ruff check backend deploy
cd frontend
npm test
npm run build
```

Tests cover price-side mapping, fees/margins, missing sides, candle boundaries and ordering, deduplication, transaction rollback, outage volume behavior, rate-limit backoff, history/book reads, exports, initial WebSocket delivery, backup integrity/retention, and pure indicators. Production frontend dependencies are locked by `package-lock.json`; Python constraints are recorded in `backend/requirements.lock`.

The terminal uses [TradingView Lightweight Charts](https://tradingview.github.io/lightweight-charts/) with its built-in attribution. Docker/Oracle deployment files are provided; running them on a VM requires that VM's access and was not performed as part of local setup.
