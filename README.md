# The Doctor Professor's Handy Translator

![Room 264](https://static.wikia.nocookie.net/undertale/images/d/dd/Room_264_screenshot.gif)

Have your friends just discovered the internet, only to be corrupted by some abominable force of darkness and suddenly they start spewing this crapola?

Well, I can't fix your broken friends (they took my certification away for that), but I can fix your ability to understand them beyond recognition! (litigation pending)

(There is no pending litigation I just made that up for funnies)

---

The **Doctor-Professor's Handy Translator** is a bot written in Python to monitor Reddit submissions and comments and translate any Wingdings discovered to reabable text.

While this project does focus on translating unicode "Wingdings", technically it can also be used subsubstitute any configured unicode codepoints and translate them to other characters.

# Requirements

This bot requires Python 3.x to run. It has been tested on at least Python 3.11.

The only third party package required is `praw`, which can be installed using `pip install praw`.

# Setup and execution

If you want to run this in a Python venv, make sure it is created and activated before going through the steps below:

1. Make sure `praw` is installed `pip install praw`
2. Copy `example.ini` to `praw.ini`. Read the [PRAW.INI documentation](https://praw.readthedocs.io/en/stable/getting_started/configuration/prawini.html) to understand how to configure the PRAW client settings.
3. Copy `config-example.json` to `config.json`, and update the list of subreddits. See [Configuration Settings](#configuration-settings) for more details on the bot configuration.
4. Assuming you are in this folder, run the bot with `python main.py`

# Configuration Settings

This section pertains to `config.json` and the settings which can be set in it. `config.json` differs from `praw.ini` as `praw.ini` is for the Reddit client settings itself, while `config.json` deals with bot-specific behavior.

- `subreddits`
    - Required. An array of subreddits to monitor
    - Example: 
    ```json
    "subreddits": [
        "SubredditNameOne",
        "SubredditNameTwo"
    ]
    ```

- `log_level`
    - How noisy the logs should be. If the bot is particularly busy and the instance where this is running is low on space, you may want to set logging to a more exclusive level to reduce the disk space utilized by the log.
    - Example:
    ```json
    "log_level": "info"
    ```
    - Default value: `info`
    - Possible values:
        - `debug`: Very noisy, lots of logging output. Useful for troubleshooting and development. Not recommended for normal use.
        - `info`: Reasonable amount of logs for normal operation, useful for auditing which submissions and comments are responded to. Recommended for normal usage.
        - `warning`: Only log warning messages
        - `error`: Only log error messages
        - `critical`: Only log critical messages 

- `overwrite_log`
    - Set to `true` if you want the bot log to be overwritten each time the bot starts. If `false`, the existing log will be appended to instead.
    - Default value: `false`
    - Example:
    ```json
    "overwrite_log": true
    ```

- `wd_detect_threshold`
    - How many translatable characters need to match in a row before a translation will occur. This does not translate to a 1:1 string length since surrogate pairs may count double towards this threashold.
    - Default value: 5
    - Example:
    ```json
    "wd_detect_threshold": 5
    ```

- `skip_existing_on_start`
    - Set to `false` if you want to act on any posts that existed before this bot was running. Useful during development in a controlled environment, but `true` is recommended for normal operation as this may result in double-translations.
    - Default value: `true`
    - Example:
    ```json
    "skip_existing_on_start": false
    ```

- `monitor_mode`
    - Sets monitor method to `single` or `multi`. Single-mode will iterate over submissions, then comments, for each subreddit, while Multi-mode will take all configured subreddits and check them through an on-the-fly multi-reddit (custom feed). `multi` is recommended, unless you plan on having this bot check against more than 100 subreddits (which is the multi-reddit maximum).
    - Default value: `multi`
    - Example:
    ```json
    "monitor_mode": "multi"
    ```

- `waiting_period`
    - The number of seconds to sleep when no new submissions or comments have been found
    - Default value: 60
    - Example:
    ```json
    "waiting_period": 60
    ```

- `distinguish_reply`
    - Set to `true` if the translation comment should be mod-distinguished. Requires the bot-user to be a mod of that sub when replying.
    - Default value: `false`
    - Example:
    ```json
    "distinguish_reply": true
    ```

- `sticky_reply`
    - Set to `true` if the translation comment should be stickied. Only has an effect if `distinguish_reply` is `true` and the reply is to a post (as opposed to replying to a comment).
    - Default value: `false`
    - Example:
    ```json
    "sticky_reply": true
    ```

- `ignore_submissions`
    - Set to `true` if you don't want to process posts (submissions) for translation
    - Default value: `false`
    - Example:
    ```json
    "ignore_submissions": true
    ```

- `ignore_comments`
    - Set to `true` if you don't want to process comments for translation
    - Default value: `false`
    - Example:
    ```json
    "ignore_comments": true
    ```

# ☜︎☠︎❄︎☼︎✡︎ ☠︎🕆︎💣︎👌︎☜︎☼︎ 💧︎☜︎✞︎☜︎☠︎❄︎☜︎☜︎☠︎

👎︎✌︎☼︎😐︎ 👎︎✌︎☼︎😐︎☜︎☼︎ ✡︎☜︎❄︎ 👎︎✌︎☼︎😐︎☜︎☼︎

❄︎☟︎☜︎ 👎︎✌︎☼︎😐︎☠︎☜︎💧︎💧︎ 😐︎☜︎☜︎🏱︎💧︎ ☝︎☼︎⚐︎🕈︎✋︎☠︎☝︎

❄︎☟︎☜︎ 💧︎☟︎✌︎👎︎⚐︎🕈︎💧︎ 👍︎🕆︎❄︎❄︎✋︎☠︎☝︎ 👎︎☜︎☜︎🏱︎☜︎☼︎

🏱︎☟︎⚐︎❄︎⚐︎☠︎ ☼︎☜︎✌︎👎︎✋︎☠︎☝︎💧︎ ☠︎☜︎☝︎✌︎❄︎✋︎✞︎☜︎

❄︎☟︎✋︎💧︎ ☠︎☜︎✠︎❄︎ ☜︎✠︎🏱︎☜︎☼︎✋︎💣︎☜︎☠︎❄︎

💧︎☜︎☜︎💣︎💧︎

✞︎☜︎☼︎✡︎

✞︎☜︎☼︎✡︎

✋︎☠︎❄︎☜︎☼︎☜︎💧︎❄︎✋︎☠︎☝︎

📬︎📬︎📬︎

🕈︎☟︎✌︎❄︎ 👎︎⚐︎ ✡︎⚐︎🕆︎ ❄︎🕈︎⚐︎ ❄︎☟︎✋︎☠︎😐︎