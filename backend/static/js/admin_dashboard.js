/**
 * Votonomy Admin Dashboard JavaScript
 * Handles sentiment analysis charts and content quality review functionality
 */

// ===== GLOBAL VARIABLES =====
let sentimentChart = null;
let topicChart = null;
let emotionChart = null;

// ===== UTILITY FUNCTIONS =====
function getDataFromElement(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        try {
            return JSON.parse(element.textContent);
        } catch (e) {
            console.error(`Error parsing data from ${elementId}:`, e);
            return null;
        }
    }
    return null;
}

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    notification.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentNode) {
            notification.parentNode.removeChild(notification);
        }
    }, 5000);
}

// ===== CHART.JS AVAILABILITY CHECK =====
function waitForChartJS(callback, maxAttempts = 50) {
    let attempts = 0;
    
    function checkChartJS() {
        attempts++;
        
        if (typeof Chart !== 'undefined') {
            console.log('✅ Chart.js is available, initializing charts...');
            callback();
        } else if (attempts < maxAttempts) {
            console.log(`⏳ Waiting for Chart.js... (attempt ${attempts}/${maxAttempts})`);
            setTimeout(checkChartJS, 100);
        } else {
            console.error('❌ Chart.js failed to load after maximum attempts');
            showFallbackChartMessage();
        }
    }
    
    checkChartJS();
}

function showFallbackChartMessage() {
    const chartIds = ['sentimentPieChart', 'topicSentimentChart', 'emotionChart'];
    
    chartIds.forEach(id => {
        const container = document.getElementById(id);
        if (container) {
            container.style.display = 'flex';
            container.style.alignItems = 'center';
            container.style.justifyContent = 'center';
            container.innerHTML = `
                <div class="text-center p-4">
                    <i class="fas fa-chart-line fa-3x text-muted mb-3"></i>
                    <p class="text-muted">Chart visualization unavailable</p>
                    <small class="text-muted">Please refresh the page or check your connection</small>
                </div>
            `;
        }
    });
}

// ===== SENTIMENT ANALYSIS CHARTS =====
function initializeSentimentCharts() {
    const analyticsData = getDataFromElement('analytics-data');
    
    if (!analyticsData) {
        console.log('No analytics data found');
        return;
    }
    
    console.log('📊 Analytics data loaded:', analyticsData);
    
    // Initialize all charts
    createSentimentPieChart(analyticsData);
    createTopicSentimentChart(analyticsData);
    createEmotionChart(analyticsData);
    setupProgressBars();
    setupKeywordSizing();
}

