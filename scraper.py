import facebook, requests, threading
import time
from datetime import datetime
import pymysql.cursors

from secrets import TOKEN, GROUPID
from secrets import DB_USER, DB_PASSWORD, DB_NAME

MAX_PAGES = 500

# Connect to the database
connection = pymysql.connect(host='localhost',
                             user=DB_USER,
                             password=DB_PASSWORD,
                             db=DB_NAME,
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)


class ScraperThread(threading.Thread):
    """Will run the scraper once every half hour"""

    def __init__(self, interval=1):
        """ Constructor
        :type interval: int
        :param interval: Check interval, in minutes
        """

        super(ScraperThread, self).__init__()
        self.interval = interval*6
        self.graph = facebook.GraphAPI(TOKEN)
        self.group = None

        """thread = threading.Thread(target=self.run, args=())
        thread.daemon = True                            # Daemonize thread
        thread.start()                                  # Start the execution"""

    def update_group(self):
        if not self.group:
            try:
                self.group = self.graph.get_object(GROUPID)
            except facebook.GraphAPIError:
                print("Page request reached, will retry in half an hour")
                self.group = None

    def run(self):
        """ Method that runs forever """
        while True:
            print("Getting posts...")
            self.get_posts()

            time.sleep(self.interval)

    def get_posts(self):
        """ Pulls all posts possible from facebook, getting the following details:
            Post text, date updated, id.
            id is in the format XXXXXXXXXXX_YYYYYYYYYYY, where the url of the post is
            https://facebook.com/XXXXXXXXXX/posts/YYYYYYYYYY, so we should break up the
            id into two components.

            During the pull, generator will put new posts into the database
            """

        try:
            self.update_group()
            posts = self.graph.get_connections(self.group['id'], 'feed')
            pages = 0
        except TypeError as e:
            return

        while(pages < MAX_PAGES):
            try:
                [self._do_post(post=post) for post in posts['data']]
                print("{} posts saved".format(self._sql("select count(*) as num from Post", (), True)[0]['num']))
                time.sleep(0.1)
                print("requesting next page...")
                posts = requests.get(posts['paging']['next']).json()

            except KeyError as e:
                break
            except TypeError as e:
                break

            pages += 1

    def create_tables(self, drop=False):
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

        self._sql(sql1, (), False)
        self._sql(sql2, (), False)
        self._sql(sql3, (), False)

    def _sql(self, sql, params, result=True):
        results = None
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql, params)
            connection.commit()
        except Exception as e:
            print("Error: {}".format(e))

        if result:
            return cursor.fetchall()

    def _do_post(self, post):
        # less costly option, check that the post isn't already in the database before we make API calls
        post_id = post['id'].split("_")[1]
        if self._sql("select count(*) as num from Post where post_id=%s", (post['id'].split("_")[1]))[0]['num'] is 1:

            check_updated = """select updated_time from Post_Updated where post_id=%s order by updated_time desc limit 1"""
            last_updated = datetime.strptime(post['updated_time'][:-5], "%Y-%m-%dT%H:%M:%S")
            last_updated_in_db = self._sql(check_updated, post_id)
            if last_updated_in_db is not ():
                last_updated_in_db = last_updated_in_db[0]['updated_time']
                if last_updated == last_updated_in_db:
                    print("Found last post since script run. Stopping...")
                    exit(0)

        # grab more post details
        post_details = self.graph.get_object(id=post_id,
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
        self._sql(sql, params, False)

        sql = "INSERT IGNORE INTO `Post_Updated` (`post_id`, `updated_time`) VALUES (%s, %s)"
        params = (int(post_id), str(post['updated_time']))
        self._sql(sql, params, False)
