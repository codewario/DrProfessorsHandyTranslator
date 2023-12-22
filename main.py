from praw import Reddit
from prawcore import exceptions as prawexceptions
from praw.models import Comment, Submission
import re
import json
import logging as log
import os
import signal
from time import sleep
from sys import platform

# global variables
script_dir = os.path.dirname(os.path.realpath(__file__))
config_json_path = os.path.join(script_dir, 'config.json')
wdmap_json_path = os.path.join(script_dir, 'wdmap.json')
md_reserved_syntax = r'''!#^&*()`~-_+[{]}\|:<.>/'''
reddit_site = 'https://www.reddit.com'
hup_received = False
exit_signaled = False
processed_ids = []

# load these later
data = None
wdmap = None


def init_logging(data: dict):
    log_level = log.INFO
    if 'log_level' in data:

        ll_val = data['log_level']

        if ll_val == 'debug':
            log_level = log.DEBUG
        elif ll_val == 'info':
            log_level = log.INFO
        elif ll_val == 'warning':
            log_level = log.WARNING
        elif ll_val == 'error':
            log_level = log.ERROR
        elif ll_val == 'critical':
            log_level = log.CRITICAL
        else:
            raise RuntimeError('Invalid log level specified, see https://docs.python.org/3/howto/logging.html#logging-levels for possible values')

        log_path = data['log_path'] if 'log_path' in data else 'dpht.log'

    log.basicConfig(
        filename=log_path,
        filemode='w' if 'overwrite_log' in data and data['overwrite_log'] else 'a',
        encoding='utf-8',
        level=log_level,
        format='%(asctime)s | %(levelname)s | PID:%(process)d %(message)s',
        force=True
    )


def signal_handler(signum: int, frame):
    global exit_signaled
    global hup_received

    # not much to do on cleanup but we do want to log the received signal
    message = None
    if signum == signal.SIGTERM:
        message = '***** SIGTERM RECEIVED *****'
        exit_signaled = True
    elif signum == signal.SIGINT:
        message = '***** SIGINT RECEIVED *****'
        exit_signaled = True
    elif (platform == 'linux' or platform == 'darwin') and signum == signal.SIGHUP:
        message = '***** SIGHUP RECEIVED *****'
        hup_received = True

    if message:
        log.critical(message)


def render_wd_map_code(mapcode: str, as_byte_string: bool = False) -> str:
    render = ''
    for code in mapcode.split('+'):
        render += rf"\u{code}"
    render_cmd = u"'{0}'.encode('utf-16', 'surrogatepass')".format(render)
    if not as_byte_string:
        render_cmd += u".decode('utf-16')"
    return eval(render_cmd)


def get_charmap_from_utfmap(utfmap: dict) -> dict:
    # generate a character mapping from the decoded unicode mappings
    charmap = {}
    for wdcode in utfmap:
        decoded = render_wd_map_code(wdcode)
        charmap[decoded] = utfmap[wdcode]
    return charmap


def translate_text(text: str, charmap: dict, vs_chars=['\ufe0e', '\ufe0f']) -> str:
    # convert characters in text as defined in the character mapping
    if not text:
        return ''
    elif not isinstance(text, str):
        raise TypeError('input must be a string')

    # remove variation selectors
    translated = text
    for char in vs_chars:
        translated = translated.replace(char, '')

    # replace characters as mapped
    for char in charmap:
        translated = translated.replace(char, charmap[char])
    return translated


def remove_vs_chars(text: str, vs_chars: list[str] = ['\ufe0e', '\ufe0f']) -> str:
    result = text
    for char in vs_chars:
        result = result.replace(char, '')
    return result


def compile_charmap_expression(charmap: dict, detect_threshold: int) -> re.Pattern:
    # compile regex for character map detection
    char_str = u''.join(charmap.keys())
    expr = f"[{char_str}]{{{detect_threshold}}}"
    return re.compile(expr, flags=re.MULTILINE)


def item_replied(reddit_username: str, item: [Comment, Submission]) -> bool:
    if isinstance(item, Submission):
        my_replies = [comment.author.name == reddit_username if comment.author else False for comment in item.comments]
        returner = any(my_replies)
        return returner

    # if not a submission assume it's a comment
    item.refresh()
    my_replies = [reply.author.name == reddit_username if reply.author else False for reply in item.replies]
    returner = any(my_replies)
    return returner


