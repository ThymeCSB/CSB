```markdown
# CSB – Crusader Secret Bureau

                 |<>| C R I D |<>|
|<>| CSB RESEARCH AND INTELLIGENCE DEPARTMENT |<>|

|<>| CRUSADER GOVERNMENT - CLASSIFIED SOFTWARE |<>|

**Official Service Software (OSS)**  
A local desktop intelligence application for Minecraft / Stoneworks.

> **Repository:** [https://github.com/ThymeCSB/CSB](https://github.com/ThymeCSB/CSB)

---

## Overview

CSB is a standalone, offline‑first intelligence management tool designed for **Minecraft roleplay and faction intelligence** – particularly for the **Stoneworks** community.  
It helps you collect, organise, analyse, and protect sensitive information about persons, organisations, operations, and their interconnections.

All data is stored locally in an **encrypted SQLite database** (with optional message‑level encryption).  
The application is built with **Python** and **Flet**, providing a modern, native‑looking graphical interface for Windows, macOS, and Linux.

---

## Features

- **🔐 Crypto Module**  
  Encrypt and decrypt arbitrary text using a shared passphrase (Fernet symmetric encryption, PBKDF2 key derivation). Useful for sharing sensitive intelligence outside the app.

- **📁 Records Module**  
  Manage three types of records:
  - **Persons** – extensive domestic and external intelligence fields (ranks, factions, locations, associates, threat levels, etc.)
  - **Organisations** – structure, leadership, military/economic strength, diplomatic status
  - **Operations** – codenames, objectives, timelines, assets, outcomes

  Each record supports:
  - **Identification image** (e.g., a screenshot or avatar)
  - **Multiple file attachments** (images, PDFs, logs, etc.)
  - **Full import/export** of individual entries (`.csbentry` files) and the whole database (`.csbdb`)

- **⚡ Data Intake**  
  Quickly add a note or attach an image to an existing person record without opening the full editor.  
  Notes are time‑stamped and appended to the person’s domestic or external intelligence notes.

- **🔗 Connection Analysis** (text‑only)  
  Automatically analyses all person records and finds possible connections based on:
  - Shared values in intelligence fields (exact, normalised, typo‑tolerant)
  - Cross‑references in “known associates” and “aliases”
  - Weighted scoring and confidence levels (Critical / Strong / Moderate / Low / Weak)

  The analysis runs with fixed, sensible defaults (similarity ≥ 0.88, minimum score 20) every time you switch to the Connections tab – **no configuration needed**.

- **🔒 Local & Portable**  
  All data is stored in `~/.csb/` – you can back it up or move it freely.  
  The database uses SQLite with WAL mode for reliability.

- **📜 Detailed Logging**  
  Every action is logged to `~/.csb/logs/` for troubleshooting and audit trails.

---

## Installation

### Prerequisites

- **Python 3.8 or newer** (download from [python.org](https://python.org))
- **pip** (usually included with Python)

### Steps

1. **Download csb_app.py**

2. **Install required Python packages**

   - `flet` – the GUI framework.
   - `cryptography` – for encryption (Fernet, PBKDF2).

3. **Run the application**

   ```bash
   python csb_app.py
   ```

   On first launch, the app will create the database and log directory in `~/.csb/`.  
   No further setup is required.

> **Note:** The application is a single Python file (`csb_app.py`) – all logic is contained within it. No external helper modules are needed.

---

## Usage

The main window is divided into **four tabs** (Navigation Rail on the left):

### 1. Crypto (Encryption / Decryption)

- Enter your plaintext or cipher text in the left field.
- Enter a **shared passphrase** (the same one used by the recipient).
- Press **Encrypt** or **Decrypt**.
- The result appears in the right field.
- Use **Clear** to reset both fields.

> Encryption uses **Fernet (symmetric authenticated encryption)** with a key derived from your passphrase. The salt is fixed (`CSB_STONEWORKS_SALT_2024`) – it is not a secret but ensures that the same passphrase always produces the same key.

### 2. Records (Database)

This is the core of the application.

- **Switch record type** using the three buttons at the top: *Persons*, *Organisations*, *Operations*.
- The left panel shows a list of all existing entries; click **Edit** (pencil icon) or **Delete** (trash icon) on any entry.
- To **create a new entry**, click the **New Entry** button.

#### Editing a record

- Fill in the fields. Required fields (marked with `*`) must not be empty.
- Once you save, you can:
  - **Set an Identification Image** – a photo/screenshot that will be displayed prominently.
  - **Add Attachments** – any number of additional files.
- All attachments are stored directly inside the SQLite database (as BLOBs). They are included when you export an entry.

#### Import / Export

- **Export Entry** – click the export button (available in the entry list or edit view) to save a single record as a `.csbentry` file (JSON format with base64‑encoded attachments).
- **Import Entry** – use the **Import Entry** button to load a previously exported file. If a record with the same name/codename exists, you will be prompted to replace it or keep the existing one.
- **Export Database** – creates a full copy of the database (all tables) as a `.csbdb` file (SQLite format). This is a complete backup.

### 3. Data Intake

A rapid‑input tool for adding notes or images to an existing person.

- **Search** – type part of a person’s name to filter the dropdown.
- **Select a person** from the dropdown.
- Choose **Intelligence Area** – Domestic or External (determines which notes field is updated).
- **Enter a note** (or leave empty if you only want to attach an image).
- **Add Image** – select an image file; it will be attached to the record (not as identification, but as an ordinary attachment).
- Press **Add to Record** – the note (if any) is appended with a timestamp, and the image is saved as an attachment.

### 4. Connections (text‑only analysis)

When you switch to this tab, the application **automatically**:

1. Loads all person records.
2. Runs a pairwise connection analysis using both Domestic and External intelligence fields.
3. Displays the results as a plain text list in the central text area.

No buttons or settings – the analysis uses fixed thresholds (similarity ≥ 0.88, minimum score 20).  
The output shows:

- `Person A ↔ Person B  [Domain]  Score: X  (Strength)`
- For each matching piece of evidence: field name, matched values, similarity percentage, and weight contribution.

The analysis is entirely **local** – no data is sent anywhere.

---

## File Locations & Data

- **Database:** `~/.csb/csb_database.db` (SQLite)
- **Logs:** `~/.csb/logs/csb_YYYYMMDD_HHMMSS.log`
- **Configuration:** None – all settings are internal.

You can safely back up the entire `.csb` folder to preserve your data.

---

## Troubleshooting

- **ModuleNotFoundError: No module named 'flet'**  
  → Install with `pip install flet`.

- **ModuleNotFoundError: No module named 'cryptography'**  
  → Install with `pip install cryptography`.

- **Database locked / busy errors**  
  The app uses WAL mode and a busy timeout of 20 seconds. If you encounter persistent locks, try restarting the app.

- **Encryption fails with "InvalidToken"**  
  You are using the wrong passphrase or the ciphertext is corrupted. Double‑check your input.

- **Logs**  
  If something goes wrong, check the latest log file in `~/.csb/logs/`. It contains detailed debug information.

---

## Contributing

This is a community project. Feel free to open issues or pull requests on the GitHub repository.  
Please ensure that any changes keep the single‑file nature and do not introduce external dependencies beyond `flet` and `cryptography`.

---

## License

This software is provided as‑is, free for personal and non‑commercial use.  
For commercial use, please contact the repository owner.

---

                |<>| C R I D |<>|
|<>| CSB RESEARCH AND INTELLIGENCE DEPARTMENT |<>|

|<>| CRUSADER GOVERNMENT - CLASSIFIED SOFTWARE |<>|

```markdown
