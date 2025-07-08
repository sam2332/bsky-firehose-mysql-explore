// Bluesky Analytics JavaScript

class BlueskyAnalytics {
    constructor() {
        this.charts = {};
        this.autoRefreshInterval = null;
        this.autoRefreshEnabled = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadAllData();
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
            const response = await fetch('/api/political-sentiment');
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            // Update stats cards
            document.getElementById('rightWingPosts').textContent = this.formatNumber(data.right_wing.posts);
            document.getElementById('rightWingUsers').textContent = this.formatNumber(data.right_wing.unique_authors);
            document.getElementById('leftWingPosts').textContent = this.formatNumber(data.left_wing.posts);
            document.getElementById('leftWingUsers').textContent = this.formatNumber(data.left_wing.unique_authors);

            // Create timeline chart
            this.createPoliticalTimelineChart(data.timeline);

            // Display trending political phrases
            this.displayTrendingPoliticalPhrases(data.trending_phrases || []);

        } catch (error) {
            console.error('Error loading political sentiment:', error);
            this.showError('Failed to load political sentiment data');
        }
    }

    async loadTrendingTopics() {
        try {
            const period = document.getElementById('trendingPeriod').value;
            const response = await fetch(`/api/trending-topics?period=${period}`);
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            this.displayTrendingList('trendingKeywords', data.trending_keywords, 'word');
            this.displayTrendingList('trendingHashtags', data.trending_hashtags, 'hashtag', '#');
            this.displayTrendingList('trendingMentions', data.trending_mentions, 'mention', '@');

        } catch (error) {
            console.error('Error loading trending topics:', error);
            this.showError('Failed to load trending topics');
        }
    }

    async loadUserBehavior() {
        try {
            const response = await fetch('/api/user-behavior');
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            this.displayTopPosters(data.top_posters);
            this.createHourlyActivityChart(data.hourly_activity);

        } catch (error) {
            console.error('Error loading user behavior:', error);
            this.showError('Failed to load user behavior data');
        }
    }

    async loadContentAnalysis() {
        try {
            const response = await fetch('/api/content-analysis');
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            this.createLinkAnalysisChart(data.link_analysis);
            this.createSentimentChart(data.sentiment_analysis);
            this.displayLanguageLengthAnalysis(data.length_by_language);

        } catch (error) {
            console.error('Error loading content analysis:', error);
            this.showError('Failed to load content analysis data');
        }
    }

    async loadNetworkAnalysis() {
        try {
            const response = await fetch('/api/network-analysis');
            const data = await response.json();

            if (data.error) {
                throw new Error(data.error);
            }

            this.displayMostMentioned(data.most_mentioned);
            this.displayConcurrentPosters(data.concurrent_posters);

        } catch (error) {
            console.error('Error loading network analysis:', error);
            this.showError('Failed to load network analysis data');
        }
    }

    createPoliticalTimelineChart(timelineData) {
        const ctx = document.getElementById('politicalTimelineChart').getContext('2d');
        
        if (this.charts.politicalTimeline) {
            this.charts.politicalTimeline.destroy();
        }

        this.charts.politicalTimeline = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timelineData.map(d => new Date(d.date).toLocaleDateString()),
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
                    }
                }
            }
        });
    }

    createHourlyActivityChart(hourlyData) {
        const ctx = document.getElementById('hourlyActivityChart').getContext('2d');
        
        if (this.charts.hourlyActivity) {
            this.charts.hourlyActivity.destroy();
        }

        // Fill in missing hours with 0
        const fullHourData = Array.from({length: 24}, (_, i) => {
            const hourData = hourlyData.find(d => d.hour === i);
            return hourData ? hourData.count : 0;
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
        const ctx = document.getElementById('linkAnalysisChart').getContext('2d');
        
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
        const ctx = document.getElementById('sentimentChart').getContext('2d');
        
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

    displayTrendingList(containerId, items, keyName, prefix = '') {
        const container = document.getElementById(containerId);
        
        if (!items || items.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No trending items found</p>';
            return;
        }

        const maxCount = Math.max(...items.map(item => item.count));
        
        container.innerHTML = items.slice(0, 10).map((item, index) => {
            const percentage = (item.count / maxCount) * 100;
            return `
                <div class="trending-item mb-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="fw-medium">${prefix}${this.escapeHtml(item[keyName])}</span>
                        <span class="badge bg-primary">${item.count}</span>
                    </div>
                    <div class="progress mt-1" style="height: 4px;">
                        <div class="progress-bar" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;
        }).join('');
    }

    displayTopPosters(topPosters) {
        const container = document.getElementById('topPostersTable');
        
        if (!topPosters || topPosters.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No high-volume posters found</p>';
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
        
        if (!languageData || languageData.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No language data available</p>';
            return;
        }

        const maxLength = Math.max(...languageData.map(lang => lang.avg_length));
        
        container.innerHTML = languageData.slice(0, 8).map(lang => {
            const percentage = (lang.avg_length / maxLength) * 100;
            return `
                <div class="mb-2">
                    <div class="d-flex justify-content-between">
                        <span>${lang.language.toUpperCase()}</span>
                        <span class="small">${Math.round(lang.avg_length)} chars (${lang.posts} posts)</span>
                    </div>
                    <div class="progress" style="height: 6px;">
                        <div class="progress-bar bg-info" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;
        }).join('');
    }

    displayMostMentioned(mentionedUsers) {
        const container = document.getElementById('mostMentioned');
        
        if (!mentionedUsers || mentionedUsers.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No mention data available</p>';
            return;
        }

        container.innerHTML = mentionedUsers.slice(0, 8).map(user => `
            <div class="d-flex justify-content-between align-items-center mb-1">
                <span class="small">@${this.escapeHtml(user.user)}</span>
                <span class="badge bg-secondary badge-sm">${user.mentions}</span>
            </div>
        `).join('');
    }

    displayConcurrentPosters(concurrentData) {
        const container = document.getElementById('concurrentPosters');
        
        if (!concurrentData || concurrentData.length === 0) {
            container.innerHTML = '<p class="text-muted text-center">No concurrent posting patterns found</p>';
            return;
        }

        container.innerHTML = concurrentData.slice(0, 8).map(pair => `
            <div class="small mb-1">
                <strong>@${this.escapeHtml(pair.user1)}</strong> & 
                <strong>@${this.escapeHtml(pair.user2)}</strong>
                <span class="badge bg-warning text-dark ms-1">${pair.count}</span>
            </div>
        `).join('');
    }

    displayTrendingPoliticalPhrases(phrases) {
        const container = document.getElementById('trendingPoliticalPhrases');
        
        if (!phrases || phrases.length === 0) {
            container.innerHTML = '<p class="text-muted text-center small">No political phrases trending in last 24h</p>';
            return;
        }

        const maxCount = Math.max(...phrases.map(phrase => phrase.count));
        
        container.innerHTML = phrases.slice(0, 8).map((phrase, index) => {
            const percentage = (phrase.count / maxCount) * 100;
            return `
                <div class="trending-phrase-item mb-2">
                    <div class="d-flex justify-content-between align-items-center">
                        <span class="small fw-medium">"${this.escapeHtml(phrase.phrase)}"</span>
                        <span class="badge bg-secondary badge-sm">${phrase.count}</span>
                    </div>
                    <div class="progress mt-1" style="height: 3px;">
                        <div class="progress-bar bg-warning" style="width: ${percentage}%"></div>
                    </div>
                </div>
            `;
        }).join('');
    }

    toggleAutoRefresh() {
        const button = document.getElementById('autoRefreshToggle');
        
        if (this.autoRefreshEnabled) {
            clearInterval(this.autoRefreshInterval);
            this.autoRefreshEnabled = false;
            button.innerHTML = '<i class="fas fa-play me-1"></i>Auto Refresh (30s)';
            button.className = 'btn btn-outline-secondary';
        } else {
            this.autoRefreshInterval = setInterval(() => {
                this.loadAllData();
            }, 30000);
            this.autoRefreshEnabled = true;
            button.innerHTML = '<i class="fas fa-pause me-1"></i>Auto Refresh (ON)';
            button.className = 'btn btn-success';
        }
    }

    updateLastUpdated() {
        document.getElementById('lastUpdated').textContent = new Date().toLocaleTimeString();
    }

    showError(message) {
        // Create a toast notification for errors
        const toast = document.createElement('div');
        toast.className = 'toast position-fixed top-0 end-0 m-3';
        toast.innerHTML = `
            <div class="toast-header bg-danger text-white">
                <i class="fas fa-exclamation-triangle me-2"></i>
                <strong class="me-auto">Error</strong>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
        
        // Remove after hiding
        toast.addEventListener('hidden.bs.toast', () => {
            toast.remove();
        });
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }

    formatDateTime(dateString) {
        if (!dateString) return 'Unknown';
        return new Date(dateString).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    truncate(text, length) {
        if (!text) return '';
        return text.length > length ? text.substring(0, length) + '...' : text;
    }
}

// Initialize the analytics dashboard when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new BlueskyAnalytics();
});
