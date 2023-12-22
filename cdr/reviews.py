import functools

from sqlalchemy import *

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for
)
from werkzeug.security import check_password_hash, generate_password_hash
from get_menu import get_menu, dining_halls
from datetime import datetime, date, timedelta

from auth import login_required

bp = Blueprint('reviews', __name__)

@bp.route('/')
def index():
    halls = g.conn.execute(text(
        'SELECT hallname'
        ' FROM dininghalls d'
    )).fetchall()
    g.conn.commit()
    return render_template('reviews/index.html', halls=halls)


@bp.route('/<hallname>/<int:order>')
def hallpage(hallname, order=0):
	today = date.today()
	tomorrow = date.today() + timedelta(1)
	yesterday = date.today() - timedelta(1)

	d1 = yesterday.strftime("%Y-%m-%d") + " 23:59:59"
	d2 = tomorrow.strftime("%Y-%m-%d") + " 00:00:01"
	cursor = g.conn.execute(text(
		'SELECT *'
		' FROM CurrentDate'
	))
	g.conn.commit()
	current_time = cursor.fetchone()
	print(current_time)
	fooditems=[]

	# Check if CurrentMeals in database needs to be updated and update if so
	if (current_time is None) or (current_time[0]!=today):
		cursor = g.conn.execute(text(
			'DELETE FROM CurrentMeals'
		))
		g.conn.commit()
		cursor = g.conn.execute(text(
			'DELETE FROM CurrentDate'
		))
		g.conn.commit()

		params_dict = {"today":today, "begin_time":d1}
		cursor = g.conn.execute(text(
			'INSERT INTO CurrentDate(today, begin_time)'
			' VALUES (:today, :begin_time)'
		), params_dict)
		g.conn.commit()	

		halls = dining_halls
		for hall in halls:
			halls[hall] = get_menu(hall)


			fooditems = {s for s in halls[hall]}

			print("items",fooditems)
			already_logged = []
			for foodname in fooditems:
				cursor = g.conn.execute(text(
					'SELECT F.foodname'
					' FROM FoodItems F'
					' WHERE F.hallname_servedat=:hallname AND F.foodname=:foodname'
				), {"hallname":hall, "foodname":foodname})
				g.conn.commit()

				for result in cursor:
					already_logged.append(result[0])			
				
			print(already_logged)	

			for foodname in fooditems:
				if foodname not in already_logged:
					cursor = g.conn.execute(text(
						'INSERT INTO FoodItems(foodname, hallname_servedat)'
						' VALUES (:foodname, :hallname)'
					), {"foodname":foodname, "hallname":hall})
					g.conn.commit()	

				cursor = g.conn.execute(text(
					'INSERT INTO CurrentMeals(foodname, hallname_servedat)'
					' VALUES (:foodname, :hallname)'
				), {"foodname":foodname, "hallname":hall})
				g.conn.commit()

		fooditems = halls[hallname]	
	else:
		cursor = g.conn.execute(text(
			'SELECT C.foodname'
			' FROM CurrentMeals C'
			' WHERE C.hallname_servedat=:hallname'
		), {"hallname":hallname})
		g.conn.commit()

		for result in cursor:
			fooditems.append(result[0])

		print("in here")

	# arrays for tracking the ordering of items on the page
	isactive1, isactive2 = [],[]


	params_dict = {"hallname": hallname, "d1":d1, "d2":d2}

	# generating the reviews, different depending on whether user is logged in or not
	if g.user is not None:
		params_dict.__setitem__('right_email', g.user["email"])
		if order==1:
			isactive1=["",""]
			isactive2=["active", "checked"]	
			reviews = g.conn.execute(text(
				'SELECT C.fname, C.lname, R.email, R.time, R.hallname, R.rating, R.comment, R.like_number, B.liker_email'
				' FROM ColumbiaStudents C JOIN (ReviewMake R LEFT JOIN ('
					'SELECT R1.email, R1.time, R1.hallname, R1.rating, R1.comment, R1.like_number, H.liker_email'
					' FROM HasLike H JOIN ReviewMake R1'
					' ON H.liked_email=R1.email AND R1.time=H.time AND R1.hallname=H.hallname'
					' WHERE H.liker_email=:right_email) B'
				' ON B.email=R.email AND R.time=B.time AND R.hallname=B.hallname)'
				' ON C.email=R.email'
				' WHERE R.hallname=:hallname AND R.time>:d1 AND R.time<:d2'
				' ORDER BY R.like_number DESC'
			), params_dict).fetchall()		

		else:
			isactive1=["active", "checked"]
			isactive2=["",""]
			reviews = g.conn.execute(text(
				'SELECT C.fname, C.lname, R.email, R.time, R.hallname, R.rating, R.comment, R.like_number, B.liker_email'
				' FROM ColumbiaStudents C JOIN (ReviewMake R LEFT JOIN ('
					'SELECT R1.email, R1.time, R1.hallname, R1.rating, R1.comment, R1.like_number, H.liker_email'
					' FROM HasLike H JOIN ReviewMake R1'
					' ON H.liked_email=R1.email AND R1.time=H.time AND R1.hallname=H.hallname'
					' WHERE H.liker_email=:right_email) B'
				' ON B.email=R.email AND R.time=B.time AND R.hallname=B.hallname)'
				' ON C.email=R.email'
				' WHERE R.hallname=:hallname AND R.time>:d1 AND R.time<:d2'
				' ORDER BY R.time DESC'
			), params_dict).fetchall()	
		g.conn.commit()
	else:
		if order==1:
			isactive1=["",""]
			isactive2=["active", "checked"]	
			reviews = g.conn.execute(text(
				'SELECT *'
				' FROM ReviewMake R'
				' WHERE R.hallname = :hallname AND R.time>:d1 AND R.time<:d2'
				' ORDER BY R.time DESC'
			), params_dict).fetchall()
		else:
			isactive1=["active", "checked"]
			isactive2=["",""]
			reviews = g.conn.execute(text(
				'SELECT *'
				' FROM ReviewMake R'
				' WHERE R.hallname = :hallname AND R.time>:d1 AND R.time<:d2'
				' ORDER BY R.time DESC'
			), params_dict).fetchall()	
		g.conn.commit()

	# Getting the ratings of each food item
	# ***** NOTE TO SELF -- currently has bug where it uses ratings from past days.
	# Should add a table of current ratings
	foodratings = g.conn.execute(text(
		'SELECT C.foodname, round(AVG(F.rating)::numeric,2) AS "avg", COUNT(F.rating) AS "count"'
		' FROM RateFoodItem F NATURAL RIGHT JOIN CurrentMeals C'
		' WHERE C.hallname_servedat = :hallname'
		' GROUP BY C.foodname'
	), params_dict).fetchall()	
	g.conn.commit()



	# When user is logged in, make dictionary with foodnames as keys and user's ratings as values
	user_ratings_dict = {}
	if g.user is not None:
		user_ratings = g.conn.execute(text(
			'SELECT R.foodname, R.rating'
			' FROM RateFoodItem R'
			' WHERE R.hallname_servedat=:hallname AND R.email=:right_email AND R.time>:d1'
		), params_dict).fetchall()	
		g.conn.commit()

		
		for rating in user_ratings:
			user_ratings_dict.__setitem__(rating[0], rating[1])

		print(user_ratings_dict)

	
	context = {"hallname": hallname, "fooditems": fooditems, "reviews":reviews, "isactive1":isactive1, "isactive2":isactive2, "foodratings":foodratings, "user_ratings_dict":user_ratings_dict}
	return render_template('reviews/hallpage.html', **context)

