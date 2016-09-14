import time
import atexit
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from flask import Flask, render_template
import pymysql.cursors

from scraper import Scraper

from secrets import DB_USER, DB_PASSWORD, DB_NAME

# Connect to the database
connection = pymysql.connect(host='localhost',
                             user=DB_USER,
                             password=DB_PASSWORD,
                             db=DB_NAME,
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

app = Flask(__name__)

def _sql(sql, params=()):
    """NOTE: Does not commit to database, so SQL injection isn't dangerous"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            connection.commit()
            return cursor.fetchall()
    except Exception as e:
        print("Error: {}".format(e))

@app.route('/')
def index():
    top_posts = _sql("""select distinct from_name, count(*) as updates,
    CONCAT("https://facebook.com/", Post.group_id,"/posts/",Post.post_id) as link
    from Post, Post_Updated where Post.post_id = Post_Updated.post_id
    group by Post.post_id
    order by updates desc
    limit 10;""")
    posts = _sql("""select from_name, SUBSTRING(message, 1, 1000) as message, created_time as date, CONCAT("https://facebook.com/", group_id,"/posts/",post_id) as link
    from Post order by created_time desc limit 20""")
    count = _sql('select count(*) as count from Post')
    return render_template('index.html', top_posts=top_posts, posts=posts, count=count)

@app.route('/posts')
def show_posts():
    posts = _sql("""select from_name, SUBSTRING(message, 1, 100) as message, created_time as date, CONCAT("https://facebook.com/", group_id,"/posts/",post_id) as link
    from Post order by created_time desc limit 1000""")
    count = _sql('select count(*) as count from Post')
    return render_template('show_posts.html', posts=posts, count=count)

def start_scraper():
    Scraper()

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    scheduler.start()
    scheduler.add_job(func=start_scraper, trigger=IntervalTrigger(seconds=60),id='scraper',name='Scrapes posts',replace_existing=True)

    # shut down the scheduler when exiting the app
    atexit.register(lambda: scheduler.shutdown())
    app.run(threaded=True, host="0.0.0.0")
