#python script to get daily columbia meals
# originally had functions according to number of meals but have since simplified
import requests
import re
from datetime import date, timedelta

dining_halls = {
	"John Jay Dining Hall": [],
	"JJ's Place": [],
	"Ferris Booth Commons": [],
	"Faculty House": [],
	"Chef Mike's Sub Shop": [],
	"Chef Don's Pizza Pi": [],
	"Grace Dodge Dining Hall": [],
	"The Fac Shack": [],
	"Robert F. Smith Dining Hall": []
}
lunch_only_halls = ['Faculty House', "Chef Mike's Sub Shop", "Chef Don's Pizza Pi", "The Fac Shack"]
# urls for each dining hall
all_3_halls = ["John Jay Dining Hall", "JJ's Place"]
lunch_dinner_halls = ["Grace Dodge Dining Hall"]
items_to_remove = ['Protein', 'Cheese', 'Toppings', 'Dressings']
urls = {
	"John Jay Dining Hall": 'https://dining.columbia.edu/content/john-jay-dining-hall',
	"JJ's Place": 'https://dining.columbia.edu/content/jjs-place-0',
	"Ferris Booth Commons": 'https://dining.columbia.edu/content/ferris-booth-commons-0',
	"Faculty House": 'https://dining.columbia.edu/content/faculty-house-0',
	"Chef Mike's Sub Shop": 'https://dining.columbia.edu/chef-mikes',
	"Chef Don's Pizza Pi": 'https://dining.columbia.edu/content/chef-dons-pizza-pi',
	"Grace Dodge Dining Hall": 'https://dining.columbia.edu/content/grace-dodge-dining-hall-0',
	"Robert F. Smith Dining Hall": 'https://dining.columbia.edu/content/robert-f-smith-dining-hall-0',
	"The Fac Shack": 'https://dining.columbia.edu/content/fac-shack'
}

def get_titles(meal_time, meals):
	
	meals_split = meal_time.split('title\\":\\"')
	for i in range(1, len(meals_split)-1):
		cur_meal = meals_split[i]
		actual_name = cur_meal.split('\\"')[0]
		if not (actual_name.lower() in [x.lower() for x in meals]):
			meals.append(actual_name.replace("\\", ""))
	return meals

def lunch_only(this_date, menu_line, item):
	first_split = menu_line.split('date_from\\":\\"' + str(this_date), 1)
	if (len(first_split)<2):
		return
	today = first_split[1]
	today = today.split('cu_dining_menu')[0]
	today = re.split('week', today, flags=re.IGNORECASE)

	meals = []
	for time in today:
		meals = get_titles(time, meals)

	
	#breakpoint()
	for x in items_to_remove:
		if x in meals:
			meals.remove(x)


	dining_halls[item] = meals

	print(item + ":")
	print(meals)
	print('-------------------------')
	print()

def get_menu(item):
	r = requests.get(urls[item], allow_redirects=True)

	outfile = open('parse.txt', 'wb')
	outfile.write(r.content)
	outfile.close()
	outfile = open('parse.txt', 'r')

	menu_line = ""
	for line in outfile:
		if 'menu_data' in line:
			menu_line = line
	outfile.close()
	#breakpoint()
	this_date = date.today()
	print("this day:", this_date)
	#this_date = this_date + timedelta(1)

	if str(this_date) not in menu_line:
		return dining_halls[item]

	lunch_only(this_date, menu_line, item)

	return dining_halls[item]


def link_to_title(link):
	mapping = {
		"john-jay-dining-hall": "John Jay Dining Hall",
		"jjs-place": "JJ's Place",
		"ferris-booth-commons": "Ferris Booth Commons",
		"faculty-house": "Faculty House",
		"chef-mikes-sub-shop": "Chef Mike's Sub Shop",
		"chef-dons-pizza-pi": "Chef Don's Pizza Pi",
		"grace-dodge-dining-hall": "Grace Dodge Dining Hall",
		"the-fac-shack": "The Fac Shack"
	}
	return mapping[link]





