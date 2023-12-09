import os

from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, abort


# create and configure the app
app = Flask(__name__, instance_relative_config=True)
app.secret_key = "super secret key"
# app.config.from_mapping(
#     SECRET_KEY='dev',
#     #DATABASE="postgresql://hjr2128:Cherrycoke1@34.75.94.195/proj1part2"
#     #os.path.join(app.instance_path, 'flaskr.sqlite'),
# )
DATABASEURI = "postgresql://harrisonriley@localhost:5432/cu_dining_data"
engine = create_engine(DATABASEURI)

@app.before_request
def before_request():
  """
  This function is run at the beginning of every web request
  (every time you enter an address in the web browser).
  We use it to setup a database connection that can be used throughout the request.

  The variable g is globally accessible.
  """
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

@app.teardown_request
def teardown_request(exception):
  """
  At the end of the web request, this makes sure to close the database connection.
  If you don't, the database could run out of memory!
  """
  try:
    g.conn.close()
  except Exception as e:
    pass

# if test_config is None:
#     # load the instance config, if it exists, when not testing
#     app.config.from_pyfile('config.py', silent=True)
# else:
#     # load the test config if passed in
#     app.config.from_mapping(test_config)

# ensure the instance folder exists
# try:
#     os.makedirs(app.instance_path)
# except OSError:
#     pass

import auth
app.register_blueprint(auth.bp)

import reviews
app.register_blueprint(reviews.bp)
app.add_url_rule('/', endpoint='index')

@app.route('/')
def index():
    cursor = g.conn.execute(text("SELECT fname FROM ColumbiaStudents"))
    g.conn.commit()

    # 2 ways to get results

    # Indexing result by column number
    names = []
    for result in cursor:
        names.append(result[0])  

    # # Indexing result by column name
    # names = []
    # results = cursor.mappings().all()
    # for result in results:
    # names.append(result["name"])
    cursor.close()

    context = dict(data = names)

    return render_template("index.html", **context)

if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    #app.config.from_mapping(
        #SECRET_KEY='dev',)

    #app.config['SESSION_TYPE'] = 'filesystem'

    def run(debug, threaded, host, port):
        """
        This function handles command line parameters.
        Run the server using:

            python3 server.py

        Show the help text using:

            python3 server.py --help

        """

        HOST, PORT = host, port
        print("running on %s:%d" % (HOST, PORT))
        app.run(host=HOST, port=PORT, debug=debug, threaded=threaded)

    run()




# from . import db
# db.init_app(app)


# from . import blog
# app.register_blueprint(blog.bp)
# app.add_url_rule('/', endpoint='index')




