# youtube_dl
wrapper script for downloading youtube FLAC audio files. 
In order to use all features, you need to have a YouTube Data API Key. 
You can get one from the [YouTube Developer Console](https://console.developers.google.com).

Place this key inside a file called `config.py`
```python
YOUTUBE_API_KEY = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
```

Planned Features:
* Download Highest Quality Audio and Convert to FLAC
* Download Youtube Thumbnail in all sizes
* Downloaded video timestamps, description, and thumbnail urls can be saved to a mongodb database if configured
* Split a single track into smaller tracks from scraped timestamps in a video description
* Possibly an interface (web) to play and interact with downloaded tracks

## Setup
0) Make sure ffmpeg is installed on your system (`apt install ffmpeg` or similar)

1) Run a mongo docker container, which stores data about downloaded tracks (video descriptions, timestamps, thumbnail urls)
2) `$ docker run -d --name mongo -p 27017:27017 mongo`

2) Make sure the YouTube API key is in `config.py`

3) Set the `DOWNLOAD_DIR` variable to point to where tracks should be downloaded to

## Running the script
Download youtube and convert to FLAC using ffmpeg.

`$ ./youtube "https://www.youtube.com/watch?v=FXdcZTv3VIw"`

`$ ./youtube FXdcZTv3VIw`

Force a download even if a track has already been downloaded before

`$ ./youtube --force FXdcZTv3VIw`

Don't download the video, but only get the track related data (video description, timestamps, thumbnails, etc.)

`$ ./youtube --no-download FXdcZTv3VIw`

Downloading multiple tracks

`$ ./youtube --no-download FXdcZTv3VIw 0doWBQK7pqQ`

Or specify a queue file containing a URL on each line

`$ ./youtube --queue-file queue.txt`