@bp.route('/rate_fooditem/<foodname>/<hallname_servedat>/<order_indic>/<from_page>', methods=["POST"])
@login_required
def rate_fooditem(foodname, hallname_servedat, order_indic, from_page):
	# Note: hallname signifies either hallname or profile email, depending on which page like is coming from
	order=1
	if order_indic=="0active":
		order=0

	new_rating = request.form["rating"]
	if new_rating == "":
		flash("You must enter a number between 1-5 to submit a rating.")
		return redirect(url_for("reviews.hallpage", hallname=hallname_servedat, order=order))

	now = datetime.now()
	time = now.strftime("%Y-%m-%d %H:%M:%S")
	today_begin = time[:11] + "00:00:00"
	params_dict = {"time":time, "today_begin":today_begin, "foodname":foodname, "hallname":hallname_servedat, "rater_email": g.user["email"], "rating":new_rating}

	# Check to ssee if this fooditem has been rated previously
	cursor = g.conn.execute(text(
		'SELECT *'
		' FROM RateFoodItem R'
		' WHERE email=:rater_email AND hallname_servedat=:hallname AND foodname=:foodname AND time>=:today_begin'
	), params_dict)
	g.conn.commit()
	previous_rating = cursor.fetchone()

	if previous_rating is not None: # case where user has already rated -> update rating
		print('rate_fooditem if')
		cursor = g.conn.execute(text(
			'UPDATE RateFoodItem'
			' SET rating=:rating, time=:time'
			' WHERE email=:rater_email AND hallname_servedat=:hallname AND foodname=:foodname AND time>=:today_begin'
		), params_dict)
		g.conn.commit()
	else: # case where user has not yet rated -> insert new tuple into RateFoodItem
		print('rate_fooditem else')
		cursor = g.conn.execute(text(
			'INSERT INTO RateFoodItem(email, time, foodname, hallname_servedat, rating)'
			' VALUES (:rater_email, :time, :foodname, :hallname, :rating)'
		), params_dict)
		g.conn.commit()	

	return redirect(url_for("reviews.hallpage", hallname=hallname_servedat, order=order))


