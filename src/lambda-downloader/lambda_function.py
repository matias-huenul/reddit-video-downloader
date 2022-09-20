import os
import subprocess
import sys
from botocore.vendored import requests
from urllib.parse import urljoin, urlparse

headers = {"User-Agent": "Reddit Video Bot"}

def make_request(method, url, **kwargs):
    response = method(url, headers=headers, **kwargs)
    response.raise_for_status()

    return response

def get_post_data(post_url):
    response = make_request(requests.get, post_url)
    return response.json()

def get_video_url(post_data):
    return post_data[0]["data"]["children"]\
        [0]["data"]["secure_media"]\
        ["reddit_video"]["fallback_url"]

def get_video(post_data):
    url = get_video_url(post_data)
    response = make_request(requests.get, url)
    return response.content

def get_audio(post_data):
    video_url = get_video_url(post_data)
    url = "/".join(video_url.split("/")[:-1]) + "/DASH_audio.mp4"
    response = make_request(requests.get, url)
    return response.content

def download_video(post_url, filepath_video, filepath_audio, filepath_result):
    post_data = get_post_data(post_url + ".json")
    post_id = post_data[0]["data"]["children"][0]["data"]["id"]

    video = get_video(post_data)
    audio = get_audio(post_data)

    with open(filepath_video, "wb") as fh:
        fh.write(video)

    with open(filepath_audio, "wb") as fh:
        fh.write(audio)

    subprocess.call([
        "./ffmpeg",
        "-i",
        filepath_video,
        "-i",
        filepath_audio,
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-shortest",
        filepath_result
    ])

def get_reddit_url_from_message(message_text):
    url = message_text.strip()
    url_parse = urlparse(url)

    if not url_parse.netloc.endswith("reddit.com"):
        return None

    return urljoin(url, url_parse.path)

def run_bot(token, message, aws_request_id):
    telegram_api_url = f"https://api.telegram.org/bot{token}"

    message_text = message["text"]
    message_chat_id = message["chat"]["id"]
    reddit_url = get_reddit_url_from_message(message_text)

    if not reddit_url:
        make_request(
            requests.post, 
            f"{telegram_api_url}/sendMessage",
            data={
                "chat_id": message_chat_id,
                "text": "Hello! Send me the link to the reddit post "
                    + "containing the video you wish to download."
            }
        )

        return

    filepath_video = f"/tmp/{aws_request_id}_video.mp4"
    filepath_audio = f"/tmp/{aws_request_id}_audio.mp3"
    filepath_result = f"/tmp/{aws_request_id}.mp4"

    download_video(reddit_url, filepath_video, filepath_audio, filepath_result)

    with open(filepath_result, "rb") as fh:
        make_request(
            requests.post,
            f"{telegram_api_url}/sendVideo",
            data={"chat_id": message_chat_id},
            files={"video": fh}
        )

def lambda_handler(event, context):
    success = False
    try:
        run_bot(
            os.environ["TELEGRAM_API_TOKEN"],
            event["message"],
            context.aws_request_id
        )
        success = True
    except Exception as e:
        print(e)
    return success
