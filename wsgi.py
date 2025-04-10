from app import app

# Ensure debug mode is off in production.
if __name__ != "__main__":
    app.config["DEBUG"] = False

# The WSGI callable for your server.
application = app