function createSentimentPieChart(data) {
    const ctx = document.getElementById('sentimentPieChart');
    if (!ctx) {
        console.warn('sentimentPieChart canvas not found');
        return;
    }
    
    try {
        // Destroy existing chart
        if (sentimentChart) {
            sentimentChart.destroy();
        }
        
        sentimentChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Positive', 'Negative', 'Neutral'],
                datasets: [{
                    data: [
                        data.positive_percentage || 0,
                        data.negative_percentage || 0,
                        data.neutral_percentage || 0
                    ],
                    backgroundColor: ['#198754', '#dc3545', '#6c757d'],
                    borderWidth: 3,
                    borderColor: '#fff',
                    hoverBorderWidth: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            font: {
                                size: 14,
                                weight: 'bold'
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        borderColor: '#fff',
                        borderWidth: 1,
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: ${context.parsed.toFixed(1)}%`;
                            }
                        }
                    }
                },
                animation: {
                    animateRotate: true,
                    duration: 1500
                }
            }
        });
        
        console.log('✅ Sentiment pie chart created');
    } catch (error) {
        console.error('❌ Error creating sentiment pie chart:', error);
    }
}

function createTopicSentimentChart(data) {
    const ctx = document.getElementById('topicSentimentChart');
    if (!ctx) {
        console.warn('topicSentimentChart canvas not found');
        return;
    }
    
    if (!data.topic_sentiments || Object.keys(data.topic_sentiments).length === 0) {
        console.warn('No topic sentiment data available');
        ctx.style.display = 'flex';
        ctx.style.alignItems = 'center';
        ctx.style.justifyContent = 'center';
        ctx.innerHTML = '<p class="text-muted">No topic data available</p>';
        return;
    }
    
    try {
        // Destroy existing chart
        if (topicChart) {
            topicChart.destroy();
        }
        
        const topics = Object.keys(data.topic_sentiments);
        const scores = Object.values(data.topic_sentiments);
        
        topicChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: topics,
                datasets: [{
                    label: 'Sentiment Score',
                    data: scores,
                    backgroundColor: scores.map(score => 
                        score > 0.1 ? '#198754' : score < -0.1 ? '#dc3545' : '#6c757d'
                    ),
                    borderColor: scores.map(score => 
                        score > 0.1 ? '#146c42' : score < -0.1 ? '#b02a37' : '#5a6268'
                    ),
                    borderWidth: 2,
                    borderRadius: 8,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        min: -1,
                        max: 1,
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(1);
                            },
                            font: {
                                size: 12,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            color: 'rgba(0,0,0,0.1)'
                        }
                    },
                    x: {
                        ticks: {
                            maxRotation: 45,
                            font: {
                                size: 11,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            display: false
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        callbacks: {
                            label: function(context) {
                                const sentiment = context.parsed.y > 0.1 ? 'Positive' : 
                                                context.parsed.y < -0.1 ? 'Negative' : 'Neutral';
                                return `${sentiment}: ${context.parsed.y.toFixed(3)}`;
                            }
                        }
                    }
                },
                animation: {
                    duration: 1500,
                    easing: 'easeOutQuart'
                }
            }
        });
        
        console.log('✅ Topic sentiment chart created');
    } catch (error) {
        console.error('❌ Error creating topic sentiment chart:', error);
    }
}

function createEmotionChart(data) {
    const ctx = document.getElementById('emotionChart');
    if (!ctx) {
        console.warn('emotionChart canvas not found');
        return;
    }
    
    if (!data.emotion_distribution || Object.keys(data.emotion_distribution).length === 0) {
        console.warn('No emotion data available');
        ctx.style.display = 'flex';
        ctx.style.alignItems = 'center';
        ctx.style.justifyContent = 'center';
        ctx.innerHTML = '<p class="text-muted">No emotion data available</p>';
        return;
    }
    
    try {
        // Destroy existing chart
        if (emotionChart) {
            emotionChart.destroy();
        }
        
        const emotions = Object.keys(data.emotion_distribution);
        const values = Object.values(data.emotion_distribution);
        
        emotionChart = new Chart(ctx, {
            type: 'radar',
            data: {
                labels: emotions.map(emotion => 
                    emotion.charAt(0).toUpperCase() + emotion.slice(1)
                ),
                datasets: [{
                    label: 'Emotion Distribution (%)',
                    data: values,
                    backgroundColor: 'rgba(1, 65, 28, 0.2)',
                    borderColor: '#01411C',
                    borderWidth: 3,
                    pointBackgroundColor: '#01411C',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 3,
                    pointRadius: 6,
                    pointHoverRadius: 8
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    r: {
                        beginAtZero: true,
                        max: Math.max(...values) * 1.2,
                        ticks: {
                            font: {
                                size: 11,
                                weight: 'bold'
                            }
                        },
                        grid: {
                            color: 'rgba(1, 65, 28, 0.2)'
                        },
                        angleLines: {
                            color: 'rgba(1, 65, 28, 0.2)'
                        }
                    }
                },
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            font: {
                                size: 13,
                                weight: 'bold'
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(0,0,0,0.8)',
                        titleColor: '#fff',
                        bodyColor: '#fff',
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: ${context.parsed.r.toFixed(1)}%`;
                            }
                        }
                    }
                },
                animation: {
                    duration: 2000,
                    easing: 'easeOutElastic'
                }
            }
        });
        
        console.log('✅ Emotion chart created');
    } catch (error) {
        console.error('❌ Error creating emotion chart:', error);
    }
}

// ===== PROGRESS BAR FUNCTIONALITY =====
function setupProgressBars() {
    // Set dynamic widths for progress bars using data attributes
    document.querySelectorAll('[data-width]').forEach(function(element) {
        const width = element.getAttribute('data-width');
        if (width) {
            // Animate the progress bar
            setTimeout(() => {
                element.style.width = width + '%';
                element.style.transition = 'width 0.6s ease-in-out';
            }, 200);
        }
    });
}

function setupKeywordSizing() {
    // Set keyword font sizes based on count
    document.querySelectorAll('[data-count]').forEach(function(element) {
        const count = parseInt(element.getAttribute('data-count'));
        if (count) {
            element.style.fontSize = Math.min(12 + (count * 1.5), 20) + 'px';
            element.style.fontWeight = count > 5 ? 'bold' : 'normal';
        }
    });
}

