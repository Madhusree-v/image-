document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('upload-form');
    const resultDiv = document.getElementById('result');

    form.addEventListener('submit', function(event) {
        event.preventDefault();

        const formData = new FormData(form);
        const fileInput = document.getElementById('file-input');
        const formatSelect = document.getElementById('format-select');

        if (fileInput.files.length === 0) {
            resultDiv.innerHTML = '<p style="color: red;">Please select a file.</p>';
            return;
        }

        // Clear previous results
        resultDiv.innerHTML = '';

        // Show loading message
        resultDiv.innerHTML = '<p>Processing your image, please wait...</p>';

        fetch('/upload', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(data => {
                    throw new Error(data.error || 'An error occurred');
                });
            }
            return response.json();
        })
        .then(data => {
            const format = formatSelect.value;

            let output;
            if (format === 'text') {
                output = `<h3>Extracted Text:</h3><pre>${data.text}</pre>`;
            } else if (format === 'json') {
                output = `<h3>JSON Output:</h3><pre>${data.json}</pre>`;
            } else if (format === 'csv') {
                output = `<h3>CSV Output:</h3><pre>${data.csv}</pre>`;
            }

            resultDiv.innerHTML = output;
        })
        .catch(error => {
            resultDiv.innerHTML = `<p style="color: red;">An error occurred: ${error.message}</p>`;
        });
    });
});