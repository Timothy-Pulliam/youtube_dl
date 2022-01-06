#!/usr/bin/env python
# -*- coding: utf-8 -*-

import youtube_dl
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from pymongo import MongoClient
from datetime import datetime
import json
import argparse
import shutil
import re
from pprint import pprint
import requests
import subprocess
from config import YOUTUBE_API_KEY

# Connect db
client = MongoClient('localhost', 27017, connect=False)
db = client['youtube_dl']
collection = db['meta']

###################################################
#
#
#               Argparse Options
#
###################################################
parser = argparse.ArgumentParser(description='Download audio and convert to FLAC')
parser.add_argument(
    '--force', action='store_true', default=False,
    help="Force a redownload. By default, if a track has already been downloaded \
        once, it will not be redownloaded again. Passing --force will redownload the track."
)

parser.add_argument(
    '--split-tracks', action='store_true', default=False,
    help="If timestamps can be successfully retrieved from the video description, \
        attempt to split the video into multiple smaller tracks."
)

parser.add_argument(
    '--download', action=argparse.BooleanOptionalAction, default=True,
    help="Download the audio file. This is the default. \
        Pass --no-download to run the script without downloading \
        (still collects song info)."
)

parser.add_argument(
    '--queue-file', type=str,
    help="A file containing the tracks to download \
        example: \
        queue.txt"\
)

