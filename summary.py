#!/usr/bin/env python
"""
Create medtech weekly summary pages

This utility fetches the medtech calendar feed, and then visit each event page
to scrape the required prep and other resources. 

Usage: 
    mt-summary.py [options] [<date>]

Arguments: 
    <date>              Week of interest

Options: 
    --user USER
    --pass PASS
    --ical URL          [default: http://meds.queensu.ca/central/calendars/2020.ics]
    --pre-post-week     Emit pages for the week, previous and following week
    --link-index-html   Link index.html to the current summary page
    --site-base URL     [default: http://jon.pipitone.ca/medtech]
    --verbose           
    --debug
    --test-mode
"""
from bs4 import BeautifulSoup
from dominate.tags import *
from dominate.util import *
import docopt
import collections
import datetime
import dateutil.parser
import dominate
import getpass
import icalendar as ical
import os
import os.path
import urlparse
import requests
import time

# SITE_BASE and MT_BASE are base urls for the summary page site and medtech,
# respectively.
MT_BASE = "http://meds.queensu.ca/central"
SITE_BASE = ""
VERBOSE = False
DEBUG = False
TESTMODE=False

def log(message, *args):
    if VERBOSE or DEBUG:
        print(str(message).format(*args))

def debug(message, *args): 
    if DEBUG:
        print("DEBUG: " + str(message).format(*args))

def create_week_summary_page(ical_data, login, date):
    """Do the work of create the summary page

    We expect an ical feed, and medtech login details, as well as date used to
    determine the week of interest.
    """
    # compute the dates for the start and end of the week
    # (we don't assume the date given was the start of the week)
    now = date.replace(hour=0, minute=0, second=0, microsecond=0)
    start = now - datetime.timedelta(days=now.weekday())
    end = start + datetime.timedelta(days=5)

    outputfile = '{}.html'.format(start.date())

    log("Building page {} for week starting {}", outputfile, start)

    # fetch events for the week and organize them by day
    log("Fetching events")
    weekday_events = collections.defaultdict(list)
    for event in ical.Calendar.from_ical(ical_data).walk("VEVENT"):
        event_date = event.decoded('dtstart').replace(tzinfo=None)
        if event_date < start or event_date > end:
            continue
        weekday_events[event_date.date()].append(event)

    # construct the summary webpage
    _html = dominate.document(title="Summary of week {}".format(start.date()))
    _html.head.add(base(href=MT_BASE))

    # steal css/script links from the medtech dashboard so that styling works
    page = requests.post(MT_BASE + '/dashboard', data=login)
    soup = BeautifulSoup(page.text, 'html.parser')
    for link in soup.find_all('link'):
        attrs = link.attrs
        if 'type' not in attrs or attrs['type'] != 'text/css':
            continue

        # make fully-qualified URLs for the stylesheets since they have a
        # different base
        _html.head.add(dominate.tags.link(
            href='https://meds.queensu.ca' + attrs['href'],
            media='media' in attrs and attrs['media'] or None,
            rel='stylesheet',
            type=attrs['type']))

    _html.head.add(script(type="text/javascript",
                          src="/central/javascript/jquery/jquery.min.js?release=4.6.0.0"))

    # some custome styling
    _html.head.add(style("""
        body { 
            margin: auto 10%; 
        }

        .no-prep h2 { 
            color: lightgrey; 
        } 

        .date, .event, .event-heading, .event-prep { 
            clear: both; 
        }
        .event-todo, .event-title {
            float: left;
        }
        .event-todo input { 
            margin: 20px 10px;
        }
        .event-prep { 
            padding-left: 40px;
        } 

        .icon-globe { 
            vertical-align: baseline;
        }
        """, type="text/css"))
    _html.head.add(meta(charset="utf-8"))
    _body = _html.body

    with _body.add(div(style=
        "padding: 10px; display: inline-block; width: 100%; "
        "background-color: rgba(255,255,25,0.1); border: thin dashed lightgrey;")):

        span("Note:", _class="label label-important event-resource-stat-label")
        text(" Click event headings to see preparation notes and materials.")

    # links for navigation from week to week
    with _body.add(div(style="overflow:hidden")):
        prev_week = (start - datetime.timedelta(weeks=1)).date()
        next_week = (start + datetime.timedelta(weeks=1)).date()
        div(a("<< prev week", href="{}/{}.html".format(SITE_BASE, prev_week)),
            style="float:left;")
        div(a("next week >>", href="{}/{}.html".format(SITE_BASE, next_week)), 
            style="float:right;")

    # finally, create the content
    for date in sorted(weekday_events.keys()):
        log("Fetching content for date {}", date)
        _body.add(h1(date.strftime("%a, %b %d %Y"), _class="date"))
        _datediv = div(style='padding-left: 10px; margin-bottom: 3em; clear: both; float: left;')
        _body.add(_datediv)

        for event in weekday_events[date]:
            eventurl = event['url']
            parsedurl = urlparse.urlparse(eventurl)
            parsedquery = urlparse.parse_qs(parsedurl.query)
            eventid = parsedquery["id"][0]

            with _datediv.add(div(_class="event")) as event_div: 
                with div(_class="event-heading") as event_heading:
                    with div(_class="event-todo"): 
                        input_(id="chk_{}".format(eventid), type="checkbox", _class="todo"),
                    with div(_class = "event-title"):
                        h2(
                            event.decoded('summary'),
                            a(
                                span(_class="icon-globe"),
                                href=eventurl, style="font-size: x-small",
                                target="_blank"), 
                        )

                with div(_class="event-prep") as prep_div:
                    # fetch the medtech page content for the date
                    debug("Fetching event page: {}", eventurl)
                    page = requests.post(eventurl, data=login)
                    soup = BeautifulSoup(page.text, 'html.parser')
                    
                    has_prep = False 

                    # extract the "required preparation" section
                    req = soup.find_all("h3", text="Required Preparation")
                    if req:
                        req.extend([e for e in req[0].next_siblings])
                        div(raw("".join(map(unicode, req))))
                        has_prep = True

                    # extract the event resources
                    res = soup.find_all(class_='resource-list')
                    for reslist in res: 
                        raw(unicode(reslist))
                        has_prep = True

                    if not has_prep:
                        event_heading['class'] += ' no-prep'

                    if TESTMODE and len(_datediv.get()) >= 3: 
                        break

    # a disclaimer
    with _body.add(div(style="clear: both;")):
        hr()
        p("Last Updated: {}".format(datetime.datetime.now()))
        p("""DISCLAIMER: Don't trust any of this. Updates occur once daily and
        reflect whatever MedTech is showing at that time. To Do list state is
        stored in your browser only.""")
        p("Contribute or suggest features/bugs at",
            a("github.com/pipitone/medtech-tools",
                href="https://github.com/pipitone/medtech-tools"))

    # inject some sweet javscript that makes headings collapse/expand
    # visibility of their associated content
    js = """
    $('h1').each(function(index, element) {
        $(this).click(function() { 
            $(this).next('div').toggle();
        });
    });

    $('.event-title').each(function(index, element) {
        $(this).parent('.event-heading').next('.event-prep').hide();
        $(this).click(function() { 
            $(this).parent('.event-heading').next('.event-prep').toggle();
        });
    });

    $('.todo').each(function(index, element) {
        $(this).prop('checked', localStorage.getItem($(this).attr('id')) == 'true');
        $(this).change(function() { 
            localStorage.setItem($(this).attr('id'), $(this).prop('checked'));
        });
    });
    """

    with _html.body: 
        script(js, type="text/javascript")
        script("""
            (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
            (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
            m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
            })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');

            ga('create', 'UA-84357249-1', 'auto');
            ga('send', 'pageview');
            """, type="text/javascript")

    pagefile = open(outputfile, 'wb')
    pagefile.write(_html.__unicode__().encode('utf8'))
    pagefile.close()
    return outputfile


