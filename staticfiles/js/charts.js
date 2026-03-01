// Charts for Charles Academy SMS

function initializeCharts() {
    // Initialize all charts on page
    const chartElements = document.querySelectorAll('[data-chart]');
    chartElements.forEach(element => {
        const chartType = element.getAttribute('data-chart-type') || 'bar';
        const chartData = JSON.parse(element.getAttribute('data-chart-data') || '{}');
        
        if (chartData && Object.keys(chartData).length > 0) {
            createChart(element, chartType, chartData);
        }
    });
}

function createChart(canvas, type, data) {
    const ctx = canvas.getContext('2d');
    
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
            },
            tooltip: {
                mode: 'index',
                intersect: false,
            }
        },
        scales: {
            y: {
                beginAtZero: true
            }
        }
    };
    
    // Customize based on chart type
    switch(type) {
        case 'line':
            return new Chart(ctx, {
                type: 'line',
                data: data,
                options: {
                    ...defaultOptions,
                    elements: {
                        line: {
                            tension: 0.4
                        }
                    }
                }
            });
        
        case 'bar':
            return new Chart(ctx, {
                type: 'bar',
                data: data,
                options: defaultOptions
            });
        
        case 'pie':
            return new Chart(ctx, {
                type: 'pie',
                data: data,
                options: {
                    ...defaultOptions,
                    plugins: {
                        legend: {
                            position: 'right'
                        }
                    }
                }
            });
        
        case 'doughnut':
            return new Chart(ctx, {
                type: 'doughnut',
                data: data,
                options: {
                    ...defaultOptions,
                    cutout: '70%'
                }
            });
        
        default:
            return new Chart(ctx, {
                type: type,
                data: data,
                options: defaultOptions
            });
    }
}

// Create fees collection chart
function createFeesChart() {
    const ctx = document.getElementById('feesChart');
    if (!ctx) return;
    
    const chart = new Chart(ctx.getContext('2d'), {
        type: 'line',
        data: {
            labels: ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'],
            datasets: [{
                label: 'Fees Collected (TZS)',
                data: [1200000, 1900000, 1500000, 2500000, 2200000, 3000000, 2800000, 3500000, 3200000, 4000000, 3800000, 4500000],
                borderColor: '#0d6efd',
                backgroundColor: 'rgba(13, 110, 253, 0.1)',
                borderWidth: 2,
                fill: true,
                tension: 0.4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'top',
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return 'TZS ' + value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}

// Create attendance chart
function createAttendanceChart() {
    const ctx = document.getElementById('attendanceChart');
    if (!ctx) return;
    
    const chart = new Chart(ctx.getContext('2d'), {
        type: 'bar',
        data: {
            labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
            datasets: [
                {
                    label: 'Present',
                    data: [85, 82, 88, 90, 87],
                    backgroundColor: '#198754',
                },
                {
                    label: 'Absent',
                    data: [5, 8, 2, 3, 3],
                    backgroundColor: '#dc3545',
                },
                {
                    label: 'Late',
                    data: [10, 10, 10, 7, 10],
                    backgroundColor: '#ffc107',
                }
            ]
        },
        options: {
            responsive: true,
            scales: {
                x: {
                    stacked: true,
                },
                y: {
                    stacked: true,
                    beginAtZero: true,
                    max: 100
                }
            }
        }
    });
}

// Create grade distribution chart
function createGradeDistributionChart() {
    const ctx = document.getElementById('gradeChart');
    if (!ctx) return;
    
    const chart = new Chart(ctx.getContext('2d'), {
        type: 'doughnut',
        data: {
            labels: ['A', 'B', 'C', 'D', 'E', 'F'],
            datasets: [{
                data: [15, 25, 30, 20, 5, 5],
                backgroundColor: [
                    '#198754',
                    '#0dcaf0',
                    '#0d6efd',
                    '#ffc107',
                    '#6c757d',
                    '#dc3545'
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

// Create payment methods chart
function createPaymentMethodsChart() {
    const ctx = document.getElementById('paymentMethodsChart');
    if (!ctx) return;
    
    const chart = new Chart(ctx.getContext('2d'), {
        type: 'pie',
        data: {
            labels: ['Cash', 'Bank Transfer', 'Mobile Money', 'Credit Card'],
            datasets: [{
                data: [45, 25, 20, 10],
                backgroundColor: [
                    '#198754',
                    '#0d6efd',
                    '#f0ad4e',
                    '#dc3545'
                ]
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'right'
                }
            }
        }
    });
}

// Update charts on page load
document.addEventListener('DOMContentLoaded', function() {
    if (typeof Chart !== 'undefined') {
        createFeesChart();
        createAttendanceChart();
        createGradeDistributionChart();
        createPaymentMethodsChart();
    }
});