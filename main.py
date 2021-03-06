#!/usr/bin/python
# encoding: utf-8

import os
import re
import sys
import json
import urllib
from time import time

import cache
from workflow import Workflow3, web, ICON_NOTE
from workflow.background import run_in_background, is_running

DISPLAY_DETAILS = True
EXTENDED_DEFINITION = False

REFRESH_RATE = 1.2

URL_SEARCH_SUGGEST_GET = "https://dle.rae.es/srv/keys?q="
URL_SEARCH_GET = "https://dle.rae.es/"


def get_rae_suggestions(word):
    url = URL_SEARCH_SUGGEST_GET + urllib.quote(word.encode('utf-8'))
    return web.get(url)


def get_url_for_word(word):
    return URL_SEARCH_GET + urllib.quote(word.encode('utf-8'))


def get_details_preview(details):
    first_article = next(iter(details), None)
    if first_article is None:
        return "No details found"
    meanings_list = first_article.get('meanings', [])
    return first_article.get('etymology', '') + " " +\
        next(iter(first_article.get('meanings', [])), '')

def get_details_full(details):
    details_str = ""
    for article in details:
        if article is None:
            continue
        details_str += article.get('title', '') + '\n-\n'
        details_str += article.get('etymology', '') + '\n\n'
        for meaning in article.get('meanings', []):
            details_str += meaning + '\n'
        details_str += '\n\n\n'
    return details_str


def is_details_empty(details):
    detail_preview = get_details_preview(details)
    return len(detail_preview) < 5 #check if string is long enough


def is_valid_args(args_str):
    return len(args_str.split()) <= 1 and \
        len(args_str) > 0


def get_menaing_strings_from_details(details):
    etymology = details.get('etymology', '')
    meanings = details.get('meanings', [])
    return [x for x in [etymology] + meanings if len(x) > 0]


def main(wf):

    if DISPLAY_DETAILS:
        from pyquery import PyQuery as pq

    input_word = ' '.join(wf.args)
    if not is_valid_args(input_word):
        wf.add_item(
            title="Invalid arguments.",
            subtitle="Type just one word. Insert space or select one to see definitions.",
            valid=False,
        )
        wf.send_feedback()
        return
    
    #word is selected when space is at end
    if re.search(r"\s$", input_word) is not None and EXTENDED_DEFINITION:
        selectedWord = input_word.strip()
        searchString = None
    else:
        selectedWord = None
        searchString = input_word.strip()
    

    if searchString is not None:
        res = wf.cached_data(searchString, max_age=0)
        if res is None:
            res = get_rae_suggestions(searchString).json()
            wf.cache_data(searchString, res)
        
        for word in res:
            
            # defaults 
            details_preview_str = ""
            details_full_str = ""

            if DISPLAY_DETAILS:
                details = wf.cached_data('details_' + word, max_age=0)
                if details is None:
                    
                    run_in_background(
                        'update_details_' + word,
                        [
                            '/usr/bin/python',
                            wf.workflowfile('update_details.py'),
                            word
                        ]
                    )
                    details_preview_str = "Loading details... "
                    wf.rerun = REFRESH_RATE
                else:
                    details_preview_str = get_details_preview(details)
                    details_full_str = get_details_full(details)
                    
            can_automcomplete = details is not None and not is_details_empty(details)
            
            wf.add_item(
                icon=None,
                title=word,
                quicklookurl=get_url_for_word(word) if can_automcomplete else None,
                autocomplete=word + " " if can_automcomplete else None,
                subtitle=details_preview_str,
                copytext=details_full_str,
                largetext=details_full_str
            )
            # .add_modifier(
            #     key='alt',
            #     subtitle='Full screen definition ',
            #     arg=details_full_str,
            #     valid=True,
            #     icon=ICON_NOTE
            # )
            
    # Temporarily disabled
    elif selectedWord is not None and EXTENDED_DEFINITION:
        details = wf.cached_data("details_" + selectedWord, max_age=0)
        if details is None:
            run_in_background(
                'update_details_' + selectedWord,
                [
                    '/usr/bin/python',
                    wf.workflowfile('update_details.py'),
                    word
                ]
            )
            details = []
            wf.rerun = REFRESH_RATE

        for detail in details:
            for item in get_menaing_strings_from_details(detail):
                wf.add_item(
                    icon=None,
                    title=item,
                )

    # Default option to search if no result found
    wf.add_item(
        icon="icon-search.png",
        title="Search on web",
        subtitle="Open search RAE for " + input_word,
        arg=get_url_for_word(searchString or selectedWord),
        valid=True,
    )

    # --- 
    # Send output to Alfred. You can only call this once.
    # Well, you *can* call it multiple times, but subsequent calls
    # are ignored (otherwise the JSON sent to Alfred would be invalid).
    # ----
    wf.send_feedback()


if __name__ == '__main__':
    # Create a global `Workflow3` object
    wf = Workflow3(libraries=[os.path.abspath(os.path.join(os.path.dirname(__file__), 'lib'))])
    # wf = Workflow3(libraries=[os.path.join(os.path.dirname(__file__), 'lib')])
    log = wf.logger
    # Call your entry function via `Workflow3.run()` to enable its
    # helper functions, like exception catching, ARGV normalization,
    # magic arguments etc.
    sys.exit(wf.run(main))