// ===== CONTENT QUALITY REVIEW FUNCTIONS =====
function approveResponse(surveyId) {
    if (!surveyId) {
        showNotification('Invalid survey ID', 'danger');
        return;
    }
    
    if (confirm('Approve this response as high quality?')) {
        const loadingBtn = event.target;
        const originalText = loadingBtn.innerHTML;
        loadingBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';
        loadingBtn.disabled = true;
        
        fetch(`/admin/approve-response/${surveyId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showNotification('✅ Response approved successfully!', 'success');
                setTimeout(() => {
                    location.reload();
                }, 1500);
            } else {
                throw new Error(data.message || 'Unknown error occurred');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification(`❌ Error: ${error.message}`, 'danger');
            loadingBtn.innerHTML = originalText;
            loadingBtn.disabled = false;
        });
    }
}

function flagResponse(surveyId) {
    if (!surveyId) {
        showNotification('Invalid survey ID', 'danger');
        return;
    }
    
    const reason = prompt('Reason for flagging this response:');
    if (reason && reason.trim()) {
        const loadingBtn = event.target;
        const originalText = loadingBtn.innerHTML;
        loadingBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Processing...';
        loadingBtn.disabled = true;
        
        fetch(`/admin/flag-response/${surveyId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            },
            body: JSON.stringify({reason: reason.trim()})
        })
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                showNotification('🚩 Response flagged successfully!', 'warning');
                setTimeout(() => {
                    location.reload();
                }, 1500);
            } else {
                throw new Error(data.message || 'Unknown error occurred');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification(`❌ Error: ${error.message}`, 'danger');
            loadingBtn.innerHTML = originalText;
            loadingBtn.disabled = false;
        });
    }
}

// ===== QUALITY METRICS DASHBOARD =====
function refreshQualityMetrics() {
    fetch('/admin/content-quality-stats')
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            
            // Update quality statistics
            updateQualityStats(data);
            showNotification('📊 Quality metrics refreshed!', 'info');
        })
        .catch(error => {
            console.error('Error refreshing metrics:', error);
            showNotification('❌ Failed to refresh metrics', 'danger');
        });
}

function updateQualityStats(data) {
    // Update quality count displays
    const elements = {
        'total-responses': data.total_responses,
        'high-quality': data.high_quality,
        'medium-quality': data.medium_quality,
        'low-quality': data.low_quality,
        'flagged-by-admin': data.flagged_by_admin,
        'approved-by-admin': data.approved_by_admin
    };
    
    Object.entries(elements).forEach(([id, value]) => {
        const element = document.getElementById(id);
        if (element) {
            // Animate number change
            animateNumber(element, parseInt(element.textContent) || 0, value);
        }
    });
}

function animateNumber(element, start, end) {
    const duration = 1000;
    const startTime = performance.now();
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const current = Math.round(start + (end - start) * progress);
        element.textContent = current;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// ===== EXPORT FUNCTIONALITY =====
function exportSentimentData() {
    showNotification('📊 Preparing export...', 'info');
    
    // Create a temporary link and trigger download
    const link = document.createElement('a');
    link.href = '/admin/sentiment/export-data';
    link.download = `sentiment_analysis_${new Date().toISOString().slice(0, 10)}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    setTimeout(() => {
        showNotification('✅ Export completed!', 'success');
    }, 2000);
}

// ===== FILTER FUNCTIONALITY =====
function setupFilters() {
    // Quality filter
    const qualityFilter = document.getElementById('quality-filter');
    if (qualityFilter) {
        qualityFilter.addEventListener('change', function() {
            updateURL('quality_filter', this.value);
        });
    }
    
    // Halka filter
    const halkaFilter = document.getElementById('halka-filter');
    if (halkaFilter) {
        halkaFilter.addEventListener('change', function() {
            updateURL('halka_filter', this.value);
        });
    }
    
    // Date filter
    const dateFilter = document.getElementById('date-filter');
    if (dateFilter) {
        dateFilter.addEventListener('change', function() {
            updateURL('date_from', this.value);
        });
    }
}

function updateURL(param, value) {
    const url = new URL(window.location);
    if (value) {
        url.searchParams.set(param, value);
    } else {
        url.searchParams.delete(param);
    }
    window.location.href = url.toString();
}

// ===== RESPONSIVE CHART HANDLING =====
function handleResize() {
    // Resize charts when window size changes
    if (sentimentChart) sentimentChart.resize();
    if (topicChart) topicChart.resize();
    if (emotionChart) emotionChart.resize();
}

// ===== INITIALIZATION =====
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Initializing Votonomy Admin Dashboard...');
    
    // Setup non-chart elements first
    setupProgressBars();
    setupKeywordSizing();
    setupFilters();
    
    // Wait for Chart.js and then initialize charts
    waitForChartJS(function() {
        // Configure Chart.js defaults
        Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";
        Chart.defaults.plugins.tooltip.cornerRadius = 8;
        Chart.defaults.plugins.tooltip.displayColors = true;
        
        // Initialize charts
        initializeSentimentCharts();
        console.log('📊 Charts initialized');
    });
    
    // Setup window resize handler
    let resizeTimeout;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(handleResize, 250);
    });
    
    console.log('✅ Admin dashboard initialized successfully');
});

// ===== GLOBAL ERROR HANDLER =====
window.addEventListener('error', function(e) {
    console.error('Global error:', e.error);
    showNotification('⚠️ An error occurred. Please refresh the page.', 'warning');
});

// ===== EXPOSE FUNCTIONS GLOBALLY =====
window.approveResponse = approveResponse;
window.flagResponse = flagResponse;
window.refreshQualityMetrics = refreshQualityMetrics;
window.exportSentimentData = exportSentimentData;