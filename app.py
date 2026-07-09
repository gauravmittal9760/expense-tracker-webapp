from flask import ( Flask, render_template, request, redirect, session, flash )
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta ,UTC
import pytz
from functools import wraps
import requests
from sqlalchemy import extract
from email.message import EmailMessage
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from flask import *
from dotenv import load_dotenv
load_dotenv()
# from flask_wtf import CSRFProtect

import csv
import pandas as pd

from flask import send_file
from fpdf import FPDF
import random
import json
import uuid
import time
import shutil
import zipfile
import os
import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
from collections import defaultdict

india_time = pytz.timezone("Asia/Kolkata")

print("NEW APP RUNNING")

app = Flask(__name__)

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

os.makedirs("static/profile_pics", exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config["ADMIN_PROFILE_FOLDER"] = "static/admin_profiles"

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "").strip()
# app.secret_key = "expense_secret_key"
app.secret_key = os.environ.get("SECRET_KEY", "expense_secret_key")
print(app.url_map)

# Database setup
database_url = os.getenv("DATABASE_URL")

if database_url:
    database_url = database_url.replace(
        "postgres://",
        "postgresql://",
        1
    )

app.config["SQLALCHEMY_DATABASE_URI"] = (
    database_url
    if database_url
    else "sqlite:///expense_tracker.db"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {

    "pool_pre_ping": True,

    "pool_recycle": 300

}

db = SQLAlchemy(app)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}

RESEND_API_KEY = os.getenv("RESEND_API_KEY")


def send_otp_email(receiver_email, otp):

    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = BREVO_API_KEY

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(
        sib_api_v3_sdk.ApiClient(configuration)
    )

    email = sib_api_v3_sdk.SendSmtpEmail(
        sender={
            "name": "Expense Tracker",
            "email": "gauravmittal1198141@gmail.com"
        },
        to=[
            {
                "email": receiver_email
            }
        ],
        subject="Your OTP for Expense Tracker",
        html_content=f"""
        <h2>Expense Tracker OTP Verification</h2>

        <p>Your OTP is:</p>

        <h1>{otp}</h1>

        <p>This OTP is valid for a 10 minutes.</p>
        <p>Do not share it with anyone.</p>
        """
    )

    try:
        response = api_instance.send_transac_email(email)
        print("Brevo Success:", response)
        return True

    except ApiException as e:
        print("Brevo Error:", e.body)
        return False

def ist_now():
    return datetime.now(pytz.utc).astimezone(india_time)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect("/")
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "admin_logged_in" not in session:

            return redirect("/open_admin_panel")

        return f(*args, **kwargs)

    return decorated_function

@app.route("/test")
def test():

    return "TEST WORKING"

