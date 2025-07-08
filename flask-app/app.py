from flask import Flask
import threading
from flask_socketio import SocketIO
from routes.stats import register_routes as register_stats_routes
from routes.posts import register_routes as register_posts_routes
from routes.languages import register_routes as register_languages_routes
from routes.authors import register_routes as register_authors_routes
from routes.ingress import register_routes as register_ingress_routes,register_socket_routes
from routes.analytics import register_routes as register_analytics_routes
from libs.database import get_db_connection
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-change-in-production'
socketio = SocketIO(app, cors_allowed_origins="*")


register_stats_routes(app)
register_posts_routes(app)
register_languages_routes(app)
register_authors_routes(app)
register_ingress_routes(app)
register_analytics_routes(app)

background_thread = register_socket_routes(socketio)




# Start background monitoring thread
monitor_thread = threading.Thread(target=background_thread, daemon=True)
monitor_thread.start()

for route in app.url_map.iter_rules():
    if route.endpoint != 'static':
        print(f"Registered route: {route.rule} -> {route.endpoint}")
if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
