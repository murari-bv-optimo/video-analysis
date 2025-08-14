class RoomAnalyzer {
    constructor() {
        this.selectedFiles = [];
        this.currentHouseId = null;
        this.pollInterval = null;
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // File input handling
        const fileInput = document.getElementById('file-input');
        const uploadArea = document.getElementById('upload-area');
        const analyzeBtn = document.getElementById('analyze-btn');
        
        fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        
        // Drag and drop handling
        uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        
        // Analyze button
        analyzeBtn.addEventListener('click', () => this.startAnalysis());
        
        // Download button
        document.getElementById('download-btn').addEventListener('click', () => this.downloadReport());
        
        // New analysis button
        document.getElementById('new-analysis-btn').addEventListener('click', () => this.resetForNewAnalysis());
        
        // JSON toggle
        document.querySelector('.toggle-json').addEventListener('click', () => this.toggleJsonViewer());
    }

    handleFileSelect(event) {
        const files = Array.from(event.target.files);
        this.processSelectedFiles(files);
    }

    handleDragOver(event) {
        event.preventDefault();
        event.currentTarget.classList.add('dragover');
    }

    handleDragLeave(event) {
        event.currentTarget.classList.remove('dragover');
    }

    handleDrop(event) {
        event.preventDefault();
        event.currentTarget.classList.remove('dragover');
        
        const files = Array.from(event.dataTransfer.files);
        this.processSelectedFiles(files);
    }

    processSelectedFiles(files) {
        // Filter for image files
        const imageFiles = files.filter(file => file.type.startsWith('image/'));

        if (imageFiles.length === 0) {
            this.showMessage('Please select valid image files.', 'error');
            return;
        }

        // Accumulate selections across multiple interactions and de-duplicate
        const combined = [...(this.selectedFiles || []), ...imageFiles];
        const seen = new Set();
        this.selectedFiles = combined.filter(file => {
            const key = `${file.name}:${file.size}:${file.lastModified}`;
            if (seen.has(key)) return false;
            seen.add(key);
            return true;
        });

        this.displayFilePreview();
        
        // Enable analyze button only if we have files
        document.getElementById('analyze-btn').disabled = this.selectedFiles.length === 0;
    }

    displayFilePreview() {
        const previewContainer = document.getElementById('file-preview');
        previewContainer.innerHTML = '';

        this.selectedFiles.forEach((file, index) => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            
            const img = document.createElement('img');
            img.src = URL.createObjectURL(file);
            img.alt = file.name;
            
            const fileName = document.createElement('div');
            fileName.className = 'file-name';
            fileName.textContent = file.name;
            
            const fileSize = document.createElement('div');
            fileSize.className = 'file-size';
            fileSize.textContent = this.formatFileSize(file.size);
            
            fileItem.appendChild(img);
            fileItem.appendChild(fileName);
            fileItem.appendChild(fileSize);
            
            previewContainer.appendChild(fileItem);
        });
    }

    formatFileSize(bytes) {
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        if (bytes === 0) return '0 Bytes';
        const i = parseInt(Math.floor(Math.log(bytes) / Math.log(1024)));
        return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
    }

    async startAnalysis() {
        if (this.selectedFiles.length === 0) {
            this.showMessage('Please select images first.', 'error');
            return;
        }

        // Show progress section
        this.showSection('progress-section');
        this.hideSection('upload-section');
        
        try {
            // Upload files
            const formData = new FormData();
            this.selectedFiles.forEach(file => {
                formData.append('files', file);
            });

            this.updateProgress(10, 'Uploading images...');
            
            const uploadResponse = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!uploadResponse.ok) {
                throw new Error('Upload failed');
            }

            const uploadResult = await uploadResponse.json();
            this.currentHouseId = uploadResult.house_id;
            
            this.updateProgress(20, 'Images uploaded. Starting analysis...');
            
            // Start polling for progress
            this.startProgressPolling();
            
        } catch (error) {
            console.error('Analysis failed:', error);
            this.showMessage('Analysis failed. Please try again.', 'error');
            this.showSection('upload-section');
            this.hideSection('progress-section');
        }
    }

    startProgressPolling() {
        this.pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${this.currentHouseId}`);
                const status = await response.json();
                
                if (status.status === 'processing') {
                    const progress = Math.min(90, 20 + (status.progress || 0) * 0.7);
                    this.updateProgress(progress, 'Analyzing rooms with AI...');
                    
                } else if (status.status === 'completed') {
                    this.updateProgress(100, 'Analysis complete!');
                    clearInterval(this.pollInterval);
                    
                    setTimeout(() => {
                        this.loadResults();
                    }, 1000);
                    
                } else if (status.status === 'failed') {
                    clearInterval(this.pollInterval);
                    this.showMessage(`Analysis failed: ${status.error}`, 'error');
                    this.showSection('upload-section');
                    this.hideSection('progress-section');
                }
                
            } catch (error) {
                console.error('Error polling status:', error);
            }
        }, 2000);
    }

    async loadResults() {
        try {
            const response = await fetch(`/api/result/${this.currentHouseId}`);
            const result = await response.json();
            
            this.displayResults(result);
            this.hideSection('progress-section');
            this.showSection('results-section');
            
        } catch (error) {
            console.error('Error loading results:', error);
            this.showMessage('Error loading results.', 'error');
        }
    }

    displayResults(result) {
        // Display house summary
        this.displayHouseSummary(result.report.house_summary);
        
        // Display room details
        this.displayRoomDetails(result.report.rooms);
        
        // Display JSON
        this.displayJsonReport(result.report);
    }

    displayHouseSummary(summary) {
        const summaryContainer = document.getElementById('house-summary');
        summaryContainer.innerHTML = '';
        
        const summaryItems = [
            { label: 'Total Rooms', value: summary.total_rooms },
            { label: 'Rooms with Balcony', value: summary.rooms_with_balcony },
            { label: 'Total Windows', value: summary.total_windows },
            { label: 'Total Doors', value: summary.total_doors },
            { label: 'Total Furnishings', value: summary.total_furnishings }
        ];
        
        summaryItems.forEach(item => {
            const summaryItem = document.createElement('div');
            summaryItem.className = 'summary-item';
            summaryItem.innerHTML = `
                <div class="number">${item.value}</div>
                <div class="label">${item.label}</div>
            `;
            summaryContainer.appendChild(summaryItem);
        });
    }

    displayRoomDetails(rooms) {
        const roomsList = document.getElementById('rooms-list');
        roomsList.innerHTML = '';
        
        rooms.forEach(room => {
            const roomCard = document.createElement('div');
            roomCard.className = 'room-card';
            
            roomCard.innerHTML = `
                <div class="room-header">
                    <div class="room-type">${this.formatRoomType(room.room_type)}</div>
                    <div class="room-area">${room.estimated_area_sqm} m²</div>
                </div>
                <div class="room-details">
                    <div class="detail-item">
                        <div class="value">${room.object_counts.chair}</div>
                        <div class="label">Chairs</div>
                    </div>
                    <div class="detail-item">
                        <div class="value">${room.object_counts.table}</div>
                        <div class="label">Tables</div>
                    </div>
                    <div class="detail-item">
                        <div class="value">${room.object_counts.light}</div>
                        <div class="label">Lights</div>
                    </div>
                    <div class="detail-item">
                        <div class="value">${room.object_counts.fan}</div>
                        <div class="label">Fans</div>
                    </div>
                    <div class="detail-item">
                        <div class="value">${room.features.doors_and_windows.window_count}</div>
                        <div class="label">Windows</div>
                    </div>
                    <div class="detail-item">
                        <div class="value">${room.features.flooring.material}</div>
                        <div class="label">Flooring</div>
                    </div>
                </div>
            `;
            
            roomsList.appendChild(roomCard);
        });
    }

    displayJsonReport(report) {
        const jsonContent = document.getElementById('json-content');
        jsonContent.textContent = JSON.stringify(report, null, 2);
    }

    formatRoomType(roomType) {
        return roomType.split('_').map(word => 
            word.charAt(0).toUpperCase() + word.slice(1)
        ).join(' ');
    }

    toggleJsonViewer() {
        const jsonContent = document.getElementById('json-content');
        jsonContent.style.display = jsonContent.style.display === 'none' ? 'block' : 'none';
    }

    async downloadReport() {
        if (!this.currentHouseId) return;
        
        try {
            const response = await fetch(`/api/download/${this.currentHouseId}`);
            const blob = await response.blob();
            
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `house_analysis_${this.currentHouseId.substring(0, 8)}.json`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
        } catch (error) {
            console.error('Download failed:', error);
            this.showMessage('Download failed.', 'error');
        }
    }

    resetForNewAnalysis() {
        this.selectedFiles = [];
        this.currentHouseId = null;
        
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }
        
        // Reset file input
        document.getElementById('file-input').value = '';
        document.getElementById('file-preview').innerHTML = '';
        document.getElementById('analyze-btn').disabled = true;
        
        // Show upload section, hide others
        this.showSection('upload-section');
        this.hideSection('progress-section');
        this.hideSection('results-section');
        
        // Reset progress
        this.updateProgress(0, '');
    }

    updateProgress(percentage, message) {
        document.getElementById('progress-fill').style.width = `${percentage}%`;
        document.getElementById('progress-text').textContent = message;
    }

    showSection(sectionId) {
        const section = document.getElementById(sectionId);
        section.style.display = 'block';
        section.classList.add('fade-in');
    }

    hideSection(sectionId) {
        const section = document.getElementById(sectionId);
        section.style.display = 'none';
        section.classList.remove('fade-in');
    }

    showMessage(message, type = 'info') {
        // Create and show toast message
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        
        // Style the toast
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? '#e53e3e' : '#38a169'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            z-index: 1000;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            document.body.removeChild(toast);
        }, 5000);
    }
}

// Initialize the application
document.addEventListener('DOMContentLoaded', () => {
    new RoomAnalyzer();
});
