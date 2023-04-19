from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import json

def get_token(credential, scopes):
    flow = InstalledAppFlow.from_client_config(credential, scopes)
    creds = flow.run_local_server(port=0, prompt='consent')
    creds_dict = json.loads(creds.to_json())
    return creds_dict