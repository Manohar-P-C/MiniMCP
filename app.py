"""Application entry point.

Runs the MiniMCP Flask development server. For production use Gunicorn:
    gunicorn -w 4 -b 0.0.0.0:5000 app:app
"""

from minimcp.transport import create_app

app = create_app()

if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO)

    from minimcp.config import Config

    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
