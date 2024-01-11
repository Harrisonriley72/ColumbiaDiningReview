import os

from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, abort


# Create and configure the app
app = Flask(__name__, instance_relative_config=True)
app.secret_key = "super secret key"
DATABASEURI = "postgresql://harrisonriley@localhost:5432/cu_dining_data"
engine = create_engine(DATABASEURI)

# Connect to the database before every request
@app.before_request
def before_request():
  try:
    g.conn = engine.connect()
  except:
    print("uh oh, problem connecting to database")
    import traceback; traceback.print_exc()
    g.conn = None

# Make sure to close database connection at the end of every request
@app.teardown_request
def teardown_request(exception):
  try:
    g.conn.close()
  except Exception as e:
    pass


# auth module used for authentication
import auth
app.register_blueprint(auth.bp)

# reviews module used for hall pages
import reviews
app.register_blueprint(reviews.bp)
app.add_url_rule('/', endpoint='index')

# profile module used for profile pages
import profile
app.register_blueprint(profile.bp)

if __name__ == "__main__":
    import click

    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    
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




