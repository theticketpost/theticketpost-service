from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow, Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from flask import session, redirect
import json

#def get_token(credential, scopes):
#    flow = InstalledAppFlow.from_client_config(credential, scopes)
#    creds = flow.run_local_server(port=0, prompt='consent')
#    creds_dict = json.loads(creds.to_json())
#    return creds_dict

def get_token(credential, scopes):
    redirect_uri = credential['web']['redirect_uris'][0]  # We use the first redirect URI in the list.

    # Convert the credential to the format expected by Flow.
    # This involves converting the outer 'web' key to 'client_info',
    # and removing any unnecessary keys.
    client_config = {
        'client_info': {
            'client_id': credential['web']['client_id'],
            'client_secret': credential['web']['client_secret'],
            'auth_uri': credential['web']['auth_uri'],
            'token_uri': credential['web']['token_uri'],
            'redirect_uris': credential['web']['redirect_uris'],
        }
    }

    flow = Flow.from_client_config(client_config, scopes, redirect_uri=redirect_uri)
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true')  
    
    session['flow'] = flow
    redirect(redirect_uri)
    # Redirect the user to authorization_url, and have them authenticate.

    # After the user has authenticated, they will be redirected to your specified
    # redirect URI, and you will need to extract the 'code' query parameter
    # from the URL. Use this code to complete the flow.

    # Substitute `code_from_redirect_uri` for the actual code retrieved from the redirect URI
    flow.fetch_token(code=code_from_redirect_uri)

    creds = flow.credentials
    creds_dict = json.loads(creds.to_json())
    return creds_dict