@bp.route('/increase_likes/<email>/<time>/<hallname>/<order_indic>/<from_page>')
@login_required
def increment(email, time, hallname, order_indic, from_page):
	# Note: hallname signifies either hallname or profile email, depending on which page like is coming from
	order=1
	if order_indic=="0active":
		order=0
	params_dict = {"right_time":time, "right_email":email, "right_hallname":hallname, "liker_email": g.user["email"]}
	

	#params_dict2 = {}
	#dict.__setitem__('newkey2', 'GEEK')
	cursor = g.conn.execute(text(
		'SELECT *'
		' FROM HasLike'
		' WHERE liker_email=:liker_email AND liked_email=:right_email AND time=:right_time AND hallname=:right_hallname'
	), params_dict)
	g.conn.commit()

	if cursor.fetchone() is None: # case where user has not liked this review -> increment
		cursor = g.conn.execute(text(
			'INSERT INTO HasLike(liker_email, liked_email, time, hallname)'
			' VALUES (:liker_email, :right_email, :right_time, :right_hallname)'
		), params_dict)
		g.conn.commit()

		cursor = g.conn.execute(text(
			'UPDATE ReviewMake'
			' SET like_number = like_number + 1'
			' WHERE time=:right_time AND email=:right_email AND hallname=:right_hallname'
		), params_dict)
		g.conn.commit()	
	else: # case where user has liked this review -> decrement
		cursor = g.conn.execute(text(
			'DELETE FROM HasLike'
			' WHERE liker_email=:liker_email AND liked_email=:right_email AND time=:right_time AND hallname=:right_hallname'
		), params_dict)
		g.conn.commit()

		cursor = g.conn.execute(text(
			'UPDATE ReviewMake'
			' SET like_number = like_number - 1'
			' WHERE time=:right_time AND email=:right_email AND hallname=:right_hallname'
		), params_dict)
		g.conn.commit()			
	if from_page=="hallpage":
		return redirect(url_for("reviews.hallpage", hallname=hallname, order=order))
	else:
		return redirect(url_for("reviews.profile", email=email, order=order))



