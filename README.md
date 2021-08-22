# arxiv-notification-bot
A bot that sends an email when a new paper matching a specified search query is published on the arXiv.

## Required Python Packages
  - arxiv: https://pypi.org/project/arxiv/
  - PyYAML: https://pypi.org/project/PyYAML/

## Usage
  1. Place `arxiv-notification-bot.py` and `arxiv-notification-config_default.yml` in the same directory in your system.
  2. Edit `arxiv-notification-config_default.yml` as described below and rename it to `arxiv-notification-config.yml`
  3. Run the script either as `python arxiv-notification-bot.py` or as `python arxiv-notification-bot.py [days]`, where `days` is an integer.
    In the first case the script searches for all papers matching your search query that have been published in the arXiv since the last time
    the script was run, in the second case the script searches for all matching papers published in the last `days` days.
  4. You'll receive an email with the names and abstracts of papers that where found. Additionally, the same information is written into a textfile
    specified in `arxiv-notification-config.yml`
  5. To run the script regularly you can for example let it start automatically on system startup.
  
## Configuration
  The script is configured in the configuration file `arxiv-notification-config.yml`. The different options are documented in the comments of the file.
  Because the password for the email adress from which the notifications are sent is not stored encrypted, I use a seperat email adress dedicted
  only to the `arxiv-notification-bot`.