def fetch_unprocessed_comment_mentions(reddit: Reddit, username=None, limit: int = 50) -> list[str]:
    global processed_ids

    use_username = username if username else reddit.config.username
    new_mentions = []
    for item in reddit.inbox.mentions(limit=limit):

        if isinstance(item, Submission):
            # don't process mentions in submissions
            continue
        elif item.fullname in processed_ids:
            # skip any mentions we're already aware of
            continue
        elif not re.search(rf"^\s*\/?u\/{use_username}\s*$", item.body, flags=re.IGNORECASE | re.MULTILINE):
            # only process mentions that are only tagging the bot
            continue

        parent = item.parent()

        if parent.fullname in processed_ids:
            # don't waste API calls if we know we processed the parent
            continue

        if item_replied(use_username, parent):
            # check that we haven't already replied in real time
            # if yes, add it to the known list
            processed_ids.extend([parent.fullname, item.fullname])
            continue

        # if we haven't replied, go ahead and return this as a new one
        new_mentions.append(item)
    return new_mentions


def check_and_translate_item(
        item: [Comment, Submission],
        detect_pattern: re.Pattern,
        charmap: dict,
        distinguish: bool = False,
        sticky: bool = False) -> Comment:

    global processed_ids
    is_post = isinstance(item, Submission)
    returner = None

    title = remove_vs_chars(item.title) if is_post else ''
    text = remove_vs_chars(item.selftext if is_post else item.body)
    link = item.shortlink if is_post else f"{reddit_site}{item.permalink}"

    log.debug(f"Checking submission: {link}")

    if detect_pattern.search(title) or detect_pattern.search(text):

        log.info(f"Translating {'post' if is_post else 'comment'}: {link}")

        log.debug('Translating title')
        t_title = translate_text(title, charmap) if title else None

        log.debug('Translating text')
        t_text = translate_text(text, charmap)

        reply = f"""
{f"# Title: {t_title}" if t_title else ''}

{t_text}

---

^(This is a Wingdings translation from the) [^(above {'post' if is_post else 'comment'})]({link})^(. This reply is courtesy of the) [^(Dr. Professor's Handy Translator)](https://github.com/codewario/DrProfessorsHandyTranslator)^!

^(Issues? Report a problem on the) [^(issue tracker)](https://github.com/codewario/DrProfessorsHandyTranslator/issues)^.
"""

        log.debug('Sending translation as reply')

        result = item.reply(reply)
        if distinguish:
            try:
                result.mod.distinguish(sticky=sticky)
            except prawexceptions.PrawcoreException as e:
                log.warning(f"Failed to distinguish {reddit_site}{result.permalink}: {e}")
        returner = result
    return returner


def init_reddit_client() -> Reddit:
    reddit = Reddit('dpht')

    # Fix the extra quotes that reading from praw.ini adds to these
    # fields for some reason
    reddit.config.username = reddit.config.username.replace('"', '')
    reddit.config.password = reddit.config.password.replace('"', '')
    reddit.config.client_id = reddit.config.client_id.replace('"', '')
    reddit.config.client_secret = reddit.config.client_id.replace('"', '')

    return reddit


def load_data_and_map(config_json_path: str, wdmap_json_path: str):
    global data
    global wdmap

    # load bot config (not praw stuff)
    with open(config_json_path, "r") as config:
        data = json.load(config)

    # load character remap config
    with open(wdmap_json_path, "r", encoding='utf-16') as config:
        wdmap = json.load(config)['unicode_to_char_map']


