let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let recordingStartTime;
let audioContext = new (window.AudioContext || window.webkitAudioContext)();
let analyser = audioContext.createAnalyser();
let audioStream;

document.addEventListener('DOMContentLoaded', async () => {
    try {
        audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (error) {
        console.error('Error accessing media devices:', error);
    }
});

document.getElementById('recordButton').addEventListener('click', function() {
    if (isRecording || !audioStream) return;
    mediaRecorder = new MediaRecorder(audioStream);
    audioChunks = [];
    mediaRecorder.start();
    isRecording = true;
    recordingStartTime = Date.now();
    this.classList.add('recording');
    updateTimer = setInterval(() => {
        const elapsed = Date.now() - recordingStartTime;
        document.getElementById('recordingDuration').textContent = formatTime(elapsed);
    }, 10);

    mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        clearInterval(updateTimer); // stop timer when stop recording

        const audioBlob = new Blob(audioChunks, { type: 'audio/mp3' }); // Set MIME type to mp3
        const filename = new Date().toISOString().replace('T', '_').replace(/\..+/, '').replace(/:/g, '').slice(2);

        //const canvas = document.getElementById('spectrogramCanvas');
        //const imageDataURL = canvas.toDataURL('image/png'); //save png from canvas

        //const imageBlob = await fetch(imageDataURL).then(res => res.blob());
        
        const formData = new FormData();
        formData.append('audio', audioBlob, `${filename}.mp3`);
        //formData.append('image', imageBlob, `${filename}.png`);

        try {
            const response = await fetch('/upload-temp', { method: 'POST', body: formData });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || 'Failed to upload audio');
            }
            document.getElementById('audioPlayback').src = `/temp/${data.audio_filename}`;
            document.getElementById('spgimg').src = `/spectrogram/${data.image_filename}`;
            document.getElementById('audioPlayback').hidden = false;
            document.getElementById('spgimg').hidden = false;
            document.getElementById('submitBtn').disabled = false;
        } catch (error) {
            console.error('Failed to upload audio:', error);
        }
    };
    document.getElementById('recordButton').disabled = true;
    document.getElementById('stopButton').disabled = false;
    document.getElementById('recordButton').classList.remove('active');
});

document.getElementById('stopButton').addEventListener('click', () => {
        mediaRecorder.stop();
        document.getElementById('recordButton').disabled = false;
        document.getElementById('stopButton').disabled = true;
        isRecording = false;
        document.getElementById('recordButton').classList.remove('recording');
    });

function formatTime(milliseconds) {
    let totalSeconds = milliseconds / 1000;
    let minutes = Math.floor(totalSeconds / 60);
    let seconds = Math.floor(totalSeconds % 60);
    let millisecondsDisplay = Math.floor((totalSeconds - Math.floor(totalSeconds)) * 1000).toString().padStart(3, '0');
    return `${minutes}:${seconds < 10 ? '0' : ''}${seconds}:${millisecondsDisplay.slice(0, 2)}`;
}

document.getElementById('submitBtn').addEventListener('click', async () => {
    const recordedTime = Date.now() - recordingStartTime;
    const recordedSeconds = recordedTime / 1000;

    const audioSrc = document.getElementById('audioPlayback').src;
    const audio_filename = audioSrc.split('/').pop();
    const imageSrc = document.getElementById('spgimg').src;
    const image_filename = imageSrc.split('/').pop();

    console.log("submitting", { audio_filename })

    try {
        const response = await fetch(`/submit`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ audio_filename: audio_filename, image_filename: image_filename })
        });
        const data = await response.json();

        if (!response.ok) {
            showAlertModal();
            throw new Error(data.error || 'Failed to submit audio');
        }
        showSubmitModal();
        document.getElementById('submitBtn').disabled = true;
        console.log('Submission successful:', data.message);
    } catch (error) {
        console.error('Error submitting file:', error);
    }
});

// modal
const alertModal = document.getElementById('alertModal');
const submitModal = document.getElementById('submitModal');
const alertCloseButton = document.querySelector('#alertModal .close-button');
const submitCloseButton = document.querySelector('#submitModal .close-button');

alertCloseButton.onclick = function() {
    alertModal.style.display = "none";
}

submitCloseButton.onclick = function() {
    submitModal.style.display = "none";
}

window.onclick = function(event) {
    if (event.target == alertModal) {
        alertModal.style.display = "none";
    }
    if (event.target == submitModal) {
        submitModal.style.display = "none";
    }
}

// show modal when recording is not longer than 30sec
function showAlertModal() {
    alertModal.style.display = "block";
}
//show modal when recording is submitted
function showSubmitModal() {
    submitModal.style.display = "block";
}