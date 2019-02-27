from urllib.request import urlopen, urlretrieve
from html.parser import HTMLParser
import json
from mastodon import Mastodon
import os.path
import datetime
import time

BASE_URL = "https://www.abgeordnetenwatch.de"
KEY_FILE = "urls.json"
LOGIN_FILE = "credentials.json"
LOG_FILE = "history.log"


class Application:
    """Orchestrates the entire script."""

    def __init__(self):
        url = "{}/bundestag/abstimmungen".format(BASE_URL)
        html = urlopen(url).read().decode('utf-8')
        url_parser = URLParser()
        url_parser.feed(html)
        url_parser.remove_articles_without_results()
        pollhandler = PollHandler(url_parser.articles)
        pollhandler.load_archive_keys()
        pollhandler.set_missing_aricles()
        publisher = Publisher()
        publisher.publish_new(pollhandler.missing_articles)
        pollhandler.complement_archive_keys()
        logger = Logger()
        logger.log_execution()
        


class Publisher:
    """Interface to publish given articles."""

    def __init__(self):
        self.login_info = {}
        self._get_cedentials()
    
    def _get_cedentials(self):
        with open(LOGIN_FILE, "r", encoding="utf-8") as file:
            keys = file.read()
        if keys is not None:
            self.login_info = json.loads(keys)
        else:
            print("ERROR: No content in given file found.")
            return
        
    
    def publish_new(self, articles):
        """Responsible to publish the given articles to console for now."""
        
        mastodon = Mastodon(
            client_id = self.login_info["client_id"],
            client_secret = self.login_info["client_secret"],
            access_token = self.login_info["access_token"],
            api_base_url = self.login_info["api_base_url"]
        )


        for article in articles:
            url = article
            title = articles[article][0]
            pro = articles[article][1]
            contra = articles[article][2]
            
            winner = "---"
            if(articles[article][3] == 'left'):
                winner = "Pro"
            elif(articles[article][3] == 'right'):
                winner = "Contra"
            date = articles[article][4]
            image = articles[article][5]
            image_data = urlopen(image).read()
            print("Publish: %s - %s - %s - %s - %s - %s - %s" % (title,
                                                                 pro,
                                                                 contra,
                                                                 winner,
                                                                 date,
                                                                 url,
                                                                 image))

            media_id = mastodon.media_post(image_data, 'image/jpeg')
            post_message = ('Abstimmung im Bundestag: "{}"\n\n'
                           'Mit {} zu {} gewinnt die {}-Seite!\n\n'
                           'Datum: {}\n'
                           'Quelle: {}{}\n'
                           'Bild: Quelle siehe verlinkter Artikel\n'
                           '---\n'
                           '#abgeordnetenwatch #Bundestag #Abstimmung #Politik').format(title, pro, contra, winner, date, BASE_URL, url)
            mastodon.status_post(post_message, media_ids=media_id)



class PollHandler:
    """Uses the data from URLParser to evaluate the polls."""

    def __init__(self, data):
        self.data = data
        self.archive_keys = []
        self.missing_articles = {}

    def set_missing_aricles(self):
        """Fills the missing_articles property of PollHandler."""

        self.missing_articles = {}

        for article in self.data.keys():
            if article in self.archive_keys:
                pass
            else:
                self.missing_articles[article] = self.data[article]

    def complement_archive_keys(self):
        """Adds the missing articles to the archive (file)."""

        for article in self.missing_articles.keys():
            self.archive_keys.append(article)
        self.save_archive_keys(self.archive_keys)

    def load_archive_keys(self):
        """Sets the archive_keys property of PollHandler from the file."""

        self.archive_keys = []
        with open(KEY_FILE, "r", encoding="utf-8") as file:
            keys = file.read()
        if keys is not None:
            self.archive_keys = json.loads(keys)
        else:
            print("ERROR: No content in given file found.")
            return

    def save_archive_keys(self, keys):
        """Saves a list of keys to the KEY_FILE."""
        with open(KEY_FILE, 'w') as fp:
            json.dump(list(keys), fp)


