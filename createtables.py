from flask import Flask
from flask_sqlalchemy import SQLAlchemy
import configparser

config = configparser.ConfigParser()
config.read('config/ingestapi.ini')
# ['section1', 'section2']
#print(config.items('section2'))

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = config['amqpworker']['output_by_mysql_url']
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# i.e. mysql mysql://user:pass@localhost/db_name
# i.e. pg postgresql+psycopg2://user:pass@localhost/db_name'
db = SQLAlchemy(app)

class Envelope(db.Model):
    """
    un-normalized database table for inbound messages
    this may cause performance issues (slowness) paginating the API at 4+ million rows
    foreign key optimization for a rainy day?
    """
    id = db.Column(db.BigInteger, primary_key=True)
    uuid = db.Column(db.String(20), unique=True)
    read = db.Column(db.Boolean(), default=False)
    read_expireafter = db.Column(db.DateTime())
    identity = db.Column(db.Integer, unique=False)
    campaign = db.Column(db.String(64), unique=False)
    domain = db.Column(db.String(512), unique=False)
    amqp_processed = db.Column(db.DateTime())
    worker_processed = db.Column(db.DateTime())
    xfrom = db.Column(db.String(512), unique=False)
    tos = db.Column(db.String(1024), unique=False)

    def __init__(self, id, uuid, read, identity, amqp_processed, worker_processed, xfrom, tos):
        self.id = id
        self.uuid = uuid
        self.read = read
        self.identity = identity
        self.amqp_processed = amqp_processed
        self.worker_processed = worker_processed
        self.xfrom = xfrom
        self.tos = tos

    def __repr__(self):
        return '<Envelope %r>' % self.uuid

print("Inflating alpha table structure...")
db.create_all()
db.session.commit()
print("Done.")

#admin = User('admin', 'admin@example.com')
#db.session.add(admin)
#db.session.commit()
#envelopes = Envelope.query.all()
#print(envelopes)
