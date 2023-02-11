#!/usr/bin/env python

"""Upload receipts to Xero from a CSV file"""

# Contributed by @davidbitton, https://github.com/freakboy3742/pyxero/pull/48

# http://developer.xero.com/documentation/api/receipts/

import argparse
import csv
import os.path
import pickle
import sys
import webbrowser

from xero import Xero
from xero.auth import PublicCredentials

# from config import xero_config
xero_config = {
    "consumer_key": "XXX",
    "consumer_secret": "XXX",
}


argp = argparse.ArgumentParser(description=__doc__)
argp.add_argument(
    "-i", "--input-file", dest="input_file", default="-", help="input file name"
)
argp.add_argument(
    "-c",
    "--credentials-file",
    dest="credentials_file",
    default="credentials.pickle",
    help="credentials file name",
)
args = argp.parse_args()

# Connect to Xero
if os.path.isfile(args.credentials_file):
    # Use cached credentials
    with open(args.credentials_file) as credentials_fh:
        credentials_state = pickle.loads(credentials_fh.read())
        credentials = PublicCredentials(**credentials_state)
else:
    credentials = PublicCredentials(
        xero_config["consumer_key"], xero_config["consumer_secret"]
    )
    print(credentials.url)
    webbrowser.open(credentials.url)
    verifier = input("Enter auth code: ")
    credentials.verify(verifier)
    with open(args.credentials_file, "w") as credentials_fh:
        pickle.dump(credentials.state, credentials_fh)
xero = Xero(credentials)

# Get userids matching user email
userids = {}
users = xero.users.all()
# print(users)
for user in users:
    userids[user["EmailAddress"]] = user["UserID"]

# Get receipts and add them to Xero
if args.input_file == "-":
    in_fh = sys.stdin
else:
    in_fh = open(args.input_file)

# Date,UserEmail,ContactName,Reference,Description,UnitAmount,AccountCode
reader = csv.DictReader(in_fh, delimiter=",")
receipts = []
for i in reader:
    # print(i)

    user_email = i["UserEmail"]
    if user_email not in userids:
        print(f"Unknown user: {user_email}")
        continue
    userid = (userids[i["UserEmail"]],)

    # TODO: Validate input data

    data = {
        "Date": i["Date"],
        "Contact": {"Name": i["ContactName"]},
        "Reference": i["Reference"],
        "LineItems": [
            {
                "Description": i["Description"],
                "UnitAmount": i["UnitAmount"],
                "AccountCode": i["AccountCode"],
            },
        ],
        "User": {"UserID": userids[i["UserEmail"]]},
    }
    # print(data)
    # xml = xero.receipts._prepare_data_for_save(data)
    # print(xml)
    receipts.append(data)

# print(receipts)

if receipts:
    results = xero.receipts.put(receipts)
    # import pprint
    # pp = pprint.PrettyPrinter(depth=6)
    # pp.pprint(results)
