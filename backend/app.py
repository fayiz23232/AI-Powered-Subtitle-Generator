from flask import Flask, request, render_template, jsonify, send_from_directory
import os
import whisper
from moviepy.editor import VideoFileClip
import cv2
import numpy as np
import datetime

app = Flask(__name__, template_folder='../templates', static_folder='../static')

# --- Configuration ---
UPLOAD_FOLDER = 'uploads'
SUBTITLE_FOLDER = 'subtitles'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SUBTITLE_FOLDER'] = SUBTITLE_FOLDER

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SUBTITLE_FOLDER, exist_ok=True)

# --- Helper Functions ---
def format_time(seconds):
    """Converts seconds to SRT time format (HH:MM:SS,ms)."""
    delta = datetime.timedelta(seconds=seconds)
    hours, remainder = divmod(delta.seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = delta.microseconds // 1000
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"

def detect_scene_changes(video_path, threshold=30.0):
    """Detects scene changes and returns their timestamps in seconds."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    scene_changes = [0.0]  # Start with the beginning of the video
    prev_frame_hist = None
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps == 0:
        fps = 25 # Default fps

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        cv2.normalize(hist, hist)

        if prev_frame_hist is not None:
            diff = cv2.compareHist(prev_frame_hist, hist, cv2.HISTCMP_BHATTACHARYYA)
            if diff > threshold / 100.0: # Threshold adjusted for this comparison method
                timestamp = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                scene_changes.append(timestamp)
        
        prev_frame_hist = hist
    
    cap.release()
    return scene_changes

# --- Flask Routes ---
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_video():
    if 'video' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    video_file = request.files['video']
    if video_file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    video_path = os.path.join(app.config['UPLOAD_FOLDER'], video_file.filename)
    video_file.save(video_path)

    try:
        # 1. Extract Audio
        video_clip = VideoFileClip(video_path)
        audio_path = os.path.splitext(video_path)[0] + ".wav"
        video_clip.audio.write_audiofile(audio_path)
        video_clip.close()

        # 2. Transcribe Audio
        model = whisper.load_model("base") # Use "small", "medium" for better accuracy
        transcription_result = model.transcribe(audio_path, word_timestamps=True)

        # 3. Detect Scene Changes
        scene_changes = detect_scene_changes(video_path)

        # 4. Generate SRT Subtitles
        subtitle_filename = os.path.splitext(video_file.filename)[0] + ".srt"
        subtitle_path = os.path.join(app.config['SUBTITLE_FOLDER'], subtitle_filename)
        
        with open(subtitle_path, 'w') as f:
            segment_index = 1
            for i, segment in enumerate(transcription_result['segments']):
                start_time = segment['start']
                end_time = segment['end']
                text = segment['text'].strip()

                # Adjust segment end time based on scene changes
                for scene_time in scene_changes:
                    if start_time < scene_time < end_time:
                        end_time = scene_time
                        break

                f.write(f"{segment_index}\n")
                f.write(f"{format_time(start_time)} --> {format_time(end_time)}\n")
                f.write(f"{text}\n\n")
                segment_index += 1
                
        # Clean up temporary files
        os.remove(video_path)
        os.remove(audio_path)

        return jsonify({'subtitle_file': subtitle_filename})

    except Exception as e:
        # Clean up in case of error
        if os.path.exists(video_path):
            os.remove(video_path)
        return jsonify({'error': str(e)}), 500

@app.route('/subtitles/<filename>')
def download_subtitle(filename):
    return send_from_directory(app.config['SUBTITLE_FOLDER'], filename, as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)