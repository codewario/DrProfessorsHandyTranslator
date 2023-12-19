from praw import Reddit as f_praw_Reddit
from prawcore import exceptions as m_prawexceptions
from re import compile as f_re_compile
from re import MULTILINE as e_re_MULTILINE
from json import load as f_json_load
from os import getcwd as f_os_getcwd
from os.path import dirname as f_os_path_dirname
from os.path import join as f_os_path_join
from os.path import realpath as f_os_path_realpath
from time import sleep
from logging import DEBUG as e_log_DEBUG
from logging import INFO as e_log_INFO
from logging import WARNING as e_log_WARNING
from logging import ERROR as e_log_ERROR
from logging import CRITICAL as e_log_CRITICAL
from logging import debug as f_log_debug
from logging import info as f_log_info
from logging import warning as f_log_warning
from logging import error as f_log_error
from logging import critical as f_log_critical
from logging import basicConfig as f_log_basicConfig

# global variables
script_dir = f_os_path_dirname(f_os_path_realpath(__file__))
config_json_path = f_os_path_join(script_dir, 'config.json')
wdmap_json_path = f_os_path_join(script_dir, 'wdmap.json')
md_reserved_syntax = r'''!#^&*()`~-_+[{]}\|:<.>/'''
reddit_site = 'https://www.reddit.com'


def init_logging(data):
    log_level = e_log_INFO
    if 'log_level' in data:

        ll_val = data['log_level']

        if ll_val == 'debug':
            log_level = e_log_DEBUG
        elif ll_val == 'info':
            log_level = e_log_INFO
        elif ll_val == 'warning':
            log_level = e_log_WARNING
        elif ll_val == 'error':
            log_level = e_log_ERROR
        elif ll_val == 'critical':
            log_level = e_log_CRITICAL
        else:
            raise RuntimeError('Invalid log level specified, see https://docs.python.org/3/howto/logging.html#logging-levels for possible values')

        log_path = data['log_path'] if 'log_path' in data else 'dpht.log'

    f_log_basicConfig(
        filename=log_path,
        filemode='w' if 'overwrite_log' in data and data['overwrite_log'] else 'a',
        encoding='utf-8',
        level=log_level,
        format='%(asctime)s | %(levelname)s | PID:%(process)d %(message)s'
    )


def render_wd_map_code(mapcode, as_byte_string=False):
    render = ''
    for code in mapcode.split('+'):
        render += rf"\u{code}"
    render_cmd = u"'{0}'.encode('utf-16', 'surrogatepass')".format(render)
    if not as_byte_string:
        render_cmd += u".decode('utf-16')"
    return eval(render_cmd)


def get_charmap_from_utfmap(utfmap):
    # generate a character mapping from the decoded unicode mappings
    charmap = {}
    for wdcode in utfmap:
        decoded = render_wd_map_code(wdcode)
        charmap[decoded] = utfmap[wdcode]
    return charmap


def translate_text(text, charmap, flags=0, vs_chars=['\ufe0e', '\ufe0f']):
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


def remove_vs_chars(text, vs_chars=['\ufe0e', '\ufe0f']):
    result = text
    for char in vs_chars:
        result = result.replace(char, '')
    return result


def compile_charmap_expression(charmap, detect_threshold):
    # compile regex for character map detection
    char_str = u''.join(charmap.keys())
    expr = f"[{char_str}]{{{detect_threshold}}}"
    return f_re_compile(expr, flags=e_re_MULTILINE)


def init_reddit_client():
    reddit = f_praw_Reddit('dpht')

    # Fix the extra quotes that reading from praw.ini adds to these
    # fields for some reason
    reddit.config.username = reddit.config.username.replace('"', '')
    reddit.config.password = reddit.config.password.replace('"', '')
    reddit.config.client_id = reddit.config.client_id.replace('"', '')
    reddit.config.client_secret = reddit.config.client_id.replace('"', '')

    return reddit


