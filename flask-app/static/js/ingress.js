// Real-time data ingress monitoring with Socket.IO
class IngressMonitor {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.isMonitoring = false;
        
        // Chart data storage
        this.realtimeData = {
            labels: [],
            datasets: [{
                label: 'Posts/Min',
                data: [],
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.2)',
                tension: 0.1
            }, {
                label: 'Errors/Min',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.2)',
                tension: 0.1
            }]
        };
        
        this.languageData = {
            labels: [],
            datasets: [{
                data: [],
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0',
                    '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                ]
            }]
        };
        
        this.initializeCharts();
        this.initializeSocket();
        this.bindEvents();
    }
    
    initializeSocket() {
        // Initialize Socket.IO connection
        this.socket = io();
        
        // Connection event handlers
        this.socket.on('connect', () => {
            console.log('Connected to server');
            this.isConnected = true;
            this.updateConnectionStatus('Connected', 'success');
            this.startMonitoring();
        });
        
        this.socket.on('disconnect', () => {
            console.log('Disconnected from server');
            this.isConnected = false;
            this.isMonitoring = false;
            this.updateConnectionStatus('Disconnected', 'danger');
        });
        
        this.socket.on('connect_error', (error) => {
            console.error('Connection error:', error);
            this.updateConnectionStatus('Connection Error', 'danger');
        });
        
        // Data event handlers
        this.socket.on('ingress_update', (data) => {
            this.handleRealtimeUpdate(data);
        });
        
        this.socket.on('monitoring_started', (data) => {
            console.log('Monitoring started:', data);
            this.isMonitoring = true;
            this.updateMonitoringStatus(true);
        });
        
        this.socket.on('monitoring_stopped', (data) => {
            console.log('Monitoring stopped:', data);
            this.isMonitoring = false;
            this.updateMonitoringStatus(false);
        });
        
        this.socket.on('error', (error) => {
            console.error('Server error:', error);
            this.showError('Server Error: ' + error.message);
        });
    }
    
    startMonitoring() {
        if (this.isConnected && !this.isMonitoring) {
            this.socket.emit('start_monitoring');
        }
    }
    
    stopMonitoring() {
        if (this.isConnected && this.isMonitoring) {
            this.socket.emit('stop_monitoring');
        }
    }
    
    updateConnectionStatus(status, type) {
        const statusElement = document.getElementById('connectionStatus');
        if (statusElement) {
            statusElement.className = `badge bg-${type}`;
            statusElement.textContent = status;
        }
    }
    
    updateMonitoringStatus(isActive) {
        const statusElement = document.getElementById('monitoringStatus');
        if (statusElement) {
            statusElement.className = `badge bg-${isActive ? 'success' : 'secondary'}`;
            statusElement.textContent = isActive ? 'Monitoring Active' : 'Monitoring Stopped';
        }
    }
    
    handleRealtimeUpdate(data) {
        // Update all metrics and charts with real-time data
        this.updateMetrics(data);
        this.updateLanguageChart(data);
        this.updateActiveAuthors(data);
        this.updateRecentPosts(data);
        this.updateRealtimeChart(data);
    }
    
    initializeCharts() {
        // Real-time ingress chart
        const ctx1 = document.getElementById('realtimeChart').getContext('2d');
        this.realtimeChart = new Chart(ctx1, {
            type: 'line',
            data: this.realtimeData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                animation: {
                    duration: 0 // Disable animations for real-time updates
                },
                scales: {
                    x: {
                        type: 'linear',
                        position: 'bottom',
                        title: {
                            display: true,
                            text: 'Time'
                        }
                    },
                    y: {
                        beginAtZero: true,
                        title: {
                            display: true,
                            text: 'Rate (per minute)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    }
                }
            }
        });
        
        // Language distribution chart
        const ctx2 = document.getElementById('languageChart').getContext('2d');
        this.languageChart = new Chart(ctx2, {
            type: 'doughnut',
            data: this.languageData,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            boxWidth: 12,
                            font: {
                                size: 11
                            }
                        }
                    }
                }
            }
        });
    }
    
    bindEvents() {
        // Manual refresh button
        document.getElementById('manualRefresh')?.addEventListener('click', () => {
            this.manualRefresh();
        });
        
        // Start/Stop monitoring buttons
        document.getElementById('startMonitoring')?.addEventListener('click', () => {
            this.startMonitoring();
        });
        
        document.getElementById('stopMonitoring')?.addEventListener('click', () => {
            this.stopMonitoring();
        });
        
        // Pause chart updates
        document.getElementById('pauseChart')?.addEventListener('click', (e) => {
            this.isPaused = !this.isPaused;
            const btn = e.target.closest('button');
            if (this.isPaused) {
                btn.innerHTML = '<i class="fas fa-play me-1"></i>Resume';
                btn.classList.replace('btn-outline-primary', 'btn-outline-success');
            } else {
                btn.innerHTML = '<i class="fas fa-pause me-1"></i>Pause';
                btn.classList.replace('btn-outline-success', 'btn-outline-primary');
            }
        });
        
        // Pause stream button
        document.getElementById('pauseStream')?.addEventListener('click', () => {
            this.toggleStreamPause();
        });
    }
    
    manualRefresh() {
        if (this.isConnected) {
            // Request fresh data from server
            this.socket.emit('request_update');
        }
    }
    
    toggleStreamPause() {
        this.streamPaused = !this.streamPaused;
        const button = document.getElementById('pauseStream');
        if (button) {
            button.textContent = this.streamPaused ? 'Resume Stream' : 'Pause Stream';
            button.className = this.streamPaused ? 'btn btn-success btn-sm' : 'btn btn-warning btn-sm';
        }
    }
    
    showError(message) {
        console.error(message);
        // You could show a toast or alert here
    }
    
    updateRealtimeChart(data) {
        if (this.isPaused) return;
        
        const now = new Date().toLocaleTimeString();
        this.realtimeData.labels.push(now);
        this.realtimeData.datasets[0].data.push(data.posts_per_minute || 0);
        this.realtimeData.datasets[1].data.push(data.errors_per_minute || 0);
        
        // Keep only last 20 data points
        if (this.realtimeData.labels.length > 20) {
            this.realtimeData.labels.shift();
            this.realtimeData.datasets[0].data.shift();
            this.realtimeData.datasets[1].data.shift();
        }
        
        this.realtimeChart.update('none');
    }
    
    updateMetrics(data) {
        // Update metric cards
        document.getElementById('postsPerMinute').textContent = data.posts_per_minute || 0;
        document.getElementById('totalToday').textContent = this.formatNumber(data.total_today || 0);
        document.getElementById('lastHour').textContent = this.formatNumber(data.last_hour || 0);
        document.getElementById('errorsPerMinute').textContent = data.errors_per_minute || 0;
        
        // Update trends
        this.updateTrend('postsPerMinuteTrend', data.posts_per_minute_change);
        this.updateTrend('totalTodayChange', data.total_today_change);
        this.updateTrend('lastHourTrend', data.last_hour_change);
        this.updateTrend('errorsPerMinuteTrend', data.errors_per_minute_change);
        
        // Update database metrics
        document.getElementById('dbWriteRate').textContent = data.db_write_rate || 0;
        document.getElementById('dbQueueSize').textContent = data.db_queue_size || 0;
        
        // Update database usage
        const dbUsage = data.db_usage_percent || 0;
        document.getElementById('dbUsageBar').style.width = `${dbUsage}%`;
        document.getElementById('dbUsageText').textContent = `${dbUsage}% Used`;
        
        // Update status message
        document.getElementById('ingressStatus').textContent = 
            `Collecting ${data.posts_per_minute || 0} posts/min from Bluesky firehose`;
    }
    
    updateTrend(elementId, change) {
        const element = document.getElementById(elementId);
        if (change === undefined || change === null) {
            element.textContent = '-';
            return;
        }
        
        const icon = change >= 0 ? '↗' : '↘';
        const color = change >= 0 ? 'text-success' : 'text-danger';
        element.className = `opacity-75 ${color}`;
        element.textContent = `${icon} ${Math.abs(change).toFixed(1)}%`;
    }
    
    updateLanguageChart(data) {
        if (!data.languages || data.languages.length === 0) return;
        
        this.languageData.labels = data.languages.map(l => l.language || 'Unknown');
        this.languageData.datasets[0].data = data.languages.map(l => l.count);
        
        this.languageChart.update('none'); // No animation for real-time updates
    }
    
    updateActiveAuthors(data) {
        document.getElementById('newAuthorsToday').textContent = data.new_authors_today || 0;
        document.getElementById('activeAuthorsNow').textContent = data.active_authors_now || 0;
        
        const authorsList = document.getElementById('activeAuthorsList');
        if (data.top_active && data.top_active.length > 0) {
            authorsList.innerHTML = data.top_active.map(author => `
                <div class="d-flex justify-content-between align-items-center mb-2">
                    <div>
                        <strong>@${author.handle}</strong>
                        <br>
                        <small class="text-muted">${author.display_name || 'No display name'}</small>
                    </div>
                    <span class="badge bg-primary">${author.post_count} posts</span>
                </div>
            `).join('');
        } else {
            authorsList.innerHTML = '<p class="text-muted">No active authors in the last 10 minutes</p>';
        }
    }
    
    updateRecentPosts(data) {
        if (this.streamPaused || !data.posts || data.posts.length === 0) return;
        
        const streamContainer = document.getElementById('livePostStream');
        
        data.posts.forEach(post => {
            const postElement = this.createPostElement(post);
            
            // Add to top of stream
            if (streamContainer.children.length === 0 || 
                streamContainer.children[0].classList.contains('text-center')) {
                streamContainer.innerHTML = '';
            }
            
            streamContainer.insertBefore(postElement, streamContainer.firstChild);
            
            // Keep only last 20 posts
            while (streamContainer.children.length > 20) {
                streamContainer.removeChild(streamContainer.lastChild);
            }
        });
    }
    
    createPostElement(post) {
        const div = document.createElement('div');
        div.className = 'border-bottom pb-2 mb-2 fade-in';
        
        const timeAgo = this.getTimeAgo(new Date(post.created_at));
        const shortText = post.text.length > 100 ? 
            post.text.substring(0, 100) + '...' : post.text;
        
        div.innerHTML = `
            <div class="d-flex justify-content-between align-items-start">
                <div class="flex-grow-1">
                    <div class="d-flex align-items-center mb-1">
                        <strong class="text-primary">@${post.author_handle}</strong>
                        <span class="badge bg-secondary ms-2">${post.language || 'unknown'}</span>
                        <small class="text-muted ms-2">${timeAgo}</small>
                    </div>
                    <p class="mb-0 text-break">${this.escapeHtml(shortText)}</p>
                </div>
                <div class="ms-2">
                    <i class="fas fa-circle text-success" style="font-size: 8px;"></i>
                </div>
            </div>
        `;
        
        return div;
    }
    
    updateRealtimeChart(data) {
        if (this.isPaused) return;
        
        const now = new Date();
        const timeLabel = now.getTime();
        
        // Add new data point
        this.realtimeData.labels.push(timeLabel);
        this.realtimeData.datasets[0].data.push(data.posts_per_minute || 0);
        
        // Keep only last 20 data points (for performance)
        if (this.realtimeData.labels.length > 20) {
            this.realtimeData.labels.shift();
            this.realtimeData.datasets[0].data.shift();
        }
        
        // Update x-axis to show time labels
        this.realtimeChart.options.scales.x.ticks = {
            callback: function(value, index, values) {
                const date = new Date(value);
                return date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
            }
        };
        
        this.realtimeChart.update('none');
    }
    
    updateConnectionStatus(status, message) {
        const statusElement = document.getElementById('connectionStatus');
        const bannerElement = document.getElementById('statusBanner');
        
        // Remove existing status classes
        statusElement.className = 'badge';
        bannerElement.className = 'alert d-flex justify-content-between align-items-center';
        
        switch (status) {
            case 'connected':
                statusElement.classList.add('bg-success');
                bannerElement.classList.add('alert-success');
                statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Connected';
                break;
            case 'connecting':
                statusElement.classList.add('bg-warning');
                bannerElement.classList.add('alert-warning');
                statusElement.innerHTML = '<i class="fas fa-circle me-1"></i>Connecting';
                break;
            case 'paused':
                statusElement.classList.add('bg-secondary');
                bannerElement.classList.add('alert-secondary');
                statusElement.innerHTML = '<i class="fas fa-pause me-1"></i>Paused';
                break;
            case 'error':
                statusElement.classList.add('bg-danger');
                bannerElement.classList.add('alert-danger');
                statusElement.innerHTML = '<i class="fas fa-exclamation-triangle me-1"></i>Error';
                break;
        }
    }
    
    updateLastUpdated() {
        const now = new Date();
        document.getElementById('lastUpdated').textContent = 
            now.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit', second:'2-digit'});
    }
    
    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
    
    getTimeAgo(date) {
        const now = new Date();
        const diffInSeconds = Math.floor((now - date) / 1000);
        
        if (diffInSeconds < 60) {
            return `${diffInSeconds}s ago`;
        } else if (diffInSeconds < 3600) {
            const minutes = Math.floor(diffInSeconds / 60);
            return `${minutes}m ago`;
        } else {
            const hours = Math.floor(diffInSeconds / 3600);
            return `${hours}h ago`;
        }
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

// CSS for fade-in animation
const style = document.createElement('style');
style.textContent = `
    .fade-in {
        animation: fadeIn 0.5s ease-in;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .trending-list {
        max-height: 300px;
        overflow-y: auto;
    }
`;
document.head.appendChild(style);

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.ingressMonitor = new IngressMonitor();
});
