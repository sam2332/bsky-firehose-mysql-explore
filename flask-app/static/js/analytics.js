// Bluesky Analytics JavaScript with Socket.IO support

class BlueskyAnalytics {
    constructor() {
        this.charts = {};
        this.autoRefreshInterval = null;
        this.autoRefreshEnabled = false;
        this.socket = null;
        this.init();
    }

    init() {
        this.setupSocketIO();
        this.setupEventListeners();
        this.loadAllData();
    }

    setupSocketIO() {
        // Initialize Socket.IO connection
        this.socket = io();
        
        // Socket event handlers
        this.socket.on('connect', () => {
            console.log('Connected to analytics server');
            this.socket.emit('connect_analytics');
        });

        this.socket.on('disconnect', () => {
            console.log('Disconnected from analytics server');
        });

        this.socket.on('analytics_status', (data) => {
            console.log('Analytics status:', data.message);
        });

        this.socket.on('analytics_update', (data) => {
            console.log('Received real-time analytics update');
            this.updateAnalyticsData(data);
        });

        this.socket.on('analytics_error', (data) => {
            console.error('Analytics error:', data.message);
            this.showError(data.message);
        });
    }

    updateAnalyticsData(data) {
        // Update all analytics sections with real-time data
        if (data.political_sentiment) {
            this.updatePoliticalSentiment(data.political_sentiment);
        }
        if (data.trending_topics) {
            this.updateTrendingTopics(data.trending_topics);
        }
        if (data.user_behavior) {
            this.updateUserBehavior(data.user_behavior);
        }
        if (data.content_analysis) {
            this.updateContentAnalysis(data.content_analysis);
        }
        if (data.network_analysis) {
            this.updateNetworkAnalysis(data.network_analysis);
        }
        
        this.updateLastUpdated();
    }

    setupEventListeners() {
        // Trending period change
        document.getElementById('trendingPeriod').addEventListener('change', () => {
            this.loadTrendingTopics();
        });

        // Refresh controls
        document.getElementById('refreshAll').addEventListener('click', () => {
            this.loadAllData();
        });

        document.getElementById('autoRefreshToggle').addEventListener('click', () => {
            this.toggleAutoRefresh();
        });
    }

    async loadAllData() {
        this.updateLastUpdated();
        
        // Load all analytics data in parallel
        Promise.all([
            this.loadPoliticalSentiment(),
            this.loadTrendingTopics(),
            this.loadUserBehavior(),
            this.loadContentAnalysis(),
            this.loadNetworkAnalysis()
        ]).catch(error => {
            console.error('Error loading analytics data:', error);
            this.showError('Failed to load analytics data');
        });
    }

    async loadPoliticalSentiment() {
        try {
            const response = await fetch('/api/analytics/political-sentiment');
            const data = await response.json();
            this.updatePoliticalSentiment(data);
        } catch (error) {
            console.error('Error loading political sentiment:', error);
        }
    }

    async loadTrendingTopics() {
        try {
            const period = document.getElementById('trendingPeriod').value;
            const response = await fetch(`/api/analytics/trending-topics?period=${period}`);
            const data = await response.json();
            this.updateTrendingTopics(data);
        } catch (error) {
            console.error('Error loading trending topics:', error);
        }
    }

    async loadUserBehavior() {
        try {
            const response = await fetch('/api/analytics/user-behavior');
            const data = await response.json();
            this.updateUserBehavior(data);
        } catch (error) {
            console.error('Error loading user behavior:', error);
        }
    }

    async loadContentAnalysis() {
        try {
            const response = await fetch('/api/analytics/content-analysis');
            const data = await response.json();
            this.updateContentAnalysis(data);
        } catch (error) {
            console.error('Error loading content analysis:', error);
        }
    }

    async loadNetworkAnalysis() {
        try {
            const response = await fetch('/api/analytics/network-analysis');
            const data = await response.json();
            this.updateNetworkAnalysis(data);
        } catch (error) {
            console.error('Error loading network analysis:', error);
        }
    }

