#!/usr/bin/env python
"""
Download medtech event resources

This utility fetches the medtech calendar feed, and then visit each event page
to downloads attached resources. 

Usage: 
    mt-download.py [options] [<date>]

Options: 
    --user USER
    --pass PASS
    --ical URL          [default: http://meds.queensu.ca/central/calendars/2021.ics]
    -v --verbose           
    --debug
"""
from __future__ import print_function
from bs4 import BeautifulSoup
from termcolor import colored as color
import datetime
import dateutil.parser
import docopt
import getpass
import icalendar as ical
import os.path
import requests
import shutil
import urlparse

VERBOSE = False
DEBUG = False

def debug(message): 
    if DEBUG: 
        print(color(message, 'white'))

def log(message):
    if VERBOSE:
        print(color(message, 'white'))

def download_resources(ical_data, login, fromdate):
    """Visit each event and download attached resources

    We expect an ical feed, and medtech login details.
    """

    if fromdate:
        log(color("Ignoring dates earlier than {}".format(fromdate), 'yellow'))

    # finally, create the content
    for event in ical.Calendar.from_ical(ical_data).walk("VEVENT"):
        date = event.decoded('dtstart').replace(tzinfo=None)

        if fromdate and date < fromdate: 
            continue

        # fetch the medtech page content for the date
        url = event['url']
        page = requests.post(url, data=login)
        soup = BeautifulSoup(page.text, 'html.parser')
        
        try:     
            course_code = soup.find(id='page-top').find_previous('a').text.split(":")[0]
            formatted_date = date.strftime("%Y-%m-%d")
            class_title = soup.find(id='page-top').text
        except AttributeError, e: 
            log("Malformed page at url: {}".format(url))

        # fetch all resources
        for link in soup.find_all("a", class_="resource-link"):
            try: 
                _, fileid =  link.attrs['href'].split('=')
            except:
                continue

            source_url = r"https://meds.queensu.ca/central/?url=%2Fmedicine%2Ffile-event.php%3Fid%3D"+fileid

            r = requests.post(source_url, data=login, stream=True)

            if 'Content-Disposition' not in r.headers: 
                log(color("Skipping: ", 'cyan') + link.attrs['href'] + " from " + event['url'] + color(" [No content disposition]", 'red'))
                continue

            label = link.find_next(class_="label-info")
            if not label: 
                log(color("Skipping: ", 'cyan') + link.attrs['href'] + " from " + event['url'] + color(" [No label]", 'red'))
                continue

            if not (label.text.endswith("KB") or label.text.endswith("MB")): 
                log(color("Skipping: ", 'cyan') + link.attrs['href'] + " from " + event['url'] + color(" [No file size]", 'red'))
                continue

            # dirty removal of file size
            file_kind = " ".join(label.text.split()[:-2]) 
            
            source_filename = r.headers['Content-Disposition'].split('filename=')[-1].strip('"')
            target_filename = "data/" + " - ".join([course_code, formatted_date, class_title, file_kind, source_filename]).replace('/','_')
            target_filename = target_filename.replace('\n','')[:250]

            if target_filename.endswith(".mp3"): 
                continue

            if os.path.exists(target_filename): 
                log(color("Skipping: ", 'cyan') + target_filename + color(" [File exists]", 'red'))
                continue
            else:
                log(color("Downloading: ", 'cyan') + target_filename)
                with open(target_filename, 'wb') as f:
                    r.raw.decode_content = True
                    shutil.copyfileobj(r.raw, f)

def main():
    global VERBOSE, DEBUG
    arguments = docopt.docopt(__doc__)
    VERBOSE = arguments['--verbose']
    DEBUG = arguments['--debug']

    debug(arguments)

    fromdate = arguments['<date>'] and \
        dateutil.parser.parse(arguments['<date>']) or None

    login = {
        'username': arguments['--user'] or raw_input("MEdTech username: "),
        'password': arguments['--pass'] or getpass.getpass(),
        'submit': 'Login',
        'action': 'login'}

    log("Downloading calendar...")
    ical_url = arguments['--ical']
    ical_r = requests.get(ical_url)
    ical_data = ical_r.text

    log("Downloading resources...")
    download_resources(ical_data, login, fromdate)

if __name__ == '__main__':
    main()
