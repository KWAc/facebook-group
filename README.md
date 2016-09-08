# Facebook Group Moderation
A tool to help moderate Facebook groups, using Python3 and [facebook-sdk](https://github.com/mobolic/facebook-sdk)

Currently, there exists a script `start.py`, which will pull up to 625 posts (25 pages, 25 posts per page) from the Facebook group of your choice, and store it in a database.

Suggestions and PR's are more than welcome. I'm looking for help to build out this tool since I couldn't find anything else that does the job out there, so even if you don't code shoot me suggestions for things that you want to be able to moderate in a Facebook group!

## Deploying
### Installing dependencies
```
sudo apt-get install python3 git
git clone git@github.com:nylonee/facebook-group.git
cd facebook-group
virtualenv env -p /usr/bin/python3
source env/bin/activate
pip install -r requirements.txt --upgrade
```

### Setting up database
The script requires a MySQL database to be set up. These instructions are for getting the database working out of the box.
```
sudo apt-get update
sudo apt-get install mysql-server
mysql -u root -p
> CREATE DATABASE facebook;
> GRANT ALL PRIVILEGES ON facebook.* To 'user'@'localhost' IDENTIFIED BY 'password';
> exit
```


## Running
First, you will need the ID of the group you want to pull posts from, and a token.
 See [here](http://findmyfbid.com/) for a good way to find your group ID, and [here](http://stackoverflow.com/questions/17197970/facebook-permanent-page-access-token) for creating a permanent group access token.  

Once you've got both bits of information, create your secrets.py file:
```
printf '%s\n' 'TOKEN = "YOUR_TOKEN_GOES_HERE"' 'GROUPID = "YOUR_GROUP_ID"' 'DB_USER = "user"' 'DB_PASSWORD = "password"' 'DB_NAME = "facebook"'> secrets.py
```

And run the post scraper:
```
python start.py
```

To run the web interface:
```
python interface.py
```
And navigate to `http://localhost:5000` in your web browser

## Roadmap

At the time of writing (1 September 2016), all that exists is a script `start.py` that pulls posts and stores them in a database, and stores every time the post has been updated. There is also a very basic single HTML table view in `interface.py`. This is pretty hacky, but it's baby steps towards the end goal of having a full Facebook group moderation tool eventually.

 * Create a web interface for seeing all posts that have been pulled, sorted by created_time, or by updated_time (in Flask)
 * Allow admins of the group to log in
 * Admins are able to 'approve' of posts using the web interface, or flag posts
 * Pull number of comments for each post, and store in the database
