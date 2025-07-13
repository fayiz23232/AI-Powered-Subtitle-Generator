document.addEventListener('DOMContentLoaded', () => {
    const videoInput = document.getElementById('video-input');
    const fileNameDisplay = document.getElementById('file-name');
    const generateBtn = document.getElementById('generate-btn');
    const statusText = document.getElementById('status-text');
    const loader = document.getElementById('loader');
    const resultArea = document.getElementById('result-area');
    const downloadLink = document.getElementById('download-link');
    const uploadArea = document.getElementById('upload-area');

    uploadArea.addEventListener('click', () => videoInput.click());

    videoInput.addEventListener('change', () => {
        if (videoInput.files.length > 0) {
            fileNameDisplay.textContent = videoInput.files[0].name;
            generateBtn.disabled = false;
        }
    });

    generateBtn.addEventListener('click', async () => {
        if (videoInput.files.length === 0) {
            alert('Please select a video file first.');
            return;
        }

        const formData = new FormData();
        formData.append('video', videoInput.files[0]);

        // Reset UI
        generateBtn.disabled = true;
        statusText.textContent = 'Uploading and processing video... This may take a while.';
        loader.style.display = 'block';
        resultArea.style.display = 'none';

        try {
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const result = await response.json();

            if (response.ok) {
                statusText.textContent = 'Processing complete!';
                downloadLink.href = `/subtitles/${result.subtitle_file}`;
                downloadLink.download = result.subtitle_file;
                resultArea.style.display = 'block';
            } else {
                throw new Error(result.error || 'An unknown error occurred.');
            }

        } catch (error) {
            statusText.textContent = `Error: ${error.message}`;
        } finally {
            loader.style.display = 'none';
            generateBtn.disabled = false;
        }
    });
});