    updatePoliticalSentiment(data) {
        // Update political sentiment cards
        const container = document.getElementById('politicalSentiment');
        if (!container) return;
        
        container.innerHTML = `
            <div class="col-md-6">
                <div class="card bg-danger text-white mb-3">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-elephant me-2"></i>
                            Right-Wing Content
                        </h5>
                        <h2>${data.right_wing_count || 0}</h2>
                        <p class="card-text">Posts with conservative political content</p>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card bg-primary text-white mb-3">
                    <div class="card-body">
                        <h5 class="card-title">
                            <i class="fas fa-donkey me-2"></i>
                            Left-Wing Content
                        </h5>
                        <h2>${data.left_wing_count || 0}</h2>
                        <p class="card-text">Posts with progressive political content</p>
                    </div>
                </div>
            </div>
        `;

        // Update political timeline chart
        if (data.timeline_data && data.timeline_data.length > 0) {
            this.createPoliticalTimelineChart(data.timeline_data);
        }

        // Update trending political phrases
        if (data.political_phrases) {
            this.displayTrendingPoliticalPhrases(data.political_phrases);
        }
    }

    updateTrendingTopics(data) {
        // Update trending hashtags
        const hashtagsContainer = document.getElementById('trendingHashtags');
        if (hashtagsContainer && data.hashtags) {
            hashtagsContainer.innerHTML = data.hashtags.slice(0, 10).map(item => 
                `<div class="d-flex justify-content-between align-items-center mb-1">
                    <span class="badge bg-primary">${item.tag}</span>
                    <small>${item.count}</small>
                </div>`
            ).join('');
        }

        // Update trending words/keywords
        const keywordsContainer = document.getElementById('trendingKeywords');
        if (keywordsContainer && data.words) {
            keywordsContainer.innerHTML = data.words.slice(0, 10).map(item => 
                `<div class="d-flex justify-content-between align-items-center mb-1">
                    <span>${item.word}</span>
                    <small class="text-muted">${item.count}</small>
                </div>`
            ).join('');
        }

        // Update trending mentions (use words data as proxy)
        const mentionsContainer = document.getElementById('trendingMentions');
        if (mentionsContainer && data.words) {
            mentionsContainer.innerHTML = data.words.slice(0, 5).map(item => 
                `<div class="d-flex justify-content-between align-items-center mb-1">
                    <span>@${item.word}</span>
                    <small class="text-muted">${item.count}</small>
                </div>`
            ).join('');
        }
    }

    updateUserBehavior(data) {
        // Update top posters table
        if (data.top_posters) {
            this.displayTopPosters(data.top_posters);
        }

        // Update hourly activity chart
        if (data.hourly_activity) {
            this.createHourlyActivityChart(data.hourly_activity);
        }
    }

    updateContentAnalysis(data) {
        // Update sentiment chart
        if (data.sentiment_analysis) {
            this.createSentimentChart(data.sentiment_analysis);
        }

        // Update link analysis chart
        if (data.link_analysis) {
            this.createLinkAnalysisChart(data.link_analysis);
        }

        // Update language length analysis
        if (data.language_length) {
            this.displayLanguageLengthAnalysis(data.language_length);
        }
    }

    updateNetworkAnalysis(data) {
        // Update most mentioned users
        if (data.most_mentioned) {
            this.displayMostMentioned(data.most_mentioned);
        }

        // Update concurrent posters
        if (data.concurrent_activity) {
            this.displayConcurrentPosters(data.concurrent_activity);
        }
    }

