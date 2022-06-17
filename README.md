# awatch-bot (DISCONTINUED)
Gets entries from https://www.abgeordnetenwatch.de/bundestag/abstimmungen and posts new entries to mastodon.

## Current Version
1.0

## Warning
This project is not suppost to run stable by any means. It is just a little side project for me. Feel free to adjust the code to your liking :D

## Requirements
- Python 3
- Mastodon.py

## Installation
- Copy the files to any directory.

- Fill in your information in credentials.json.

- urls.json keeps track of already posted entries.



This script is supposed to run with crontabs. Use the following:

`0 17 * * * cd /path/to/awatch-bot/ && ./main.py > /tmp/awatch-bot.log 2>&1`

Credit: https://stackoverflow.com/questions/29527469/executing-python3-file-with-a-cron-job/34735675#34735675

## Additional Information
I personally think this code is quite ugly but I will probably only add changes if I personally need them. If you really want to improve this mess feel free to make a pull request ^^