# User Table
class User(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    username = db.Column(db.String(50), unique=True, nullable=False)

    email = db.Column(db.String(100), nullable=False)

    password = db.Column(db.String(300), nullable=False)

    security_question = db.Column(db.String(200),nullable=False)

    security_answer = db.Column(db.String(300),nullable=False)

    budget = db.Column(db.Float, default=0)

    income = db.Column(db.Float, default=0)

    created_at = db.Column(db.DateTime,default=ist_now)

    two_step_enabled = db.Column(db.Boolean,default=False)

    currency = db.Column(db.String(20),default="INR")

    profile_pic = db.Column(db.String(300),default="default.png")

    failed_attempts = db.Column(db.Integer,default=0)

    account_locked = db.Column(db.Boolean,default=False)

    lock_time = db.Column(db.DateTime,nullable=True)

    is_locked = db.Column(db.Boolean,default=False)

    is_admin = db.Column(db.Boolean,default=False)
    
    admin_password = db.Column(db.String(300))

    admin_security_question = db.Column(db.String(300))

    admin_security_answer = db.Column(db.String(300))

    expenses = db.relationship("Expense",backref="user",lazy=True,cascade="all, delete")


class Budget(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    balance = db.Column(
        db.Float,
        nullable=False
    )

    monthly_budget = db.Column(
        db.Float,
        nullable=False
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

class Expense(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    category = db.Column(db.String(100), nullable=False)

    description = db.Column( db.String(500) )

    amount = db.Column(db.Float, nullable=False)

    date = db.Column(db.Date, nullable=False)

    image = db.Column(db.String(300))
    
    images = db.Column( db.Text)

    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))


class LoginHistory(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    login_time = db.Column(
        db.DateTime,
        default=ist_now
    )

    ip_address = db.Column(
        db.String(100)
    )


class UserActivityLog(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(200)
    )

    email = db.Column(
        db.String(200)
    )

    action = db.Column(
        db.String(100)
    )

    action_time = db.Column(
        db.DateTime,
        default=ist_now
    )

    extra_info = db.Column(
        db.String(500)
    )

class AdminProfile(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    profile_pic = db.Column(
        db.String(300)
    )

class NotificationSettings(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        unique=True
    )

    notifications_enabled = db.Column(
        db.Boolean,
        default=True
    )

    budget_alerts = db.Column(
        db.Boolean,
        default=True
    )

    inactivity_alerts = db.Column(
        db.Boolean,
        default=True
    )

    expense_reminders = db.Column(
        db.Boolean,
        default=True
    )


@app.route("/set_budget", methods=["GET", "POST"])
def set_budget():

    if "user_id" not in session:
        return redirect("/")

    budget = Budget.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if request.method == "POST":

        balance = int(
            request.form.get("balance")
        )

        monthly_budget = int(
            request.form.get("monthly_budget")
        )

        if budget:

            budget.balance = balance
            budget.monthly_budget = monthly_budget

        else:

            budget = Budget(
                balance=balance,
                monthly_budget=monthly_budget,
                user_id=session["user_id"]
            )

            db.session.add(budget)

        db.session.commit()

        return redirect("/dashboard")

    return render_template(
        "set_budget.html",
        budget=budget
    )

@app.route("/notifications_settings")
def notifications_settings():

    if "user_id" not in session:

        return redirect("/")

    settings = NotificationSettings.query.filter_by(
        user_id=session["user_id"]
    ).first()

    if not settings:

        settings = NotificationSettings(
            user_id=session["user_id"]
        )

        db.session.add(settings)

        db.session.commit()

    return render_template(

        "notifications_settings.html",

        settings=settings

    )


@app.route("/save_notification_settings", methods=["POST"])
def save_notification_settings():

    if "user_id" not in session:

        return redirect("/")

    user_id = session["user_id"]

    settings = NotificationSettings.query.filter_by(
        user_id=user_id
    ).first()

    if not settings:

        settings = NotificationSettings(
            user_id=user_id
        )

        db.session.add(settings)

    settings.notifications_enabled = (
        True if request.form.get("notifications_enabled")
        else False
    )

    settings.budget_alerts = (
        True if request.form.get("budget_alerts")
        else False
    )

    settings.inactivity_alerts = (
        True if request.form.get("inactivity_alerts")
        else False
    )

    settings.expense_reminders = (
        True if request.form.get("expense_reminders")
        else False
    )

    db.session.commit()

    return redirect("/dashboard")

@app.route("/search_expenses")
def search_expenses():

    if "user_id" not in session:
        return redirect("/")

    return render_template(
        "search_expenses.html"
    )

@app.route(
    "/search/category",
    methods=["GET", "POST"]
)
def search_category():

    if "user_id" not in session:
        return redirect("/")

    expenses = []

    if request.method == "POST":

        category = request.form.get(
            "category"
        )

        expenses = Expense.query.filter(
            Expense.category.ilike(
                f"%{category}%"
            ),
            Expense.user_id == session["user_id"]
        ).all()

    return render_template(
        "search_category.html",
        expenses=expenses
    )
@app.route(
    "/search/date",
    methods=["GET", "POST"]
)
def search_date():

    if "user_id" not in session:
        return redirect("/")

    expenses = []

    if request.method == "POST":

        date_str = request.form.get("date")

        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except:
            return "Invalid date"

        expenses = Expense.query.filter_by(
            date=date,
            user_id=session["user_id"]
        ).all()

    return render_template(
        "search_date.html",
        expenses=expenses
    )

@app.route(
    "/search/month",
    methods=["GET", "POST"]
)
def search_month():

    if "user_id" not in session:
        return redirect("/")

    expenses = []

    if request.method == "POST":

        month = request.form.get("month")

        expenses = Expense.query.filter(
                extract('month', Expense.date) == int(month),
                Expense.user_id == session["user_id"]
            ).all()

    return render_template(
        "search_month.html",
        expenses=expenses
    )

@app.route(
    "/search/amount",
    methods=["GET", "POST"]
)
def search_amount():

    if "user_id" not in session:
        return redirect("/")

    expenses = []

    if request.method == "POST":

        amount = float(request.form.get("amount"))

        expenses = Expense.query.filter_by(
            amount=amount,
            user_id=session["user_id"]
        ).all()

    return render_template(
        "search_amount.html",
        expenses=expenses
    )

@app.route("/", methods=["GET", "POST"])
def home():

    if request.method == "POST":

        username = request.form.get(
            "username"
        )

        password = request.form.get(
            "password"
        )



        # ===================================
        # SUPER ADMIN LOGIN (.env)
        # ===================================

        admin_username = os.getenv(
            "ADMIN_USERNAME"
        )

        admin_password = os.getenv(
            "ADMIN_PASSWORD"
        )

        if (

            username == admin_username

            and

            password == admin_password

        ):

            session["admin_access"] = True

            session["admin_candidate"] = (
                admin_username
            )

            return redirect(
                "/admin_options"
            )

        # ===================================
        # NORMAL USER LOGIN
        # ===================================

        user = User.query.filter_by(
            username=username
        ).first()

        if user:

            # =========================
            # AUTO UNLOCK AFTER 15 MIN
            # =========================

            if user.account_locked:

                if user.lock_time:

                    unlock_time = (

                        user.lock_time +

                        timedelta(minutes=15)

                    )

                    if ist_now() >= unlock_time:

                        user.account_locked = False

                        user.failed_attempts = 0

                        user.lock_time = None

                        db.session.commit()

                    else:

                        remaining = (

                            unlock_time -

                            ist_now()

                        )

                        minutes_left = (

                            int(

                                remaining.total_seconds() // 60

                            ) + 1

                        )

                        return f"""

                        <h2 style='
                            color:red;
                            text-align:center;
                            margin-top:50px;
                        '>

                        Account Locked 🔒

                        <br><br>

                        Try again after
                        {minutes_left} minute(s)

                        </h2>

                        """

            # =========================
            # PASSWORD CHECK
            # =========================

            if check_password_hash(

                user.password,

                password

            ):

                user.failed_attempts = 0

                user.account_locked = False

                user.lock_time = None

                db.session.commit()

                # =========================
                # TWO STEP LOGIN
                # =========================

                if user.two_step_enabled:

                    otp = random.randint(
                        100000,
                        999999
                    )

                    session["login_otp"] = str(
                        otp
                    )

                    session["temp_user_id"] = (
                        user.id
                    )
                    

                    send_otp_email(user.email, otp)

                    return redirect(
                        "/verify_login_otp"
                    )

                # =========================
                # NORMAL LOGIN SUCCESS
                # =========================

                session["user_id"] = (
                    user.id
                )

                session["username"] = (
                    user.username
                )
                print("UTC :", datetime.utcnow())

                print("INDIA :", ist_now())
                history = LoginHistory(

                    user_id=user.id,

                    ip_address=request.remote_addr

                )

                db.session.add(history)

                db.session.commit()

                return redirect(
                    "/dashboard"
                )

            else:

                # =========================
                # WRONG PASSWORD
                # =========================

                user.failed_attempts += 1

                if user.failed_attempts >= 5:

                    activity = UserActivityLog(

                        username=user.username,

                        email=user.email,

                        action="ACCOUNT BLOCKED",

                        extra_info="Too many wrong password Attempts"
                    )

                    db.session.add(activity)

                    db.session.commit()
                    

                    user.account_locked = True

                    user.lock_time =ist_now()

                    db.session.commit()

                    return """

                    <h2 style='
                        color:red;
                        text-align:center;
                        margin-top:50px;
                    '>

                    Account Locked 🔒

                    <br><br>

                    Too many wrong attempts.

                    Try again after 15 minutes.

                    </h2>

                    """

                db.session.commit()

                remaining = (
                    5 - user.failed_attempts
                )

                return f"""

                <h2 style='
                    color:orange;
                    text-align:center;
                    margin-top:50px;
                '>

                Wrong Password ❌

                <br><br>

                Attempts Left:
                {remaining}

                </h2>

                """

        else:

            return """

            <h2 style='
                color:red;
                text-align:center;
                margin-top:50px;
            '>

            Invalid Username ❌

            </h2>

            """

    return render_template(
        "login.html"
    )

@app.route(
    "/verify_login_otp",
    methods=["GET", "POST"]
)
def verify_login_otp():

    if request.method == "POST":

        entered_otp = request.form.get(
            "otp"
        )

        real_otp = session.get(
            "login_otp"
        )

        if entered_otp == real_otp:

            user = User.query.get(
                session["temp_user_id"]
            )

            session["user_id"] = user.id
            session["username"] = user.username

            session.pop("login_otp", None)
            session.pop("temp_user_id", None)

            flash(
                "Login Successful ✅",
                "success"
            )

            return redirect("/dashboard")

        else:

            flash(
                "Wrong OTP ❌",
                "danger"
            )

    return render_template(
        "verify_login_otp.html"
    )

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        username = request.form.get(
            "username"
        )

        email = request.form.get(
            "email"
        )

        password = generate_password_hash(
            request.form.get("password")
        )

        budget = float(
            request.form.get("budget", 0)
        )

        income = float(
            request.form.get("income", 0)
        )

        security_question = request.form.get(
            "security_question"
        )

        security_answer = generate_password_hash(

            request.form.get(
                "security_answer"
            ).strip().lower()

        )

        # =========================
        # CHECK EXISTING USER
        # =========================

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:

            return """
            <h2 style='
                color:red;
                text-align:center;
                margin-top:50px;
            '>

            User already exists ❌

            <br><br>

            <a href='/signup'>

                Back

            </a>

            </h2>
            """

        # =========================
        # CREATE NORMAL USER
        # =========================

        new_user = User(

            username=username,

            email=email,

            password=password,

            budget=budget,

            income=income,

            security_question=
            security_question,

            security_answer=
            security_answer

        )

        db.session.add(new_user)

        activity = UserActivityLog(

            username=username,

            email=email,

            action="ACCOUNT CREATED",

            extra_info="New user account created"
        )

        db.session.add(activity)

        db.session.commit()

        return redirect("/")

    return render_template(
        "signup.html"
    )

@app.route("/upload_profile_pic",methods=["POST"])
@login_required
def upload_profile_pic():

    user = User.query.get(
        session["user_id"]
    )

    file = request.files.get(
        "profile_pic"
    )

    if file and file.filename != "":

        filename = secure_filename(
            file.filename
        )

        file_path = os.path.join(
            "static/profile_pics",
            filename
        )

        file.save(file_path)

        if (
            user.profile_pic
            and user.profile_pic != "default.png"
        ):

            old_path = os.path.join(
                "static/profile_pics",
                user.profile_pic
            )

            if os.path.exists(old_path):

                os.remove(old_path)

        user.profile_pic = filename

        db.session.commit()

        flash(
            "Profile picture updated ✅",
            "success"
        )

    return redirect("/dashboard")

@app.route("/delete_profile_pic")
@login_required
def delete_profile_pic():

    user = User.query.get(
        session["user_id"]
    )

    user.profile_pic = "default.png"

    db.session.commit()

    flash(
        "Profile picture removed 🗑️",
        "warning"
    )

    return redirect("/dashboard")

@app.route(
    "/recover_by_security/<int:user_id>",
    methods=["POST"]
)
def recover_by_security(user_id):

    user = User.query.get(user_id)

    entered_answer = request.form.get(
        "security_answer"
    ).strip().lower()

    if check_password_hash(

        user.security_answer,

        entered_answer

    ):

        session["reset_user_id"] = user.id

        return redirect("/reset_password")

    else:

        flash("Wrong Security Answer")

        return redirect("/forgot_password")

@app.route(
    "/recover_by_email",
    methods=["GET", "POST"]
)
def recover_by_email():

    error = None

    success = None

    if request.method == "POST":

        # STEP 1

        if "step" not in request.form:

            email = request.form.get(
                "email"
            )

            user = User.query.filter_by(
                email=email
            ).first()

            if user:

                current_time = time.time()

                last_otp_time = session.get(
                    "otp_time"
                )

                if last_otp_time:

                    remaining = max(0, 60 - int(current_time - last_otp_time))
                    if remaining > 0:

                        error = (
                            f"Wait {remaining} seconds before requesting another OTP"
                        )

                        return render_template(

                            "recover_by_email.html",

                            error=error
                        )

                otp = str(
                    random.randint(100000, 999999)
                )

                session["otp"] = otp

                session["reset_email"] = email

                session["otp_time"] = current_time
                send_otp_email(user.email, otp)
                return render_template(

                    "recover_by_email.html",

                    step=2
                )

            else:

                error = "Email not found"

        # STEP 2

        else:

            otp = request.form.get("otp")

            new_password = request.form.get(
                "new_password"
            )

            saved_otp = session.get("otp")

            otp_time = session.get("otp_time")

            current_time = time.time()

            if not otp_time:
                error = "OTP session expired"

            elif current_time - otp_time > 600:
                error = "OTP Expired"

            elif otp == saved_otp:

                email = session.get(
                    "reset_email"
                )

                user = User.query.filter_by(
                    email=email
                ).first()

                user.password = generate_password_hash(new_password)

                activity = UserActivityLog(

                    username=user.username,

                    email=user.email,

                    action="PASSWORD RESET",

                    extra_info="User reset account password"
                )

                db.session.add(activity)
                
                db.session.commit()

                session.pop("otp", None)

                session.pop(
                    "reset_email",
                    None
                )

                success = (
                    "Password Reset Successful"
                )

                

            else:

                error = "Invalid OTP"

    return render_template(

        "recover_by_email.html",

        error=error,

        success=success
    )

@app.route("/current_balance")
def current_balance():

    if "user_id" not in session:
        return redirect("/")

    user = User.query.get(
        session["user_id"]
    )

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    total_expense = 0

    total_expense = sum(exp.amount for exp in expenses)

    balance = user.income - total_expense

    return render_template(

        "current_balance.html",

        balance=balance
    )

@app.route("/dashboard")
@login_required
def dashboard():

    user = User.query.get(
    session["user_id"]
)

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    total_expense = 0

    for expense in expenses:

        total_expense += expense.amount
    remaining_budget = user.budget - total_expense
    current_balance = user.income - total_expense

    budget = Budget.query.filter_by(
    user_id=session["user_id"]
    ).first()

    if budget:

        total_balance = (budget.balance - total_expense)
        monthly_budget = (budget.monthly_budget)
    
    else:

        total_balance = 0
        monthly_budget = 0

    total_savings = total_balance

    categories = [
    expense.category for expense in expenses
    ]

    amounts = [
        expense.amount for expense in expenses
    ]

    return render_template(
        "dashboard.html",
        user=user,
        expenses=expenses,
        total_expense=total_expense,
        total_balance=total_balance,
        total_savings=total_savings,
        username=session["username"],
        categories=categories,
        amounts=amounts,
        balance=current_balance,
        budget=remaining_budget
    )


@app.route("/account_details")
@login_required
def account_details():

    user = User.query.get(session["user_id"])

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    total_spending = sum(
        expense.amount for expense in expenses
    )

    current_balance = user.income - total_spending

    login_history = LoginHistory.query.filter_by(
        user_id=user.id
    ).order_by(
        LoginHistory.login_time.desc()
    ).all()

    return render_template(
        "account_details.html",
        user=user,
        current_balance=current_balance,
        login_history=login_history
    )

@app.route("/add_expense", methods=["GET", "POST"])
@login_required
def add_expense():

    if request.method == "POST":

        category = request.form["category"]

        description = request.form["description"]

        amount_str = request.form.get("amount")

        try:
            amount = float(amount_str)
        except:
            flash("Invalid amount")
            return redirect("/add_expense")

        expense_date = datetime.strptime(
            request.form["date"],
            "%Y-%m-%d"
        ).date()

        uploaded_files = request.files.getlist(
            "images"
        )

        image_list = []

        for file in uploaded_files:

            if file and allowed_file(file.filename):

                filename = (
                    str(uuid.uuid4())
                    + "_"
                    + secure_filename(file.filename)
                )

                file.save(
                    os.path.join(
                        app.config["UPLOAD_FOLDER"],
                        filename
                    )
                )

                image_list.append(filename)

        expense = Expense(

            category=category,

            description=description,

            amount=amount,

            date=expense_date,

            image=image_list[0]
            if image_list else None,

            images=json.dumps(
                image_list
            ),

            user_id=session["user_id"]
        )

        db.session.add(expense)

        db.session.commit()

        flash(
            "Expense Added Successfully!"
        )

        return redirect("/dashboard")

    return render_template(
        "add_expense.html"
    )

@app.route("/logout")
def logout():

    session.clear()

    return redirect("/")

@app.route("/expense_management")
@login_required
def expense_management():

    return render_template(
        "expense_management.html"
    )

@app.route("/edit_expense_list")
@login_required
def edit_expense_list():

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(
        "edit_expense_list.html",
        expenses=expenses
    )

@app.route("/edit_expense/<int:id>", methods=["GET", "POST"])
@login_required
def edit_expense(id):

    expense = Expense.query.get_or_404(id)

    if expense.user_id != session["user_id"]:
        return redirect("/dashboard")

    # Load existing images safely
    existing_images = []
    if expense.images:
        try:
            existing_images = json.loads(expense.images)
        except:
            existing_images = []

    if request.method == "POST":

        expense.category = request.form["category"]
        expense.description = request.form["description"]
        expense.amount = float(request.form["amount"])
        expense.date = datetime.strptime(
            request.form["date"], "%Y-%m-%d"
        ).date()

        # REMOVE SELECTED IMAGES
        remove_images = request.form.getlist("remove_images")

        for img in remove_images:
            if img in existing_images:
                existing_images.remove(img)

                img_path = os.path.join(
                    app.config["UPLOAD_FOLDER"], img
                )

                if os.path.exists(img_path):
                    os.remove(img_path)

        # ADD NEW IMAGES
        new_files = request.files.getlist("new_images")

        for file in new_files:
            if file and allowed_file(file.filename):
                filename = str(uuid.uuid4()) + "_" + secure_filename(file.filename)

                file.save(
                    os.path.join(app.config["UPLOAD_FOLDER"], filename)
                )

                existing_images.append(filename)

        # ✅ IMPORTANT FIX
        expense.images = json.dumps(existing_images)

        # optional: keep first image for preview
        expense.image = existing_images[0] if existing_images else None

        db.session.commit()

        flash("Expense Updated Successfully!")
        return redirect("/edit_expense_list")

    return render_template(
        "edit_expense.html",
        expense=expense,
        image_list=existing_images
    )

@app.route("/delete_expense_list")
@login_required
def delete_expense_list():

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(
        "delete_expense_list.html",
        expenses=expenses
    )

@app.route("/delete_expense/<int:id>")
@login_required
def delete_expense(id):

    expense = Expense.query.filter_by(
        id=id,
        user_id=session["user_id"]
    ).first()

    if not expense:
        return "Expense not found"

    # delete all images properly
    if expense.images:
        try:
            image_list = json.loads(expense.images)

            for img in image_list:
                img_path = os.path.join(app.config["UPLOAD_FOLDER"], img)

                if os.path.exists(img_path):
                    os.remove(img_path)

        except Exception as e:
            print("Image delete error:", e)

    db.session.delete(expense)
    db.session.commit()

    return redirect("/delete_expense_list")

@app.route("/analytics")
@login_required
def analytics():

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    category_totals = {}

    for expense in expenses:

        if expense.category in category_totals:

            category_totals[
                expense.category
            ] += expense.amount

        else:

            category_totals[
                expense.category
            ] = expense.amount

    labels = list(category_totals.keys())

    amounts = list(category_totals.values())

    plt.figure(figsize=(8, 8))

    colors = ["#1f77b4",
              "#d62728",
              "#ff7f0e",
              "#2ca02c",
              "#4a90e2",
              "#50e3c2",
              "#f5a623",
              "#e2849e",
              "#2b5c8f",
              "#4682b4",
              "#00a896",
              "#028090",
              "#ff007f",
              "#00f5ff",
              "#7fff00",
              "#e066ff",
              "#ff4500",
              "#ff8c00",
              "#ffd700",
              "#ff1493",
              "#00bfff",
              "#00fa9a",
              "#00ffff",
              "#1e90ff",
              "#ff3366",
              "#33ccff",
              "#33cc66",
              "#ffcc00"]

    plt.pie(

        amounts,

        labels=labels,

        autopct='%1.1f%%',

        colors=colors
    )

    plt.title("Expense Distribution")

    chart_path = os.path.join(

        "static",

        chart_path = f"expense_charts_{session['user_id']}_{time.time()}.png"
        )

    plt.savefig(chart_path)

    plt.clf()

    plt.close()

    return render_template(
        "analytics.html", chart_url=chart_path
    )

@app.template_filter("from_json")
def from_json(value):

    try:
        return json.loads(value)
    except:
        return []

@app.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "POST":

        username = request.form.get("username")

        email = request.form.get("email")

        user = User.query.filter_by(

            username=username,

            email=email

        ).first()

        if not user:

            flash("Invalid Username or Email")

            return redirect("/forgot_password")

        otp = random.randint(100000, 999999)

        session["reset_otp"] = str(otp)

        session["reset_user_id"] = user.id

        session["otp_time"] = time.time()

        sent = send_otp_email(user.email, otp)

        if sent:
            flash("OTP sent successfully")
            return redirect("/verify_reset_otp")
        else:
            flash("Failed to send OTP. Please try again.")
            return redirect("/forgot_password")

    return render_template("forgot_password.html")


@app.route("/verify_reset_otp", methods=["GET", "POST"])
def verify_reset_otp():

    if request.method == "POST":

        entered_otp = request.form.get("otp")
        real_otp = session.get("reset_otp")

        if time.time() - session.get("otp_time", 0) > 600:

            session.pop("reset_otp", None)
            session.pop("otp_time", None)
            session.pop("reset_user_id", None)

            flash("OTP has expired. Please request a new OTP.")
            return redirect("/forgot_password")

        if entered_otp == real_otp:

            session.pop("reset_otp", None)
            session.pop("otp_time", None)

            return redirect("/reset_password")

        else:

            flash("Wrong OTP")

    return render_template("verify_reset_otp.html")

@app.route(
    "/reset_password",
    methods=["GET", "POST"]
)
def reset_password():

    if "reset_user_id" not in session:

        return redirect("/forgot_password")

    user = User.query.get(

        session["reset_user_id"]

    )

    if request.method == "POST":

        new_password = request.form.get(
            "new_password"
        )

        confirm_password = request.form.get(
            "confirm_password"
        )

        if new_password != confirm_password:

            flash("Passwords do not match")

            return redirect("/reset_password")

        user.password = generate_password_hash(
            new_password
        )

        db.session.commit()

        session.pop("reset_user_id", None)

        flash("Password Reset Successful")

        activity = UserActivityLog(

        username=user.username,

        email=user.email,

        action="PASSWORD RESET",

        extra_info="User reset accont password"
    )

        db.session.add(activity)

        db.session.commit()

        return redirect("/")

    return render_template(
        "reset_password.html"
    )

@app.route(
    "/security_question_search",
    methods=["POST"]
)
def security_question_search():

    username = request.form.get("username")

    user = User.query.filter_by(

        username=username

    ).first()

    if not user:

        flash("Username not found")

        return redirect("/forgot_password")

    return render_template(

        "recover_by_security.html",

        user=user

    )

@app.route(
    "/forgot_username",
    methods=["GET", "POST"]
)
def forgot_username():

    usernames = []

    if request.method == "POST":

        email = request.form.get("email")

        users = User.query.filter_by(
            email=email
        ).all()

        for user in users:

            usernames.append(
                user.username
            )

    return render_template(

        "forgot_username.html",

        usernames=usernames
    )

@app.route("/view_analyze")
def view_analyze():

    if "user_id" not in session:
        return redirect("/")

    return render_template(
        "view_analyze.html"
    )

@app.route("/analytics_menu")
def analytics_menu():

    if "user_id" not in session:
        return redirect("/")

    return render_template(
        "analytics_menu.html"
    )

@app.route("/expense_charts")
def expense_charts():

    if "user_id" not in session:
        return redirect("/")

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    category_totals = {}

    for expense in expenses:

        if expense.category in category_totals:

            category_totals[
                expense.category
            ] += expense.amount

        else:

            category_totals[
                expense.category
            ] = expense.amount

    categories = list(
        category_totals.keys()
    )

    amounts = list(
        category_totals.values()
    )

    return render_template(

        "expense_charts.html",

        categories=categories,

        amounts=amounts
    )

@app.route("/expense_statistics")
def expense_statistics():

    if "user_id" not in session:
        return redirect("/")

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    total_expense = 0

    highest = 0

    lowest = 0

    average = 0

    total_categories = 0

    categories = set()

    if expenses:

        amounts = []

        for expense in expenses:

            total_expense += expense.amount

            amounts.append(
                expense.amount
            )

            categories.add(
                expense.category
            )

        highest = max(amounts)

        lowest = min(amounts)

        average = round(
            total_expense / len(expenses),
            2
        )

        total_categories = len(
            categories
        )

    return render_template(

        "expense_statistics.html",

        total_expense=total_expense,

        highest=highest,

        lowest=lowest,

        average=average,

        total_categories=total_categories,

        total_transactions=len(expenses)
    )

@app.route("/expense_predictions")
def expense_predictions():

    if "user_id" not in session:
        return redirect("/")

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    total_expense = 0

    total_transactions = len(
        expenses
    )

    prediction = 0

    trend = "Stable"

    for expense in expenses:

        total_expense += expense.amount

    if total_transactions > 0:

        average = (
            total_expense / total_transactions
        )

        prediction = round(
            average * 30,
            2
        )

        if average > 1000:

            trend = "High Spending Trend"

        elif average > 500:

            trend = "Moderate Spending Trend"

        else:

            trend = "Low Spending Trend"

    else:

        average = 0

    return render_template(

        "expense_predictions.html",

        average=round(average, 2),

        prediction=prediction,

        trend=trend,

        total_expense=total_expense
    )

@app.route("/ai_insights")
def ai_insights():

    if "user_id" not in session:
        return redirect("/")

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    total_expense = 0

    category_totals = {}

    insight = ""

    advice = ""

    for expense in expenses:

        total_expense += expense.amount

        if expense.category in category_totals:

            category_totals[
                expense.category
            ] += expense.amount

        else:

            category_totals[
                expense.category
            ] = expense.amount

    highest_category = "None"

    highest_amount = 0

    if category_totals:

        highest_category = max(

            category_totals,

            key=category_totals.get
        )

        highest_amount = category_totals[
            highest_category
        ]

    if total_expense > 50000:

        insight = (
            "Your spending is very high this month."
        )

        advice = (
            "Try reducing unnecessary expenses and increase savings."
        )

    elif total_expense > 20000:

        insight = (
            "Your spending is moderate."
        )

        advice = (
            "Maintain a balanced budget for better savings."
        )

    else:

        insight = (
            "Your spending is under control."
        )

        advice = (
            "Great job! Keep managing your finances wisely."
        )

    return render_template(

        "ai_insights.html",

        total_expense=total_expense,

        highest_category=highest_category,

        highest_amount=highest_amount,

        insight=insight,

        advice=advice
    )

@app.route("/budget_warnings")
def budget_warnings():

    if "user_id" not in session:
        return redirect("/")

    user = User.query.get(
        session["user_id"]
    )

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    total_expense = 0

    for expense in expenses:

        total_expense += expense.amount

    remaining = user.budget - total_expense

    status = ""

    warning = ""

    if total_expense > user.budget:

        status = "Budget Exceeded"

        warning = (
            "Warning! You have crossed your monthly budget."
        )

    elif remaining < user.budget * 0.2:

        status = "Budget Near Limit"

        warning = (
            "Careful! Your remaining budget is very low."
        )

    else:

        status = "Budget Safe"

        warning = (
            "Great! Your spending is under control."
        )

    return render_template(

        "budget_warnings.html",

        budget=user.budget,

        total_expense=total_expense,

        remaining=remaining,

        status=status,

        warning=warning
    )

@app.route("/all_expenses")
def all_expenses():

    if "user_id" not in session:
        return redirect("/")

    expenses = Expense.query.filter_by(
        user_id=session.get("user_id")
    ).all()

    return render_template(
        "all_expenses.html",
        expenses=expenses
    )

@app.route("/category_spending")
def category_spending():

    if "user_id" not in session:
        return redirect("/")

    expenses = Expense.query.filter_by(
        user_id=session.get("user_id")
    ).all()

    category_totals = {}

    for expense in expenses:

        if expense.category in category_totals:

            category_totals[
                expense.category
            ] += expense.amount

        else:

            category_totals[
                expense.category
            ] = expense.amount

    return render_template(

        "category_spending.html",

        category_totals=category_totals
    )
@app.route("/filter_expenses")
def filter_expenses():

    if "user_id" not in session:
        return redirect("/")

    expenses = Expense.query.filter_by(
        user_id=session.get("user_id")
    ).all()

    return render_template(
        "filter_expenses.html",
        expenses=expenses
    )

@app.route("/sort_expenses")
def sort_expenses():

    if "user_id" not in session:
        return redirect("/")

    highest = Expense.query.filter_by(
        user_id=session.get("user_id")
    ).order_by(
        Expense.amount.desc()
    ).all()

    lowest = Expense.query.filter_by(
        user_id=session.get("user_id")
    ).order_by(
        Expense.amount.asc()
    ).all()

    return render_template(

        "sort_expenses.html",

        highest=highest,

        lowest=lowest
    )

@app.route("/monthly_report")
@login_required
def monthly_report():

    user_id = session["user_id"]

    expenses = Expense.query.filter_by(
        user_id=user_id
    ).all()

    current_year = ist_now().year
    current_month = ist_now().month

    monthly_expenses = []

    total_monthly = 0

    for expense in expenses:

        if (
            expense.date.year == current_year
            and
            expense.date.month == current_month
        ):

            monthly_expenses.append(expense)

            total_monthly += float(expense.amount)

    print(total_monthly)

    return render_template(
        "monthly_report.html",
        expenses=monthly_expenses,
        total_monthly=total_monthly
    )

@app.route("/expense_gallery")
def expense_gallery():

    if "user_id" not in session:
        return redirect("/")

    expenses = Expense.query.filter_by(
        user_id=session.get("user_id")
    ).all()

    return render_template(

        "expense_gallery.html",

        expenses=expenses
    )

@app.route("/money_budget")
def money_budget():

    return render_template(
        "money_budget.html"
    )

@app.route("/total_spending")
@login_required
def total_spending():

    user_id = session["user_id"]

    expenses = Expense.query.filter_by(
        user_id=user_id
    ).all()

    total = 0

    for expense in expenses:

        total += float(expense.amount)

    return render_template(
        "total_spending.html",
        total=total,
        expenses=expenses
    )

@app.route("/add_income", methods=["GET", "POST"])
def add_income():

    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":

        income = float(
            request.form["income"]
        )

        user = User.query.get(
            session["user_id"]
        )

        user.income += income

        db.session.commit()

        return redirect("/dashboard")

    return render_template(
        "add_income.html"
    )

@app.route(
    "/edit_budget",
    methods=["GET", "POST"]
)
def edit_budget():

    if "user_id" not in session:
        return redirect("/")

    user = User.query.get(
        session["user_id"]
    )

    if request.method == "POST":

        user.budget = float(
            request.form["budget"]
        )

        db.session.commit()

        return redirect(
            "/money_budget"
        )

    return render_template(
        "edit_budget.html"
    )

class SavingsGoal(db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id")
    )

    goal_name = db.Column(
        db.String(100)
    )

    goal_amount = db.Column(
        db.Float
    )

    saved_amount = db.Column(
        db.Float,
        default=0
    )

@app.route("/savings_goal", methods=["GET", "POST"])
def savings_goal():

    if "user_id" not in session:
        return redirect("/")

    if request.method == "POST":

        goal_name = request.form["goal_name"]

        goal_amount = float(
            request.form["goal_amount"]
        )

        saved_amount = float(
            request.form.get(
                "saved_amount",
                0
            )
        )

        goal = SavingsGoal(

            user_id=session["user_id"],

            goal_name=goal_name,

            goal_amount=goal_amount,

            saved_amount=saved_amount
        )

        db.session.add(goal)

        db.session.commit()

        return redirect("/savings_goal")

    goals = SavingsGoal.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(

        "savings_goal.html",

        goals=goals
    )

@app.route("/edit_goal/<int:id>", methods=["GET", "POST"])
@login_required
def edit_goal(id):

    goal = SavingsGoal.query.filter_by(
    id=id,
    user_id=session["user_id"]
    ).first()

    if request.method == "POST":

        goal.goal_name = request.form["goal_name"]

        goal.goal_amount = float(
            request.form["goal_amount"]
        )

        goal.saved_amount = float(
            request.form.get(
                "saved_amount",
                0
            )
        )

        db.session.commit()

        return redirect("/savings_goal")

    return render_template(
        "edit_goal.html",
        goal=goal
    )

@app.route("/delete_goal/<int:id>")
@login_required
def delete_goal(id):

    goal = SavingsGoal.query.filter_by(
    id=id,
    user_id=session["user_id"]
    ).first()

    if not goal:
        return "Goal not found"

    db.session.delete(goal)

    db.session.commit()

    return redirect("/savings_goal")

@app.route(
    "/split_expenses",
    methods=["GET", "POST"]
)
def split_expenses():

    result = None

    if request.method == "POST":

        amount = float(
            request.form["amount"]
        )

        people = int(
            request.form["people"]
        )

        if people == 0:
            result = "Invalid input"
        else:
            result = amount / people

    return render_template(

        "split_expenses.html",

        result=result
    )

@app.route("/export_center")
@login_required
def export_center():

    return render_template(
        "export_center.html"
    )

@app.route(
    "/export_csv",
    methods=["GET", "POST"]
)
@login_required
def export_csv():

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    include_description = request.form.get(
        "include_description"
    )

    file_name = f"""
expenses_{session['user_id']}.csv
""".strip()

    with open(

        file_name,

        mode="w",

        newline="",

        encoding="utf-8"

    ) as file:

        writer = csv.writer(file)

        headers = [

            "Category",
            "Amount",
            "Date"

        ]

        if include_description:

            headers.append(
                "Description"
            )

        writer.writerow(headers)

        for expense in expenses:

            row = [

                expense.category,
                expense.amount,
                expense.date

            ]

            if include_description:

                row.append(
                    expense.description
                )

            writer.writerow(row)

    return send_file(

        file_name,

        as_attachment=True

    )

@app.route("/export_pdf_menu")
@login_required
def export_pdf_menu():

    return render_template(
        "export_pdf_menu.html"
    )

@app.route("/export_all_pdf")
@login_required
def export_all_pdf():

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font(
        "Arial",
        "B",
        16
    )

    pdf.cell(
        200,
        10,
        txt="Expense Report",
        ln=True,
        align="C"
    )

    pdf.ln(10)

    pdf.set_font(
        "Arial",
        size=12
    )

    total = 0

    for expense in expenses:

        total += expense.amount

        line = (
            f"{expense.category} | "
            f"Rs.{expense.amount} | "
            f"{expense.date}"
        )

        pdf.multi_cell(
            0,
            10,
            line
        )

    pdf.ln(10)

    pdf.set_font(
        "Arial",
        "B",
        14
    )

    pdf.cell(
        200,
        10,
        txt=f"Total Spending: Rs.{total}",
        ln=True
    )

    file_name = f"expense_report_{session['user_id']}.pdf"
    pdf.output(file_name)

    response = send_file(
       file_name, as_attachment=True
    )
    os.remove(file_name)
    return response


@app.route("/export_monthly_pdf")
@login_required
def export_monthly_pdf():

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font(
        "Arial",
        "B",
        16
    )

    pdf.cell(
        200,
        10,
        txt="Monthly Expense Report",
        ln=True,
        align="C"
    )

    total = 0

    for expense in expenses:

        total += expense.amount

        pdf.multi_cell(

            0,

            10,

            f"{expense.category} | Rs.{expense.amount}"

        )

    pdf.ln(10)

    pdf.cell(

        200,

        10,

        txt=f"Monthly Total: Rs.{total}",

        ln=True

    )

    file_name = f"monthly_{session['user_id']}_{int(time.time())}.pdf"
    pdf.output(file_name)
    response = send_file(file_name, as_attachment=True
    )

    os.remove(file_name)
    return response


@app.route("/export_date_range_pdf")
@login_required
def export_date_range_pdf():

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(

        "date_range_pdf.html",

        expenses=expenses
    )

@app.route("/generate_date_pdf",methods=["POST"])
@login_required
def generate_date_pdf():

    if request.method != "POST":
        return redirect("/export_date_range_pdf")

    start = request.form.get("start")
    end = request.form.get("end")

    start = datetime.strptime(start, "%Y-%m-%d").date()
    end = datetime.strptime(end, "%Y-%m-%d").date()

    expenses = Expense.query.filter(

        Expense.user_id == session["user_id"],

        Expense.date >= start,

        Expense.date <= end

    ).all()

    pdf = FPDF()

    pdf.add_page()

    pdf.set_font(
        "Arial",
        size=12
    )

    total = 0

    for expense in expenses:

        total += expense.amount

        pdf.multi_cell(

            0,

            10,

            f"{expense.category} | Rs.{expense.amount}"

        )

    pdf.ln(10)

    pdf.cell(

        200,

        10,

        txt=f"Total: Rs.{total}",

        ln=True

    )

    pdf.output(
        "date_range_report.pdf"
    )
    file_name = "date_range_report.pdf"

    pdf.output(file_name)
    response = send_file(

        file_name, as_attachment=True
    )
    os.remove(file_name)
    return response


@app.route(
    "/export_excel",
    methods=["GET", "POST"]
)
@login_required
def export_excel():

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    include_description = request.form.get(
        "include_description"
    )

    data = []

    for expense in expenses:

        row = {

            "Category": expense.category,
            "Amount": expense.amount,
            "Date": expense.date

        }

        if include_description:

            row["Description"] = (
                expense.description
            )

        data.append(row)

    df = pd.DataFrame(data)

    file_name = f"""
expenses_{session['user_id']}.xlsx
""".strip()

    df.to_excel(

        file_name,

        index=False

    )

    return send_file(

        file_name,

        as_attachment=True

    )

@app.route("/print_statement")
def print_statement():

    if "user_id" not in session:
        return redirect("/")

    expenses = Expense.query.filter_by(
        user_id=session["user_id"]
    ).all()

    return render_template(

        "print_statement.html",

        expenses=expenses
    )

@app.route("/advanced_export_pdf", methods=["GET", "POST"])
@login_required
def advanced_export_pdf():

    user_id = session["user_id"]

    # =========================================
    # FILTERS
    # =========================================

    export_type = request.form.get(
        "export_type",
        "all"
    )

    include_images = request.form.get(
        "include_images"
    )

    include_description = request.form.get(
        "include_description"
    )

    include_charts = request.form.get(
    "include_charts"
    )

    current_month = ist_now().strftime(
        "%Y-%m"
    )

    # =========================================
    # GET EXPENSES
    # =========================================

    all_expenses = Expense.query.filter_by(
        user_id=user_id
    ).all()

    expenses = []

    for expense in all_expenses:

        expense_date = str(expense.date)

        # ALL EXPENSES
        if export_type == "all":

            expenses.append(expense)

        # MONTHLY EXPENSES
        elif export_type == "monthly":

            if expense_date.startswith(current_month):

                expenses.append(expense)

        # DATE RANGE
        elif export_type == "date_range":

            start_date = request.form.get(
                "start_date"
            )

            end_date = request.form.get(
                "end_date"
            )

            if start_date <= expense_date <= end_date:

                expenses.append(expense)

    # =========================================
    # EXPORT FOLDER
    # =========================================

    export_folder = os.path.join(
        "static",
        "exports"
    )

    os.makedirs(
        export_folder,
        exist_ok=True
    )

    # =========================================
    # CREATE CHART
    # =========================================

    category_data = {}

    for expense in expenses:

        if expense.category in category_data:

            category_data[
                expense.category
            ] += expense.amount

        else:

            category_data[
                expense.category
            ] = expense.amount

    categories = list(
        category_data.keys()
    )

    amounts = list(
        category_data.values()
    )

    chart_path = os.path.join(

        export_folder,

        f"chart_{user_id}.png"

    )

    if include_charts and len(categories) > 0:
        plt.figure(figsize=(7, 7))

        plt.pie(

            amounts,

            labels=categories,

            autopct="%1.1f%%"

        )

        plt.title(
            "Expense Distribution"
        )

        plt.savefig(chart_path)

        plt.clf()

        plt.close()

    # =========================================
    # PDF START
    # =========================================

    pdf = FPDF()

    pdf.set_auto_page_break(
        auto=True,
        margin=15
    )

    pdf.add_page()

    # =========================================
    # TITLE
    # =========================================

    pdf.set_font(
        "Arial",
        "B",
        24
    )

    pdf.cell(
        190,
        15,
        "Expense Tracker Report",
        ln=True,
        align="C"
    )

    pdf.ln(10)

    # =========================================
    # REPORT TYPE
    # =========================================

    pdf.set_font(
        "Arial",
        "B",
        13
    )

    report_name = "All Expenses Report"

    if export_type == "monthly":

        report_name = "Monthly Expense Report"

    elif export_type == "date_range":

        report_name = "Date Range Expense Report"

    pdf.cell(
        190,
        10,
        report_name,
        ln=True
    )

    pdf.ln(5)

    # =========================================
    # STATISTICS
    # =========================================

    total_spending = sum(
        expense.amount for expense in expenses
    )

    total_expenses = len(expenses)

    average_expense = 0

    if total_expenses > 0:

        average_expense = round(

            total_spending / total_expenses,

            2

        )

    pdf.set_font(
        "Arial",
        "B",
        14
    )

    pdf.cell(
        190,
        10,
        "Statistics",
        ln=True
    )

    pdf.set_font(
        "Arial",
        "",
        12
    )

    pdf.cell(
        190,
        8,
        f"Total Expenses : {total_expenses}",
        ln=True
    )

    pdf.cell(
        190,
        8,
        f"Total Spending : Rs. {total_spending}",
        ln=True
    )

    pdf.cell(
        190,
        8,
        f"Average Expense : Rs. {average_expense}",
        ln=True
    )

    pdf.ln(10)

    # =========================================
    # CHART
    # =========================================

    if os.path.exists(chart_path):

        pdf.set_font(
            "Arial",
            "B",
            14
        )

        pdf.cell(
            190,
            10,
            "Expense Analytics Chart",
            ln=True
        )

        pdf.image(
            chart_path,
            x=35,
            w=140
        )

        pdf.ln(90)

    # =========================================
    # TABLE SECTION
    # =========================================

    pdf.set_font(
        "Arial",
        "B",
        14
    )

    pdf.cell(
        190,
        10,
        "Expense Details",
        ln=True
    )

    # =========================================
    # TABLE HEADERS
    # =========================================

    pdf.set_font(
        "Arial",
        "B",
        11
    )

    pdf.cell(
        50,
        10,
        "Category",
        1
    )

    pdf.cell(
        35,
        10,
        "Amount",
        1
    )

    pdf.cell(
        45,
        10,
        "Date",
        1
    )

    if include_description:

        pdf.cell(
            60,
            10,
            "Description",
            1
        )

    pdf.ln()

    # =========================================
    # TABLE DATA
    # =========================================

    pdf.set_font(
        "Arial",
        "",
        10
    )

    if len(expenses) == 0:

        pdf.cell(
            190,
            10,
            "No Expenses Found",
            1,
            ln=True
        )

    else:

        for expense in expenses:

            pdf.cell(
                50,
                10,
                str(expense.category),
                1
            )

            pdf.cell(
                35,
                10,
                f"Rs. {expense.amount}",
                1
            )

            pdf.cell(
                45,
                10,
                str(expense.date),
                1
            )

            # DESCRIPTION
            if include_description:

                description_text = ""

                if hasattr(expense, "description"):

                    if expense.description:

                        description_text = str(
                            expense.description
                        )[:28]

                pdf.cell(
                    60,
                    10,
                    description_text,
                    1
                )

            pdf.ln()

            # =========================================
            # IMAGE SECTION
            # =========================================
            if include_images:

                if expense.images:

                    try:

                        import json

                        image_list = json.loads(expense.images)

                    except:

                        image_list = [expense.images]

                    for image_name in image_list:

                        image_path = os.path.join(
                            "static",
                            "uploads",
                            image_name
                        )

                        if os.path.exists(image_path):

                            try:

                                pdf.cell(
                                    190,
                                    10,
                                    "Attached Receipt/Image",
                                    ln=True
                                )

                                pdf.image(
                                    image_path,
                                    w=120
                                )

                                pdf.ln(85)

                            except Exception as e:

                                print("PDF Image Error:", e)
    # =========================================
    # FOOTER
    # =========================================

    pdf.ln(10)

    pdf.set_font(
        "Arial",
        "I",
        10
    )

    pdf.cell(
        190,
        10,
        f"Generated On : {ist_now()}",
        ln=True,
        align="C"
    )

    # =========================================
    # SAVE PDF
    # =========================================

    pdf_path = os.path.join(

        export_folder,

        f"expense_report_{user_id}_{int(time.time())}.pdf"

    )

    pdf.output(pdf_path)

    return send_file(

        pdf_path,

        as_attachment=True

    )

@app.route("/settings_storage")
@login_required
def settings_storage():

    user = User.query.get(
        session["user_id"]
    )

    expenses = Expense.query.filter_by(
        user_id=user.id
    ).all()

    total_images = 0

    total_size = 0

    for expense in expenses:

        image_list = []

        # NEW MULTIPLE IMAGES
        if expense.images:

            try:

                image_list = json.loads(
                    expense.images
                )

            except:

                image_list = []

        # OLD SINGLE IMAGE SUPPORT
        elif expense.image:

            image_list = [expense.image]

        for img in image_list:

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                img
            )

            if os.path.exists(image_path):

                total_images += 1

                total_size += os.path.getsize(
                    image_path
                )

    storage_mb = round(
        total_size / (1024 * 1024),
        2
    )

    return render_template(

        "settings_storage.html",

        user=user,

        total_images=total_images,

        storage_mb=storage_mb
    )

@app.route(
    "/change_password",
    methods=["GET", "POST"]
)
@login_required
def change_password():

    user = User.query.get(
        session["user_id"]
    )

    if request.method == "POST":

        old_password = request.form.get(
            "old_password"
        )

        new_password = request.form.get(
            "new_password"
        )

        if check_password_hash(
            user.password,
            old_password
        ):

            user.password = generate_password_hash(
                new_password
            )

            db.session.commit()

            flash(
                "Password changed successfully ✅",
                "success"
            )

        else:

            flash(
                "Wrong old password ❌",
                "danger"
            )

        return redirect(
            "/change_password"
        )

    return render_template(
        "change_password.html"
    )

@app.route(
    "/change_email",
    methods=["GET", "POST"]
)
@login_required
def change_email():

    user = User.query.get(
        session["user_id"]
    )

    if request.method == "POST":

        new_email = request.form.get(
            "new_email"
        )

        user.email = new_email

        db.session.commit()

        flash(
            "Email updated successfully ✅",
            "success"
        )

        return redirect(
            "/change_email"
        )

    return render_template(
        "change_email.html"
    )

@app.route(
    "/change_security_question",
    methods=["GET", "POST"]
)
@login_required
def change_security_question():

    user = User.query.get(
        session["user_id"]
    )

    if request.method == "POST":

        question = request.form.get(
            "security_question"
        )

        answer = request.form.get(
            "security_answer"
        ).strip().lower()

        user.security_question = question

        user.security_answer = generate_password_hash(
            answer
        )

        db.session.commit()

        flash(
            "Security question updated ✅",
            "success"
        )

        return redirect(
            "/change_security_question"
        )

    return render_template(
        "change_security_question.html"
    )

@app.route("/toggle_2step")
@login_required
def toggle_2step():

    user = User.query.get(
        session["user_id"]
    )

    user.two_step_enabled = (
        not user.two_step_enabled
    )

    db.session.commit()

    if user.two_step_enabled:

        flash(
            "Two Step Verification Enabled Successfully ✅",
            "success"
        )

    else:

        flash(
            "Two Step Verification Disabled ❌",
            "danger"
        )

    return redirect(
        "/settings_storage"
    )

@app.route(
    "/change_currency",
    methods=["GET", "POST"]
)
@login_required
def change_currency():

    user = User.query.get(
        session["user_id"]
    )

    if request.method == "POST":

        currency = request.form.get(
            "currency"
        )

        user.currency = currency

        db.session.commit()

        flash(
            "Currency changed successfully 💱",
            "success"
        )

        return redirect(
            "/change_currency"
        )

    return render_template(
        "change_currency.html"
    )

@app.route("/backup_account")
@login_required
def backup_account():

    user = User.query.get(
        session["user_id"]
    )

    expenses = Expense.query.filter_by(
        user_id=user.id
    ).all()

    data = []

    for expense in expenses:

        data.append({

            "category": expense.category,

            "amount": expense.amount,

            "date": str(expense.date)

        })

    file_name = f"backup_user_{user.id}.json"

    with open(file_name, "w") as f:

        json.dump(data, f, indent=4)

    return send_file(
        file_name,
        as_attachment=True
    )

@app.route("/factory_reset")
@login_required
def factory_reset():

    user = User.query.get(
        session["user_id"]
    )

    user_id = session["user_id"]

    Expense.query.filter_by(
        user_id=user_id
    ).delete()

    SavingsGoal.query.filter_by(
        user_id=user_id
    ).delete()


    activity = UserActivityLog(

        username=user.username,

        email=user.email,

        action="ACCOUNT FACTORY RESET",

        extra_info="User performs factory reset operation"
    )

    db.session.add(activity)

    db.session.commit()

    flash(
        "Factory reset completed 🏭",
        "warning"
    )

    return redirect(
        "/settings_storage"
    )

@app.route("/factory_reset_confirm")
@login_required
def factory_reset_confirm():

    db.session.commit()

    return render_template(
        "factory_reset_confirm.html"
    )

@app.route("/delete_account")
@login_required
def delete_account():

    user = User.query.get(
        session["user_id"]
    )

    Expense.query.filter_by(
        user_id=user.id
    ).delete()

    SavingsGoal.query.filter_by(
        user_id=user.id
    ).delete()

    activity = UserActivityLog(

        username=user.username,

        email=user.email,

        action="ACCOUNT DELETED",

        extra_info="User deleted his/her account"
    )

    db.session.add(activity)

    db.session.commit()


    db.session.delete(user)

    db.session.commit()

    session.clear()

    return redirect("/")

@app.route("/admin_verify", methods=["GET", "POST"])
def admin_verify():

    if "admin_candidate" not in session:

        return redirect("/")

    if request.method == "POST":

        entered_password = request.form.get(
            "admin_panel_password"
        )

        actual_password = os.getenv(
            "ADMIN_PANEL_PASSWORD"
        )

        if entered_password == actual_password:

            session["admin_panel_access"] = True

            return redirect(
                "/admin_dashboard"
            )

        else:

            return """

            <h2 style='
                color:red;
                text-align:center;
                margin-top:50px;
            '>

            Wrong Admin Panel Password ❌

            </h2>

            """

    return render_template(
        "admin_verify.html"
    )

# =========================
# ADMIN PROFILE PICTURE UPLOAD
# =========================

@app.route("/upload_admin_profile", methods=["POST"])
@admin_required
def upload_admin_profile():

    file = request.files.get("profile_pic")

    if file and file.filename != "":

        filename = secure_filename(file.filename)

        save_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            filename
        )

        file.save(save_path)

        session["admin_profile_pic"] = filename

    return redirect("/admin_dashboard")


# =========================
# REMOVE ADMIN PROFILE PIC
# =========================

@app.route("/remove_admin_profile")
@admin_required
def remove_admin_profile():

    session.pop("admin_profile_pic", None)

    return redirect("/admin_dashboard")


# =========================
# ADMIN DASHBOARD
# =========================

@app.route("/admin_dashboard")
@admin_required
def admin_dashboard():

    total_users = User.query.count()

    total_expenses = Expense.query.count()

    total_images = 0

    all_expenses = Expense.query.all()

    for exp in all_expenses:

        if exp.images:

            try:

                image_list = json.loads(exp.images)

                total_images += len(image_list)

            except:

                pass

    admin_profile_pic = session.get(
        "admin_profile_pic"
    )

    return render_template(

        "admin_dashboard.html",

        total_users=total_users,

        total_expenses=total_expenses,

        total_images=total_images,

        admin_profile_pic=admin_profile_pic
    )

@app.route("/admin_users")
@admin_required
def admin_users():

    users = User.query.all()

    return render_template(

        "admin_users.html",

        users=users
    )

@app.route("/open_admin_panel", methods=["GET", "POST"])
def open_admin_panel():

    if "admin_candidate" not in session:
        return redirect("/")

    if request.method == "POST":

        entered_password = request.form.get(
            "admin_password"
        )

        real_password = os.getenv(
            "ADMIN_PANEL_PASSWORD"
        )

        if entered_password == real_password:

            session["admin_logged_in"] = True

            # ADMIN LOGIN HISTORY SAVE
            admin_login = LoginHistory(

                user_id = None,

                ip_address = request.remote_addr

            )

            db.session.add(admin_login)

            db.session.commit()

            return redirect("/admin_dashboard")

        else:

            return """
            <h2 style='color:red;text-align:center;margin-top:50px;'>
            Wrong Admin Password ❌
            </h2>
            """

    return render_template(
        "open_admin_panel.html"
    )

@app.route("/admin_logout")
def admin_logout():

    session.pop(
        "admin_access",
        None
    )

    session.pop(
        "admin_candidate",
        None
    )

    session.pop( "admin_logged_in", None )

    return redirect("/")

@app.route("/delete_account_confirm")
@login_required
def delete_account_confirm():

    return render_template(
        "delete_account_confirm.html"
    )

@app.route("/delete_any_user")
@admin_required
def delete_any_user():

    users = User.query.all()

    return render_template(
        "delete_any_user.html",
        users=users
    )


@app.route("/delete_user/<int:user_id>")
@admin_required
def delete_user(user_id):

    user = User.query.get(user_id)

    if user:

        Expense.query.filter_by(
            user_id=user.id
        ).delete()

        db.session.delete(user)

        db.session.commit()

    return redirect("/delete_any_user")

@app.route("/continue_as_user")
def continue_as_user():

    admin_username = os.getenv("ADMIN_USERNAME")

    user = User.query.filter_by(
        username=admin_username
    ).first()

    if not user:

        return redirect("/")

    session["user_id"] = user.id

    session["username"] = user.username

    return redirect("/dashboard")


# =========================
# STORAGE MANAGEMENT
# =========================

import os


def get_folder_size(folder_path):

    total_size = 0

    for dirpath, dirnames, filenames in os.walk(folder_path):

        for f in filenames:

            fp = os.path.join(dirpath, f)

            if os.path.exists(fp):

                total_size += os.path.getsize(fp)

    return total_size


def format_size(size):

    for unit in ["B", "KB", "MB", "GB"]:

        if size < 1024:

            return f"{size:.2f} {unit}"

        size /= 1024

    return f"{size:.2f} TB"


@app.route("/storage_management")
@admin_required
def storage_management():

    upload_size = get_folder_size(
        "static/uploads"
    )

    export_size = get_folder_size(
        "static/exports"
    )

    profile_size = get_folder_size(
        "static/profile_pics"
    )

    db_size = 0

    if os.path.exists("instance/expense_tracker.db"):

        db_size = os.path.getsize(
            "instance/expense_tracker.db"
        )

    total_storage = (
        upload_size +
        export_size +
        profile_size +
        db_size
    )

    users = User.query.all()

    user_storage_data = []

    for user in users:

        expenses = Expense.query.filter_by(
            user_id=user.id
        ).all()

        total_user_size = 0

        image_count = 0

        for expense in expenses:

            if expense.images:

                try:

                    image_list = json.loads(
                        expense.images
                    )

                    for image in image_list:

                        path = os.path.join(
                            "static/uploads",
                            image
                        )

                        if os.path.exists(path):

                            total_user_size += (
                                os.path.getsize(path)
                            )

                            image_count += 1

                except:

                    pass

        user_storage_data.append({

            "username": user.username,

            "storage": total_user_size,

            "formatted_storage":
                format_size(total_user_size),

            "image_count": image_count

        })

    largest_user = max(
        user_storage_data,
        key=lambda x: x["storage"],
        default=None
    )

    return render_template(

        "storage_management.html",

        total_storage=format_size(
            total_storage
        ),

        upload_size=format_size(
            upload_size
        ),

        export_size=format_size(
            export_size
        ),

        profile_size=format_size(
            profile_size
        ),

        db_size=format_size(
            db_size
        ),

        user_storage_data=user_storage_data,

        largest_user=largest_user
    )


@app.route("/view_all_users")
@login_required
def view_all_users():

    if not session.get("is_admin"):
        return redirect("/dashboard")

    users = User.query.all()

    return render_template(
        "view_all_users.html",
        users=users
    )

@app.route("/total_registered_users")
@admin_required
def total_registered_users():

    total_users = User.query.count()

    return render_template(
        "total_registered_users.html",
        total_users=total_users
    )

# =========================
# ADMIN PRIVACY & SECURITY
# =========================

@app.route("/admin_security")
@admin_required
def admin_security():

    users = User.query.all()

    locked_users = User.query.filter_by(
        account_locked=True
    ).all()

    return render_template(
        "admin_security.html",
        users=users,
        locked_users=locked_users
    )


# =========================
# CHANGE ADMIN PASSWORD
# =========================

@app.route(
    "/change_admin_password",
    methods=["POST"]
)
@admin_required
def change_admin_password():

    current_password = request.form.get(
        "current_password"
    )

    new_password = request.form.get(
        "new_password"
    )

    admin_username = session.get(
        "admin_username"
    )

    if current_password != os.getenv(
        "ADMIN_PANEL_PASSWORD"
    ):

        return """
        <h2 style='color:red;text-align:center;margin-top:50px;'>
        Wrong Current Admin Password ❌
        </h2>
        """

    env_path = ".env"

    with open(env_path, "r") as file:

        lines = file.readlines()

    with open(env_path, "w") as file:

        for line in lines:

            if line.startswith(
                "ADMIN_PANEL_PASSWORD="
            ):

                file.write(
                    f"ADMIN_PANEL_PASSWORD={new_password}\n"
                )

            else:

                file.write(line)

    return redirect("/admin_security")


# =========================
# CHANGE ADMIN EMAIL
# =========================

@app.route(
    "/change_admin_email",
    methods=["POST"]
)
@admin_required
def change_admin_email():

    new_email = request.form.get(
        "new_email"
    )

    env_path = ".env"

    with open(env_path, "r") as file:

        lines = file.readlines()

    with open(env_path, "w") as file:

        for line in lines:

            if line.startswith(
                "ADMIN_EMAIL="
            ):

                file.write(
                    f"ADMIN_EMAIL={new_email}\n"
                )

            else:

                file.write(line)

    return redirect("/admin_security")


# =========================
# UNLOCK USER ACCOUNT
# =========================

@app.route("/unlock_user/<int:user_id>")
@admin_required
def unlock_user(user_id):

    user = User.query.get(user_id)

    activity = UserActivityLog(

        username=user.username,

        email=user.email,

        action="ACCOUNT UNBLOCKED",

        extra_info="Admin unlocked this account"
    )

    db.session.add(activity)

    db.session.commit()


    if user:

        user.account_locked = False

        user.failed_attempts = 0

        user.lock_time = None

        db.session.commit()

    return redirect("/admin_security")

@app.route("/forgot_admin_password", methods=["GET", "POST"])
def forgot_admin_password():

    if request.method == "POST":

        security_answer = request.form.get(
            "security_answer"
        ).strip().lower()

        real_answer = os.getenv(
            "ADMIN_SECURITY_ANSWER"
        ).strip().lower()

        if security_answer == real_answer:

            return f"""
            <h2 style='
                color:lime;
                text-align:center;
                margin-top:50px;
            '>

            Your Admin Password Is:<br><br>

            {os.getenv("ADMIN_PANEL_PASSWORD")}

            </h2>
            """

        else:

            return """
            <h2 style='
                color:red;
                text-align:center;
                margin-top:50px;
            '>

            Wrong Security Answer ❌

            </h2>
            """

    return render_template(
        "forgot_admin_password.html"
    )

@app.route("/admin_user_expenses")
@admin_required
def admin_user_expenses():

    users = User.query.all()

    expenses_count = {}

    for user in users:

        expenses_count[user.id] = Expense.query.filter_by(
            user_id=user.id
        ).count()

    return render_template(

        "admin_user_expenses.html",

        users=users,

        expenses_count=expenses_count
    )


@app.route("/view_user_expenses/<int:user_id>")
@admin_required
def view_user_expenses(user_id):

    user = User.query.get_or_404(user_id)

    expenses = Expense.query.filter_by(
        user_id=user.id
    ).all()

    return render_template(

        "view_user_expenses.html",

        user=user,

        expenses=expenses
    )

@app.route("/admin_user_management")
@login_required
def admin_user_management():

    if not session.get("is_admin"):
        return redirect("/dashboard")

    return render_template(
        "admin_user_management.html"
    )

@app.route("/admin_options")
def admin_options():

    admin_username = os.getenv("ADMIN_USERNAME")

    # agar admin login hi nahi hua
    if "admin_candidate" not in session:

        return redirect("/")

    # admin username verify
    if session["admin_candidate"] != admin_username:

        return redirect("/")

    return render_template(
        "admin_options.html",
        admin_username=admin_username
    )


# =========================
# BACKUP & RESET PANEL
# =========================

@app.route("/admin_backup")
@admin_required
def admin_backup():

    users = User.query.all()

    return render_template(
        "admin_backup.html",
        users=users
    )


# =========================
# FULL APP BACKUP
# =========================

@app.route("/full_app_backup")
@admin_required
def full_app_backup():

    backup_folder = "backups"

    os.makedirs(
        backup_folder,
        exist_ok=True
    )

    backup_zip = os.path.join(
        backup_folder,
        "full_app_backup.zip"
    )

    with zipfile.ZipFile(
        backup_zip,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zipf:

        for folder_name in [

            "static/uploads",

            "static/profile_pics",

            "static/exports",

            "templates"

        ]:

            if os.path.exists(folder_name):

                for root, dirs, files in os.walk(folder_name):

                    for file in files:

                        file_path = os.path.join(
                            root,
                            file
                        )

                        zipf.write(file_path)

        if os.path.exists(
            "instance/expense_tracker.db"
        ):

            zipf.write(
                "instance/expense_tracker.db"
            )

    return send_file(

        backup_zip,

        as_attachment=True
    )


# =========================
# PARTICULAR USER BACKUP
# =========================

@app.route("/backup_user/<int:user_id>")
@admin_required
def backup_user(user_id):

    user = User.query.get(user_id)

    if not user:

        return "User Not Found"

    backup_folder = "backups"

    os.makedirs(
        backup_folder,
        exist_ok=True
    )

    zip_name = (
        f"{user.username}_backup.zip"
    )

    zip_path = os.path.join(
        backup_folder,
        zip_name
    )

    with zipfile.ZipFile(
        zip_path,
        "w",
        zipfile.ZIP_DEFLATED
    ) as zipf:

        expenses = Expense.query.filter_by(
            user_id=user.id
        ).all()

        for expense in expenses:

            if expense.images:

                try:

                    image_list = json.loads(
                        expense.images
                    )

                    for image in image_list:

                        img_path = os.path.join(
                            "static/uploads",
                            image
                        )

                        if os.path.exists(img_path):

                            zipf.write(img_path)

                except:

                    pass

    return send_file(

        zip_path,

        as_attachment=True
    )


# =========================
# RESET ENTIRE APP
# =========================

@app.route(
    "/reset_entire_app",
    methods=["POST"]
)
@admin_required
def reset_entire_app():

    confirm = request.form.get(
        "confirm_text"
    )

    if confirm != "RESET EVERYTHING":

        return """
        <h2 style='
        color:red;
        text-align:center;
        margin-top:50px;
        '>

        Wrong Confirmation Text ❌

        </h2>
        """

    # DELETE ALL USERS

    Expense.query.delete()

    User.query.delete()

    db.session.commit()

    # CLEAR UPLOADS

    folders = [

        "static/uploads",

        "static/profile_pics",

        "static/exports"

    ]

    for folder in folders:

        if os.path.exists(folder):

            for file in os.listdir(folder):

                path = os.path.join(
                    folder,
                    file
                )

                try:

                    os.remove(path)

                except:

                    pass

    session.clear()

    return """
    <h1 style='
    color:red;
    text-align:center;
    margin-top:100px;
    font-size:60px;
    '>

    ENTIRE APP RESET SUCCESSFULLY ⚠️

    </h1>
    """

# =========================
# ACCOUNT & LOGIN RECORDS
# =========================

@app.route("/account_login_records")
@admin_required
def account_login_records():

    users = User.query.all()

    total_logins = LoginHistory.query.count()

    latest_login = (
        LoginHistory.query
        .order_by(LoginHistory.login_time.desc())
        .first()
    )

    admin_login_records = (
    LoginHistory.query
    .filter(LoginHistory.user_id.is_(None))
    .order_by(LoginHistory.login_time.desc())
    .all()
)

    return render_template(

        "account_login_records.html",

        users=users,

        total_logins=total_logins,

        latest_login=latest_login,

        admin_login_records=admin_login_records

    )

# =========================
# PARTICULAR USER RECORDS
# =========================

@app.route("/user_login_records/<int:user_id>")
@admin_required
def user_login_records(user_id):

    user = User.query.get_or_404(user_id)

    login_records = (
        LoginHistory.query
        .filter_by(user_id=user.id)
        .order_by(LoginHistory.login_time.desc())
        .all()
    )

    return render_template(

        "user_login_records.html",

        user=user,

        login_records=login_records

    )

@app.route("/delete_admin_login_record/<int:record_id>", methods=["POST"])
@admin_required
def delete_admin_login_record(record_id):

    record = (
    LoginHistory.query
    .filter(
        LoginHistory.id == record_id,
        LoginHistory.user_id.is_(None)
    )
    .first()
    )

    if record:

        db.session.delete(record)

        db.session.commit()

    return redirect("/account_login_records")


@app.route("/delete_user_login_record/<int:record_id>", methods=["POST"])
def delete_user_login_record(record_id):

    if "admin_logged_in" not in session:
        return redirect("/")

    record = LoginHistory.query.get_or_404(record_id)

    user_id = record.user_id

    db.session.delete(record)

    db.session.commit()

    return redirect(f"/user_login_records/{user_id}")

@app.route("/account_activity_center")
@admin_required
def account_activity_center():

    logs = (
        UserActivityLog.query
        .order_by(UserActivityLog.action_time.desc())
        .all()
    )

    total_created = (
        UserActivityLog.query
        .filter_by(action="ACCOUNT CREATED")
        .count()
    )

    total_deleted = (
        UserActivityLog.query
        .filter_by(action="ACCOUNT DELETED")
        .count()
    )

    total_blocked = (
        UserActivityLog.query
        .filter_by(action="ACCOUNT BLOCKED")
        .count()
    )

    total_unblocked = (
        UserActivityLog.query
        .filter_by(action="ACCOUNT UNBLOCKED")
        .count()
    )

    return render_template(

        "account_activity_center.html",

        logs=logs,

        total_created=total_created,

        total_deleted=total_deleted,

        total_blocked=total_blocked,

        total_unblocked=total_unblocked
    )

@app.route("/delete_activity_log/<int:log_id>", methods=["POST"])
@admin_required
def delete_activity_log(log_id):

    log = UserActivityLog.query.get_or_404(log_id)

    db.session.delete(log)

    db.session.commit()

    return redirect("/account_activity_center")

@app.route(
    "/delete_user_all_logs/<username>",
    methods=["POST"]
)
@admin_required
def delete_user_all_logs(username):

    UserActivityLog.query.filter_by(
        username=username
    ).delete()

    db.session.commit()

    return redirect("/account_activity_center")


@app.route(
    "/clear_all_activity_logs",
    methods=["POST"]
)
@admin_required
def clear_all_activity_logs():

    UserActivityLog.query.delete()

    db.session.commit()

    return redirect("/account_activity_center")


# ==============================
# DELETE ALL LOGIN RECORDS OF ONE USER
# ==============================

@app.route("/delete_all_user_records/<int:user_id>", methods=["POST"])
@admin_required
def delete_all_user_records(user_id):

    user = User.query.get_or_404(user_id)

    # delete login history
    LoginHistory.query.filter_by(user_id=user_id).delete()

    # delete activity logs using username
    UserActivityLog.query.filter_by(
        username=user.username
    ).delete()

    db.session.commit()

    flash(
        f"All login records of {user.username} deleted successfully!",
        "success"
    )

    return redirect(
        url_for(
            "user_login_records",
            user_id=user_id
        )
    )

# ==============================
# CLEAR ALL USER LOGIN RECORDS
# ==============================

@app.route("/clear_all_user_login_records", methods=["POST"])
@admin_required
def clear_all_user_login_records():

    UserActivityLog.query.delete()

    db.session.commit()

    return redirect("/account_login_records")


# ==============================
# CLEAR ALL ADMIN LOGIN RECORDS
# ==============================

@app.route("/clear_all_admin_login_records", methods=["POST"])
@admin_required
def clear_all_admin_login_records():

    LoginHistory.query.delete()

    db.session.commit()

    return redirect("/account_login_records")



with app.app_context():
    print("BBB CREATE ALL START")
    db.create_all()
    print("BBB CREATE ALL DONE")

if __name__ == "__main__":
    app.run(debug=True)

