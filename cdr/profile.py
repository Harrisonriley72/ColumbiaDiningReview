import functools
from sqlalchemy import *
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from cdr.auth import login_required

bp = Blueprint('profile', __name__, url_prefix='/profile')


"""
Gets the profile page for a user. User must be logged in.
in params:
    email -> email of profile page being rendered
    order (default 0) -> order of listing reviews. 0 indicates by time, 1 indicates by number of likes.
out context:
    reviews -> table of reviews made by profile page user
    user -> row from ColumbiaStudents table containing information on profile page user
    num_reviews -> number of reviews profile page user has made
    avg_rating -> average rating given by profile page user
    email -> email of the profile page user
    order -> indicates the ordering of the page. 0 indicates that order is by time, 1 indicates order is by number of likes
"""
@bp.route('/<email>/<int:order>', methods=['GET'])
@login_required
def get_profile(email, order=0):
    # Query getting row in ColumbiaStudents for profile page user
    user = g.conn.execute(text(
        'SELECT *'
        ' FROM ColumbiaStudents C'
        ' WHERE C.email=:email'
    ), {"email":email}).fetchone()
    g.conn.commit()

    # Query getting the number of reviews given by profile page user
    num_reviews = g.conn.execute(text(
        'SELECT COUNT(*)'
        ' FROM ReviewMake R'
        ' WHERE R.email=:email'
    ), {"email":email}).fetchone()
    g.conn.commit()

    # Query getting the average rating given by profile page user
    avg_rating = g.conn.execute(text(
        'SELECT AVG(R.rating)'
        ' FROM ReviewMake R'
        ' WHERE R.email=:email'
    ), {"email":email}).fetchone()
    g.conn.commit()

    params_dict = {"email": email, "right_email":g.user["email"]}
    if order==1:
        # Query getting reviews given by profile page user, ordering by number of likes
        reviews = g.conn.execute(text(
            'SELECT R.hallname, R.time, R.like_number, R.comment, B.liker_email, R.rating'
            ' FROM ReviewMake R LEFT JOIN ('
                'SELECT R1.email, R1.time, R1.hallname, R1.rating, R1.comment, R1.like_number, H.liker_email'
                ' FROM HasLike H JOIN ReviewMake R1'
                ' ON H.liked_email=R1.email AND R1.time=H.time AND R1.hallname=H.hallname'
                ' WHERE H.liker_email=:right_email) B'
            ' ON B.email=R.email AND R.time=B.time AND R.hallname=B.hallname'
            ' WHERE R.email=:email'
            ' ORDER BY R.like_number DESC'
        ), params_dict).fetchall()              

    else:
        # Query getting reviews given by profile page user, ordering by time
        reviews = g.conn.execute(text(
            'SELECT R.hallname, R.time, R.like_number, R.comment, B.liker_email, R.rating'
            ' FROM ReviewMake R LEFT JOIN ('
                'SELECT R1.email, R1.time, R1.hallname, R1.rating, R1.comment, R1.like_number, H.liker_email'
                ' FROM HasLike H JOIN ReviewMake R1'
                ' ON H.liked_email=R1.email AND R1.time=H.time AND R1.hallname=H.hallname'
                ' WHERE H.liker_email=:right_email) B'
            ' ON B.email=R.email AND R.time=B.time AND R.hallname=B.hallname'
            ' WHERE R.email=:email'
            ' ORDER BY R.time DESC'
        ), params_dict).fetchall()              

    g.conn.commit()
    return render_template("profile/profile.html", **{"reviews":reviews, "user":user, "num_reviews":num_reviews[0], "avg_rating":round(avg_rating[0],2), "email":email, "order":order})


"""
Updates the order of reviews on profile pages, orders reviews by either time or number of likes.
in params:
    email -> email of profile page
out context:
    email -> email of profile page
    order -> integer in {0, 1} indicating order of page. 0 indicates order by time, 1 indicates order by number of likes.
"""
@bp.route('/update_order/<email>/', methods=['POST'])
def update_order(email):
    if request.form["options"]!="newest":
        order=1
    else:
        order=0

    return redirect(url_for("profile.get_profile", email=email, order=order))


"""
Endpoint editing profile. In progress -- requires further coding. 
"""
@bp.route('/edit-profile/<email>', methods=['POST','GET'])
@login_required
def edit_profile(email):
    if request.method=="POST":
        return redirect(url_for('profile.get_profile', email=email, order=0))
    return render_template("profile/edit_profile_form.html", email=email)