def main() -> int:
    load_data_and_map(config_json_path, wdmap_json_path)

    # variables from configs
    monitor_mode = data['monitor_mode'].lower() if 'monitor_mode' in data else 'multi'
    skip_existing_on_start = data['skip_existing_on_start'] if 'skip_existing_on_start' in data else True
    waiting_period = data['waiting_period'] if 'waiting_period' in data else 60
    wd_detect_threshold = data['wd_detect_threshold'] if 'wd_detect_threshold' in data else 5
    distinguish_reply = data['distinguish_reply'] if 'distinguish_reply' in data else False
    sticky_reply = data['sticky_reply'] if 'sticky_reply' in data else False
    ignore_submissions = data['ignore_submissions'] if 'ignore_submissions' in data else False
    ignore_comments = data['ignore_comments'] if 'ignore_comments' in data else False
    ignore_mentions = data['ignore_mentions'] if 'ignore_mentions' in data else False
    mention_limit = data['mention_limit'] if 'mention_limit' in data else 100

    # array of subreddits to monitor
    subreddits_list = data['subreddits'] if 'subreddits' in data else None

    init_logging(data)

    for i in range(3):
        log.info("================================================================================")

    log.info('Starting the Dr. Professor''s Handy Translator')
    log.info(f"Current working directory: {os.getcwd()}")

    returner = 0

    try:
        # set up signal handlers
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        if platform == 'linux' or platform == 'macos':
            signal.signal(signal.SIGHUP, signal_handler)

        # check config
        if monitor_mode == 'multi' and len(subreddits_list) > 100:
            log.critical('Too many subreddits for multireddit mode (max 100)')
            exit(2)

        log.debug('Rendering charmap from wdmap')
        charmap = get_charmap_from_utfmap(wdmap)

        log.debug('Compiling expressions')
        wd_regex = compile_charmap_expression(charmap, wd_detect_threshold)

        # connect to reddit
        log.debug('Creating client')
        reddit = init_reddit_client()
        username = reddit.config.username

        # initialize arrays of subreddit objects
        subreddits = []
        if monitor_mode == 'multi':
            # multireddit name is made by joining all sub names with a plus
            subreddits.append(reddit.subreddit('+'.join(subreddits_list)))
        else:
            for subreddit_name in subreddits_list:
                subreddits.append(reddit.subreddit(subreddit_name))

        subm_streams = [None] * len(subreddits)
        comm_streams = [None] * len(subreddits)

        # begin monitoring
        log.info(f"Monitoring subreddits: {', '.join(subreddits_list)}")
        while not exit_signaled and not hup_received:
            found_new = False

            # check each subreddit
            for subreddit in subreddits:
                subr_url = subreddit.url if monitor_mode != 'multi' else '+'.join(subreddits_list)
                subr_index = subreddits.index(subreddit)

                if not ignore_submissions:
                    log.debug(f"Checking {subr_url} for new submissions")

                    # set up stream if not done so already
                    if subm_streams[subr_index] is None:
                        subm_streams[subr_index] = subreddit.stream.submissions(skip_existing=skip_existing_on_start, pause_after=1)

                    subm_stream = subm_streams[subr_index]

                    # check incoming posts
                    for submission in subm_stream:
                        if submission is None:
                            break

                        if submission.id not in processed_ids and not item_replied(reddit.config.username, submission):
                            found_new = True
                            try:
                                check_and_translate_item(submission, wd_regex, charmap, distinguish_reply, sticky_reply)
                                processed_ids.append(submission.fullname)
                            except prawexceptions.PrawcoreException as e:
                                log.error(f"Error processing submission: {submission.shortlink}")
                                log.error(e, stack_info=True, exc_info=True)
                else:
                    log.debug('Ignoring submissions per configuration')

                # check incoming comments
                if not ignore_comments:
                    log.debug(f"Checking {subr_url} for new comments")

                    # set up stream if not done so already
                    if comm_streams[subr_index] is None:
                        comm_streams[subr_index] = subreddit.stream.comments(skip_existing=skip_existing_on_start, pause_after=1)

                    comm_stream = comm_streams[subr_index]

                    for comment in comm_stream:
                        if comment is None:
                            break

                        if comment.id not in processed_ids and not item_replied(reddit.config.username, comment):
                            found_new = True
                            try:
                                check_and_translate_item(comment, wd_regex, charmap, distinguish_reply, sticky_reply)
                                processed_ids.append(comment.fullname)
                            except prawexceptions.PrawcoreException as e:
                                log.error(f"Error processing comment: {reddit_site}{comment.permalink}")
                                log.error(e, stack_info=True, exc_info=True)
                else:
                    log.debug('Ignoring comments per configuration')

            # check explicit mentions
            if not ignore_mentions:
                log.debug(f"Checking for new mentions of {username} (max {mention_limit})")

                mentions = fetch_unprocessed_comment_mentions(reddit, username, mention_limit)
                for mention in mentions:
                    found_new = True

                    try:
                        response = check_and_translate_item(mention.parent(), wd_regex, charmap, distinguish_reply, sticky_reply)
                        processed_ids.extend([mention.fullname, mention.parent_id])
                        if response:
                            log.info(f"Responding to mentioner: {reddit_site}{mention.context}")
                            mention.reply(f"[Translation available here]({reddit_site}{response.permalink})")
                    except prawexceptions.PrawcoreException as e:
                        log.error(e, stack_info=True, exc_info=True)

            if not found_new and not exit_signaled and not hup_received:
                # If there were no posts to process, sleep 1 minute
                log.debug(f"Nothing new found, resting for {waiting_period}")

                # sleep in intervals, as we need to check for interrupt processing periodically
                waited_for = 0
                iter_sleep = 5

                while waited_for < waiting_period:
                    # while waiting, check for interrupt signals
                    if not hup_received and not exit_signaled:
                        sleep(iter_sleep)
                        waited_for += iter_sleep
                    else:
                        break
    except Exception as e:
        returner = -1
        log.critical(e, stack_info=True, exc_info=True)

    return returner


if __name__ == '__main__':
    # the main() loop will run until either sighup, sigterm, or sigint are received
    # if main() exited due to sighup, it will continue to loop here, effectively
    # reloading the configuration and re-initializing
    exitcode = 0
    while not exit_signaled:
        hup_received = False
        exitcode = main()
    exit(exitcode)
