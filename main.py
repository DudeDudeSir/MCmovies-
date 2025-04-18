from flask import Flask, render_template, request, send_file, jsonify, redirect, session, url_for
import yt_dlp
import os
import instaloader
from utils.torrent_handler import start_peerflix_stream  # ✅ Make sure this import is present
from pymongo import MongoClient  # ✅ MongoDB import
import time

app = Flask(__name__)
app.secret_key = 'supersecretkey'  # Required for session

# MongoDB connection
mongo_uri = "mongodb+srv://mc:movies@cluster0.fly2rzv.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(mongo_uri)
db = client["movieDB"]
movies_collection = db["movies"]

# Ensure uploads folder exists
UPLOAD_FOLDER = "uploads/torrents"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Download Instagram video
def download_instagram(url):
    loader = instaloader.Instaloader()
    try:
        post = instaloader.Post.from_shortcode(loader.context, url.split("/")[-2])
        if post.is_video:
            video_url = post.video_url
            return {
                "download_link": video_url,
                "thumbnail": post.url,
                "title": "Instagram Video"
            }
        else:
            return {"error": "This is not a video post"}
    except Exception as e:
        return {"error": f"Could not retrieve Instagram video: {str(e)}"}

# Download Facebook video (using yt-dlp)
def download_facebook(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get('url', None)
            thumbnail = info.get('thumbnail')
            title = info.get('title')
            return {
                "download_link": video_url,
                "thumbnail": thumbnail,
                "title": title
            }
    except Exception as e:
        return {"error": f"Could not retrieve Facebook video: {str(e)}"}

# Download YouTube video (using yt-dlp)
def download_youtube(url):
    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            video_url = info.get('url', None)
            thumbnail = info.get('thumbnail')
            title = info.get('title')
            return {
                "download_link": video_url,
                "thumbnail": thumbnail,
                "title": title
            }
    except Exception as e:
        return {"error": f"Could not retrieve YouTube video: {str(e)}"}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/tools')
def tools():
    return render_template('tools.html')

@app.route('/games')
def games():
    return render_template('games.html')

@app.route('/movies')
def movies_page():
        movies = list(movies_collection.find())  # Get all movies
        return render_template('movies.html', movies=movies)



@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/play')
def play_games():
    return render_template('games_alt.html')

@app.route('/games/memory')
def memory_game():
    return render_template('memory.html')

@app.route('/games/shooter')
def shooter_game():
    return render_template('shooter.html')

@app.route('/games/falling-blocks')
def falling_blocks_game():
    return render_template('games/falling-blocks/index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['password'] == 'adminpass123':
            session['admin'] = True
            return redirect('/add_movie_page')
        else:
            return 'Wrong password!'
    return '''
        <form method="post">
            <input type="password" name="password" placeholder="Enter admin password">
            <input type="submit" value="Login">
        </form>
    '''

@app.route('/add_movie_page')
def add_movie_page():
    if not session.get('admin'):
        return redirect('/login')
    return render_template('add_movie.html')

@app.route('/add_movie', methods=['POST'])
def add_movie():
    title = request.form.get('title')
    year = request.form.get('year')
    genre = request.form.get('genre')
    rating = float(request.form.get('rating'))
    torrent_type = request.form.get('torrent_type')
    poster = request.form.get('poster') or "https://via.placeholder.com/300x450?text=No+Poster"

    if torrent_type == 'link':
        torrent_id = request.form.get('torrent_link')
        torrent_file_name = None
    else:
        file = request.files.get('torrent_file')
        if file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)
            torrent_id = None
            torrent_file_name = file.filename
        else:
            torrent_id = None
            torrent_file_name = None

    movie = {
        "title": title,
        "year": year,
        "genre": genre,
        "rating": rating,
        "torrent_id": torrent_id,
        "torrent_file": torrent_file_name,
        "poster": poster
    }
    movies_collection.insert_one(movie)
    return redirect('/movies')

@app.route('/watch')
def watch_movie():
    torrent = request.args.get('torrent')
    return render_template('watch.html', torrent=torrent)




@app.route('/download')
def download_movie():
    torrent_id = request.args.get('torrent')
    title = request.args.get('title')
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{torrent_id}.torrent")

    if os.path.exists(file_path):
        return send_file(file_path, as_attachment=True)
    else:
        return jsonify({"error": "Torrent file not found"}), 404

@app.route('/tools/download', methods=['POST'])
def download():
    url = request.form.get('url')

    if not url:
        return jsonify({"error": "No URL provided"})

    if 'youtube.com' in url or 'youtu.be' in url:
        result = download_youtube(url)
    elif 'instagram.com' in url:
        result = download_instagram(url)
    elif 'facebook.com' in url:
        result = download_facebook(url)
    else:
        result = {"error": "Unsupported URL"}

    return jsonify(result)

if __name__ == '__main__':
    if not os.path.exists("downloads"):
        os.makedirs("downloads")
    app.run(host='0.0.0.0', port=8080)
