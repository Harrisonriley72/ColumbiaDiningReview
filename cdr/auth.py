import functools

from sqlalchemy import *

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash


bp = Blueprint('auth', __name__, url_prefix='/auth')

# Registration endpoint: GET request for loading registration page, PUT request for submitting registration form
@bp.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        password = request.form['password']
        #db = get_db()
        error = None

        if not email:
            error = 'Email is required.'
        elif not password:
            error = 'Password is required.'

        if error is None:
            params_dict = {"fname":fname, "lname":lname, "email":email, "password": generate_password_hash(password)}
            try:
                g.conn.execute(text(
                    "INSERT INTO ColumbiaStudents (fname, lname, email, password) VALUES (:fname, :lname, :email, :password)"),
                    params_dict,)
                g.conn.commit()
            except exc.IntegrityError:
                error = f"User with email {email} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html')

# Login endpoint: GET request for loading login page, PUT request for submitting login form
@bp.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        #db = get_db()
        error = None
        params_dict = {"email":email}
        user = g.conn.execute(text(
            'SELECT * FROM ColumbiaStudents WHERE email = :email'), params_dict
        ).fetchone()
        g.conn.commit()
        print(user)

        if user is None:
            error = 'Incorrect email.'
        elif not check_password_hash(user._mapping["password"], password):
            error = 'Incorrect password.'

        if error is None:
            session.clear()
            session['user_id'] = user._mapping["email"]
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html')

# Clears session when user logs out
@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# Function requiring that a user be logged in before accessing certain endpoint
def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

# Before request, sets g.user according to user_id in current session
@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        params_dict = {"user_id":user_id}
        g.user =  g.conn.execute(text(
            'SELECT * FROM ColumbiaStudents WHERE email = :user_id'), params_dict
        ).fetchone()._mapping
        g.conn.commit()
