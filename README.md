# AssureX Claim Engine

Streamlit app for warranty claim validation. It combines a trained Python classifier, a Google Teachable Machine image model, and a configurable warranty rule engine.

## Requirements

- **Python 3.10, 3.11, or 3.12** (required). Setup scripts refuse 3.13+ because pinned packages such as NumPy 1.26 have no installable wheels for those versions.
- pip (comes with the venv created below)
- About 2–4 GB disk for PyTorch, EasyOCR, and other dependencies

Do **not** commit or copy a `venv` folder. Each computer creates its own.

## Setup (macOS / Linux)

From the project root:

```bash
chmod +x setup.sh
./setup.sh
source venv/bin/activate
streamlit run app.py
```

The app opens at [http://localhost:8501](http://localhost:8501).

## Setup (Windows)

From the project root in PowerShell:

```powershell
.\setup.ps1
.\venv\Scripts\Activate.ps1
streamlit run app.py
```

If script execution is blocked, run:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

Then activate again.

## Manual setup (any OS)

Use this if you prefer not to run the setup script:

```bash
python3 -m venv venv
# Windows: python -m venv venv

source venv/bin/activate
# Windows: venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Always activate the venv in the **same terminal** you use to run Streamlit. Creating a venv in VS Code / Cursor does not install packages by itself.

## Demo logins

The SQLite database is created on first launch (`database/assurex.db` is local and gitignored). Seed accounts:

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `Admin@123` |
| Reviewer | `reviewer` | `Review@123` |
| Customer | `demo` | `Demo@123` |

You can also register a new customer or service employee from the Login page.

## If Streamlit is not found

The shell is not using the venv. Activate it, then confirm:

```bash
which python
which streamlit
```

Both should live under this project's `venv` directory.

## Retrain the Python model (optional)

Pre-trained files are in `model/`. To retrain from `data/processed/`:

```bash
source venv/bin/activate
python src/ml/train_model.py
```
