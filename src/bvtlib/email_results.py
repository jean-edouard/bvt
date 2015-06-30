#!/usr/bin/python

import smtplib
import sys
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from src.bvtlib.settings import BVTURL


#TODO: Prevent url from being removed from email once received.
class ResultMailer:

    def __init__(self, recipients):
        self.server = "localhost"
        self.me = "bvt@bvt.net"
        self.to = recipients
        self.message = ""

    def send(self):
        try:
            s = smtplib.SMTP(self.server)
            s.sendmail(self.me, self.to, self.message) 
            s.quit()
        except Exception:
            print sys.exc_info()

    def format_message(self, results, build_info):
        """Accept the dictionary of results for a test suite.  Format into html
            message for mailing."""

        def format_steps(steps):
            steplist = list()
            for i in range(steps):
                steplist.append("<tr><td>Step %s:</td><td><font color='%s'>%s</font></td></tr>"%
                                    (i, "green" if results['step%s'%i] == "PASS" else "red",
                                        results['step%s'%i]))
            return ''.join(steplist)

        msg = MIMEMultipart()
        steps = results['steps']
        suite = results['suite']
        result = results['result']
        color = 'green' if result == 'PASS' else 'red'
        start_time = datetime.fromtimestamp(results['start_time']).strftime('%Y-%m-%d %H:%M:%S')
        end_time = datetime.fromtimestamp(results['finish_time']).strftime('%Y-%m-%d %H:%M:%S')

        msg['Subject'] = 'Test suite %s %s' % (suite, 'PASSED' if result == 'PASS' else 'FAILED')
        msg['From'] = self.me
        msg['To'] = self.to
      
        log_url = BVTURL+"/logs/result_id=%s" %build_info['result_id']
        steplist = format_steps(steps)
  
        html = """\
        <html>
            <head>
            <h4>Test suite %s <font color='%s'>%s</font></h4>
            </head>
          <body>
            <p>
            <table cellspacing="10">
            <tr><td>Build:</td><td><b>%s</b></td></tr>    
            <tr><td>Test Node:</td><td><b>%s</b></td></tr>    
            <tr><td>Logs:</td><td><b><a href='%s'>%s</a></b></td></tr>    
            <tr><td>Start time:</td><td><b>%s</b></td></tr>    
            <tr><td>End time:</td><td><b>%s</b></td></tr>    
            <tr><td>Total Steps:</td><td><b>%s</b></td></tr>    
            %s 
            </p>
          </body>
        </html>
        """% (suite, color, result, build_info['build'], build_info['node'], log_url, log_url, 
                start_time, end_time, steps, steplist)

        part1 = MIMEText(html, 'html')
        msg.attach(part1)
        self.message = msg.as_string()

    def change_recipients(self, new_recipients):
        self.to = new_recipients

