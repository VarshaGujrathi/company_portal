from flask import Flask, render_template, request, jsonify
from datetime import datetime

app = Flask(__name__)

pending_requests = []
approved_users = []

ADMIN_CREDENTIALS = [
    {"email": "admin@company.com", "password": "company123"}
]

USER_PORTAL = {"email": "user@company.com", "password": "company123"}


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/first-login", methods=["POST"])
def first_login():
    data = request.json
    email = data["email"]
    password = data["password"]

    if any(a["email"] == email and a["password"] == password for a in ADMIN_CREDENTIALS):
        return jsonify({"role": "admin"})

    if email == USER_PORTAL["email"] and password == USER_PORTAL["password"]:
        return jsonify({"role": "user"})

    return jsonify({"error": "Invalid credentials"}), 401


# ---------- USER ----------
@app.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    name = data["username"]

    if any(u["name"].lower() == name.lower() for u in approved_users):
        return jsonify({"error": "User already exists"}), 400

    if any(u["name"].lower() == name.lower() for u in pending_requests):
        return jsonify({"error": "Signup request already pending"}), 400

    pending_requests.append({
        "name": name,
        "password": data["password"],
        "requested_at": datetime.now().strftime("%d/%m/%Y, %I:%M %p")
    })

    return jsonify({"success": True})


@app.route("/api/signin", methods=["POST"])
def signin():
    data = request.json

    user = next(
        (u for u in approved_users
         if u["name"].lower() == data["username"].lower()
         and u["password"] == data["password"]),
        None
    )

    if not user:
        if any(u["name"].lower() == data["username"].lower() for u in pending_requests):
            return jsonify({"error": "Account pending approval"}), 403
        return jsonify({"error": "Invalid credentials"}), 401

    if user["blocked"]:
        return jsonify({"error": "Account blocked"}), 403

    return jsonify({"success": True, "username": user["name"]})


# ---------- ADMIN ----------
@app.route("/api/admin/data")
def admin_data():
    return jsonify({
        "approved": approved_users,
        "pending": pending_requests,
        "entries": 156
    })


@app.route("/api/admin/approve", methods=["POST"])
def approve():
    name = request.json["name"]
    user = next(u for u in pending_requests if u["name"] == name)

    approved_users.append({
        "name": user["name"],
        "password": user["password"],
        "approved_at": datetime.now().strftime("%d/%m/%Y, %I:%M %p"),
        "blocked": False
    })

    pending_requests.remove(user)
    return jsonify({"success": True})


@app.route("/api/admin/block", methods=["POST"])
def block_user():
    name = request.json["name"]
    user = next(u for u in approved_users if u["name"] == name)
    user["blocked"] = not user["blocked"]
    return jsonify({"success": True})


@app.route("/api/admin/remove", methods=["POST"])
def remove_user():
    name = request.json["name"]
    approved_users[:] = [u for u in approved_users if u["name"] != name]
    return jsonify({"success": True})


@app.route("/api/admin/edit", methods=["POST"])
def edit_user():
    data = request.json
    user = next(u for u in approved_users if u["name"] == data["oldName"])
    user["name"] = data["newName"]
    user["password"] = data["newPassword"]
    return jsonify({"success": True})


if __name__ == "__main__":
    app.run(debug=True)
