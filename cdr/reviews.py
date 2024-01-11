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

"""
Endpoint for home page
"""
@bp.route('/')
def index():
	# SQL query to get list of dininghalls for database, to be displayed on home page
    halls = g.conn.execute(text(
        'SELECT hallname'
        ' FROM dininghalls d'
    )).fetchall()
    g.conn.commit()
    return render_template('reviews/index.html', halls=halls)

""" 
Endpoint to access page for each dining hall.
in params: 
	hallname -> dining hall's name, 
	int:order (default 0) -> ordering of the reviews, where 0 indicates the ordering by most recent and 1 by most popular
out context:
	hallname -> indicates dining hall name for the page to be accessed
	fooditems -> a list of the food items currently served at the dining hall
	reviews -> a list of the reviews for the dining hall
	foodratings -> rows from database with columns for the name of a food item, its average rating, and the number of ratings its received
	user_ratings_dict -> dictionary containing food item names from this dining hall as keys and user's rating for each one as values
	order -> indicates the ordering of the page. 0 indicates that order is by time, 1 indicates order is by number of likes

"""

@bp.route('/<hallname>/<int:order>')
def hallpage(hallname, order=0):
	# Current date is track
	today = date.today()
	tomorrow = date.today() + timedelta(1)
	yesterday = date.today() - timedelta(1)

	# d1 and d2 are the earliest and lates times included in the current day, respectively 
	d1 = yesterday.strftime("%Y-%m-%d") + " 23:59:59"
	d2 = tomorrow.strftime("%Y-%m-%d") + " 00:00:01"
	# The time currently stored in the database as the current data is fetched to ensure that it is correct or update accordingly
	cursor = g.conn.execute(text(
		'SELECT *'
		' FROM CurrentDate'

	))
	g.conn.commit()
	current_time = cursor.fetchone()
	fooditems=[]

	"""
	If the time must be updated, the CurrentMeals table in the database must be as well. 
	Check if this is the case, and update if so. 
	"""
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


		"""
		Use the dictionary dining_halls from get_menu.py, which has dining hall names as keys.
		Fill the dictionary with values for today's food items using get_menu().
		Update FoodItems and CurrentMeals tables accordingly. 
		"""
		halls = dining_halls
		for hall in halls:
			halls[hall] = get_menu(hall)


			fooditems = {s for s in halls[hall]}

			# Build list of food items that are already in the FoodItems table
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
				
			for foodname in fooditems:
				# Only add those food items to FoodItems which are not already logged
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
		"""
		If CurrentDate is logged correctly, simply query those food item names for this page's dining hall and add to fooditems
		"""
		cursor = g.conn.execute(text(
			'SELECT C.foodname'
			' FROM CurrentMeals C'
			' WHERE C.hallname_servedat=:hallname'
		), {"hallname":hallname})
		g.conn.commit()

		for result in cursor:
			fooditems.append(result[0])


	params_dict = {"hallname": hallname, "d1":d1, "d2":d2}

	"""
	Generating the reviews. 
	If the user is logged in, whether they have liked a given review will be tracked so as to be reflected in the front-end.
	"""
	if g.user is not None:
		params_dict.__setitem__('right_email', g.user["email"])
		if order==1:
			# Query gets attributes from table of reviews ReviewMake relevant for this time and dining hall, along with attribute indicating whether the current user has liked the given review.
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
			# Identical to if-segment above, except ordering is done by time instead of number of likes 
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
		# In the case when there is no user, simply retrieve the reviews without worrying about indicating any specific user has liked them
		if order==1:
			reviews = g.conn.execute(text(
				'SELECT *'
				' FROM ReviewMake R'
				' WHERE R.hallname = :hallname AND R.time>:d1 AND R.time<:d2'
				' ORDER BY R.time DESC'
			), params_dict).fetchall()
		else:
			reviews = g.conn.execute(text(
				'SELECT *'
				' FROM ReviewMake R'
				' WHERE R.hallname = :hallname AND R.time>:d1 AND R.time<:d2'
				' ORDER BY R.time DESC'
			), params_dict).fetchall()	
		g.conn.commit()

	# Getting the ratings of each food item
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

	context = {"hallname": hallname, "fooditems": fooditems, "reviews":reviews, "foodratings":foodratings, "user_ratings_dict":user_ratings_dict,"order": order}
	return render_template('reviews/hallpage.html', **context)