parser.add_argument(
    'urls', metavar='URLS', type=str, nargs='*',
    help='urls for the youtube videos. \
    example: \
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

#############################################
#
#   Youtube_DL Options
#
#############################################

# download files to this location
DOWNLOAD_DIR = '/Users/tpulliam/Archives/Music/'
if args.is_playlist:
    outtmpl = DOWNLOAD_DIR + '%(playlist_title)s/%(title)s.%(ext)s'
else:
    outtmpl = DOWNLOAD_DIR + '%(title)s/%(title)s.%(ext)s'

ydl_options = {
    'outtmpl': outtmpl,
    'format': 'bestaudio/best',
    'retries': 10,
    'continuedl': True,
    'verbose': True,
    'postprocessors': [{
        'key': 'FFmpegExtractAudio',
        'preferredcodec': 'flac',
        #'preferredquality': '192',
    }],
    'writethumbnail': True,
}

ydl = youtube_dl.YoutubeDL(ydl_options)

def split_tracks(original_track, timestamps):
    """split a music track into specified sub-tracks by calling ffmpeg from the shell"""
    # create a template of the ffmpeg call in advance
    cmd_string = 'ffmpeg -i {tr} -acodec copy -ss {st} -to {en} {nm}.flac'
    with open('timestamps.txt', 'r') as f:
        timestamps = collection.find_one({"video_id": url}, {"timestamps": 1})['timestamps']
        for line in f:
            # skip comments and empty lines
            if line.startswith('#') or len(line) <= 1:
                continue

            # create command string for a given track
            start, end, name = line.strip().split()
            command = cmd_string.format(tr=original_track, st=start, en=end, nm=name)
            subprocess.call(command, shell=True)
    return None

def get_thumbnails(url, file_dest):
    with build('youtube', 'v3', developerKey=YOUTUBE_API_KEY) as service:
        request = service.videos().list(part='snippet', id=url)
        try:
            response = request.execute()
            thumbnails = response['items'][0]['snippet']['thumbnails']
            for key in thumbnails.keys():
                r = requests.get(thumbnails[key]['url'], stream=True)
                with open(file_dest + key + '.jpg', 'wb') as out_file:
                    shutil.copyfileobj(r.raw, out_file)
        except HttpError as e:
            print('Error response status code : {0}, reason : {1}'.format(e.status_code, e.error_details))
            return {}
        collection.update_one({"video_id": url}, {"$set": {"thumbnails": thumbnails}})
        #return response

# def get_comment_threads(videoId, maxResults=20, pageToken=None):
#     """Returns top level comments
#     maxResults: number of threads per page
#     pageToken: page to retrieve"""
#     with build('youtube', 'v3', developerKey=YOUTUBE_API_KEY) as service:
#         request = service.commentThreads().list(part='snippet,replies', videoId=videoId, maxResults=maxResults, pageToken=pageToken)
#         try:
#             response = request.execute()
#         except HttpError as e:
#             print('Error response status code : {0}, reason : {1}'.format(e.status_code, e.error_details))
#             return {}
#         return response

# def get_comment(parentCommentId):
#     """gets reply to top level comment"""
#     with build('youtube', 'v3', developerKey=YOUTUBE_API_KEY) as service:
#         request = service.comments().list(part='snippet', videoId=videoId)
#         try:
#             response = request.execute()
#         except HttpError as e:
#             print('Error response status code : {0}, reason : {1}'.format(e.status_code, e.error_details))
#             return {}
#         return response


def get_video_id(url):
    """
    input: https://www.youtube.com/watch?v=beHVaOSn9-o
    output: beHVaOSn9-o

    input: beHVaOSn9-o
    output: beHVaOSn9-o
    """
    try:
        return url[url.rindex('=')+1:]
    except ValueError:
        return url

def download_audio(urls):
    """
    Download specified YouTube tracks as command line arguments, or through a queue file

    Returns:
    file_dest where the audio file was downloaded to
    """
    with ydl:
        # Get filename location
        meta = ydl.extract_info(
            url,
            download=args.download) # We just want to extract the path the filename the audio file is downloaded to
        # where the files are downloaded
        # file_dest = ["~/Music/songname/", "~/Music/songname/songname.flac"]
        file_dest = ["{}{}/".format(DOWNLOAD_DIR, meta['title']), "{}{}/{}.{}".format(DOWNLOAD_DIR, meta['title'], meta['title'], meta['ext'])]
    collection.update_one({"video_id": url}, {"$set": {"download_date": datetime.utcnow(), "downloaded": False}})
    if args.download:
        collection.update_one({"video_id": url}, {"$set": {"downloaded": True}})
    return file_dest

def get_description(url):
    """
    Get the video descriptions, which may include artist, date, timstamp information.
    """
    with build('youtube', 'v3', developerKey=YOUTUBE_API_KEY) as service:
        request = service.videos().list(part='snippet', id=url)
        try:
            response = request.execute()
        except HttpError as e:
            print('Error response status code : {0}, reason : {1}'.format(e.status_code, e.error_details))
            return {}
    description = response['items'][0]['snippet']['description']
    collection.update_one({"video_id": url}, {"$set": {"description": description}}, upsert=True)
    return description


def get_timestamps(url):
    """
    Get timestamp information from the video description if available

    Example output:
    {"video_id": ['00:00', '03:30', ...]}
    """
    description = get_description(url)
    timestamps = []
    matches = re.finditer(r'([0-9]{1,2}:)?[0-9]{1,2}:[0-9]{1,2}', description)
    for m in matches:
        timestamps.append(m[0])
    collection.update_one({'video_id': url}, {'$set': {'timestamps': timestamps}})

def dedup_queue():
    # remove duplicate entries from the queue to
    # avoid downloading the same track multiple times
    with open('queue.txt', 'r') as queue:
        unique_lines = set(queue.readlines())
    with open('queue.txt', 'w') as queue:
        queue.writelines(unique_lines)

if __name__ == '__main__':
    dedup_queue()
    if args.queue_file:
        with open(args.queue_file, 'r') as queue:
            for url in queue:
                url = get_video_id(url)
                # Has this video been downloaded before?
                if args.force or (collection.count_documents({"video_id": url}) == 0) or (collection.count_documents({"video_id": url}, {"downloaded", 1})["downloaded"] == False):
                    timestamps = get_timestamps(url)
                    file_dest = download_audio(url, file_dest[0])
                    get_thumbnails(url)
                    if args.split_tracks:
                        split_tracks(dest_file, timestamps)
                else:
                    # if track has already been downloaded, skip it
                    # unless --force has been passed
                    print("already downloaded, skipping")
                    continue
    if args.urls:
        for url in args.urls:
            url = get_video_id(url)
            # Has this video been downloaded before?
            if args.force or (collection.count_documents({"video_id": url}) == 0) or (collection.count_documents({"video_id": url}, {"downloaded", 1})["downloaded"] == False):
                timestamps = get_timestamps(url)
                file_dest = download_audio(url)
                get_thumbnails(url, file_dest[0])
                if args.split_tracks:
                    split_tracks(dest_file, timestamps)
            else:
                # if track has already been downloaded, skip it
                # unless --force has been passed
                print("already downloaded, skipping")
                continue

