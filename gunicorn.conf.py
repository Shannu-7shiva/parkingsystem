import os

# Automatically bind to 0.0.0.0 and the port assigned by Render/Railway/Heroku
port = os.environ.get("PORT", "10000")
bind = f"0.0.0.0:{port}"

workers = 1
threads = 4
timeout = 120
