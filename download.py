#!/usr/bin/env python3
"""
Download medtech event resources

This utility fetches the medtech calendar feed, and then visit each event page
to downloads attached resources. 

Usage: 
    mt-download.py [options] [<date>]

Options: 
    --user USER
    --pass PASS
    --ical URL          [default: https://elentra.healthsci.queensu.ca/calendars/private-4fd4cecfffb5cde02dce2afdb81545d9/15jcp4.ics]
    --youtube-dl        Display youtube-dl commands for video links
    --dry-run        
    -v --verbose           
    --debug
"""
# --ical URL          [default: http://meds.queensu.ca/central/calendars/2021.ics]
from bs4 import BeautifulSoup
from termcolor import colored as color
import datetime
import dateutil.parser
import docopt
import getpass
import icalendar as ical
import os.path
import mechanize
import requests
import cgi
import shutil
import re

VERBOSE = False
DEBUG = False
YTDL = False
DRYRUN = False

def debug(message): 
    if DEBUG: 
        print(color(message, 'white'))

def log(message):
    if VERBOSE or DEBUG:
        print(color(message, 'white'))

def download_resources(ical_data, login, fromdate):
    """Visit each event and download attached resources

    We expect an ical feed, and medtech login details.
    """

    if fromdate:
        log(color("Ignoring dates earlier than {}".format(fromdate), 'yellow'))

    # login
    br = mechanize.Browser()
    r = br.open('https://elentra.healthsci.queensu.ca')
    br.select_form(nr=0)
    br['username'] = login['username']
    br['password'] = login['password']
    br.submit()

    # finally, create the content
    for event in ical.Calendar.from_ical(ical_data).walk("VEVENT"):
        date = event.decoded('dtstart').replace(tzinfo=None)

        if fromdate and date < fromdate: 
            continue

        # fetch the medtech page content for the date
        url = event['url']
        br.open(url)
        soup = BeautifulSoup(br.response().read(), 'html.parser')
        
        audience = soup.find('a', href=re.compile('^#audience'))
        if not audience: 
            log("Skipping " + url + " as does not appear to be for our class.")
            continue
        if audience.text != 'Class of 2020': 
            log("Skipping " + url + " as does not appear to be for our class: " + audience.text)
            continue

        try:     
            course_code = soup.find('a', href=re.compile('courses.id')).text.split(":")[0]
            formatted_date = date.strftime("%Y-%m-%d")
            class_title = soup.find('h1', class_='event-title').text
        except AttributeError as e: 
            log("Malformed page at url: {}".format(url))
            log(e)
            continue

        
        if YTDL: 
            target_filename = " ".join([course_code, formatted_date, class_title]).replace('/','_')

            # video links
            for link in soup.find_all('a', title=re.compile('stream.queensu.ca')): 
                url = re.search('https.*', link.get('title')).group(0)
                cmd = 'youtube-dl -o "'+target_filename+' - video.mp4" -q --no-warnings '+url
                log(cmd)
                open('youtube-dl.txt', 'a').write(cmd+'\n')

        # fetch all resources
        for link in soup.find_all("a", class_="resource-link", href=re.compile('file-event')):
            try: 
                _, fileid =  link.attrs['href'].split('=')
            except:
                continue

            source_url = r'https://elentra.healthsci.queensu.ca/file-event.php?id='+ fileid

            r = br.open(source_url)
            cd = r.info().getheader('Content-Disposition')
            if not cd:  
                log(color("Skipping: ", 'cyan') + link.attrs['href'] + " from " + event['url'] + color(" [No content disposition]", 'red'))
                continue

            _, cd_params = cgi.parse_header(cd)
            source_filename = '- ' + cd_params['filename']
            target_filename = "data/" + " ".join([course_code, formatted_date, class_title, source_filename]).replace('/','_')
            target_filename = target_filename.replace('\n','')[:250]

            if source_filename.endswith(".mp3") or source_filename.endswith('.m4a'): 
                continue

            if os.path.exists(target_filename): 
                log(color("Skipping: ", 'cyan') + target_filename + color(" [File exists]", 'red'))
                continue
            else:
                log(color("Downloading: ", 'cyan') + target_filename)
                if not DRYRUN:
                    with open(target_filename, 'wb') as f:
                        f.write(r.read())

def main():
    global VERBOSE, DEBUG, YTDL, DRYRUN
    arguments = docopt.docopt(__doc__)
    VERBOSE = arguments['--verbose']
    DEBUG = arguments['--debug']
    YTDL = arguments['--youtube-dl']
    DRYRUN = arguments['--dry-run']

    debug(arguments)

    fromdate = arguments['<date>'] and \
        dateutil.parser.parse(arguments['<date>']) or None

    login = {
        'username': arguments['--user'] or input("MEdTech username: "),
        'password': arguments['--pass'] or getpass.getpass()}

    log("Downloading calendar...")
    ical_url = arguments['--ical']
    ical_r = requests.get(ical_url)
    ical_data = ical_r.text

    log("Downloading resources...")
    download_resources(ical_data, login, fromdate)

if __name__ == '__main__':
    main()