@bp.route('/update_order/<hallname>/', methods=['POST'])
def update_order(hallname):
	if request.form["options"]!="newest":
		order=1
	else:
		order=0

	return redirect(url_for("reviews.hallpage", hallname=hallname, order=order))

@bp.route('/update_order_profile/<email>/', methods=['POST'])
def update_order_profile(email):
	if request.form["options"]!="newest":
		order=1
	else:
		order=0

	return redirect(url_for("reviews.profile", email=email, order=order))


@bp.route('/add_review/<hallname>/', methods=['POST', 'GET'])
@login_required
def add_review(hallname):
	if request.method=="POST":
		now = datetime.now()
		time = now.strftime("%Y-%m-%d %H:%M:%S")
		rating = int(request.form["inlineRadioOptions"])
		comment = request.form["body"]

		params_dict = {"email":g.user["email"], "rating":rating, "hallname":hallname, "comment":comment, "time": time}	
		cursor = g.conn.execute(text(
			'INSERT INTO ReviewMake(email, rating, hallname, comment, time)'
			' VALUES (:email, :rating, :hallname, :comment, :time)'
		), params_dict)
		g.conn.commit() 			

		return redirect(url_for("reviews.hallpage", hallname=hallname, order=0))

	return render_template("reviews/add_review.html", hallname=hallname)

@bp.route('/profile/<email>/<int:order>', methods=['GET'])
@login_required
def profile(email, order=0):
	user = g.conn.execute(text(
		'SELECT *'
		' FROM ColumbiaStudents C'
		' WHERE C.email=:email'
	), {"email":email}).fetchone()
	g.conn.commit()

	num_reviews = g.conn.execute(text(
		'SELECT COUNT(*)'
		' FROM ReviewMake R'
		' WHERE R.email=:email'
	), {"email":email}).fetchone()
	g.conn.commit()

	avg_rating = g.conn.execute(text(
		'SELECT AVG(R.rating)'
		' FROM ReviewMake R'
		' WHERE R.email=:email'
	), {"email":email}).fetchone()
	g.conn.commit()

	isactive1, isactive2 = [],[]
	params_dict = {"email": email, "right_email":g.user["email"]}
	if order==1:
		isactive1=["",""]
		isactive2=["active", "checked"]	
		# reviews = g.conn.execute(text(
		# 	'SELECT *'
		# 	' FROM ReviewMake R'
		# 	' WHERE R.hallname = :hallname AND R.time>:d1 AND R.time<:d2'
		# 	' ORDER BY R.like_number DESC'	
		# ), params_dict).fetchall()

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
		isactive1=["active", "checked"]
		isactive2=["",""]
		# reviews = g.conn.execute(text(
		# 	'SELECT *'
		# 	' FROM ReviewMake R'
		# 	' WHERE R.hallname = :hallname AND R.time>:d1 AND R.time<:d2'
		# 	' ORDER BY R.time DESC'
		# ), params_dict).fetchall()
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
	return render_template("reviews/profile.html", **{"reviews":reviews, "user":user, "num_reviews":num_reviews[0], "avg_rating":round(avg_rating[0],2),  "isactive1":isactive1, "isactive2":isactive2, "email":email})

@bp.route('/edit-profile/<email>', methods=['POST','GET'])
@login_required
def edit_profile(email):
	if request.method=="POST":
		return redirect(url_for('reviews.profile', email=email, order=0))
	return render_template("reviews/edit_profile_form.html", email=email)

# View for home page of getting data on halls throughout all time
@bp.route('/dining-hall-data/<hallname>')
def macro_halls(hallname):
	if hallname=="":
		return render_template("dining_hall_macro_home.html")

	return render_template("dining_hall_macro.html", hallname=hallname)







