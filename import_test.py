try:
    from google_auth_oauthlib.flow import InstalledAppFlow
    print("Successfully imported google_auth_oauthlib.flow.InstalledAppFlow")
except ImportError as e:
    print(f"Failed to import: {e}")