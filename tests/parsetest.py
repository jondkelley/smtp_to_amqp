import email
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
import os
import mimetypes
import re

with open ("test_message2.eml", "r") as myfile:
    data=myfile.read()
msg = email.message_from_string(data)

print(msg['reply-to'])
print(msg['message-id'])
print(msg['from'])
print(msg['date'])
print(msg['mime-version'])
recipient = re.search(r'[\w\.-]+@[\w\.-]+', msg['to']).group(0)
domain = recipient.split('@')[-1]
identity = recipient.split('@')[0].split('-')[-1]
campaign = recipient.split('@')[0].split('-')[0]

counter = 0
redismessage = {}
redismessage['raw_files'] = {}
ALLOW_EXT = []
DISALLOW_EXT = ['exe', 'png']
setattr(msg,"recipient", recipient)
setattr(msg,"domain", domain)
setattr(msg,"identity", identity)
setattr(msg,"campaign", campaign)

for part in msg.walk():
    # multipart/* are just containers
    if part.get_content_maintype() == 'multipart':
        continue

    counter += 1
    # Applications should really sanitize the given filename so that an
    # email message can't be used to overwrite important files
    filename = part.get_filename()
    if not filename:
        ext = mimetypes.guess_extension(part.get_content_type())
        # Use a generic bag-of-bits extension
        ext = '.txt'
        filename = 'part-%03d%s' % (counter, ext)
    realext = str(filename).split('.')[-1]
    payload=part.get_payload(decode=True)
    allow_file = False
    if (len(ALLOW_EXT) == 0) or (realext in ALLOW_EXT):
        allow_file = True
    if (len(DISALLOW_EXT) > 0) and (realext in DISALLOW_EXT):
        allow_file = False
    if allow_file:
        if filename == "part-001.txt":
            redismessage['txt'] = payload
        elif filename == "part-002.txt":
            redismessage['html'] = payload
        else:
            print("including attachment {}".format(filename))
            redismessage['raw_files'][filename] = payload
    else:
        print("dropping prohibited attachment {}".format(filename))
        #logger.info()
        counter = counter - 1
    redismessage['object'] = msg
    #print(payload)
    fp = open(os.path.join('lol', filename), 'wb')

#print(redismessage)
print("{} attachments found in MIME in message for {}".format(counter, msg.identity))
