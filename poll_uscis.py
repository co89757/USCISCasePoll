# -*- coding: utf-8 -*
from pyquery import PyQuery as pq
import requests
import smtplib
import os
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
              server='smtp.gmail.com:587',
              user='',
              password='xxxxx'):
    "generate automated email to a client using Gmail, by default colin's Gmail. "
    assert type(to) == list
    assert type(files) == list

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


def main():
    def get_days_since_received(status_detail):
        "parse case status and computes number of days elapsed since case-received"
        date_regex = re.compile(r'^On (\w+ +\d+, \d{4}), we received.*')
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
    if opts.detailOn:
        report = '\n'.join((report, "\nDetail:\n\n%s" % detail))
    # console output
    print report
    # email notification
    if opts.receivers:
        recv_list = opts.receivers.split(',')
        subject = "Your USCIS Case %s Status Report " % casenumber
        send_mail("USCIS Case Status Notify", recv_list, subject, report)


if __name__ == '__main__':
    main()
