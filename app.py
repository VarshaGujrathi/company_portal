from flask import Flask, render_template, request, jsonify
from datetime import datetime
from supabase import create_client
import os

SUPABASE_URL = "https://fxzzdmpusmhroyxjzfwk.supabase.co"
SUPABASE_KEY = "YeyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ4enpkbXB1c21ocm95eGp6ZndrIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MjAyOTc3MiwiZXhwIjoyMDg3NjA1NzcyfQ.OPDu7-jmaFc4vD16zDR8BcsoJjYWRiCOfmFdKtP3ZYg"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

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
    email = data["email"]
    username = data["username"]
    password = data["password"]

    # Check if already approved
    existing = supabase.table("users").select("*").eq("email", email).execute()
    if existing.data:
        return jsonify({"error": "User already exists"}), 400

    # Check pending
    pending = supabase.table("signup_requests").select("*").eq("email", email).execute()
    if pending.data:
        return jsonify({"error": "Signup already pending"}), 400

    supabase.table("signup_requests").insert({
        "email": email,
        "username": username,
        "password_hash": password,  # we will hash later
        "requested_at": "now()"
    }).execute()

    return jsonify({"success": True})

@app.route("/api/signin", methods=["POST"])
def signin():
    data = request.json
    email = data["email"]
    password = data["password"]

    user = supabase.table("users").select("*").eq("email", email).execute()

    if not user.data:
        return jsonify({"error": "Invalid credentials"}), 401

    user = user.data[0]

    if not user["approved"]:
        return jsonify({"error": "Pending approval"}), 403

    if user["blocked"]:
        return jsonify({"error": "Account blocked"}), 403

    if user["password_hash"] != password:
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"success": True})

@app.route("/api/user/update", methods=["POST"])
def update_profile():
    data = request.json
    current_username = data["username"]
    current_password = data["currentPassword"]
    new_username = data.get("newUsername")
    new_password = data.get("newPassword")

    user = next((u for u in approved_users 
                 if u["name"].lower() == current_username.lower() 
                 and u["password"] == current_password), None)

    if not user:
        return jsonify({"error": "Invalid current password"}), 401

    if new_username and new_username.lower() != current_username.lower():
        if any(u["name"].lower() == new_username.lower() for u in approved_users):
            return jsonify({"error": "Username already taken"}), 400
        user["name"] = new_username

    if new_password:
        user["password"] = new_password

    return jsonify({"success": True, "username": user["name"]})


# ---------- ADMIN ----------
@app.route("/api/admin/approve", methods=["POST"])
def approve_user():
    email = request.json["email"]

    request_data = supabase.table("signup_requests").select("*").eq("email", email).execute()

    if not request_data.data:
        return jsonify({"error": "Request not found"}), 404

    user = request_data.data[0]

    supabase.table("users").insert({
        "email": user["email"],
        "username": user["username"],
        "password_hash": user["password_hash"],
        "approved": True,
        "blocked": False
    }).execute()

    supabase.table("signup_requests").delete().eq("email", email).execute()

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
    user = next((u for u in approved_users if u["name"] == name), None)
    if user:
        approved_users.remove(user)
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
