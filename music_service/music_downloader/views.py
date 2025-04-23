# music_downloader/views.py

from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import requests
from hashlib import md5
from django.http import JsonResponse
from django.conf import settings
import os
import time
from threading import Thread

from mutagen.flac import FLAC
from mutagen.id3 import USLT, ID3, TIT2, TALB, TPE1, ID3NoHeaderError
from mutagen.easyid3 import EasyID3

from music_downloader.api_url import MUSIC_API_SEARCH_URL, MUSIC_API_TRACK_URL, MUSIC_API_LYRIC_URL, MUSIC_API_COVER_URL

# 全局变量模拟任务状态
task_status = {
    "status": "idle",  # 状态：idle -> parsing -> downloading_song -> downloading_lyrics -> completed
    "message": "",
}

def update_status(new_status, message):
    """更新全局任务状态"""
    task_status["status"] = new_status
    task_status["message"] = message

def get_status(request):
    """返回当前任务状态"""
    return JsonResponse(task_status)

def sanitize_filename(filename):
    """清理文件名中的特殊字符"""
    import re
    return re.sub(r'[\\/*?:"<>|]', '', filename)

def write_tags(song_path, artist, title, album, lyrics):
    """将标签信息写入音频文件"""
    try:
        if song_path.endswith('.flac'):
            # 操作 FLAC 文件
            audio = FLAC(song_path)
            audio["artist"] = artist
            audio["title"] = title
            audio["album"] = album
            if lyrics:
                audio["lyrics"] = lyrics
            audio.save()
        elif song_path.endswith('.mp3'):
            # 操作 MP3 文件
            try:
                audio = EasyID3(song_path)
            except ID3NoHeaderError:
                audio = ID3(song_path)

            audio["artist"] = artist
            audio["title"] = title
            audio["album"] = album
            audio.save()

            # 添加歌词到 MP3
            if lyrics:
                id3 = ID3(song_path)
                id3.add(USLT(encoding=3, text=lyrics))
                id3.save()
        else:
            print(f"不支持的文件类型: {song_path}")
    except Exception as e:
        print(f"写入标签失败: {e}, 跳过...")

def fetch_cover(pic_id, source = "netease", size = 500):
    """
    根据歌名、专辑名和歌手调用 API 获取封面 URL
    """
    try:
        # 调用外部封面 API
        cover_url = MUSIC_API_COVER_URL.replace("[PIC ID]", str(pic_id)).replace("[MUSIC SOURCE]", source).replace("[SIZE]", str(size))
        response = requests.get(cover_url)
        if response.status_code != 200:
            raise Exception("获取封面失败，API 返回错误")
        # 检查返回数据
        response_data = response.json()
        if not response_data.get("url"):
            raise Exception("获取封面失败，返回数据不完整")
        # 返回封面 URL
        return response_data.get("url")
    except Exception as e:
        print(f"获取封面失败: {e}")
        return None
    

# def search_music(request):
#     """处理搜索请求"""
#     query = request.GET.get('query', '').strip()
#     limit = int(request.GET.get('limit', 10))  # 默认10条，用户可选10或50条
#     if not query:
#         return JsonResponse({"status": "error", "message": "请输入搜索关键词"})

#     try:
#         # 调用外部搜索 API
#     # 调用网易云音乐搜索 API
#         search_url = f"http://music.163.com/api/search/get/web?csrf_token=&hlpretag=&hlposttag=&s={query}&type=1&offset=0&total=true&limit={limit}"
#         response = requests.get(search_url)
#         response_data = response.json()

#         if response_data.get("code") == 200:
#             songs = response_data["result"].get("songs", [])
#             results = []
#             # 提取需要的数据
#             for song in songs:
#                 song_id = song["id"]
#                 song_name = song["name"]
#                 song_artists = ", ".join(artist["name"] for artist in song["artists"])
#                 song_album = song["album"]["name"]
#                 # song_cover = fetch_cover(song_name, song_album, song_artists)
#                 results.append({
#                     "id": song_id,
#                     "name": song_name,
#                     "artists": song_artists,
#                     "album": song_album,
#                     # "cover": song_cover
#                 }) 
#             return JsonResponse({"status": "success", "results": results})
#         else:
#             return JsonResponse({"status": "error", "message": "搜索失败"})
#     except Exception as e:
#         return JsonResponse({"status": "error", "message": str(e)})

