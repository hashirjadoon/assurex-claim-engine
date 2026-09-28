#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

pick_python() {
  local c ver major minor
  for c in python3.12 python3.11 python3.10 python3; do
    if command -v "$c" >/dev/null 2>&1; then
      ver=$("$c" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
      major=${ver%%.*}
      minor=${ver#*.}
      if [ "$major" -eq 3 ] && [ "$minor" -ge 10 ] && [ "$minor" -le 12 ]; then
        echo "$c"
        return 0
      fi
    fi
  done
  return 1
}

if ! PY=$(pick_python); then
  echo "This project needs Python 3.10, 3.11, or 3.12."
  echo "Your default python3 is $(python3 --version 2>/dev/null || echo 'missing')."
  echo "Install 3.12 (recommended), then re-run ./setup.sh"
  echo "  Fedora:  sudo dnf install python3.12 python3.12-devel"
  echo "  Ubuntu:  sudo apt install python3.12 python3.12-venv python3.12-dev"
  echo "  macOS:   brew install python@3.12"
  echo "  Windows: https://www.python.org/downloads/release/python-31210/"
  exit 1
fi

echo "Using $(command -v "$PY") ($("$PY" --version))"

need_venv=0
if [ ! -x venv/bin/python ]; then
  need_venv=1
elif ! venv/bin/python -m pip -V >/dev/null 2>&1; then
  echo "Existing venv is missing pip; recreating it."
  need_venv=1
else
  vver=$(venv/bin/python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  pver=$("$PY" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
  if [ "$vver" != "$pver" ]; then
    echo "Existing venv is Python $vver; recreating with $pver."
    need_venv=1
  fi
fi

if [ "$need_venv" -eq 1 ]; then
  rm -rf venv
  "$PY" -m venv venv --upgrade-deps
fi

# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo
echo "Setup complete."
echo "Activate the environment, then start the app:"
echo "  source venv/bin/activate"
echo "  streamlit run app.py"
