#!/usr/bin/env python
# -*- coding: utf-8 -*-

import youtube_dl
from pymongo import MongoClient
from pprint import pprint
import sys
import argparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pprint import pprint
import re
import html
import requests
import shutil
import json

# Connect db
mongo_uri = "mongodb://root:example@172.17.0.1:27017/"
client = MongoClient(mongo_uri)

YOUTUBE_API_KEY = 'AIzaSyCEg40YmdKCgLkBSWxkhD6xyxy1ysQTfgk'

parser = argparse.ArgumentParser(description='Download audio and convert to FLAC')
parser.add_argument(
        'urls', metavar='URLS', type=str, nargs='+',
        help='urls for the youtube videos. example: \
        http://www.youtube.com/watch?v=BaW_jenozKc \
        \
        You can pass multiple URLs.'
)
parser.add_argument(
        'is_playlist', default=False, type=bool, nargs='?',
        help="By default, this script will download a single video and convert \
        to flac audio. The is_playlist boolean will download the entire playlist and \
        save each track to a directory with the name of the playlist."
)
# parser.add_argument('include_video', metavar='INCLUDE_VIDEO', type=str,
#                     help="if true, video will be downloaded as well. Defaults to false")

args = parser.parse_args()

# download a single album to this location
ALBUM_DIR = '~/Music/%(title)s/%(title)s.%(ext)s'
# download tracks from a playlist to this location
PLAYLIST_DIR = '~/Music/%(playlist_title)s/%(title)s.%(ext)s'
if args.is_playlist:
    output_dir = PLAYLIST_DIR
else:
    output_dir = ALBUM_DIR

ydl_options = {
    'outtmpl': output_dir,
    'format': 'bestaudio/best',
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'flac',
        'preferredquality': '192',
    }],
    'writethumbnail': True,
}

ydl = youtube_dl.YoutubeDL(ydl_options)

################# ^ GOOD

def create_database(urls):
    filename = Path('sqlite.db')
    filename.touch(exist_ok=True)  # will create file, if it exists will do nothing
    cursor = connection.cursor()
    cursor.execute("CREATE TABLE music (id TEXT, description TEXT, timestamps text)")


def get_description(urls):
    """
    Get the video descriptions, which may include artist, date, timstamp information.
    """
    for url in urls:
        with build('youtube', 'v3', developerKey=YOUTUBE_API_KEY) as service:
            request = service.videos().list(part='snippet', id=url)
            try:
                response = request.execute()
            except HttpError as e:
                print('Error response status code : {0}, reason : {1}'.format(e.status_code, e.error_details))
                return {}
        description = response['items'][0]['snippet']['description']
        meta[url]['description'] = description

def get_timestamps(urls):
    """
    Get timestamp information from the video description if available

    Example output:
    {"video_id": ['00:00', '03:30', ...]}
    """
    get_description(urls)
    for url in urls:
        meta[url]['timestamps'] = []
        matches = re.finditer(r'([0-9]{1,2}:)?[0-9]{1,2}:[0-9]{1,2}', meta[url]['description'])
        for m in matches:
            meta[url]['timestamps'].append(m[0])
            # # write timestamps to file
            # with open('timestamps.txt', 'w') as f:
            #     for match in timestamps:
            #         f.write(match[0] + "\n")
            # # optionally return timestamps
    return meta

def split_tracks(original_track, timestamps):
    """split a music track into specified sub-tracks by calling ffmpeg from the shell"""
    # create a template of the ffmpeg call in advance
    cmd_string = 'ffmpeg -i {tr} -acodec copy -ss {st} -to {en} {nm}.flac'
    with open('timestamps.txt', 'r') as f:
        for line in f:
            # skip comments and empty lines
            if line.startswith('#') or len(line) <= 1:
                continue

            # create command string for a given track
            start, end, name = line.strip().split()
            command = cmd_string.format(tr=original_track, st=start, en=end, nm=name)
            subprocess.call(command, shell=True)
    return None

def get_thumbnails(urls):
    ids = get_video_ids(urls)
    for videoId in ids:
        with build('youtube', 'v3', developerKey=YOUTUBE_API_KEY) as service:
            request = service.videos().list(part='snippet', id=videoId)
            try:
                response = request.execute()
                pprint(response)
                thumbnails = response['items'][0]['snippet']['thumbnails']
                pprint(thumbnails)
                print(thumbnails.keys())
                for key in thumbnails.keys():
                    r = requests.get(thumbnails[key]['url'], stream=True)
                    with open(key + '.jpg', 'wb') as out_file:
                        shutil.copyfileobj(r.raw, out_file)
            except HttpError as e:
                print('Error response status code : {0}, reason : {1}'.format(e.status_code, e.error_details))
                return {}
            return response

    ids = get_video_ids(urls)
    for id in ids:
        image_url = 'https://img.youtube.com/vi/{}/maxresdefault.jpg'.format(id)
        response = requests.get(image_url, stream=True)
        with open('img.png', 'wb') as out_file:
            shutil.copyfileobj(response.raw, out_file)
        del response

def get_comment_threads(videoId, maxResults=20, pageToken=None):
    """Returns top level comments
    maxResults: number of threads per page
    pageToken: page to retrieve"""
    with build('youtube', 'v3', developerKey=YOUTUBE_API_KEY) as service:
        request = service.commentThreads().list(part='snippet,replies', videoId=videoId, maxResults=maxResults, pageToken=pageToken)
        try:
            response = request.execute()
        except HttpError as e:
            print('Error response status code : {0}, reason : {1}'.format(e.status_code, e.error_details))
            return {}
        return response

def get_comment(parentCommentId):
    """gets reply to top level comment"""
    with build('youtube', 'v3', developerKey=YOUTUBE_API_KEY) as service:
        request = service.comments().list(part='snippet', videoId=videoId)
        try:
            response = request.execute()
        except HttpError as e:
            print('Error response status code : {0}, reason : {1}'.format(e.status_code, e.error_details))
            return {}
        return response


def get_video_ids(urls):
    """
    input: https://www.youtube.com/watch?v=beHVaOSn9-o
    output: beHVaOSn9-o

    input: beHVaOSn9-o
    output: beHVaOSn9-o
    """
    ids = []
    for url in urls:
        if ids.append(url[url.rindex('=')+1:]):
            pass
    return ids

def trim_logs():
    with open('track_log.txt', 'r') as log:
        lines = set(log.readlines())

def download_audio(urls):
    """
    Download specified YouTube tracks as command line arguments, or through a queue file

    Returns:
    <list dest_files> : list of where the audio files are downloaded to
    """
    # where the files are downloaded
    file_dest = []
    with ydl:
        for url in urls:
            print(url)
            # history of downloaded tracks
            with open('track_log.txt', 'a') as log:
                log.write(url+'\n')
            # Get filename location
            meta = ydl.extract_info(
                url,
                download=False) # We just want to extract the path the filename the audio file is downloaded to
            file_dest.append("~/Music/{}/{}.{}".format(meta['title'], meta['title'], meta['ext']))
        result = ydl.download(urls)
        return file_dest


def convert_audio():
    """
    Convert file to FLAC
    """
    pass


if __name__ == '__main__':
    get_metadata(args.urls)
    timestamps = get_timestamps(args.urls)
    pprint(timestamps)
    file_dest = download_audio(args.urls)
    split_tracks(dest_files, timestamps)
    #get_thumbnails(args.url)
