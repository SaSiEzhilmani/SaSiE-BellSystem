<div align="center">

# 🔔 SaSiE Bell System
### Professional Automated Bell Scheduling System
###  பள்ளி மற்றும் கல்வி நிறுவனங்களுக்காக தானியங்கி மணி அமைப்பு

**Created by சசி எழில்மணி (SaSi Ezhilmani)**


[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Windows-green.svg)]()
[![Language](https://img.shields.io/badge/Language-Python-yellow.svg)]()
[![Status](https://img.shields.io/badge/Status-Live%20Deployment-brightgreen.svg)]()

</div>

---

## 🌟 The Story Behind SaSiE

I am Ezhilmani S — System Administrator, RJ, DJ, Tamil Poet, from India. 
Every day I watched a staff member walk to the
bell manually, ring it, and walk back — ten times a day, every working
day. One missed ring meant late classes. One wrong timing meant
confusion across the campus.

I built SaSiE Bell System to solve that real problem.

This software is deployed and running live at an educational institution.
It works. It is free. It is yours.

---

## 📋 What It Does

SaSiE Bell System is a Windows desktop application that automates your
school bell schedule completely. Connect a USB relay module to your
existing bell — the software does the rest.

### ✨ Key Features

- 🕐 **Automated Scheduling** — Set times once, rings every day
- 📋 **Multiple Saved Schedules** — Regular day, exam week, special events
- 🔔 **Manual Override** — Ring bell anytime with one click
- ⏱️ **Customisable Bell Duration** — 1 to 9 seconds, your choice
- ⚠️ **30-Second Countdown Warning** — On-screen alert before every bell
- ⏩ **Smart Mid-Day Start** — Skips past bells, picks up from now
- 📝 **Activity Log** — Every ring recorded with date and time
- 🔐 **Dual Password System** — Admin and User roles
- 👤 **Guest Mode** — Manual bell only for unauthorised users
- 🏫 **Institute Branding** — Your school name and logo in the header
- 🌐 **HTML Header Support** — Customise with standard HTML tags

---

## 🖥️ System Requirements

| Requirement | Specification |
|---|---|
| Operating System | Windows 7 / 8 / 10 / 11 |
| Python | 3.8 or above |
| Hardware | USB HID Relay Module (VID: 16C0, PID: 05DF) |
| RAM | 512 MB minimum |
| Disk Space | 50 MB |
| Screen | 1024 × 768 or larger |

---

## 🚀 Installation

### Step 1 — Install Python
Download from https://www.python.org/downloads/
During installation tick **"Add Python to PATH"**

### Step 2 — Install Required Libraries
Open Command Prompt and run:
```bash
pip install pillow
pip install hid
```

### Step 3 — Copy Files
Create a folder `C:\BellSystem\` and place these files:
- `BellSystem.py` — Main application
- `institute.html` — Your school name and details
- `logo.png` — Your school logo (optional)

### Step 4 — Connect USB Relay
Plug the USB HID Relay Module into your computer.
Connect relay output to your school bell circuit.

### Step 5 — Run
```bash
python BellSystem.py
```
Default Admin password: `789`
Default User password: `1234`

---

## 📁 File Structure
SaSiE-BellSystem/
│
├── BellSystem.py          # Main application
├── institute.html         # School name and details
├── schedules.json         # Saved schedules (auto-created)
├── bell_log.txt           # Activity log (auto-created)
├── user_password.txt      # User password (auto-created)
└── logo.png               # School logo (optional)

---

## 🔧 Changing the Relay Module

If you use a different USB relay module, update these lines
at the top of `BellSystem.py`:

```python
VENDOR_ID  = 0x16c0   # Change to your module's Vendor ID
PRODUCT_ID = 0x05df   # Change to your module's Product ID
```

Also update the command bytes in `relay_on()` and `relay_off()`
as per your module's datasheet.

---

## 🏫 Customise for Your School

Edit `institute.html` with your school details:

```html
<h1>Your School Name</h1>
<h3>Affiliation / Board</h3>
<p>Address | Phone | Email</p>
```

Place your logo as `logo.png` in the same folder.

---

## 📊 Live Deployment

✅ Deployed at an institution 
✅ 10 bells automated per day
✅ Schedule: 08:00 AM to 03:00 PM
✅ System uptime: 07:30 AM to 04:30 PM daily
✅ Previously manual — now fully automated
✅ Zero missed bells since deployment

---

## 🗺️ Roadmap — Future Features

- [ ] Mobile app remote control
- [ ] WhatsApp / SMS notification on bell ring
- [ ] Multi-campus / multi-relay support
- [ ] Cloud activity log
- [ ] Android app for manual override

---

## 🤝 For Schools That Need Help

If your school wants to use this system and needs help
with installation and setup, I offer:

| Service | Price |
|---|---|
| Software installation + relay setup | ₹2,000 – ₹3,000 |
| Annual maintenance + support | ₹1,000 – ₹1,500/year |
| Custom configuration | ₹500 |
| Remote support | ₹300/session |

Contact: *(sasiezhilmani@gmail.com / +91 9092 566 569)*

---

## ☕ Support This Project

## ☕ Support This Project

If SaSiE Bell System helped your school, consider supporting
the work that went into building it.

Every contribution, however small, helps me continue building
free tools for schools and educational institutions.

**💳 UPI Payment (India)**
sasie@scb
*Scan any UPI app — GPay, PhonePe, Paytm, or any bank app.*
*Any amount. Even ₹10 means someone cared. Thank you.*

**🌍 International Support**
Email me at sasiezhilmani@gmail.com
I will share a payment link.

---

## 📜 License

MIT License — © 2026 சசி எழில்மணி (SaSi Ezhilmani / SaSiE)

Free to use. Free to modify. Free to deploy.
**Credit must be given to the original creator.**

See [LICENSE](LICENSE) for full terms.

---

## 🙏 Acknowledgement

*"This software was developed using Python with AI-assisted tools.*
*System design, requirement analysis, feature specification,*
*deployment and testing were carried out by the author."*

---

<div align="center">

**சசி எழில்மணி (SaSiE)**
*System Administrator | Developer | RJ*
*Tamil Nadu, India*


</div>