"""
Endpoint for user to rate food item. User must be logged in.
in params:
	foodname -> the name of the food being rated
	hallname_servedat -> the name of the dining hall the rated food is served at
	order -> indicates the ordering of the page. 0 indicates that order is by time, 1 indicates order is by number of likes
	from_page -> indicates the page that the request came from so that it knows where to redirect -- not currenly useful but will be if other pages are added to the site from which a food item can be liked 
out context: (after operation redirects back to page request came from)
	hallname -> the dining hall name for the hall page the request came from 
	order -> the order that was set on the page when the user rated the food item
"""
@bp.route('/rate_fooditem/<foodname>/<hallname_servedat>/<order>/<from_page>', methods=["POST"])
@login_required
def rate_fooditem(foodname, hallname_servedat, order, from_page):
	# Note: hallname signifies either hallname or profile email, depending on which page like is coming from

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

"""
Endpoint for user to add a like to a review. User must be logged in.
in params:
	email -> email of the user who created the review that the current user is attempting to like
	time -> time of the review that current user is attempting to like
	hallname -> name of the dining hall the review is on
	order -> indicates the ordering of the page. 0 indicates that order is by time, 1 indicates order is by number of likes
	from_page -> indicates the page that the request came from so that it knows where to redirect
	hallname -> the dining hall name for the hall page the request came from 
	order -> the order that was set on the page when the user attempted the like
"""
@bp.route('/increase_likes/<email>/<time>/<hallname>/<order>/<from_page>')
@login_required
def increment(email, time, hallname, order, from_page):
	# Note: hallname signifies either hallname or profile email, depending on which page like is coming from

	params_dict = {"right_time":time, "right_email":email, "right_hallname":hallname, "liker_email": g.user["email"]}
	

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

	# Check from_page to see where to redirect to	
	if from_page=="hallpage":
		return redirect(url_for("reviews.hallpage", hallname=hallname, order=order))
	else:
		return redirect(url_for("profile.get_profile", email=email, order=order))



"""
Updates the ordering of reviews for dining hall pages, orders reviews by either time or number of likes.
in params:
	hallname -> the name of the dining hall representing the page having its order updated
out context:
	hallname -> name of the dining hall representing the page being redirected to
	order -> integer in {0, 1} indicating order of page. 0 indicates order by time, 1 indicates order by number of likes.
"""
@bp.route('/update_order/<hallname>/', methods=['POST'])
def update_order(hallname):
	if request.form["options"]!="newest":
		order=1
	else:
		order=0

	return redirect(url_for("reviews.hallpage", hallname=hallname, order=order))


"""
Endpoint to add a review. GET method gets page with form to create a review, POST method submits information in form to create new review in ReviewMake table.
in params:
	hallname -> name of dining hall review is being made for
out context:
	GET:
		hallname -> hall name of dining hall being reviewed
	POST:
		hallname -> hall name for dining hall page to be rendered
"""
@bp.route('/add_review/<hallname>/', methods=['POST', 'GET'])
@login_required
def add_review(hallname):
	if request.method=="POST":
		# Get current time to use as time the review was made, then insert row into ReviewMake table
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

		# after updating database, redirect back to hall page
		return redirect(url_for("reviews.hallpage", hallname=hallname, order=0))

	return render_template("reviews/add_review.html", hallname=hallname)


"""
Endpoint viewing data on dining hall data for all time. In progress -- requires further coding. 
"""
@bp.route('/dining-hall-data/<hallname>')
def macro_halls(hallname):
	if hallname=="":
		return render_template("dining_hall_macro_home.html")

	return render_template("dining_hall_macro.html", hallname=hallname)







