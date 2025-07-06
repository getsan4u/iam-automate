import boto3
import csv
import sys
import json
from datetime import datetime
from botocore.exceptions import ClientError

# Read inputs from GitHub Actions
user_name = sys.argv[1]
group_name = sys.argv[2]
tags_input = sys.argv[3]
email_to = sys.argv[4]
email_from = sys.argv[5]
region = "eu-west-2"
password = "S3cureP@ssw0rd!"  # You can generate this if needed

iam = boto3.client("iam")
ses = boto3.client("ses", region_name=region)

def parse_tags(tag_str):
    """Parses tags from 'key=value,key2=value2' format to list of dicts"""
    try:
        return [{"Key": k.strip(), "Value": v.strip()} for k, v in (tag.split('=') for tag in tag_str.split(','))]
    except Exception:
        raise ValueError("Tags must be formatted like key=value,key2=value2")

def create_user(username, groupname, tags):
    # Create IAM user
    iam.create_user(UserName=username)
    
    # Add to group
    iam.add_user_to_group(GroupName=groupname, UserName=username)

    # Tag user
    iam.tag_user(UserName=username, Tags=tags)

    # Create login profile
    iam.create_login_profile(
        UserName=username,
        Password=password,
        PasswordResetRequired=True
    )

    return {
        "UserName": username,
        "Password": password,
        "LoginURL": f"https://{region}.console.aws.amazon.com/"
    }

def write_csv(data, filename):
    with open(filename, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["UserName", "Password", "LoginURL"])
        writer.writerow([data["UserName"], data["Password"], data["LoginURL"]])

def send_email(subject, message, to_email, from_email):
    ses.send_email(
        Source=from_email,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Text": {"Data": message}}
        }
    )

def main():
    try:
        tags = parse_tags(tags_input)
        user_info = create_user(user_name, group_name, tags)
        
        file_name = f"{user_name}_credentials.csv"
        write_csv(user_info, file_name)

        message = (
            f"IAM User '{user_name}' created successfully.\n\n"
            f"Login URL: {user_info['LoginURL']}\n"
            f"Username: {user_info['UserName']}\n"
            f"Password: {user_info['Password']} (reset required)\n"
            "\nThe credentials are also saved in the CSV file."
        )

        send_email(f"IAM Credentials for {user_name}", message, email_to, email_from)
        print("✅ All done!")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()