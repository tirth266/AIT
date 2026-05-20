from flask import Blueprint, jsonify

bp = Blueprint("health", __name__)

@bp.route("/ping")
def ping():
    return jsonify({
        "status": "pong"
    })