def main():
    global VERBOSE, DEBUG, TESTMODE, SITE_BASE
    arguments = docopt.docopt(__doc__)
    VERBOSE = arguments['--verbose']
    DEBUG = arguments['--debug']
    TESTMODE = arguments['--test-mode']
    SITE_BASE = arguments['--site-base']

    nowdate = arguments['<date>'] and dateutil.parser.parse(
        arguments['<date>']) or datetime.datetime.now()

    log("Week of interest: {}", nowdate)

    login = {
        'username': arguments['--user'] or raw_input("MEdTech username: "),
        'password': arguments['--pass'] or getpass.getpass(),
        'submit': 'Login',
        'action': 'login'}

    ical_url = arguments['--ical']

    if os.path.exists('.cached-feed.ics'): 
        log("Using cached feed .cached-feed.ics")
        ical_data = open('.cached-feed.ics').read()
    else: 
        log("Fetching ical feed {}", ical_url)
        ical_r = requests.get(ical_url)
        ical_data = ical_r.text

    log("Building summary page...")
    outputfile = create_week_summary_page(ical_data, login, nowdate)

    if arguments['--link-index-html']:
        os.path.exists('index.html') and os.remove('index.html')
        os.symlink(outputfile, 'index.html')

    if arguments['--pre-post-week']:
        log("Building pre/post week summary pages...")
        create_week_summary_page(
            ical_data, login, nowdate - datetime.timedelta(weeks=1))
        create_week_summary_page(
            ical_data, login, nowdate + datetime.timedelta(weeks=1))

if __name__ == '__main__':
    main()
