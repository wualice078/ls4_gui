from __future__ import annotations

import mimetypes
from functools import wraps

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

from config import (
    AWS_SERVER_URL,
    ENABLE_SCHEDULER_PAUSE,
    GUI_PASSWORD,
    GUI_USERNAME,
    HOST,
    LOGBOOK_URL,
    PORT,
    SECRET_KEY,
    SIMULATE,
    WEBCAM_REFRESH_SECONDS,
    DEBUG,
)
from services import control

app = Flask(__name__)
app.secret_key = SECRET_KEY

_PASSWORD_HASH = generate_password_hash(GUI_PASSWORD)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("logged_in"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("logged_in"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        if username == GUI_USERNAME and check_password_hash(_PASSWORD_HASH, password):
            session["logged_in"] = True
            session["username"] = username
            next_url = request.args.get("next") or url_for("dashboard")
            return redirect(next_url)

        flash("Invalid username or password.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for("login"))


@app.route("/")
@login_required
def dashboard():
    return render_template(
        "dashboard.html",
        status=control.status(),
        aws_server_url=AWS_SERVER_URL,
        logbook_url=LOGBOOK_URL,
        simulate=SIMULATE,
        webcam_refresh_seconds=WEBCAM_REFRESH_SECONDS,
        scheduler_pause_enabled=ENABLE_SCHEDULER_PAUSE,
    )


@app.route("/api/status")
@login_required
def api_status():
    return jsonify(control.status())


@app.route("/api/dome/<action>", methods=["POST"])
@login_required
def api_dome(action: str):
    if action == "open":
        result = control.open_dome()
    elif action == "close":
        result = control.close_dome()
    else:
        return jsonify({"ok": False, "message": f"Unknown dome action: {action}"}), 400

    return jsonify({"ok": result.ok, "message": result.message, "status": control.status()})


@app.route("/api/telescope/<action>", methods=["POST"])
@login_required
def api_telescope(action: str):
    handlers = {
        "start": control.telescope_start,
        "stop": control.telescope_stop,
        "stow": control.stow_telescope,
    }
    handler = handlers.get(action)
    if handler is None:
        return jsonify({"ok": False, "message": f"Unknown telescope action: {action}"}), 400

    result = handler()
    status_code = 200 if result.ok else 400
    return jsonify(
        {"ok": result.ok, "message": result.message, "status": control.status()}
    ), status_code


@app.route("/api/pdu/<int:outlet>/<action>", methods=["POST"])
@login_required
def api_pdu(outlet: int, action: str):
    if action == "on":
        result = control.set_pdu_outlet(outlet, True)
    elif action == "off":
        result = control.set_pdu_outlet(outlet, False)
    else:
        return jsonify({"ok": False, "message": f"Unknown PDU action: {action}"}), 400

    status_code = 200 if result.ok else 400
    return jsonify(
        {"ok": result.ok, "message": result.message, "status": control.status()}
    ), status_code


@app.route("/api/scheduler/<action>", methods=["POST"])
@login_required
def api_scheduler(action: str):
    handlers = {
        "start": control.scheduler_start,
        "stop": control.scheduler_stop,
        "pause": control.scheduler_pause,
    }
    handler = handlers.get(action)
    if handler is None:
        return jsonify({"ok": False, "message": f"Unknown scheduler action: {action}"}), 400

    result = handler()
    status_code = 200 if result.ok else 400
    return jsonify(
        {"ok": result.ok, "message": result.message, "status": control.status()}
    ), status_code


@app.route("/api/webcam/<camera>", methods=["POST"])
@login_required
def api_webcam(camera: str):
    result = control.fetch_webcam(camera)
    status_code = 200 if result.ok else 400
    return jsonify(
        {
            "ok": result.ok,
            "message": result.message,
            "camera": camera,
            "fetched_at": result.details.get("fetched_at"),
            "status": control.status(),
        }
    ), status_code


@app.route("/api/webcam/<camera>/image")
@login_required
def api_webcam_image(camera: str):
    from flask import Response, send_file

    allowed = {"oil_pump", "tcs", "flux_meter", "dome"}
    if camera not in allowed:
        return jsonify({"ok": False, "message": f"Unknown camera: {camera}"}), 404

    image_path = control.webcam_image_path(camera)
    if image_path and image_path.exists():
        mimetype = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        return send_file(image_path, mimetype=mimetype)

    labels = {
        "oil_pump": "Oil Pump Webcam",
        "tcs": "TCS Webcam",
        "flux_meter": "Flux Meter Camera",
        "dome": "Dome Camera",
    }
    mode = "SIMULATED" if SIMULATE else "LIVE"
    label = labels[camera]
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
  <rect width="640" height="360" fill="#0f172a"/>
  <text x="320" y="150" fill="#e2e8f0" font-family="sans-serif" font-size="28" text-anchor="middle">{label}</text>
  <text x="320" y="195" fill="#94a3b8" font-family="sans-serif" font-size="18" text-anchor="middle">{mode} preview</text>
</svg>"""
    return Response(svg, mimetype="image/svg+xml")


@app.route("/api/mosaic/generate", methods=["POST"])
@login_required
def api_mosaic_generate():
    payload = request.get_json(silent=True) or {}
    prefix = (payload.get("prefix") or request.form.get("prefix") or "").strip()
    result = control.generate_mosaic(prefix)
    status_code = 200 if result.ok else 400
    return jsonify(
        {
            "ok": result.ok,
            "message": result.message,
            **result.details,
        }
    ), status_code


@app.route("/api/mosaic/image")
@login_required
def api_mosaic_image():
    from flask import Response, send_file

    image_path = control.mosaic_preview_path()
    if image_path and image_path.exists():
        mimetype = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
        return send_file(image_path, mimetype=mimetype)

    svg = """<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360" viewBox="0 0 640 360">
  <rect width="640" height="360" fill="#0f172a"/>
  <text x="320" y="170" fill="#94a3b8" font-family="sans-serif" font-size="20" text-anchor="middle">Generate a mosaic to preview data</text>
</svg>"""
    return Response(svg, mimetype="image/svg+xml")


if __name__ == "__main__":
    print(f"LS4 GUI starting on http://{HOST}:{PORT} (simulate={SIMULATE}, debug={DEBUG})")
    app.run(host=HOST, port=PORT, debug=DEBUG)