def search_music(request):
    """处理搜索请求"""
    query = request.GET.get('query', '').strip()
    limit = int(request.GET.get('limit', 10))  # 默认10条，用户可选10或50条
    pages = int(request.GET.get('pages', 1))  # 默认第1页
    source = request.GET.get('source', 'netease')  # 默认网易云音乐

    if not query:
        return JsonResponse({"status": "error", "message": "请输入搜索关键词"})

    try:
        # 调用外部搜索 API
        search_url = MUSIC_API_SEARCH_URL.replace("[KEYWORD]", query).replace("[PAGE LENGTH]", str(limit)).replace("[PAGE NUM]", str(pages)).replace("[MUSIC SOURCE]", source)
        response = requests.get(search_url)

        if response.status_code == 200:
            songs = response.json()
            results = []
            # 提取需要的数据
            for song in songs:
                song_id = song["id"]
                song_name = song["name"]
                song_artists = ", ".join(artist for artist in song["artist"])
                song_album = song["album"]
                song_cover_id= song["pic_id"]
                song_cover = fetch_cover(song_cover_id, source)
                results.append({
                    "id": song_id,
                    "name": song_name,
                    "artists": song_artists,
                    "album": song_album,
                    "cover": song_cover
                }) 
            return JsonResponse({"status": "success", "results": results})
        else:
            return JsonResponse({"status": "error", "message": "搜索失败"})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)})

def download_song_thread(music_info, source = "netease", bitrate = "999"):
    update_status("parsing", "正在解析链接...")

    try:
        # Step 1: 请求歌曲地址
        update_status("parsing", "调用接口获取歌曲信息...")
        download_url = MUSIC_API_TRACK_URL.replace("[TRACK ID]", music_info['id']).replace("[BITRATE]", bitrate).replace("[MUSIC SOURCE]", source)
        response = requests.get(download_url)
        if response.status_code != 200:
            update_status("error", "获取歌曲信息失败")
            return JsonResponse({"status": "error", "message": "Failed to get music information."})
        # 检查返回数据
        music_data = response.json()
        if not music_data or 'url' not in music_data:
            update_status("error", "歌曲信息不完整")
            return JsonResponse({"status": "error", "message": "Incomplete music information."})
        # Step 3: 下载歌曲
        update_status("downloading_song", "正在下载歌曲...")
        song_url = music_data['url']
        if not song_url:
            update_status("error", "歌曲链接缺失，该音源可能不支持下载")
            return JsonResponse({"status": "error", "message": "Song URL is missing."})

        # 下载歌曲文件
        extension = song_url.split('.')[-1]
        song_response = requests.get(song_url, stream=True)
        song_path = os.path.join(settings.MEDIA_ROOT, f"{music_info['artists']} - {music_info['name']}.{extension}")
        os.makedirs(os.path.dirname(song_path), exist_ok=True)

        with open(song_path, 'wb') as f:
            for chunk in song_response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Step 4: 下载歌词
        update_status("downloading_lyrics", "正在下载歌词...")
        lyric_url = MUSIC_API_LYRIC_URL.replace("[LYRIC ID]", music_info['id']).replace("[MUSIC SOURCE]", source)
        lyric_response = requests.get(lyric_url)
        if lyric_response.status_code != 200:
            update_status("error", "获取歌词失败")
            return JsonResponse({"status": "error", "message": "Failed to get lyrics."})
        # 检查返回数据
        lyric_response_data = lyric_response.json()
        lyrics = lyric_response_data['lyric']
        lyric_path = os.path.join(settings.MEDIA_ROOT, f"{music_info['artists']} - {music_info['name']}.lrc")
        with open(lyric_path, 'w', encoding='utf-8') as f:
            f.write(lyrics)

         # Step 5: 写入标签
        update_status("writing_tags", "正在写入标签...")
        write_tags(song_path, music_info['artists'], music_info['name'], music_info['album'], lyrics)
        
        # 完成
        update_status("completed", "下载完成！")
        return JsonResponse({
            "status": "success",
            "song_path": song_path,
            "lyric_path": lyric_path,
            "details": music_data
        })

    except Exception as e:
        update_status("error", f"下载失败：{str(e)}")
        return JsonResponse({"status": "error", "message": str(e)})    

def format_music_url(input_value):
    """
    格式化用户输入为完整的歌曲 URL
    如果用户输入的是纯数字（id），拼接成完整 URL
    如果是完整 URL，直接返回
    """
    if input_value.isdigit():
        return f"https://music.163.com/#/song?id={input_value}"
    elif input_value.startswith("https://music.163.com"):
        return input_value
    else:
        raise ValueError("无效的输入，请输入歌曲 ID 或合法的网易云音乐链接")

def download_song(request):
    if request.method == 'POST':
        # 重置状态
        update_status("idle", "等待操作...")
        
        music_info = {}
        music_info['id'] = request.POST.get('id')
        music_info['name'] = request.POST.get('name')
        music_info['album'] = request.POST.get('album')
        music_info['artists'] = request.POST.get('artists')
        source = request.POST.get('source', 'netease')

        print(music_info)
        Thread(target=download_song_thread, args=(music_info,source)).start()
        
        return JsonResponse({"status": "success", "message": "Downloading..."})
    return JsonResponse({"status": "error", "message": "仅支持 POST 请求"})
