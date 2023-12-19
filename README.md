# The Doctor Professor's Handy Translator

![Room 264](https://static.wikia.nocookie.net/undertale/images/d/dd/Room_264_screenshot.gif)

Have your friends *just* discovered the front page of the internet, only to be corrupted by some abominable force of darkness and suddenly they start spewing *this* crapola?

Well, I can't fix your broken friends (they took my certification away for that), but I *can* fix your ability to understand them beyond recognition! (litigation pending)

(There is no pending litigation I just made that up for funnies)

---

The **Doctor Professor's Handy Translator** is a bot written in Python to monitor Reddit submissions and comments and translate any Wingdings discovered to readable text.

While this project does focus on translating unicode "Wingdings", technically it can also be used to substitute any configured unicode codepoints and translate them to other characters.

This may be useful to Undertale and Deltarune centric communities due to the use of Wingdings in their lore.

# Requirements

This bot requires Python 3.9 or later to run. May run on some earlier versions of 3.x but this is untested.

The only third party package required is `praw`, which can be installed using `pip install praw`.

This bot should be compatible with Windows, Mac OS, and Linux operating systems.

# Setup and execution

If you want to run this in a Python venv, make sure it is created and activated before going through the steps below:

1. Make sure `praw` is installed: `pip install praw`
2. Copy [`example.ini`](./example.ini) to `praw.ini`. Read the [PRAW.INI documentation](https://praw.readthedocs.io/en/stable/getting_started/configuration/prawini.html) to understand how to configure the PRAW client settings.
3. Copy [`config-example.json`](./config-example.json) to `config.json`, and update the list of subreddits. See [Configuration Settings](#configuration-settings) for more details on the bot configuration.
4. Assuming you are in this folder, run the bot with `python main.py`

## Install as a service

> Note: Installing as a service is ***not*** a requirement. This is simply a "nice-to-have".

### Windows

While this is possible on Windows via the use of [NSSM](https://nssm.cc), I'm not familiar enough with the tool to be able to provide instructions at this time. Windows services must implement a Windows-service control interface (the CPython interpreter does not), which is why special tooling is required to run "non-services" as a service.

As an alternative, you can use the Windows Task Scheduler to configure Python to run [`main.py`](./main.py) on boot or login.

### Linux

Included in this repo is a `systemd` service template, [`dpht.service-template`](./dpht-template.service). It can be installed as a `systemd` service with the following steps (the `systemd` folder may be elsewhere on non-Debian-based distributions of Linux):

1. Copy [`dpht-template.service`](./dpht-template.service) to `/etc/systemd/system/dpht.service`
2. Edit the following fields in `dpht.service`:
   - `User`: This should be the username you want the bot to run as on the local system.
   - `WorkingDirectory`: This should be a path to the folder containing [`main.py`](./main.py)
   - `ExecStart`: Change the path to the `python` executable in this field in the following situations:
      - If you want to use an alternative Python installation and not the system-configured one, provide the path to that `python` executable here.
      - If you want to use a venv'd Python instance, provide the path to the venv's `python` executable here.
      - If your system Python exists at a path other than `/usr/bin/python`
      - In the situations above, `main.py` still needs to be the first parameter to `python` (else it will just start the interactive interpreter).
3. You can now control the `dpht` service with the `service` command (e.g. `service dpht start|stop|restart|status`)

Example `dpht.service` which uses a venv'd Python instance:

```ini
[Unit]
Description=Doctor Professor's Handy Translator
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=on-failure
RestartPreventExitStatus=1 2
RestartSec=1
User=codewario
WorkingDirectory=/home/codewario/src/dpht
ExecStart=/home/codewario/src/dpht/venv/bin/python main.py

[Install]
WantedBy=multi-user.target
```

### Mac OS

I have no idea how to configure `launchd`. Instructions/pull requests are welcome for this one :)

# Configuration Settings

This section pertains to [`config.json`](./config-example.json) and the settings which can be set in it. `config.json` differs from [`praw.ini`](./example.ini) as `praw.ini` is for the Reddit client settings itself, while `config.json` deals with bot-specific behavior.

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
    - Default value: `info`
    - Example:
    ```json
    "log_level": "info"
    ```
    - Possible values:
        - `debug`: Very noisy, lots of logging output. Useful for troubleshooting and development. Not recommended for normal use.
        - `info`: Reasonable amount of logs for normal operation, useful for auditing which submissions and comments are responded to. Recommended for normal usage.
        - `warning`: Only log warning messages
        - `error`: Only log error messages
        - `critical`: Only log critical messages

- `log_path`
    - File path where the bot log file will be written to. Must have write permissions to the directory. Filename can be absolute or relative to the working directory when executing.
    - Default value: `dpht.log` (will be placed in current directory at time of execution)
    - Examples:
    ```json
    "log_path": "/tmp/dpht.log"
    ```
    ```json
    "log_path": "C:\\Temp\\dpht.log"
    ```

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
    - Mod permission: `Manage Posts and Comments`
    - Example:
    ```json
    "distinguish_reply": true
    ```

- `sticky_reply`
    - Set to `true` if the translation comment should be stickied. Only has an effect if `distinguish_reply` is `true` and the reply is to a post (as opposed to replying to a comment).
    - Default value: `false`
    - Mod permission: `Manage Posts and Comments`
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

# wdmap.json

> For a more in-depth explanation of surrogate pairs and variation selectors, [review this article](https://learn.microsoft.com/en-us/globalization/encoding/surrogate-pairs).

[`wdmap.json`](./wdmap.json) is the mapping of unicode codepoints for Wingdings characters to readable characters. It is laid out like this:

```json
{
    "unicode_to_char_map": {
        "264b": "a",
        ...
        "d8d3+de70": "j",
        ...
    }
}
```

Under the `unicode_to_char_map` object, each key is a 4-digit hexadecimal unicode codepoint representing a given Wingdings character, and its value is what the Wingdings character should be replaced with. In the example, unicode codepoint 264b will be translated to a lowercase `a`.

For characters that require surrogate pairs, you can represent this in the codepoint key by separating the high and low surrogate codepoints with a `+` symbol, as demonstrated in the `j` example above.

Variation selectors should be omitted from `wdmap.json` definitions. The reasoning is that the bot will strip the variation selector characters from Reddit content before evaluation, as they interfere with character detection and replacement since they are technically different characters.

If desired, `wdmap.json` can be updated for translating additional character sets or the general substitution of characters in text, if someone wanted to use the bot in this way. It's not limited to Wingdings despite Wingdings translation being its purpose.

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
