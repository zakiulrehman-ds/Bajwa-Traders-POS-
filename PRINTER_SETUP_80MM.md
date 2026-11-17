# Bajwa Traders — 80mm USB Thermal Printer Setup

## Windows printer setup
1. Connect the 80mm USB thermal printer to the shop PC and install its manufacturer/Windows driver.
2. Open **Settings → Bluetooth & devices → Printers & scanners** (Windows 11) or **Settings → Devices → Printers & scanners** (Windows 10).
3. Select the thermal printer and choose **Set as default**.
4. In Printing preferences, choose the 80mm roll/paper option if the driver exposes it. Disable headers/footers and enable the highest practical monochrome/text quality.
5. If the driver only offers a custom form, create an 80mm-wide continuous form using the printer manufacturer's utility. Keep margins at 0 where supported.

## Bajwa Traders receipt profile
- Physical roll: 80mm.
- Receipt content width: 76mm to leave a small safety margin for common print heads.
- QR code: 25mm square; it encodes the local receipt URL, not only the bill number. Scan it while connected to the shop Wi-Fi and logged in to Bajwa Traders to open that sale's receipt/database record.
- Urdu: right-to-left HTML receipt. For consistent Nastaliq shaping, place `NotoNastaliqUrdu-Regular.ttf` in `core/static/core/fonts/` and ensure it is served by Django static files. If absent, Windows/browser fallback fonts will be used.

## One-key printing
1. Set the USB thermal printer as the Windows default printer.
2. Start Bajwa Traders using `scripts\start_bajwa_traders.bat`. The launcher opens Edge/Chrome in app mode with kiosk printing enabled.
3. At checkout press **F12**. The sale is saved first, stock is reduced, and the receipt page calls the browser print function. Kiosk printing sends it to the default printer without the normal print dialog in supported Chromium builds.
4. After printing, the receipt page returns to the POS screen.

## First test (required before live sales)
- Print one test bill with English and Urdu item names, a long product name, discount, cash and change.
- Confirm no columns or QR edges are clipped. If clipping occurs, reduce the printer driver's left/right margins or adjust the receipt content width from 76mm to 72mm in `core/static/core/app.css`.
- Scan the QR code using a phone on the same Wi-Fi. Log in if prompted. The QR link uses the host address through which the receipt was opened; use the shop PC's LAN IP on phones, not `127.0.0.1`.
- Print 5–10 test bills before using it at the counter. Check that each bill prints once.

## Important limitation
Silent printing depends on the installed driver, printer paper-size settings, and Edge/Chrome kiosk-printing support. Test on the actual shop PC and printer. The app cannot silently print directly to a USB printer from an ordinary phone browser.
