import facebook, requests
import time
from datetime import datetime
import pymysql.cursors

from secrets import TOKEN, GROUPID
from secrets import DB_USER, DB_PASSWORD, DB_NAME

MAX_PAGES = 25

# Connect to the database
connection = pymysql.connect(host='localhost',
                             user=DB_USER,
                             password=DB_PASSWORD,
                             db=DB_NAME,
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

def get_posts():
    """ Pulls all posts possible from facebook, getting the following details:
        Post text, date updated, id.
        id is in the format XXXXXXXXXXX_YYYYYYYYYYY, where the url of the post is
        https://facebook.com/XXXXXXXXXX/posts/YYYYYYYYYY, so we should break up the
        id into two components.

        During the pull, generator will put new posts into the database
        """

    graph = facebook.GraphAPI(TOKEN)
    group = graph.get_object(GROUPID)
    posts = graph.get_connections(group['id'], 'feed')
    pages = 0

    while(pages < MAX_PAGES):
        try:
            [_do_post(post=post) for post in posts['data']]
            print("{} posts saved".format(_sql("select count(*) as num from Post", (), True)[0]['num']))
            time.sleep(0.1)
            print("requesting next page...")
            posts = requests.get(posts['paging']['next']).json()

        except KeyError as e:
            break

        pages += 1

def create_tables(drop=False):
    """Creates the necessary table in the database. If drop=True, drop existing first"""
    sql1 = "DROP TABLE IF EXISTS Post;" if drop else ""
    sql1 += """CREATE TABLE IF NOT EXISTS Post (
        post_id bigint NOT NULL,
        group_id bigint NOT NULL,
        message text,
        created_time datetime NOT NULL,
        from_name varchar(255),
        from_id bigint NOT NULL,
        PRIMARY KEY (post_id)
    );"""

    sql2 = "DROP TABLE IF EXISTS Post_Updated;" if drop else ""
    sql2 += """CREATE TABLE IF NOT EXISTS Post_Updated (
        post_id bigint NOT NULL,
        updated_time datetime NOT NULL
    );"""

    sql3 = "DROP TABLE IF EXISTS Post_Checked;" if drop else ""
    sql3 += """CREATE TABLE IF NOT EXISTS Post_Checked (
        post_id bigint NOT NULL,
        checked_time datetime NOT NULL,
        checked_by varchar(50) NOT NULL
    );"""

    _sql(sql1, (), False)
    _sql(sql2, (), False)
    _sql(sql3, (), False)

def _sql(sql, params, result=True):
    results = None
    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
        connection.commit()
    except Exception as e:
        print("Error: {}".format(e))

    if result:
        return cursor.fetchall()

def _do_post(post):
    # less costly option, check that the post isn't already in the database before we make API calls
    post_id = post['id'].split("_")[1]
    if _sql("select count(*) as num from Post where post_id=%s", (post['id'].split("_")[1]))[0]['num'] is 1:

        check_updated = """select updated_time from Post_Updated where post_id=%s order by updated_time desc limit 1"""
        last_updated = datetime.strptime(post['updated_time'][:-5], "%Y-%m-%dT%H:%M:%S")
        last_updated_in_db = _sql(check_updated, post_id)
        if last_updated_in_db is not ():
            last_updated_in_db = last_updated_in_db[0]['updated_time']
            if last_updated == last_updated_in_db:
                print("Found last post since script run. Stopping...")
                exit(0)

    # grab more post details
    graph = facebook.GraphAPI(TOKEN)
    group = graph.get_object(GROUPID)
    post_details = graph.get_object(id=post_id,
        fields='created_time,from')

    sql = "INSERT IGNORE INTO `Post` (`post_id`, `group_id`, `message`, `created_time`, `from_name`, `from_id`) VALUES (%s, %s, %s, %s, %s, %s)"

    params = (
        int(post_id), # remember, we're grabbing post id first
        int(post['id'].split("_")[0]), # then group id
        str(post['message']).encode('utf-8') if 'message' in post else u'', # message
        str(post_details['created_time']), # created time
        str(post_details['from']['name']).encode('utf-8'), # name
        int(post_details['from']['id']), # profile id
    )
    _sql(sql, params, False)

    sql = "INSERT IGNORE INTO `Post_Updated` (`post_id`, `updated_time`) VALUES (%s, %s)"
    params = (int(post_id), str(post['updated_time']))
    _sql(sql, params, False)

def main():
    # create a table, destroying any already existing one first, then populate
    create_tables(drop=False)
    get_posts()

if __name__ == "__main__":
    main()
