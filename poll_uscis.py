# -*- coding: utf-8 -*
## @author: colin
## @date: 2016-11-30
## @filename: poll_uscis.py
from pyquery import PyQuery as pq
import requests
import smtplib
import os
import sys
import os.path
import re
from email.MIMEMultipart import MIMEMultipart
from email.MIMEBase import MIMEBase
from email.MIMEText import MIMEText
from email.utils import COMMASPACE, formatdate
from email import Encoders
from optparse import OptionParser
from datetime import datetime, date

STATUS_OK = 0
STATUS_ERROR = -1
FILENAME_LASTSTATUS = os.path.join(sys.path[0], "LAST_STATUS_{0}.txt")

# ----------------- SETTINGS -------------------
# set up your email sender here
# example settings: (if you use gmail)
# email: myname@gmail.com
# password: xxxx
# smtpserver: smtp.gmail.com:587
EMAIL_NOTICE_SENDER = {"email": "", "password": "", "smtpserver": ""}


def poll_optstatus(casenumber):
    """
    poll USCIS case status given receipt number (casenumber)
    Args:
        param1: casenumber the case receipt number

    Returns:
        a tuple (status, details) containing status and detailed info
    Raise:
        error:
    """
    headers = {
        'Accept': 'text/html, application/xhtml+xml, image/jxr, */*',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language':
        'en-US, en; q=0.8, zh-Hans-CN; q=0.5, zh-Hans; q=0.3',
        'Cache-Control': 'no-cache',
        'Connection': 'Keep-Alive',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Host': 'egov.uscis.gov',
        'Referer': 'https://egov.uscis.gov/casestatus/mycasestatus.do',
        'User-Agent':
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2486.0 Safari/537.36 Edge/13.10586'
    }
    url = "https://egov.uscis.gov/casestatus/mycasestatus.do"
    data = {"appReceiptNum": casenumber, 'caseStatusSearchBtn': 'CHECK+STATUS'}

    res = requests.post(url, data=data, headers=headers)
    doc = pq(res.text)
    status = doc('h1').text()
    code = STATUS_OK if status else STATUS_ERROR
    details = doc('.text-center p').text()
    return (code, status, details)


def send_mail(sentfrom,
              to,
              subject="nil",
              text="",
              files=[],
              server=EMAIL_NOTICE_SENDER['smtpserver'],
              user=EMAIL_NOTICE_SENDER['email'],
              password=EMAIL_NOTICE_SENDER['password']):
    "send email to a list of receivers"
    assert type(to) == list
    assert type(files) == list
    # get email settings
    if not (server and user and password):
        raise LookupError("Invalid email sending settings")
    msg = MIMEMultipart()
    msg['From'] = sentfrom
    msg['To'] = COMMASPACE.join(to)
    msg['Date'] = formatdate(localtime=True)
    msg['Subject'] = subject

    msg.attach(MIMEText(text))

    for f in files:
        part = MIMEBase('application', "octet-stream")
        part.set_payload(open(f, 'rb').read())
        Encoders.encode_base64(part)
        part.add_header('Content-Disposition',
                        'attachment; filename="%s"' % os.path.basename(f))
        msg.attach(part)
    try:
        smtp_s = smtplib.SMTP(server)
        smtp_s.ehlo()
        smtp_s.starttls()
        smtp_s.login(user, password)
        smtp_s.sendmail(sentfrom, to, msg.as_string())
        smtp_s.close()
        print "successfully sent the mail !"
    except:
        print 'failed to send a mail '


def on_status_fetch(status, casenumber):
    """
    fetch status and update last_status record file,
    or create it if it doesn't exist
    Returns:
        changed flag indicating if status has changed since last time and last status
        (changed, last_status)
        If no prior history is available, then return (False, None)
    """
    # normalize
    status = status.strip()
    record_filepath = FILENAME_LASTSTATUS.format(casenumber)
    changed = False
    last_status = None
    if not os.path.exists(record_filepath):
        with open(record_filepath, 'w') as f:
            f.write(status)
    # there is prior status, read it and compare with current
    else:
        with open(record_filepath, 'r+') as f:
            last_status = f.read().strip()
            # update status on difference
            if status != last_status:
                changed = True
                f.seek(0)
                f.truncate()
                f.write(status)
    return (changed, last_status)


def main():
    def get_days_since_received(status_detail):
        "parse case status and computes number of days elapsed since case-received"
        date_regex = re.compile(r'^On (\w+ +\d+, \d{4}), .*')
        m = date_regex.match(status_detail)
        datestr = m.group(1)
        if not datestr:
            return -1
        recv_date = datetime.strptime(datestr, "%B %d, %Y").date()
        today = date.today()
        span = (today - recv_date).days
        return span

    usage = """
    usage: %prog -c <case_number> [options]
    """
    parser = OptionParser(usage=usage)
    parser.add_option(
        '-c',
        '--casenumber',
        type='string',
        action='store',
        dest='casenumber',
        default='YSC1790016391',
        help='the USCIS case receipt number you can to query')
    parser.add_option(
        '-d',
        '--detail',
        action='store_true',
        dest='detailOn',
        help="request details about the status returned")
    parser.add_option(
        '--mailto',
        action='store',
        dest='receivers',
        help=(
            "optionally add one or more emails addresses, separated by comma,"
            " to send the notification mail to"))
    opts, args = parser.parse_args()
    casenumber = opts.casenumber
    if not casenumber:
        raise parser.error("No casenumber is provided")
    # poll status
    code, status, detail = poll_optstatus(casenumber)
    if code == STATUS_ERROR:
        print "The case number %s is invalid." % casenumber
        return
    # report format
    report_format = ("-------  Your USCIS Case [{0}]---------"
                     "\nCurrent Status: [{1}]"
                     "\nDays since received: [{2}]")
    days_elapsed = get_days_since_received(detail)

    report = report_format.format(casenumber, status, days_elapsed)
    # compare with last status
    changed, laststatus = on_status_fetch(status, casenumber)
    # generate report
    report = '\n'.join(
        [report, "Previous Status:%s \nChanged?: %s" % (laststatus, changed),
         "Current Timestamp: %s " % datetime.now().strftime("%Y-%m-%d %H:%M")])
    if opts.detailOn:
        report = '\n'.join((report, "\nDetail:\n\n%s" % detail))
    # console output
    print report
    # email notification on status change
    if opts.receivers and changed:
        recv_list = opts.receivers.split(',')
        subject = "Your USCIS Case %s Status Change Notice " % casenumber
        send_mail("USCIS Case Status Notify", recv_list, subject, report)


if __name__ == '__main__':
    main()
