from pydub import AudioSegment
from flask import Flask, request, jsonify, send_from_directory, render_template
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import soundfile as sf
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.signal import spectrogram
import subprocess

app = Flask(__name__, static_url_path='', static_folder='static')

UPLOAD_FOLDER = './audio'
TEMP_FOLDER = './temp'
IMAGE_FOLDER = './spectrogram'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['TEMP_FOLDER'] = TEMP_FOLDER
app.config['IMAGE_FOLDER'] = IMAGE_FOLDER

def convert_mp3_to_wav(input_path, output_path):
    """
    Converts an MP3 file to a WAV file using FFmpeg, ensuring the output format is explicitly set.

    Args:
        input_path (str): Path to the input MP3 file.
        output_path (str): Path to the output WAV file.
    """
    command = [
        "ffmpeg",
        "-i", input_path,
        "-acodec", "pcm_s16le",
        "-ar", "44100",
        "-ac", "2",
        "-f", "wav",
        output_path
    ]
    try:
        result = subprocess.run(command, check=True, stderr=subprocess.PIPE, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        raise Exception("Conversion failed: " + e.stderr.decode())

@app.route('/upload-temp', methods=['POST'])
def upload_temp():
    audio = request.files['audio']
    filename = datetime.now().strftime('%y%m%d%H%M%S%f')[:15]  # GMT+9
    audio_filename = secure_filename(f"{filename}.mp3")
    audio_path = os.path.join(app.config['TEMP_FOLDER'], audio_filename)
    audio.save(audio_path)

    if not os.path.exists(audio_path) or os.path.getsize(audio_path) == 0:
        return jsonify({'error': 'Failed to save file properly'}), 500
    
    # image
    #time.sleep(1)

    wav_filename = filename.replace('.mp3', '.wav')
    wav_filename = f"{wav_filename}.wav"
    wav_path = os.path.join(app.config['IMAGE_FOLDER'], wav_filename)

    try:
        convert_mp3_to_wav(audio_path, wav_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    # WAV 파일로부터 스펙트로그램 생성
    image_filename = wav_filename.replace('.wav', '.png')
    image_path = os.path.join(app.config['IMAGE_FOLDER'], image_filename)
    
    try:
        generate_spectrogram(wav_path, image_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    return jsonify({
        'message': 'File processed successfully', 
        'audio_filename': audio_filename, 
        'wav_filename': wav_filename, 
        'image_filename': image_filename
        }), 200
    
    #return jsonify({'error': 'No file uploaded'}), 400

@app.route('/convert-to-audio/<filename>', methods=['GET'])
def convert_to_audio(filename):
    temp_path = os.path.join(app.config['TEMP_FOLDER'], filename)
    audio_path = os.path.join(app.config['UPLOAD_FOLDER'], filename.replace('.mp3', '.wav'))
    if not os.path.exists(temp_path):
        return jsonify({'error': 'Temporary file not found'}), 404

    command = f"ffmpeg -i \"{temp_path}\" -acodec pcm_s16le \"{audio_path}\""
    try:
        result = os.system(command)
        if result != 0:
            return jsonify({'error': f'Conversion failed with exit code {result}'}), 500
        os.remove(temp_path)
        return jsonify({'message': 'Recording is submitted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/generate-spectrogram', methods=['POST'])
def generate_spectrogram(wav_path, output_path):
    if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
        return
    
    data, samplerate = sf.read(wav_path)

    if data.ndim > 1:
        data = data.mean(axis=1)  # 모노 변환

    nperseg = 256
    if len(data) < nperseg:
        data = np.pad(data, (0, nperseg - len(data)), 'constant', constant_values=(0, 0))

    f, t, Sxx = spectrogram(data, samplerate, nperseg=nperseg)

    if Sxx.size == 0:
        return

    plt.figure(figsize=(10, 4))
    try:
        plt.pcolormesh(t, f, 10 * np.log10(Sxx), shading='gouraud')
        plt.ylabel('Frequency [Hz]')
        plt.xlabel('Time [sec]')
        plt.colorbar(label='Intensity [dB]')
        plt.savefig(output_path)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        plt.close()

    return jsonify({'message': 'Spectrogram generated successfully', 'path': output_path}), 200

@app.route('/spectrogram/<filename>')
def spectrogram_file(filename):
    return send_from_directory(app.config['IMAGE_FOLDER'], filename)

@app.route('/submit', methods=['POST'])
def submit_file():
    data = request.get_json()
    audio_filename = data.get('audio_filename')

    temp_path = os.path.join(TEMP_FOLDER, audio_filename)

    if not audio_filename:
        return jsonify({'error': 'Filename is required'}), 400

    mp3_path = os.path.join(app.config['TEMP_FOLDER'], audio_filename)
    if not os.path.exists(mp3_path):
        return jsonify({'error': 'File not found'}), 404
    
    # check file length
    audio = AudioSegment.from_file(temp_path)
    duration_seconds = len(audio) / 1000

    if duration_seconds < 30:
        return jsonify({'error': 'Recording must be at least 30 seconds long'}), 400
    
    wav_path = os.path.join(app.config['UPLOAD_FOLDER'], audio_filename.replace('.mp3', '.wav'))

    #AudioSegment.from_mp3(mp3_path).export(wav_path, format='wav')
    audio.export(wav_path, format='wav')
    #os.rename(os.path.join(TEMP_FOLDER, image_filename), os.path.join('/spectrogram', image_filename))

    os.remove(temp_path)  # Clean up MP3 after conversion

    return jsonify({'message': 'File submitted successfully', 'filename': audio_filename.replace('.mp3', '.wav')}), 200

@app.route('/temp/<filename>')
def temp_file(filename):
    return send_from_directory(TEMP_FOLDER, filename)

@app.route('/delete-temp/<filename>', methods=['POST'])
def delete_temp_file(filename):
    file_path = os.path.join(app.config['TEMP_FOLDER'], filename)
    if os.path.exists(file_path):
        os.remove(file_path)
        return jsonify({'message': 'Temp file deleted successfully'})
    return jsonify({'error': 'File not found'}), 404

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/record')
def record():
    return render_template('record.html')

if __name__ == '__main__':
    app.run(debug=True)