class URLParser(HTMLParser):
    def __init__(self):
        self.in_article = False
        self.in_title = False
        self.in_content = False
        self.in_left = False
        self.in_right = False
        self.in_date = False
        self.current_winner = ''
        self.articles = {}
        self.current_link = ''
        self.current_title = ''
        self.current_left = -1
        self.current_right = -1
        self.current_date = ''
        self.current_image = ''
        HTMLParser.__init__(self)

    def handle_starttag(self, tag, attrs):
        # Detect beginning of a poll
        if tag == 'article':
            self.in_article = True
        # Detect the title of the poll
        elif tag == 'h2' and attrs[0][1] == "tile__title mh-item":
            self.in_title = True
        elif tag == 'a' and self.in_article and self.in_title:
            self.in_content = True
            self.current_link = self.get_href_from_attrs(attrs)
        # Detect the values of the poll
        elif tag == 'div' and "tile__pollchart__value_left" in self.\
                get_class_from_attrs(attrs) and self.in_article:
            self.in_left = True
            if "won" in attrs[0][1]:
                self.current_winner = 'left'
        # Detect winner of the poll
        elif tag == 'div' and "tile__pollchart__value_right" in self.\
                get_class_from_attrs(attrs) and self.in_article:
            self.in_right = True
            if "won" in attrs[0][1]:
                self.current_winner = 'right'
        # Detect date of the poll
        elif tag == 'span' and self.in_article:
            try:
                if "date-display-single" in self.get_class_from_attrs(attrs):
                    self.in_date = True
            except(IndexError):
                pass
        # Detect image
        elif tag == 'img' and self.in_article:
            self.current_image = self.get_src_from_attrs(attrs)

    def handle_endtag(self, tag):
        # Detect end of the poll and reset current values
        if tag == 'article':
            self.in_article = False
            self.articles[self.current_link] = (self.current_title,
                                                self.current_left,
                                                self.current_right,
                                                self.current_winner,
                                                self.current_date,
                                                self.current_image)
            self.current_winner = ''
            self.current_left = -1
            self.current_right = -1
            self.current_date = ''
        # Detect end of the title of the poll
        elif tag == 'h2' and self.in_article:
            self.in_title = False
        elif tag == 'a' and self.in_article and self.in_title:
            self.in_content = False
        # Detect end of the results of the poll
        elif tag == 'div' and (self.in_right or self.in_left):
            self.in_right = False
            self.in_left = False
        # Detect end of the date of the poll
        elif tag == 'span' and self.in_date:
            self.in_date = False

    def handle_data(self, data):
        # Retrieve title
        if self.in_article and self.in_title and self.in_content:
            self.current_title = data
        # Retrieve left number
        elif self.in_article and self.in_left:
            self.current_left = int(data)
        # Retrieve right number
        elif self.in_article and self.in_right:
            self.current_right = int(data)
        # Retrieve date
        elif self.in_article and self.in_date:
            self.current_date = data

    def get_href_from_attrs(self, attrs):

        # The attrs dict is a list of tuples like:
        #  [('href', 'www.google.com'), ('class', 'some-class')]
        for prop, val in attrs:
            if prop == 'href':
                return val
        return ''

    def get_src_from_attrs(self, attrs):
        for prop, val in attrs:
            if prop == 'src':
                return val
        return ''

    def get_class_from_attrs(self, attrs):
        for prop, val in attrs:
            if prop == 'class':
                return val
        return ''

    def remove_articles_without_results(self):
        for article in self.articles.keys():
            if self.articles[article][1] == -1 or self.articles[article][2] == -1:
                self.articles.pop(article)
      
            
class Logger:
    def __init__(self):
        pass
    
    def _check_for_logfile(self):
        if os.path.isfile(LOG_FILE):
            file = open(LOG_FILE, "w")
            
    def log_execution(self):
        ts = time.time()
        st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
        file_content = "Script has been successfully executet on {}.\n".format(st)
        with open(LOG_FILE, "a") as myfile:
            myfile.write(file_content)

class Article:
    # TODO: Introduce the article class for a better overview
    def __init__(self):
        self.winner = ''
        self.link = ''
        self.title = ''
        self.left = -1
        self.right = -1
        self.date = ''
        self.image = ''


if __name__ == "__main__":
    app = Application()
