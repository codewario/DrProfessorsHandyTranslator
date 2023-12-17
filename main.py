import praw
import re
import json
import logging as log
import os
from time import sleep

# path variables
script_dir = os.path.dirname(os.path.realpath(__file__))
config_json_path = os.path.join(script_dir, 'config.json')
wdmap_json_path = os.path.join(script_dir, 'wdmap.json')

# functions
def init_logging(data):
    log_level = log.INFO
    if 'log_level' in data:
        
        match data['log_level'].lower():
            case 'debug':
                log_level = log.DEBUG
            case 'info':
                log_level = log.INFO
            case 'warning':
                log_level = log.WARNING
            case 'error':
                log_level = log.ERROR
            case 'critical':
                log_level = log.CRITICAL
            case _:
                raise RuntimeError(f"Invalid log level specified, see https://docs.python.org/3/howto/logging.html#logging-levels for possible values")

    log.basicConfig(
        filename = 'dpht.log',
        filemode = 'w' if ('overwrite_log' in data and data['overwrite_log'] == True) else 'a',
        encoding = 'utf-8',
        level = log_level,
        format = '%(asctime)s | %(levelname)s | PID:%(process)d %(message)s'
    )

def render_wd_map_code(mapcode, as_byte_string = False):
    render = ''
    for code in mapcode.split('+'):
        render += rf"\u{code}"
    render_cmd = u"'{0}'.encode('utf-16', 'surrogatepass')".format(render)
    if not as_byte_string:
        render_cmd += u".decode('utf-16')"
    return eval(render_cmd)

# generate a character mapping from the decoded unicode mappings
def get_charmap_from_utfmap(utfmap):
    charmap = {}
    for wdcode in utfmap:
        decoded = render_wd_map_code(wdcode)
        charmap[decoded] = utfmap[wdcode]
    return charmap

# convert characters in text as defined in the character mapping
def translate_text(text, charmap, flags=0, vs_chars=['\ufe0e', '\ufe0f']):
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
        # repl = render_wd_map_code(char)
        translated = translated.replace(char, charmap[char])
    return translated

def remove_vs_chars(text, vs_chars=['\ufe0e', '\ufe0f']):
    result = text
    for char in vs_chars:
        result = result.replace(char, '')
    return result

# compile regex for character map detection
def compile_charmap_expression(charmap, detect_threshold):
    char_str = u''.join(charmap.keys())
    expr = f"[{char_str}]{{{detect_threshold}}}"
    return re.compile(expr, flags = re.MULTILINE)

def init_reddit_client():
    reddit = praw.Reddit('dpht')

    # Fix the extra quotes that reading from praw.ini adds to these
    # fields for some reason
    reddit.config.username = reddit.config.username.replace('"', '')
    reddit.config.password = reddit.config.password.replace('"', '')
    reddit.config.client_id = reddit.config.client_id.replace('"', '')
    reddit.config.client_secret = reddit.config.client_id.replace('"', '')

    return reddit

