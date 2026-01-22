
const dropzone = document.getElementById('dropzone');
const fileInput = document.getElementById('fileInput');
const dropzoneContent = document.querySelector('.dropzone-content');
const loadingState = document.getElementById('loading');
const successState = document.getElementById('success');
const downloadBtn = document.getElementById('downloadBtn');
const resetBtn = document.getElementById('resetBtn');

let currentBlob = null;
let currentFilename = "";

// Drag & Drop
dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropzone.classList.add('dragover');
});

dropzone.addEventListener('dragleave', () => {
    dropzone.classList.remove('dragover');
});

dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropzone.classList.remove('dragover');
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
});

// Click to upload
dropzone.addEventListener('click', () => {
    if (currentBlob) return; // Don't trigger if done
    fileInput.click();
});

fileInput.addEventListener('change', (e) => {
    if (fileInput.files.length > 0) {
        handleFile(fileInput.files[0]);
    }
});

async function handleFile(file) {
    if (file.type !== 'application/pdf') {
        alert('Please upload a PDF file.');
        return;
    }

    // UI Transition -> Loading
    dropzoneContent.classList.add('hidden');
    successState.classList.add('hidden');
    loadingState.classList.remove('hidden');

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch('/convert', {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error(await response.text());
        }

        currentBlob = await response.blob();
        currentFilename = file.name.replace('.pdf', '.pptx');

        // UI Transition -> Success
        loadingState.classList.add('hidden');
        successState.classList.remove('hidden');

        // Auto trigger download? Only if user wants?
        // Let's wait for button click to add "Wow" factor.

    } catch (err) {
        console.error(err);
        alert('Error converting file: ' + err.message);
        resetUI();
    }
}

downloadBtn.addEventListener('click', (e) => {
    e.stopPropagation(); // Prevent dropzone click
    if (!currentBlob) return;

    const url = window.URL.createObjectURL(currentBlob);
    const a = document.createElement('a');
    a.href = url;
    a.download = currentFilename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    a.remove();
});

resetBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    resetUI();
});

function resetUI() {
    currentBlob = null;
    fileInput.value = '';
    successState.classList.add('hidden');
    loadingState.classList.add('hidden');
    dropzoneContent.classList.remove('hidden');
}
