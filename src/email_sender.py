from mailjet_rest import Client
from config import BaseConfig

host_server = BaseConfig.MAIL_SERVER
# sender_mail = BaseConfig.MAIL_USERNAME
# sender_passcode = BaseConfig.MAIL_PASSWORD
api_key = BaseConfig.MAILJET_API_KEY
api_secret = BaseConfig.MAILJET_API_SECRET

# mailjet_secret_file = "mailjet_client_secret.json"
# with open(mailjet_secret_file, "r") as file:
#     secrets = json.load(file)
#     MAILJET_API_KEY = secrets['mailjet']['API_KEY']
#     MAILJET_API_SECRET = secrets['mailjet']['API_SECRET']


# def send_mail(receiver='', mail_title='', mail_content=''):
#     # ssl login
#     smtp = SMTP_SSL(host_server)
#     # set_debuglevel() for debug, 1 enable debug, 0 for disable
#     # smtp.set_debuglevel(1)
#     smtp.ehlo(host_server)
#     smtp.login(sender_mail, sender_passcode)
#
#     # construct message
#     msg = MIMEText(mail_content, "html", 'utf-8')
#     msg["Subject"] = Header(mail_title, 'utf-8')
#     msg["From"] = sender_mail
#     msg["To"] = receiver
#     smtp.sendmail(sender_mail, receiver, msg.as_string())
#     smtp.quit()


def send_email_api(receiver='', first_name="", mail_title='', mail_content=''):
    mailjet = Client(auth=(api_key, api_secret), version='v3.1')
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "ruoxi.liu@columbia.edu",
                    "Name": "Team-Matcher"
                },
                "To": [
                    {
                        "Email": receiver,
                        "Name": first_name
                    }
                ],
                "Subject": mail_title,
                "TextPart": "My first Mailjet email",
                "HTMLPart": mail_content,
                "CustomID": "Hello"
            }
        ]
    }
    result = mailjet.send.create(data=data)
    print(result.json())
    return True if result.status_code == 200 else False
