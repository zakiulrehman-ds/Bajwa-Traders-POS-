# Bajwa Traders — Shop Management & POS

A Django + HTMX + Alpine.js shop-management starter tailored for a Pakistani cold-drinks agency and general retail shop. It includes a product catalogue, POS checkout, stock movement tracking, supplier purchases, Urdu receipt page with QR bill reference, sales history, analytics charts, settings, and a Windows desktop launcher.

## Stack
- Django 5.x + SQLite + WhiteNoise static-file serving
- Django templates + HTMX + Alpine.js
- Tailwind CDN starter styling (replace with a compiled local Tailwind build for fully offline use)
- Chart.js charts
- Waitress on Windows
- Noto Nastaliq Urdu font target for receipts

## Windows quick start
1. Install Python 3.12 or newer and Microsoft Edge or Chrome.
2. Extract the complete ZIP into a permanent folder, e.g. `C:\BajwaTraders`.
3. Double-click `scripts\setup_windows.bat`. Create your owner login when prompted.
4. Double-click `scripts\start_bajwa_traders.bat` whenever you want to open the desktop app.
5. Open the Django admin at `http://127.0.0.1:8000/django-admin/` if you need the built-in admin interface.

The setup script creates the database tables and owner account. The first user created by `createsuperuser` is the owner/admin.

## Mobile access on shop Wi-Fi
- Connect the phone and shop PC to the same Wi-Fi router.
- Find the PC's local IPv4 address with `ipconfig`.
- Allow inbound TCP port 8000 in Windows Firewall (private network only).
- On the phone open `http://PC-IP:8000`, sign in, then use the browser's Add to Home Screen option.
- This is a local-network PWA-style web app, not a Play Store native app. HTTPS is required for full PWA install/offline service-worker behavior on most mobile browsers.

## First configuration
1. Sign in and open **Categories**. Add main categories such as Cold Drinks, Water & Juices, Biscuits, Snacks, Grocery, and Other.
2. Add subcategories by selecting a parent category.
3. Add products with company, product photo, Urdu receipt name, SKU/barcode, unit, buy price, sell price, opening stock, and reorder level.
4. Add suppliers, then record every incoming delivery under **Purchases**. Purchases increase stock and create stock movement records.
5. Use **POS / New Bill** to tap products into the cart, enter discount and cash received, then press F12 or click Save & Print.
6. Configure the shop name, Urdu shop name, address, phone, footer and paper width in Settings.

## Urdu thermal printing
The receipt is rendered as HTML with right-to-left layout and the Urdu font family `Noto Nastaliq Urdu`. For reliable local/offline printing:
- Obtain the Noto Nastaliq Urdu TTF font file and place it in `core/static/core/fonts/NotoNastaliqUrdu-Regular.ttf`.
- Add a local `@font-face` rule in `core/static/core/app.css` pointing to that file (the stylesheet currently has a Google Fonts development import as a visual fallback).
- Install the thermal printer's Windows driver and set the printer as the Windows default.
- Set paper width (58mm or 80mm) in shop settings. The receipt stylesheet currently defaults to 80mm; adjust the print `@page` width for a 58mm printer.
- Test alignment, paper feed, Urdu glyph shaping and QR readability on the actual printer before using it for live transactions.

**Printing limitation:** F12 saves the bill and opens its receipt page. The user clicks Print in the receipt page unless Edge/Chrome kiosk printing is launched with the correct default printer configuration. Silent printing depends on the browser, printer driver and Windows setup; it cannot be guaranteed across every machine by a web app alone.

## Data safety
- SQLite database: `db.sqlite3`.
- Uploaded product photos: `media/products/`.
- Run `scripts/backup_database.bat` for a timestamped database copy in `backups/`.
- For a complete backup, copy both `db.sqlite3` and `media/` while the server is stopped.
- Never delete or edit the database file while the server is running.

## Current included functionality
- Login-protected application pages; Django admin for superusers.
- Categories and subcategories, product images, Urdu product names, companies, prices, units, stock and reorder levels.
- POS cart with quantity adjustment, discount, received cash, change calculation and stock validation.
- Transactional checkout: saves a sale and its line-item cost snapshot, decrements stock, and writes stock movement records.
- Purchases from suppliers increase inventory and update the latest purchase cost. Manual inventory adjustments are recorded with a reason and movement history.
- Sales history and printable Urdu RTL receipt with QR code encoding the bill number.
- Dashboard KPI cards, daily sales line chart, category doughnut chart, top products, low-stock alerts and recent bills.
- Date-filtered sales report and inventory snapshot.

## Important next production steps
This is a runnable first release / MVP foundation, not a fully audited commercial POS. Before real shop use, test it with sample products and bills, set a strong secret key, set `DEBUG=False`, restrict `ALLOWED_HOSTS`, configure a firewall rule, vendor Tailwind/HTMX/Alpine/Chart.js locally for offline use, add the bundled Urdu font, and test thermal printing. The initial release does not yet implement customer udhaar ledger, returns/refunds workflow, multi-counter concurrency, barcode scanner keyboard tuning, CSV import/export, automatic scheduled backup, expense tracking, or fully silent cross-browser printing. These are planned extensions.

## Development commands
```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
python manage.py makemigrations core
python manage.py migrate --run-syncdb
python manage.py collectstatic --noinput
python manage.py createsuperuser
python manage.py runserver
```

## 80mm thermal printer
See [PRINTER_SETUP_80MM.md](PRINTER_SETUP_80MM.md) for Windows driver setup, receipt sizing, QR scanning, Urdu font placement and kiosk-printing instructions. The project defaults to 80mm paper.
