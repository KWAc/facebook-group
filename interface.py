from flask import Flask, render_template
import pymysql.cursors

from secrets import DB_USER, DB_PASSWORD, DB_NAME

# Connect to the database
connection = pymysql.connect(host='localhost',
                             user=DB_USER,
                             password=DB_PASSWORD,
                             db=DB_NAME,
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

app = Flask(__name__)
app.config.from_envvar('PGM_SETTINGS', silent=True)

def _sql(sql, params=()):
    """NOTE: Does not commit to database, so SQL injection isn't possible"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
    except Exception as e:
        print("Error: {}".format(e))

    return cursor.fetchall()


@app.route('/')
def show_entries():
    entries = _sql("""select from_name, SUBSTRING(message, 1, 100) as message, CONCAT("https://facebook.com/", group_id,"/posts/",post_id) as link
    from Post order by created_time desc limit 500""")
    count = _sql('select count(*) as count from Post')
    return render_template('show_entries.html', entries=entries, count=count)

if __name__ == "__main__":
    app.run()
