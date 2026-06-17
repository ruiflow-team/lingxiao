#!/bin/bash
# Hermes Desktop — Development Server
set -e
cd ~/Desktop/hermes-desktop

echo "Python:" $(python3 --version)
echo "PyQt5:" $(python3 -c "import PyQt5; print(PyQt5.__version__)" 2>/dev/null || echo "NOT INSTALLED")

# Clean sessions for fresh test
SESSIONS_FILE="$HOME/.hermes-desktop/sessions.json"
echo '{"sessions":{},"current":null}' > "$SESSIONS_FILE"

# Import check
python3 -c "import sys; sys.path.insert(0, '.'); import main; print('Import OK')"

# Start app (background on macOS)
export QT_QPA_PLATFORM=cocoa
python3 main.py &
APP_PID=$!
echo "Hermes Desktop started (PID: $APP_PID)"
sleep 2
if kill -0 $APP_PID 2>/dev/null; then
    echo "App running OK"
else
    echo "ERROR: App exited immediately"
    exit 1
fi
