#!/usr/bin/env python
# -*- coding: utf-8 -*-

import youtube_dl
import sys
import argparse
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pprint import pprint
import re
import html
import requests
import shutil

YOUTUBE_API_KEY = 'AIzaSyCGl3sd8WcLjijySs3i3f2nd0ikV5i0O6Q'

parser = argparse.ArgumentParser(description='Download audio and video from YouTube')
parser.add_argument(
        'url', metavar='URL', type=str, nargs='+',
        help='url for the youtube video. example: \
        http://www.youtube.com/watch?v=BaW_jenozKc'
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
# print(args.url)

ALBUM_DIR = '/mnt/Music/%(title)s/%(title)s.%(ext)s'
PLAYLIST_DIR = '/mnt/Music/%(playlist_title)s/%(title)s.%(ext)s'
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

def get_description(url):
    with build('youtube', 'v3', developerKey=YOUTUBE_API_KEY) as service:
        request = service.videos().list(part='snippet', id=get_video_ids(args.url))
        try:
            response = request.execute()
        except HttpError as e:
            print('Error response status code : {0}, reason : {1}'.format(e.status_code, e.error_details))
            return {}
    description = response['items'][0]['snippet']['description']
    return description

def get_timestamps(url):
    description = get_description(url)
    timestamps = re.finditer(r'[0-9]+:[0-9]+.*', description)
    # write timestamps to file
    with open('timestamps.txt', 'w') as f:
        for match in timestamps:
            f.write(match[0] + "\n")
    # optionally return timestamps
    return timestamps

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

def get_video_ids(urls):
    """
    input: https://www.youtube.com/watch?v=beHVaOSn9-o
    output: beHVaOSn9-o
    """
    ids = []
    for url in urls:
        ids.append(url[url.rindex('=')+1:])
    return ids

def trim_logs():
    with open('track_log.txt', 'r') as log:
        lines = set(log.readlines())

def download_audio(urls):
    with ydl:
        for url in urls:
            print(url)
            with open('track_log.txt', 'a') as log:
                log.write(url+'\n')
           # result = ydl.extract_info(
           #     url,
           #     # download=False # We just want to extract the info
           # )
        result = ydl.download(urls)
       # if 'entries' in result:
       #     # can be playlist or list of videos
       #     video = result['entries'][0]
       # else:
       #     # Just a video
       #     video = result

if __name__ == '__main__':
    print(args.url)
    print(ydl.prepare_filename(ydl_options))
    #download_audio(args.url)
    timestamps = get_timestamps(args.url)
    get_thumbnails(args.url)
