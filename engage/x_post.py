"""X (Twitter) auto-post — upload an image + post a tweet to a USER's account.

⏳ PENDING the approved X developer account. This is the core posting logic so it's
a quick wire-up once keys exist; it's NOT imported anywhere yet (so the live bot
doesn't need tweepy installed). Each user connects their X account once via OAuth
(3-legged); we store their access token + secret, then post on demand.

Wiring when the dev account lands:
 1. Create the X app (OAuth 1.0a, Read+Write) and put the consumer key/secret in
    engage/.env as X_API_KEY / X_API_SECRET.
 2. Per-user "اتصال حساب ایکس" connect flow — needs a public callback URL (route it
    via the existing nginx, e.g. https://app.blazee.ir/xcallback):
        handler = tweepy.OAuth1UserHandler(API_KEY, API_SECRET, callback="<callback>")
        url = handler.get_authorization_url()      # send the user this link
        # user authorizes -> X redirects to callback with oauth_verifier
        access_token, access_secret = handler.get_access_token(oauth_verifier)
        # persist (access_token, access_secret) keyed by the telegram user id
 3. On "🚀 پست در ایکس", call post_image(...) with that user's stored tokens.
    (Instagram has no equivalent — its API only posts to Business/Creator accounts
    via Facebook review, never personal accounts, so IG stays save-and-paste.)
"""
import io

import config


def post_image(access_token, access_secret, image_bytes, text):
    """Upload the image and create a tweet on the user's account. Returns tweet id.

    media_upload uses X API v1.1 (OAuth 1.0a); create_tweet uses v2.
    """
    import tweepy  # imported lazily — only needed once X is enabled

    auth = tweepy.OAuth1UserHandler(
        config.X_API_KEY, config.X_API_SECRET, access_token, access_secret)
    media = tweepy.API(auth).media_upload(filename="photo.jpg", file=io.BytesIO(image_bytes))
    client = tweepy.Client(
        consumer_key=config.X_API_KEY, consumer_secret=config.X_API_SECRET,
        access_token=access_token, access_token_secret=access_secret)
    resp = client.create_tweet(text=text, media_ids=[media.media_id])
    return resp.data["id"]
