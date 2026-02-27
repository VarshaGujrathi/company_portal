from flask import Flask, render_template, request, jsonify # type: ignore
from datetime import datetime
from supabase import create_client # type: ignore
from werkzeug.security import generate_password_hash # type: ignore
import os

SUPABASE_URL = "https://fxzzdmpusmhroyxjzfwk.supabase.co"
SUPABASE_KEY = "sb_secret_D8-XgMPPYA7CQO03jz79zg_gisGKy8h"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__)

ADMIN_CREDENTIALS = [
    {"email": "admin@company.com", "password": "company123"}
]

USER_PORTAL = {"email": "user@company.com", "password": "company123"}

@app.route("/supatest")
def supatest():
    data = supabase.table("signup_requests").select("*").limit(1).execute()
    return {"data": data.data}

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/dashboard")
def dashboard():
    return render_template("user_dashboard.html")
@app.route("/master-file")
def master_file_page():
    return render_template("master_file.html")

@app.route("/update-master-file")
def update_master_file_page():
    return render_template("update_master_file.html")


# ---------- MASTER FILE INSERT ----------
@app.route("/api/master-file", methods=["POST"])
def add_master_file():
    try:
        data = request.json

        response = supabase.table("master_file").insert({
            "name": data["name"],
            "gst_no": data["gst_no"],
            "password": data["password"],
            "concern_person": data["concern_person"],
            "contact_no": data["contact_no"],
            "email_id": data["email_id"],
            "periodicity": data["periodicity"],
            "start_month": data["start_month"],
            "end_month": data["end_month"]
        }).execute()

        return jsonify({"success": True})

    except Exception as e:
        print("Master insert error:", e)
        return jsonify({"error": "Failed to insert data"}), 500



# ---------- MASTER FILE UPDATE ----------
@app.route("/api/update-master-file", methods=["POST"])
def update_master():
    try:
        data = request.json

        response = supabase.table("master_file") \
            .update({
                "name": data["name"],
                "password": data["password"],
                "concern_person": data["concern_person"],
                "contact_no": data["contact_no"],
                "email_id": data["email_id"],
                "periodicity": data["periodicity"],
            }) \
            .eq("gst_no", data["gst_no"]) \
            .execute()

        return jsonify({"success": True})

    except Exception as e:
        print("Update error:", e)
        return jsonify({"error": "Failed to update data"}), 500


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
    username = data["username"]
    password = data["password"]

    # Check if already approved
    existing = supabase.table("users").select("*").eq("username", username).execute()
    if existing.data:
        return jsonify({"error": "User already exists"}), 400

    # Check pending
    pending = supabase.table("signup_requests").select("*").eq("username", username).execute()
    if pending.data:
        return jsonify({"error": "Signup request already pending"}), 400

    supabase.table("signup_requests").insert({
        "username": username,
        "password_hash": password
    }).execute()

    return jsonify({"success": True})

@app.route("/api/signin", methods=["POST"])
def signin():
    data = request.json
    username = data["username"]
    password = data["password"]

    # 1️⃣ Check approved users
    user = supabase.table("users").select("*").eq("username", username).execute()

    if user.data:
        user = user.data[0]

        if user["blocked"]:
            return jsonify({"error": "Account blocked"}), 403

        if user["password_hash"] != password:
            return jsonify({"error": "Invalid credentials"}), 401

        return jsonify({"success": True})

    # 2️⃣ If not approved, check pending requests
    pending = supabase.table("signup_requests").select("*").eq("username", username).execute()

    if pending.data:
        return jsonify({"error": "Account pending approval"}), 403

    # 3️⃣ If not found anywhere
    return jsonify({"error": "Invalid credentials"}), 401

@app.route("/api/user/update", methods=["POST"])
def update_profile():
    data = request.json
    current_username = data["username"]
    current_password = data["currentPassword"]
    new_username = data.get("newUsername")
    new_password = data.get("newPassword")

    user = next((u for u in approved_users  # type: ignore
                 if u["name"].lower() == current_username.lower() 
                 and u["password"] == current_password), None)

    if not user:
        return jsonify({"error": "Invalid current password"}), 401

    if new_username and new_username.lower() != current_username.lower():
        if any(u["name"].lower() == new_username.lower() for u in approved_users): # type: ignore
            return jsonify({"error": "Username already taken"}), 400
        user["name"] = new_username

    if new_password:
        user["password"] = new_password

    return jsonify({"success": True, "username": user["name"]})


# ---------- ADMIN ----------
@app.route("/api/adminpanel", methods=["GET"])
def adminpanel():
    try:
        # Fetch pending signup requests
        pending_response = supabase.table("signup_requests").select("*").execute()
        pending_users = pending_response.data or []

        # Fetch approved users
        approved_response = supabase.table("users").select("*").execute()
        approved_users = approved_response.data or []

        return jsonify({
            "pending": pending_users,
            "approved": approved_users,
            "pending_count": len(pending_users),
            "approved_count": len(approved_users)
        })

    except Exception as e:
        print("Admin panel error:", e)
        return jsonify({"error": "Failed to load admin data"}), 500

@app.route("/api/admin/approve", methods=["POST"])
def approve_user():
    username = request.json.get("username")

    if not username:
        return jsonify({"error": "Username missing"}), 400

    request_data = supabase.table("signup_requests") \
        .select("*") \
        .eq("username", username) \
        .execute()

    if not request_data.data:
        return jsonify({"error": "Request not found"}), 404

    user = request_data.data[0]

    # Insert into users table
    supabase.table("users").insert({
        "username": user["username"],
        "password_hash": user["password_hash"],
        "approved": True,
        "blocked": False
    }).execute()

    # Delete from signup_requests
    supabase.table("signup_requests") \
        .delete() \
        .eq("username", username) \
        .execute()

    return jsonify({"success": True})

@app.route("/api/admin/block", methods=["POST"])
def block_user():
    username = request.json["username"]

    user = supabase.table("users") \
        .select("blocked") \
        .eq("username", username) \
        .execute()

    if not user.data:
        return jsonify({"error": "User not found"}), 404

    current_status = user.data[0]["blocked"]

    supabase.table("users") \
        .update({"blocked": not current_status}) \
        .eq("username", username) \
        .execute()

    return jsonify({"success": True})

@app.route("/api/admin/remove", methods=["POST"])
def remove_user():
    username = request.json["username"]

    supabase.table("users") \
        .delete() \
        .eq("username", username) \
        .execute()

    return jsonify({"success": True})

@app.route("/api/admin/edit", methods=["POST"])
def edit_user():
    old_username = request.json["oldUsername"]
    new_username = request.json["newUsername"]
    new_password = request.json["newPassword"]

    hashed_password = generate_password_hash(new_password)

    supabase.table("users") \
        .update({
            "username": new_username,
            "password_hash": hashed_password
        }) \
        .eq("username", old_username) \
        .execute()

    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True)