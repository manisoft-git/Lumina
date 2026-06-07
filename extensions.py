from flask_socketio import SocketIO
from flask_login import LoginManager

socketio = SocketIO()
login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message_category = "info"

