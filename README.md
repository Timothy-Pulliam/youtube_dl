# youtube_dl
wrapper script for downloading youtube FLAC audio files. 
In order to use all features, you need to have a YouTube Data API Key. 
You can get one from the [YouTube Developer Console](https://console.developers.google.com).

```python
YOUTUBE_API_KEY = 'XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
```

Planned Features:
* Download Highest Quality Audio and Convert to FLAC
* Download Youtube Thumbnail in all sizes
* Downloaded video timestamps, description, and thumbnail urls can be saved to a mongodb database if configured
* Split a single track into smaller tracks from scraped timestamps in a video description
