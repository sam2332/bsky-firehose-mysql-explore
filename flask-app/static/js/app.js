// Bluesky Posts Explorer JavaScript

class BlueskyExplorer {
    constructor() {
        this.currentPage = 1;
        this.currentQuery = {};
        this.init();
    }

    init() {
        this.loadStats();
        this.loadLanguages();
        this.setupEventListeners();
        this.loadPosts(); // Load initial posts
    }

    setupEventListeners() {
        // Search form submission
        document.getElementById('searchForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.currentPage = 1;
            this.loadPosts();
        });

        // Clear filters
        document.getElementById('clearFilters').addEventListener('click', () => {
            this.clearFilters();
        });

        // Author autocomplete
        let authorTimeout;
        document.getElementById('authorFilter').addEventListener('input', (e) => {
            clearTimeout(authorTimeout);
            authorTimeout = setTimeout(() => {
                this.searchAuthors(e.target.value);
            }, 300);
        });

        // Real-time search (debounced)
        let searchTimeout;
        document.getElementById('searchQuery').addEventListener('input', (e) => {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                if (e.target.value.length === 0 || e.target.value.length >= 3) {
                    this.currentPage = 1;
                    this.loadPosts();
                }
            }, 500);
        });

        // Filter changes
        ['languageFilter', 'dateFrom', 'dateTo', 'sortBy', 'sortOrder'].forEach(id => {
            document.getElementById(id).addEventListener('change', () => {
                this.currentPage = 1;
                this.loadPosts();
            });
        });
    }

    async loadStats() {
        try {
            const response = await fetch('/api/stats');
            const data = await response.json();

            if (data.error) {
                this.showError('Failed to load statistics: ' + data.error);
                return;
            }

            // Update stat cards
            document.getElementById('totalPosts').textContent = this.formatNumber(data.total_posts);
            document.getElementById('uniqueAuthors').textContent = this.formatNumber(data.unique_authors);
            document.getElementById('postsToday').textContent = this.formatNumber(data.posts_today);
            document.getElementById('postsWeek').textContent = this.formatNumber(data.posts_week);

        } catch (error) {
            console.error('Error loading stats:', error);
            this.showError('Failed to load statistics');
        }
    }

    async loadLanguages() {
        try {
            const response = await fetch('/api/languages');
            const data = await response.json();

            if (data.error) {
                console.error('Failed to load languages:', data.error);
                return;
            }

            const select = document.getElementById('languageFilter');
            select.innerHTML = '<option value="">All Languages</option>';

            data.languages.forEach(lang => {
                const option = document.createElement('option');
                option.value = lang.code;
                option.textContent = `${lang.name} (${this.formatNumber(lang.count)})`;
                select.appendChild(option);
            });

        } catch (error) {
            console.error('Error loading languages:', error);
        }
    }

    async searchAuthors(query) {
        if (query.length < 2) return;

        try {
            const response = await fetch(`/api/authors?q=${encodeURIComponent(query)}`);
            const data = await response.json();

            // Simple autocomplete - could be enhanced with a proper dropdown
            if (data.authors && data.authors.length > 0) {
                // For now, just store the results
                // In a full implementation, you'd show a dropdown with suggestions
                console.log('Author suggestions:', data.authors);
            }

        } catch (error) {
            console.error('Error searching authors:', error);
        }
    }

    async loadPosts() {
        this.showLoading(true);
        this.hideError();

        try {
            const params = this.buildQueryParams();
            const response = await fetch(`/api/posts?${params}`);
            const data = await response.json();

            if (data.error) {
                this.showError('Failed to load posts: ' + data.error);
                return;
            }

            this.currentQuery = data.query_info;
            this.displayPosts(data.posts);
            this.displayPagination(data.pagination);
            this.updateResultsInfo(data.pagination);

        } catch (error) {
            console.error('Error loading posts:', error);
            this.showError('Failed to load posts. Please try again.');
        } finally {
            this.showLoading(false);
        }
    }

    buildQueryParams() {
        const params = new URLSearchParams();
        
        const searchQuery = document.getElementById('searchQuery').value.trim();
        if (searchQuery) params.append('q', searchQuery);

        const language = document.getElementById('languageFilter').value;
        if (language) params.append('language', language);

        const author = document.getElementById('authorFilter').value.trim();
        if (author) params.append('author', author);

        const dateFrom = document.getElementById('dateFrom').value;
        if (dateFrom) params.append('date_from', dateFrom);

        const dateTo = document.getElementById('dateTo').value;
        if (dateTo) params.append('date_to', dateTo);

        const sortBy = document.getElementById('sortBy').value;
        params.append('sort', sortBy);

        const sortOrder = document.getElementById('sortOrder').value;
        params.append('order', sortOrder);

        params.append('page', this.currentPage);
        params.append('per_page', 20);

        return params.toString();
    }

    displayPosts(posts) {
        const container = document.getElementById('postsContainer');
        
        if (posts.length === 0) {
            document.getElementById('noResults').style.display = 'block';
            container.innerHTML = '';
            return;
        }

        document.getElementById('noResults').style.display = 'none';
        
        container.innerHTML = posts.map(post => this.createPostCard(post)).join('');

        // Add click listeners for post expansion
        container.querySelectorAll('.expand-post').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const postId = e.target.dataset.postId;
                const post = posts.find(p => p.id == postId);
                if (post) {
                    this.showPostModal(post);
                }
            });
        });
    }

    createPostCard(post) {
        const authorInitials = this.getAuthorInitials(post.author_display);
        const languageBadge = post.language !== 'Unknown' ? 
            `<span class="badge bg-secondary language-badge">${post.language}</span>` : '';

        const isTextTruncated = post.text !== post.text_full;
        const expandButton = isTextTruncated ? 
            `<button class="expand-post" data-post-id="${post.id}">Show more</button>` : '';

        return `
            <div class="card post-card">
                <div class="card-body">
                    <div class="post-header">
                        <div class="author-avatar">
                            ${authorInitials}
                        </div>
                        <div class="author-info">
                            <div class="author-handle">${this.escapeHtml(post.author_display)}</div>
                            <div class="post-meta">
                                <i class="fas fa-clock me-1"></i>
                                ${post.created_at_display}
                                ${languageBadge}
                            </div>
                        </div>
                    </div>
                    <div class="post-text">
                        ${this.escapeHtml(post.text)}
                        ${expandButton}
                    </div>
                    <div class="post-actions">
                        <small class="text-muted">
                            Saved: ${post.saved_at_display}
                        </small>
                        <div>
                            <button class="btn btn-sm btn-outline-primary expand-post" data-post-id="${post.id}">
                                <i class="fas fa-external-link-alt me-1"></i>
                                View Details
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    showPostModal(post) {
        const modal = new bootstrap.Modal(document.getElementById('postModal'));
        const modalBody = document.getElementById('postModalBody');
        const viewOnBluesky = document.getElementById('viewOnBluesky');

        modalBody.innerHTML = `
            <div class="row">
                <div class="col-md-8">
                    <h6>Author</h6>
                    <p>${this.escapeHtml(post.author_display)}</p>
                    
                    <h6>Content</h6>
                    <p class="border p-3 rounded bg-light">${this.escapeHtml(post.text_full)}</p>
                    
                    <h6>Details</h6>
                    <ul class="list-unstyled">
                        <li><strong>Language:</strong> ${post.language}</li>
                        <li><strong>Created:</strong> ${post.created_at_display}</li>
                        <li><strong>Saved:</strong> ${post.saved_at_display}</li>
                    </ul>
                </div>
                <div class="col-md-4">
                    <h6>Technical Details</h6>
                    <ul class="list-unstyled small">
                        <li><strong>Post ID:</strong> ${post.id}</li>
                        <li><strong>Author DID:</strong> <code class="small">${this.escapeHtml(post.author_did)}</code></li>
                        <li><strong>Post URI:</strong> <code class="small">${this.escapeHtml(post.post_uri || '')}</code></li>
                    </ul>
                </div>
            </div>
        `;

        // Set up the Bluesky link
        if (post.post_uri) {
            const blueskyUrl = this.convertToBlueskyUrl(post.post_uri, post.author_handle);
            viewOnBluesky.href = blueskyUrl;
            viewOnBluesky.style.display = 'inline-block';
        } else {
            viewOnBluesky.style.display = 'none';
        }

        modal.show();
    }

    convertToBlueskyUrl(postUri, authorHandle) {
        // Convert AT URI to Bluesky web URL
        // Example: at://did:plc:xxx/app.bsky.feed.post/xxx -> https://bsky.app/profile/handle/post/xxx
        try {
            const uriParts = postUri.split('/');
            if (uriParts.length >= 4) {
                const postId = uriParts[uriParts.length - 1];
                const handle = authorHandle || 'unknown';
                return `https://bsky.app/profile/${handle}/post/${postId}`;
            }
        } catch (error) {
            console.error('Error converting URI:', error);
        }
        return 'https://bsky.app';
    }

    displayPagination(pagination) {
        const container = document.getElementById('paginationContainer');
        const paginationList = document.getElementById('pagination');

        if (pagination.total_pages <= 1) {
            container.style.display = 'none';
            return;
        }

        container.style.display = 'block';

        let paginationHtml = '';

        // Previous button
        if (pagination.has_prev) {
            paginationHtml += `
                <li class="page-item">
                    <a class="page-link" href="#" data-page="${pagination.current_page - 1}">Previous</a>
                </li>
            `;
        }

        // Page numbers
        const startPage = Math.max(1, pagination.current_page - 2);
        const endPage = Math.min(pagination.total_pages, pagination.current_page + 2);

        if (startPage > 1) {
            paginationHtml += '<li class="page-item"><a class="page-link" href="#" data-page="1">1</a></li>';
            if (startPage > 2) {
                paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
        }

        for (let i = startPage; i <= endPage; i++) {
            const isActive = i === pagination.current_page ? 'active' : '';
            paginationHtml += `
                <li class="page-item ${isActive}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }

        if (endPage < pagination.total_pages) {
            if (endPage < pagination.total_pages - 1) {
                paginationHtml += '<li class="page-item disabled"><span class="page-link">...</span></li>';
            }
            paginationHtml += `<li class="page-item"><a class="page-link" href="#" data-page="${pagination.total_pages}">${pagination.total_pages}</a></li>`;
        }

        // Next button
        if (pagination.has_next) {
            paginationHtml += `
                <li class="page-item">
                    <a class="page-link" href="#" data-page="${pagination.current_page + 1}">Next</a>
                </li>
            `;
        }

        paginationList.innerHTML = paginationHtml;

        // Add click listeners
        paginationList.querySelectorAll('.page-link').forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(e.target.dataset.page);
                if (page && page !== this.currentPage) {
                    this.currentPage = page;
                    this.loadPosts();
                }
            });
        });
    }

    updateResultsInfo(pagination) {
        const resultsInfo = document.getElementById('resultsInfo');
        const start = (pagination.current_page - 1) * pagination.per_page + 1;
        const end = Math.min(start + pagination.per_page - 1, pagination.total_count);
        
        resultsInfo.textContent = `Showing ${start}-${end} of ${this.formatNumber(pagination.total_count)} posts`;
    }

    clearFilters() {
        document.getElementById('searchQuery').value = '';
        document.getElementById('languageFilter').value = '';
        document.getElementById('authorFilter').value = '';
        document.getElementById('dateFrom').value = '';
        document.getElementById('dateTo').value = '';
        document.getElementById('sortBy').value = 'saved_at';
        document.getElementById('sortOrder').value = 'desc';
        
        this.currentPage = 1;
        this.loadPosts();
    }

    showLoading(show) {
        document.getElementById('loadingIndicator').style.display = show ? 'block' : 'none';
        document.getElementById('postsContainer').style.opacity = show ? '0.5' : '1';
    }

    showError(message) {
        document.getElementById('errorText').textContent = message;
        document.getElementById('errorMessage').style.display = 'block';
    }

    hideError() {
        document.getElementById('errorMessage').style.display = 'none';
    }

    getAuthorInitials(authorDisplay) {
        if (!authorDisplay) return '?';
        
        // Remove @ symbol if present
        const clean = authorDisplay.replace('@', '');
        
        // Get first two characters
        return clean.substring(0, 2).toUpperCase();
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    formatNumber(num) {
        if (num >= 1000000) {
            return (num / 1000000).toFixed(1) + 'M';
        } else if (num >= 1000) {
            return (num / 1000).toFixed(1) + 'K';
        }
        return num.toString();
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new BlueskyExplorer();
});