    createPoliticalTimelineChart(timelineData) {
        const ctx = document.getElementById('politicalTimelineChart');
        if (!ctx) return;
        
        if (this.charts.politicalTimeline) {
            this.charts.politicalTimeline.destroy();
        }

        this.charts.politicalTimeline = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timelineData.map(d => {
                    const date = new Date(d.date);
                    const options = {
                        timeZone: 'America/Detroit',
                        month: 'short',
                        day: 'numeric',
                        hour: '2-digit',
                        hour12: true
                    };
                    return date.toLocaleString('en-US', options);
                }),
                datasets: [{
                    label: 'Political Posts',
                    data: timelineData.map(d => d.count),
                    borderColor: '#0d6efd',
                    backgroundColor: 'rgba(13, 110, 253, 0.1)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            title: function(context) {
                                const dataIndex = context[0].dataIndex;
                                const date = new Date(timelineData[dataIndex].date);
                                const options = {
                                    timeZone: 'America/Detroit',
                                    weekday: 'short',
                                    month: 'short',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    hour12: true
                                };
                                return date.toLocaleString('en-US', options) + ' ET';
                            }
                        }
                    }
                }
            }
        });
    }

    createHourlyActivityChart(hourlyData) {
        const ctx = document.getElementById('hourlyActivityChart');
        if (!ctx) return;
        
        if (this.charts.hourlyActivity) {
            this.charts.hourlyActivity.destroy();
        }

        // Fill in missing hours with 0
        const fullHourData = Array.from({length: 24}, (_, i) => {
            const found = hourlyData.find(d => d.hour === i);
            return found ? found.count : 0;
        });

        this.charts.hourlyActivity = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: Array.from({length: 24}, (_, i) => i + ':00'),
                datasets: [{
                    label: 'Posts',
                    data: fullHourData,
                    backgroundColor: 'rgba(13, 110, 253, 0.8)',
                    borderRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    },
                    x: {
                        ticks: {
                            maxTicksLimit: 12
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    }
                }
            }
        });
    }

    createLinkAnalysisChart(linkData) {
        const ctx = document.getElementById('linkAnalysisChart');
        if (!ctx) return;
        
        if (this.charts.linkAnalysis) {
            this.charts.linkAnalysis.destroy();
        }

        this.charts.linkAnalysis = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: linkData.map(d => d.type),
                datasets: [{
                    data: linkData.map(d => d.count),
                    backgroundColor: ['#0d6efd', '#6f42c1']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Posts with/without Links'
                    }
                }
            }
        });
    }

    createSentimentChart(sentimentData) {
        const ctx = document.getElementById('sentimentChart');
        if (!ctx) return;
        
        if (this.charts.sentiment) {
            this.charts.sentiment.destroy();
        }

        const colors = {
            'Positive': '#28a745',
            'Negative': '#dc3545', 
            'Neutral': '#6c757d'
        };

        this.charts.sentiment = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: sentimentData.map(d => d.sentiment),
                datasets: [{
                    data: sentimentData.map(d => d.count),
                    backgroundColor: sentimentData.map(d => colors[d.sentiment] || '#6c757d')
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: true,
                        text: 'Sentiment Analysis'
                    }
                }
            }
        });
    }

    displayTopPosters(topPosters) {
        const container = document.getElementById('topPostersTable');
        if (!container) return;
        
        if (!topPosters || topPosters.length === 0) {
            container.innerHTML = '<div class="text-center py-3"><p class="text-muted">No high-volume posters found</p></div>';
            return;
        }

        container.innerHTML = `
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>User</th>
                            <th>Posts</th>
                            <th>Posts/Hour</th>
                            <th>Active Period</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${topPosters.slice(0, 15).map(user => `
                            <tr>
                                <td>
                                    <strong>@${this.escapeHtml(user.handle)}</strong>
                                    <br><small class="text-muted">${this.truncate(user.did, 20)}</small>
                                </td>
                                <td><span class="badge bg-primary">${user.post_count}</span></td>
                                <td>${user.posts_per_hour}</td>
                                <td class="small">
                                    ${this.formatDateTime(user.first_post)} - 
                                    ${this.formatDateTime(user.last_post)}
                                </td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        `;
    }

    displayLanguageLengthAnalysis(languageData) {
        const container = document.getElementById('languageLengthAnalysis');
        if (!container) return;
        
        if (!languageData || languageData.length === 0) {
            container.innerHTML = '<p class="text-muted">No language data available</p>';
            return;
        }

        container.innerHTML = languageData.map(lang => `
            <div class="d-flex justify-content-between align-items-center mb-2">
                <div>
                    <strong>${lang.language}</strong>
                    <small class="text-muted">(${lang.count} posts)</small>
                </div>
                <span class="badge bg-secondary">${lang.avg_length} chars</span>
            </div>
        `).join('');
    }

    displayMostMentioned(mentionedUsers) {
        const container = document.getElementById('mostMentioned');
        if (!container) return;

        container.innerHTML = mentionedUsers.slice(0, 10).map(user => `
            <div class="d-flex justify-content-between align-items-center mb-1">
                <span>@${user.handle}</span>
                <small class="text-muted">${user.count} mentions</small>
            </div>
        `).join('');
    }

    displayConcurrentPosters(concurrentData) {
        const container = document.getElementById('concurrentPosters');
        if (!container) return;

        container.innerHTML = concurrentData.slice(0, 5).map(activity => {
            const date = new Date(activity.minute);
            const timeOptions = {
                timeZone: 'America/Detroit',
                hour: '2-digit',
                minute: '2-digit',
                hour12: true
            };
            const easternTime = date.toLocaleTimeString('en-US', timeOptions) + ' ET';
            
            return `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <span>${easternTime}</span>
                    <small class="text-muted">${activity.unique_authors} users, ${activity.total_posts} posts</small>
                </div>
            `;
        }).join('');
    }

    displayTrendingPoliticalPhrases(phrases) {
        const container = document.getElementById('trendingPoliticalPhrases');
        if (!container) return;

        const phraseCounts = {};
        phrases.forEach(phrase => {
            phraseCounts[phrase] = (phraseCounts[phrase] || 0) + 1;
        });

        const sortedPhrases = Object.entries(phraseCounts)
            .sort((a, b) => b[1] - a[1])
            .slice(0, 10);

        container.innerHTML = sortedPhrases.map(([phrase, count]) => `
            <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="badge bg-warning text-dark">${phrase}</span>
                <small>${count}</small>
            </div>
        `).join('');
    }

    toggleAutoRefresh() {
        const button = document.getElementById('autoRefreshToggle');
        
        if (this.autoRefreshEnabled) {
            // Stop auto refresh
            this.autoRefreshEnabled = false;
            if (this.autoRefreshInterval) {
                clearInterval(this.autoRefreshInterval);
                this.autoRefreshInterval = null;
            }
            if (this.socket) {
                this.socket.emit('stop_analytics_monitoring');
            }
            button.innerHTML = '<i class="fas fa-play me-1"></i>Auto Refresh (30s)';
            button.classList.remove('btn-success');
            button.classList.add('btn-outline-secondary');
        } else {
            // Start auto refresh
            this.autoRefreshEnabled = true;
            this.autoRefreshInterval = setInterval(() => {
                this.loadAllData();
            }, 30000);
            if (this.socket) {
                this.socket.emit('start_analytics_monitoring');
            }
            button.innerHTML = '<i class="fas fa-pause me-1"></i>Auto Refresh (ON)';
            button.classList.remove('btn-outline-secondary');
            button.classList.add('btn-success');
        }
    }

    updateLastUpdated() {
        const element = document.getElementById('lastUpdated');
        if (element) {
            const now = new Date();
            const options = {
                timeZone: 'America/Detroit',
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
                hour12: true
            };
            element.textContent = now.toLocaleTimeString('en-US', options) + ' ET';
        }
    }

    showError(message) {
        // Create a simple toast notification
        const toast = document.createElement('div');
        toast.className = 'toast align-items-center text-white bg-danger border-0 position-fixed top-0 end-0 m-3';
        toast.style.zIndex = '9999';
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <i class="fas fa-exclamation-triangle me-2"></i>
                    ${message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove toast after it's hidden
        toast.addEventListener('hidden.bs.toast', () => {
            document.body.removeChild(toast);
        });
    }

    formatNumber(num) {
        return new Intl.NumberFormat().format(num);
    }

    formatDateTime(dateString) {
        if (!dateString) return 'N/A';
        
        const date = new Date(dateString);
        
        // Format for Eastern timezone display
        const options = {
            timeZone: 'America/Detroit',
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit',
            hour12: true
        };
        
        return date.toLocaleString('en-US', options) + ' ET';
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    truncate(text, length) {
        return text.length > length ? text.substring(0, length) + '...' : text;
    }
}

// Initialize the analytics dashboard when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new BlueskyAnalytics();
});
