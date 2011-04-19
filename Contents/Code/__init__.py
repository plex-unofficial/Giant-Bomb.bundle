# PMS plugin framework
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *

# Simplejson
import simplejson as json

# Urllib
import urllib

# WhiMAI
import whimai.wm as wm
import whimai.gb as gb

import sys

####################################################################################################

VIDEO_PREFIX = "/video/giantbomb"

NAME = L('Title')
ART           = 'art-default.png'
ICON          = 'icon-default.png'

SETTINGS_URL = "http://whimais.googlecode.com/svn/plugin%20data/branches/giantbomb%20-%20plex/giantbomb_settings.json"
SETTINGS_FILE_BACKUP = R("settings.backup")
SETTINGS_FILE = "settings.json"

VIDEO_FILE = "video.dat"
TEMPLATE_URL = "http://media.giantbomb.com/video/%(url)s"

JUSTIN_URL = "http://api.justin.tv/api/channel/archives/giantbomb.json?limit=%(lim)s&offset=%(off)s"

####################################################################################################

def Start():
    Plugin.AddPrefixHandler(VIDEO_PREFIX, VideoMainMenu, L('VideoTitle'), ICON, ART)

    Plugin.AddViewGroup("InfoList", viewMode="InfoList", mediaType="items")
    Plugin.AddViewGroup("List", viewMode="List", mediaType="items")

    MediaContainer.art = R(ART)
    MediaContainer.title1 = NAME
    DirectoryItem.thumb = R(ICON)

# Preferences
def CreatePrefs():
    Prefs.Add(id="quality", type="enum", values=["Low", "High"], default="1", label="Video Quality")

def ValidatePrefs():
    pass

def UpdateVideoData():
    # Get categories
    SETT = ""
    load_local = False
    
    # ...get settings from web
    try:
        s = urllib.urlopen( SETTINGS_URL )
        SETT = s.read()
        
        # ...check if data is ok
        json.loads(SETT, object_hook=wm.E('categories').as_e)[0]
    
    except:
        Log("SETTINGS UPDATE ERROR")
        load_local = True
    
    else:
        Log("SETTINGS UPDATE OK")
        Data.Save(SETTINGS_FILE, SETT)
    
    if load_local is True:
        # ...load settings from file
        try:
            # ...read settings from local file
            SETT = Data.Load(SETTINGS_FILE)
            
        except:
            Log("SETTINGS FILE ERROR, LOADING BACKUP")
            # ...read settings from local backup file
            SETT = Data.Load(SETTINGS_FILE_BACKUP)
    
        else:
            Log("SETTINGS FILE OK")
        
    # Collectiong categori information
    Dict.Set('cat', json.loads(SETT, object_hook=wm.E('categories').as_e))
    
    # Update video data
    # ...init video list setup and get total number of videos
    list = gb.List("videos")
    list.extra = "field_list=deck,image,name,publish_date,url&sort=publish_date"
    ok = list.update(0,0)
    if ok is False:
        Log("ERROR UPDATING VIDEO DATA")
        return
    
    total = list.getTotal()

    videos = []
    limit = 100
    
    # ...compare total to local total
    try:
        file_content = Data.Load(VIDEO_FILE)
        offset = json.loads(file_content, object_hook=wm.E('total').as_e)
        
        # ...test file integrati
        if offset != len(json.loads(file_content, object_hook=wm.E('videos').as_e)):
            Log("RAISE")
            raise ValueError
        
    except:
        Log("ERROR IN DATA FILE")
        offset = 0
    
    # ...if no new videos return
    if total == offset:
        Log("NO NEW VIDEOS")
        return
        
    # ...get old videos from file
    if offset != 0:
        try:
            videos.extend(json.loads(file_content, object_hook=wm.E('videos').as_e))
            
            # ...remove videos from the latest date
            last_date = videos[len(videos)-1]["publish_date"][0:10]
            for i in range(len(videos)-1,0,-1):
                if videos[i]["publish_date"][0:10] != last_date:
                    break
                del videos[i]
            offset = len(videos)
        
        except:
            Log("ERROR IN DATA FILE")
            videos = []
            offset = 0
    
    start_cnt = offset
    total_cnt = total - offset    
    # ...get the remaning videos
    while (offset < total):
        ok = list.update(offset,limit)
        if ok is False:
            Log("ERROR UPDATING VIDEO DATA")
            return
        
        videos.extend(list.results)
        offset += limit
        i_pct = int(( float(offset-start_cnt) / float(total_cnt))*100.0+0.5)
        Log(str(i_pct))
        
    # ...create json formated video data and write to file
    video_list = { 'total': total, 'videos': videos }
    Data.Save(VIDEO_FILE, json.dumps( video_list ))

  
