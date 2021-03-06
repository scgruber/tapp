#! /usr/bin/env python

# talk_series/ics-gen.py
# Generator for talk series iCalendar file
# Part of the TAPP library
# Copyright 2014 Tim Parenti <tparenti@club.cc.cmu.edu>

import sys, getopt, json, datetime

# Top-level function, parses arguments
def main(argv):
  inFileName = ''
  outFileName = ''
  try:
    opts, args = getopt.getopt(argv, 'hi:o:', ['infile=','outfile='])
  except getopt.GetoptError:
    print 'talk_series/ics-gen.py -i <inputfilename> -o <outputfilename>'
    sys.exit(2)

  for opt, arg in opts:
    if opt == '-h':
      print 'talk_series/ics-gen.py -i <inputfilename> -o <outputfilename>'
      sys.exit()
    elif opt in ('-i','--infile'):
      inFileName = arg
    elif opt in ('-o','--outfile'):
      outFileName = arg

  if inFileName == '':
    inFile = sys.stdin
  else:
    try:
      inFile = open(inFileName, 'r')
    except IOError:
      print 'Input filename not valid.'
      sys.exit()

  if outFileName == '':
    outFile = sys.stdout
  else:
    try:
      outFile = open(outFileName, 'w')
    except IOError:
      print 'Output filename not valid.'
      sys.exit()

  inData = json.load(inFile)

  validate(inData)

  outIcs = render(inData)

  outFile.write(outIcs)
  outFile.write('\n')

# Checks that data is a properly-formatted input to the generator
def validate(data):
  failed = False

  if not isinstance(data, dict):
    print 'Parse Error: Input must be JSON object.'
    failed = True

  if not 'name' in data:
    print 'Parse Error: Talk series must have name.'
    failed = True
  elif not isinstance(data['name'], unicode):
    print 'Parse Error: name must be string.'
    failed = True

  if not 'first_date' in data:
    print 'Parse Error: Talk series must have first_date.'
    failed = True
  elif not isinstance(data['first_date'], unicode):
    print 'Parse Error: first_date must be datestring.'
    failed = True
  try:
    dummydate = datetime.datetime.strptime(data['first_date'], '%Y-%m-%d')
  except ValueError:
    print 'Parse Error: first_date must match format %Y-%m-%d.'
    failed = True

  if not 'location' in data:
    print 'Parse Error: Talk series must have location.'
    failed = True
  elif not isinstance(data['location'], unicode):
    print 'Parse Error: location must be string.'
    failed = True

  if not 'talks' in data:
    print 'Parse Error: Talk series must have talks.'
    failed = True
  elif not isinstance(data['talks'], list):
    print 'Parse Error: talks must be list.'
    failed = True
  elif len(data['talks']) < 2:
    print 'Parse Error: talks must have length > 1'
    failed = True
  else:
    for talk in data['talks']:
      if not 'title' in talk:
        print 'Parse Error: talk must have title.'
        failed = True
      elif not isinstance(talk['title'], unicode):
        print 'Parse Error: title must be string.'
        failed = True
      if not 'cat' in talk:
        print 'Parse Error: talk must have cat.'
        failed = True
      elif not isinstance(talk['cat'], int):
        print 'Parse Error: cat must be integer.'
        failed = True

  if failed:
    sys.exit()

# Converts the data into an ICS
def render(data):
  ICS_LINE_WIDTH = 72
  ICS_LINE_CONTINUATION = '\n '

  # Manufacture start date object
  startDate = datetime.datetime.strptime(data['first_date'], '%Y-%m-%d')
  startTime = datetime.datetime.strptime(data['start_time'], '%H:%M')
  endTime = datetime.datetime.strptime(data['end_time'], '%H:%M')

  # Preamble
  calendarDescription = data['url'] + '\\n\\n' + data['ical_desc'] + '\\n\\n'
  calendarDescription += 'Sponsored by ' + data['sponsor']['name'] + ' <' + data['sponsor']['url'] + '>'
  output = (
    'BEGIN:VCALENDAR\n'
    'VERSION:2.0\n'
    'CALSCALE:GREGORIAN\n'
    'METHOD:PUBLISH\n'
    'X-WR-CALNAME:CMU Computer Club ' + data['name'] + ' Talks Series\n'
    'X-WR-TIMEZONE:America/New_York\n'
  )
  output += wrap_line('X-WR-CALDESC:' + calendarDescription, ICS_LINE_WIDTH, ICS_LINE_CONTINUATION) + '\n'
  output += (
    'BEGIN:VTIMEZONE\n'
    'TZID:America/New_York\n'
    'X-LIC-LOCATION:America/New_York\n'
    'BEGIN:DAYLIGHT\n'
    'TZOFFSETFROM:-0500\n'
    'TZOFFSETTO:-0400\n'
    'TZNAME:EDT\n'
    'DTSTART:19700308T020000\n'
    'RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=2SU\n'
    'END:DAYLIGHT\n'
    'BEGIN:STANDARD\n'
    'TZOFFSETFROM:-0400\n'
    'TZOFFSETTO:-0500\n'
    'TZNAME:EST\n'
    'DTSTART:19701101T020000\n'
    'RRULE:FREQ=YEARLY;BYMONTH=11;BYDAY=1SU\n'
    'END:STANDARD\n'
    'END:VTIMEZONE\n'
  )

  # Create individual events
  dates = disperse_dates(startDate, len(data['talks']))
  for idx in range(0, len(dates)):
    if not data['talks'][idx]['cat'] == 0:
      fullDescription = data['talks'][idx]['desc'] + '\\n\\n' + data['url'] + '\\n\\n'
      fullDescription += 'Sponsored by ' + data['sponsor']['name'] + ' <' + data['sponsor']['url'] + '>'
      output += (
        'BEGIN:VEVENT\n'
        'UID:talks-series-' + dates[idx].strftime("%Y-%m-%d") + '@club.cc.cmu.edu\n'
        'DTSTART:' + dates[idx].strftime("%Y%m%d") + 'T' + startTime.strftime("%H%M%S") + '\n'
        'DTEND:' + dates[idx].strftime("%Y%m%d") + 'T' + endTime.strftime("%H%M%S") + '\n'
        'SUMMARY:' + data['talks'][idx]['title'] + '\n'
        'LOCATION:' + data['location'] + '\n'
      )
      output += wrap_line('DESCRIPTION:' + fullDescription, ICS_LINE_WIDTH, ICS_LINE_CONTINUATION) + '\n'
      output += (
        'SEQUENCE:0\n'
        'STATUS:CONFIRMED\n'
        'TRANSP:OPAQUE\n'
        'END:VEVENT\n'
      )

  output += 'END:VCALENDAR\n'
  return output

def disperse_dates(startDate, numEvents):
  step = datetime.timedelta(days=7)
  dates = [startDate]
  for idx in range(1, numEvents):
    startDate += step
    dates += [startDate]
  return dates

def wrap_line(line, n, sep):
  split_line = [line[i:i+n] for i in range(0, len(line), n)]
  joined_line = sep.join(split_line)
  return joined_line

# Invoke main as top-level function
if __name__ == '__main__':
  main(sys.argv[1:])
