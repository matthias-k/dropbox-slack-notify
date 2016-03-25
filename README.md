# dropbox-slack-notify

Slack integration to get notifications about changes in dropbox

## Setup

dropbox-slack-notify requires python3. Install all requirements from `requirements.txt`
and copy `app_config_sample.py` to a file `app_config.py`. Fill in all values: The app
key and secret for the dropbox app and your token (dropbox-slack-notify does not yet
support OAuth). Also fill in the URL for the Slack incoming webhook. Add all path prefixes
which you want to be notified about (if all, just use `['/']`). Then fire up the app with
`python app.py`. Add the webhook URL to your dropbox app: `<yourserver>:12345/webhook`.
Dropbox will start to notify your app via the webhook. You should see notifications on
the debug log and of course in slack.