# Main Execution
def main():

    # load bot config (not praw stuff)
    with open(config_json_path, "r") as config:
        data = json.load(config)

    # load character remap config
    with open(wdmap_json_path, "r") as config:
        wdmap = json.load(config)['unicode_to_char_map']

    # variables from config
    monitor_mode = data['monitor_mode'].lower() if 'monitor_mode' in data else 'multi'
    skip_existing_on_start = data['skip_existing_on_start'] if 'skip_existing_on_start' in data else True
    waiting_period = data['waiting_period'] if 'waiting_period' in data else 60
    wd_detect_threshold = data['wd_detect_threshold'] if 'wd_detect_threshold' in data else 5
    distinguish_reply = data['distinguish_reply'] if 'distinguish_reply' in data else False
    sticky_reply = data['sticky_reply'] if 'sticky_reply' in data else False
    ignore_submissions = data['ignore_submissions'] if 'ignore_submissions' in data else False
    ignore_comments = data['ignore_comments'] if 'ignore_comments' in data else False

    # array of subreddits to monitor
    subreddits_list = data['subreddits'] if 'subreddits' in data else None

    init_logging(data)

    for i in range(3):
        log.info("================================================================================")

    log.info('Starting the Dr. Professor''s Handy Translator')
    log.info(f"Current working directory: {os.getcwd()}")

    # check config
    if subreddits_list is None or len(subreddits_list) < 1:
        log.error('No subreddits configured to monitor, exiting')
        exit(1)

    if monitor_mode == 'multi' and len(subreddits_list) > 100:
        log.error('Too many subreddits for multireddit mode (max 100)')

    log.debug('Rendering charmap from wdmap')
    charmap = get_charmap_from_utfmap(wdmap)

    log.debug('Compiling expressions')
    wd_regex = compile_charmap_expression(charmap, wd_detect_threshold)

    # connect to reddit
    log.debug('Creating client')
    reddit = init_reddit_client()

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
    while True:
        found_new = False

        # check each subreddit
        # each property reference results in an API call, so store what we can in variables
        # to reduce usage
        for subreddit in subreddits:
            subr_url = subreddit.url
            subr_index = subreddits.index(subreddit)

            if not ignore_submissions:
                log.debug(f"Checking {subr_url} for new submissions")

                # set up stream if not done so already
                if subm_streams[subr_index] is None:
                    subm_streams[subr_index] = subreddit.stream.submissions(skip_existing = skip_existing_on_start, pause_after = 1)
                
                subm_stream = subm_streams[subr_index]

                # check incoming posts
                for submission in subm_stream:
                    if submission is None:
                        break
                    found_new = True
                    subm_id = submission.id
                    subm_title = remove_vs_chars(submission.title)
                    subm_text = remove_vs_chars(submission.selftext)
                    subm_shortlink = submission.shortlink
                    
                    log.debug(f"Checking new submission: {subm_shortlink}")

                    # if we haven't replied and wingdings are present in the title or body
                    if wd_regex.search(subm_title) or wd_regex.search(subm_text):

                        log.info(f"Translating Wingdings in {subr_url} post id {subm_id}: {subm_shortlink}")

                        # Translate detected wingdings here
                        # Comment reply should include original title and body with translated text replacing the wingdings
                        log.debug('Translating title')
                        t_title = translate_text(subm_title, charmap)
                        log.debug('Translating text')
                        t_text = translate_text(subm_text, charmap)

                        reply = f"""
Wingdings translation from the [above post]({subm_shortlink})

---

# Title: {t_title}

{t_text}
    """

                        # Post the reply comment
                        log.debug('Sending translation as reply')
                        result = submission.reply(reply)
                        if distinguish_reply:
                            result.mod.distinughish(sticky = sticky_reply)
            else:
                log.debug('Ignoring submissions per configuration')

            # check incoming comments
            if not ignore_comments:
                log.debug(f"Checking {subr_url} for new comments")

                # set up stream if not done so already
                if comm_streams[subr_index] is None:
                    comm_streams[subr_index] = subreddit.stream.comments(skip_existing = skip_existing_on_start, pause_after = 1)
                
                comm_stream = comm_streams[subr_index]

                for comment in comm_stream:
                    if comment is None:
                        break
                    found_new = True
                    comm_id = comment.id
                    comm_body = remove_vs_chars(comment.body)
                    comm_link = comment.permalink

                    log.debug(f"Checking new comment: {comm_link}")

                    # if we haven't replied and wingdings are present in the body
                    if wd_regex.search(comm_body):

                        log.info(f"Translating Wingdings in comment id {comm_id}: {comm_link}")

                        # Translate detected wingdings here
                        # Comment reply should include original body translated text replacing the wingdings
                        log.debug('Translating comment')
                        t_text = translate_text(comm_body, charmap)
                        reply = f"""
Wingdings translation from the [above comment]({comm_link})

---

{t_text}
"""

                        # Post the reply comment
                        log.debug('Sending translation as reply')
                        comment.reply(reply)
            else:
                log.debug('Ignoring comments per configuration')

        if not found_new:
            # If there were no posts to process, sleep 1 minute
            log.debug(f"Nothing new found, resting for {waiting_period}")
            sleep(waiting_period)

if __name__ == '__main__':
    main()