# Main Menu
def VideoMainMenu(sender=None, filt=None):
    
    dir = MediaContainer(viewGroup="InfoList")
    
    # Update
    UpdateVideoData()
    
    # Video catagories
    cat = Dict.Get('cat')
    for i in range(len(cat)):
        dir.Append(
            Function(
                DirectoryItem(
                    CallbackExample,
                    cat[i]["name"],
                    summary=cat[i]["description"],
                    thumb=R(ICON),
                    art=R(ART)
                ), filt=cat[i]["filters"]
            )
        )
  
    # Search
    dir.Append(
        Function(
            InputDirectoryItem(
                SearchResults,
                "Search",
                "Search",
                summary="This lets you search for videos",
                thumb=R(ICON),
                art=R(ART)
            )
        )
    )

  
    # Preferences
    dir.Append(
        PrefsItem(
            title="Preferences",
            subtile="Preferences",
            summary="This lets you set preferences",
            thumb=R(ICON)
        )
    )

    # ... and then return the container
    return dir

def addVideosFile(filt, mustPassAllFilters=False):
    
    mc = MediaContainer()
    
    # Justin.tv list
    if (filt == ["live_cat"]):
        try:
            # Checking Justin.tv
            limit = 100
            offset = 0
            done = False
            j_list = []
            while done == False:
                s = urllib.urlopen( JUSTIN_URL%{ 'lim': limit , 'off': offset } )
                tmp = eval( s.read() )
                if len(tmp) is 0:
                    done = True
                else:
                    j_list.extend( tmp )
                    offset += limit
        
        except:
            Log("JUSTIN UPDATE ERROR")
            return mc
        
        else:
            Log("JUSTIN UPDATE OK")
            
            total = len( j_list )
            video_count = 0
            for i in range(0, len(j_list)):
                try:
                    name = j_list[i]["title"]
                except:
                    name = "Archived video stream from " + j_list[i]["created_on"]
                url = j_list[i]["video_file_url"]
                image = j_list[i]["image_url_medium"]
                deck = "Archived video stream from " + j_list[i]["created_on"]
                mc.Append( VideoItem(url, name, summary=deck, thumb=image, art=image) )
        
        return mc
    
    # Get video quality setting
    if ( Prefs.Get("quality") == "1" ) :
        endString = "_1500.mp4"
    else:
        endString = "_700.mp4"

    # Read to the data file
    try:
        file_content = Data.Load(VIDEO_FILE)
        total = json.loads(file_content, object_hook=wm.E('total').as_e)
        videos = json.loads(file_content, object_hook=wm.E('videos').as_e)
        
        # Test file integrati
        if total != len(videos):
            raise ValueError
        
    except:
        Log("ERROR IN DATA FILE")
        Data.Save(VIDEO_FILE,"")
        return mc
    
    video_count = 0
    for i in range(total-1,-1,-1):
        found = False
        name = videos[i]["name"]
    
        # All videos
        if (filt == ""):
            found = True
            
        # Latest
        elif (filt == ["latest_cat"]):
            if (i>total-26):
                found = True
                
        # Custom catagories
        else:
            for x in range(0, len(filt)):
                if( name.lower().find(filt[x].lower()) != -1):
                    found = True
                else:
                    if mustPassAllFilters is True:
                        found = False
                        break
        
        if (found is True):
            url = TEMPLATE_URL%{ 'url': videos[i]["url"].replace(".mp4",endString) }
            image = videos[i]["image"]["super_url"]
            deck = videos[i]["deck"].encode('utf-8')
            mc.Append( VideoItem(url, name, summary=deck, thumb=image, art=image) )
            
    return mc

def CallbackExample(sender, filt=None):
    return addVideosFile( filt )

# Search query
def SearchResults(sender,query=None):
    filt = query.rsplit(" ")
    return addVideosFile( filt, True )
    
  