def main():

    # load bot config (not praw stuff)
    with open(config_json_path, "r") as config:
        data = f_json_load(config)

    # load character remap config
    with open(wdmap_json_path, "r") as config:
        wdmap = f_json_load(config)['unicode_to_char_map']

    # variables from config
    monitor_mode = data['monitor_mode'].lower() if 'monitor_mode' in data else 'multi'
    skip_existing_on_start = data['skip_existing_on_start'] if 'skip_existing_on_start' in data else True
    waiting_period = data['waiting_period'] if 'waiting_period' in data else 60
    wd_detect_threshold = data['wd_detect_threshold'] if 'wd_detect_threshold' in data else 5
    distinguish_reply = data['distinguish_reply'] if 'distinguish_reply' in data else False
    sticky_reply = data['sticky_reply'] if 'sticky_reply' in data else False
    ignore_submissions = data['ignore_submissions'] if 'ignore_submissions' in data else False
    ignore_comments = data['ignore_comments'] if 'ignore_comments' in data else False

    reply_footer = '''
^(This reply is courtesy of the) [^(Dr. Professor's Handy Translator)](https://github.com/codewario/DrProfessorsHandyTranslator)^!

^(Issues? Report a problem on the) [^(issue tracker)](https://github.com/codewario/DrProfessorsHandyTranslator/issues)^.
'''

    # array of subreddits to monitor
    subreddits_list = data['subreddits'] if 'subreddits' in data else None

    init_logging(data)

    for i in range(3):
        f_log_info("================================================================================")

    f_log_info('Starting the Dr. Professor''s Handy Translator')
    f_log_info(f"Current working directory: {f_os_getcwd()}")

    try:
        # check config
        if subreddits_list is None or len(subreddits_list) < 1:
            f_log_critical('No subreddits configured to monitor, exiting')
            exit(1)

        if monitor_mode == 'multi' and len(subreddits_list) > 100:
            f_log_critical('Too many subreddits for multireddit mode (max 100)')
            exit(2)

        f_log_debug('Rendering charmap from wdmap')
        charmap = get_charmap_from_utfmap(wdmap)

        f_log_debug('Compiling expressions')
        wd_regex = compile_charmap_expression(charmap, wd_detect_threshold)

        # connect to reddit
        f_log_debug('Creating client')
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
        f_log_info(f"Monitoring subreddits: {', '.join(subreddits_list)}")
        while True:
            found_new = False

            # check each subreddit
            # each property reference results in an API call, so store what we can in variables
            # to reduce usage
            for subreddit in subreddits:
                subr_url = subreddit.url if monitor_mode != 'multi' else '+'.join(subreddits_list)
                subr_index = subreddits.index(subreddit)

                if not ignore_submissions:
                    f_log_debug(f"Checking {subr_url} for new submissions")

                    # set up stream if not done so already
                    if subm_streams[subr_index] is None:
                        subm_streams[subr_index] = subreddit.stream.submissions(skip_existing=skip_existing_on_start, pause_after=1)

                    subm_stream = subm_streams[subr_index]

                    # check incoming posts
                    for submission in subm_stream:
                        if submission is None:
                            break
                        found_new = True

                        try:
                            subm_title = remove_vs_chars(submission.title)
                            subm_text = remove_vs_chars(submission.selftext)
                            subm_shortlink = submission.shortlink

                            f_log_debug(f"Checking new submission: {subm_shortlink}")

                            # if we haven't replied and wingdings are present in the title or body
                            if wd_regex.search(subm_title) or wd_regex.search(subm_text):

                                f_log_info(f"Translating Wingdings in {subr_url} post: {subm_shortlink}")

                                # Translate detected wingdings here
                                # Comment reply should include original title and body with translated text replacing the wingdings
                                f_log_debug('Translating title')
                                t_title = translate_text(subm_title, charmap)
                                f_log_debug('Translating text')
                                t_text = translate_text(subm_text, charmap)

                                reply = f"""
Wingdings translation from the [above post]({subm_shortlink})

---

# Title: {t_title}

{t_text}

---

{reply_footer}
"""

                                # Post the reply comment
                                f_log_debug('Sending translation as reply')
                                try:
                                    result = submission.reply(reply)
                                    r_link = result.permalink
                                    if distinguish_reply:
                                        try:
                                            result.mod.distinguish(sticky=sticky_reply)
                                        except m_prawexceptions.PrawcoreException as e:
                                            f_log_warning(f"Failed to distinguish {r_link}: {e}")
                                except m_prawexceptions.PrawcoreException as e:
                                    f_log_error(e, stack_info=True, exc_info=True)
                        except Exception as e:
                            f_log_error(e, stack_info=True, exc_info=True)
                else:
                    f_log_debug('Ignoring submissions per configuration')

                # check incoming comments
                if not ignore_comments:
                    f_log_debug(f"Checking {subr_url} for new comments")

                    # set up stream if not done so already
                    if comm_streams[subr_index] is None:
                        comm_streams[subr_index] = subreddit.stream.comments(skip_existing=skip_existing_on_start, pause_after=1)

                    comm_stream = comm_streams[subr_index]

                    for comment in comm_stream:
                        if comment is None:
                            break
                        found_new = True

                        try:
                            comm_body = remove_vs_chars(comment.body)
                            # Comment permalink is not the full URL, it is the part of the URL after "https://www.reddit.com"
                            comm_link = f"{reddit_site}{comment.permalink}"

                            f_log_debug(f"Checking new comment: {comm_link}")

                            # if we haven't replied and wingdings are present in the body
                            if wd_regex.search(comm_body):

                                f_log_info(f"Translating Wingdings in comment: {comm_link}")

                                # Translate detected wingdings here
                                # Comment reply should include original body translated text replacing the wingdings
                                f_log_debug('Translating comment')
                                t_text = translate_text(comm_body, charmap)
                                reply = f"""
Wingdings translation from the [above comment]({comm_link})

---

{t_text}

---

{reply_footer}
"""

                                # Post the reply comment
                                f_log_debug('Sending translation as reply')
                                try:
                                    result = comment.reply(reply)
                                    r_link = result.permalink
                                    if distinguish_reply:
                                        try:
                                            result.mod.distinguish()
                                        except m_prawexceptions.PrawcoreException as e:
                                            f_log_warning(f"Failed to distinguish {r_link}: {e}")
                                except m_prawexceptions.PrawcoreException as e:
                                    f_log_error(e, stack_info=True, exc_info=True)
                        except Exception as e:
                            f_log_error(e, stack_info=True, exc_info=True)
                else:
                    f_log_debug('Ignoring comments per configuration')

            if not found_new:
                # If there were no posts to process, sleep 1 minute
                f_log_debug(f"Nothing new found, resting for {waiting_period}")
                sleep(waiting_period)
    except Exception as e:
        f_log_critical(e, stack_info=True, exc_info=True)

    exit(-1)


if __name__ == '__main__':
    main()
