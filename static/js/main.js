// Main JavaScript for Kirim-Chiqim

document.addEventListener('DOMContentLoaded', function() {
    
    // Initialize tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
    
    // Initialize popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
    
    // Auto-dismiss alerts after 5 seconds
    const autoDismissAlerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    autoDismissAlerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
    
    // Form validation feedback
    const forms = document.querySelectorAll('.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            form.classList.add('was-validated');
        }, false);
    });
    
    // Password toggle functionality
    document.querySelectorAll('.toggle-password').forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const passwordInput = document.getElementById(targetId);
            const icon = this.querySelector('i');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                passwordInput.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
    
    // Currency formatting
    function formatCurrency(amount, currency = 'UZS') {
        const formatter = new Intl.NumberFormat('uz-UZ', {
            style: 'currency',
            currency: currency,
            minimumFractionDigits: 0,
            maximumFractionDigits: 0
        });
        return formatter.format(amount);
    }
    
    // Date formatting
    function formatDate(dateString) {
        const date = new Date(dateString);
        return date.toLocaleDateString('uz-UZ', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
    }
    
    // Format all currency elements
    document.querySelectorAll('.format-currency').forEach(element => {
        const amount = parseFloat(element.getAttribute('data-amount')) || parseFloat(element.textContent);
        const currency = element.getAttribute('data-currency') || 'UZS';
        if (!isNaN(amount)) {
            element.textContent = formatCurrency(amount, currency);
        }
    });
    
    // Format all date elements
    document.querySelectorAll('.format-date').forEach(element => {
        const dateString = element.getAttribute('data-date') || element.textContent;
        element.textContent = formatDate(dateString);
    });
    
    // Copy to clipboard functionality
    document.querySelectorAll('.copy-to-clipboard').forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const targetElement = document.getElementById(targetId);
            const textToCopy = targetElement.textContent || targetElement.value;
            
            navigator.clipboard.writeText(textToCopy).then(() => {
                // Show success feedback
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-check me-1"></i> Nusxalandi';
                this.classList.add('btn-success');
                
                setTimeout(() => {
                    this.innerHTML = originalText;
                    this.classList.remove('btn-success');
                }, 2000);
            }).catch(err => {
                console.error('Clipboard yozishda xato:', err);
            });
        });
    });
    
    // Dynamic form field addition (for repeating fields)
    document.querySelectorAll('.add-field').forEach(button => {
        button.addEventListener('click', function() {
            const templateId = this.getAttribute('data-template');
            const containerId = this.getAttribute('data-container');
            const template = document.getElementById(templateId);
            const container = document.getElementById(containerId);
            
            if (template && container) {
                const clone = template.content.cloneNode(true);
                const index = container.children.length;
                
                // Update field names with new index
                clone.querySelectorAll('[name]').forEach(field => {
                    const name = field.getAttribute('name');
                    field.setAttribute('name', name.replace('[0]', `[${index}]`));
                });
                
                container.appendChild(clone);
            }
        });
    });
    
    // Remove field functionality
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('remove-field')) {
            const field = e.target.closest('.field-group');
            if (field && field.parentNode.children.length > 1) {
                field.remove();
            }
        }
    });
    
    // Loading state for buttons
    document.addEventListener('submit', function(e) {
        const submitBtn = e.target.querySelector('button[type="submit"]');
        if (submitBtn && !submitBtn.hasAttribute('data-no-loading')) {
            submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i> Yuklanmoqda...';
            submitBtn.disabled = true;
        }
    });
    
    // Auto-save form data
    const autoSaveForms = document.querySelectorAll('.auto-save');
    autoSaveForms.forEach(form => {
        const formId = form.id || 'form-' + Math.random().toString(36).substr(2, 9);
        
        form.querySelectorAll('input, textarea, select').forEach(input => {
            const inputId = input.name || input.id;
            const storageKey = `autosave_${formId}_${inputId}`;
            
            // Load saved value
            const savedValue = localStorage.getItem(storageKey);
            if (savedValue !== null) {
                if (input.type === 'checkbox') {
                    input.checked = savedValue === 'true';
                } else {
                    input.value = savedValue;
                }
            }
            
            // Save on change
            input.addEventListener('change', function() {
                const value = this.type === 'checkbox' ? this.checked : this.value;
                localStorage.setItem(storageKey, value);
                
                // Show save indicator
                const indicator = document.createElement('small');
                indicator.className = 'text-success ms-2';
                indicator.innerHTML = '<i class="fas fa-save me-1"></i> Saqlandi';
                
                const label = this.closest('.form-group').querySelector('label');
                if (label && !label.querySelector('.save-indicator')) {
                    label.appendChild(indicator);
                    setTimeout(() => indicator.remove(), 2000);
                }
            });
        });
        
        // Clear saved data on successful submit
        form.addEventListener('submit', function() {
            form.querySelectorAll('input, textarea, select').forEach(input => {
                const inputId = input.name || input.id;
                const storageKey = `autosave_${formId}_${inputId}`;
                localStorage.removeItem(storageKey);
            });
        });
    });
    
    // Theme switcher (light/dark mode)
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        const currentTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', currentTheme);
        
        themeToggle.addEventListener('click', function() {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            
            // Update button icon
            const icon = this.querySelector('i');
            if (newTheme === 'dark') {
                icon.classList.remove('fa-moon');
                icon.classList.add('fa-sun');
            } else {
                icon.classList.remove('fa-sun');
                icon.classList.add('fa-moon');
            }
        });
    }
    
    // Print functionality
    const printButtons = document.querySelectorAll('.print-btn');
    printButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            window.print();
        });
    });
    
    // Export functionality (CSV/PDF)
    const exportButtons = document.querySelectorAll('.export-btn');
    exportButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            const format = this.getAttribute('data-format');
            const tableId = this.getAttribute('data-table');
            
            if (format === 'csv' && tableId) {
                exportTableToCSV(tableId);
            } else if (format === 'pdf') {
                // PDF export would require a library like jsPDF
                alert('PDF eksporti keyingi versiyada qoʻshiladi');
            }
        });
    });
    
    function exportTableToCSV(tableId) {
        const table = document.getElementById(tableId);
        if (!table) return;
        
        let csv = [];
        const rows = table.querySelectorAll('tr');
        
        for (let i = 0; i < rows.length; i++) {
            const row = [], cols = rows[i].querySelectorAll('td, th');
            
            for (let j = 0; j < cols.length; j++) {
                // Clean data and add quotes if needed
                let data = cols[j].innerText.replace(/(\r\n|\n|\r)/gm, '').replace(/(\s\s)/gm, ' ');
                data = data.replace(/"/g, '""');
                row.push('"' + data + '"');
            }
            
            csv.push(row.join(','));
        }
        
        // Download CSV file
        const csvFile = new Blob([csv.join('\n')], { type: 'text/csv' });
        const downloadLink = document.createElement('a');
        downloadLink.download = `kirim-chiqim_${new Date().toISOString().slice(0,10)}.csv`;
        downloadLink.href = window.URL.createObjectURL(csvFile);
        downloadLink.style.display = 'none';
        document.body.appendChild(downloadLink);
        downloadLink.click();
        document.body.removeChild(downloadLink);
    }
    
    // Infinite scroll for transaction history
    const transactionList = document.getElementById('transaction-list');
    if (transactionList) {
        let page = 1;
        let loading = false;
        
        window.addEventListener('scroll', function() {
            if (loading) return;
            
            const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
            
            if (scrollTop + clientHeight >= scrollHeight - 100) {
                loading = true;
                page++;
                
                // Show loading indicator
                const loader = document.createElement('div');
                loader.className = 'text-center py-3';
                loader.innerHTML = '<i class="fas fa-spinner fa-spin fa-2x"></i>';
                transactionList.appendChild(loader);
                
                // Load more data
                fetch(`/api/transactions/?page=${page}`)
                    .then(response => response.json())
                    .then(data => {
                        loader.remove();
                        
                        if (data.results && data.results.length > 0) {
                            // Append new transactions
                            data.results.forEach(transaction => {
                                const transactionElement = createTransactionElement(transaction);
                                transactionList.appendChild(transactionElement);
                            });
                        } else {
                            // No more data
                            const noMore = document.createElement('div');
                            noMore.className = 'text-center py-3 text-muted';
                            noMore.textContent = 'Koʻrsatish uchun maʼlumot qolmadi';
                            transactionList.appendChild(noMore);
                        }
                        
                        loading = false;
                    })
                    .catch(error => {
                        console.error('Error loading more transactions:', error);
                        loader.remove();
                        loading = false;
                    });
            }
        });
    }
    
    function createTransactionElement(transaction) {
        const div = document.createElement('div');
        div.className = `transaction-item card mb-2 ${transaction.type === 'income' ? 'border-success' : 'border-danger'}`;
        div.innerHTML = `
            <div class="card-body py-2">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <h6 class="mb-0">${transaction.category}</h6>
                        <small class="text-muted">${transaction.description}</small>
                    </div>
                    <div class="text-end">
                        <h6 class="mb-0 ${transaction.type === 'income' ? 'text-success' : 'text-danger'}">
                            ${transaction.type === 'income' ? '+' : '-'}${formatCurrency(transaction.amount, transaction.currency)}
                        </h6>
                        <small>${formatDate(transaction.date)}</small>
                    </div>
                </div>
            </div>
        `;
        return div;
    }
    
    // Notification bell
    const notificationBell = document.getElementById('notification-bell');
    if (notificationBell) {
        notificationBell.addEventListener('click', function() {
            fetch('/api/notifications/mark-all-read/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCookie('csrftoken'),
                    'Content-Type': 'application/json'
                }
            }).then(response => {
                if (response.ok) {
                    const badge = this.querySelector('.badge');
                    if (badge) badge.remove();
                }
            });
        });
    }
    
    // Helper function to get CSRF token
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Initialize charts (if Chart.js is loaded)
    if (typeof Chart !== 'undefined') {
        initializeCharts();
    }
    
    function initializeCharts() {
        // Income vs Expense Chart
        const incomeExpenseCtx = document.getElementById('incomeExpenseChart');
        if (incomeExpenseCtx) {
            new Chart(incomeExpenseCtx.getContext('2d'), {
                type: 'bar',
                data: {
                    labels: ['Yanvar', 'Fevral', 'Mart', 'Aprel', 'May', 'Iyun'],
                    datasets: [{
                        label: 'Kirim',
                        data: [5000000, 5500000, 6000000, 5800000, 6200000, 6500000],
                        backgroundColor: 'rgba(40, 167, 69, 0.7)',
                        borderColor: 'rgba(40, 167, 69, 1)',
                        borderWidth: 1
                    }, {
                        label: 'Chiqim',
                        data: [3500000, 3800000, 4200000, 4000000, 4500000, 4300000],
                        backgroundColor: 'rgba(220, 53, 69, 0.7)',
                        borderColor: 'rgba(220, 53, 69, 1)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return formatCurrency(value);
                                }
                            }
                        }
                    }
                }
            });
        }
        
        // Expense by Category Chart
        const categoryChartCtx = document.getElementById('categoryChart');
        if (categoryChartCtx) {
            new Chart(categoryChartCtx.getContext('2d'), {
                type: 'doughnut',
                data: {
                    labels: ['Oziq-ovqat', 'Transport', 'Kommunal', 'Ta\'lim', 'Sog\'liq', 'Kiyim', 'Ko\'ngilochar'],
                    datasets: [{
                        data: [30, 15, 10, 20, 8, 12, 5],
                        backgroundColor: [
                            '#0d6efd',
                            '#6610f2',
                            '#6f42c1',
                            '#d63384',
                            '#fd7e14',
                            '#ffc107',
                            '#198754'
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
    }
    
    // Language switcher
    const languageSelect = document.querySelector('select[name="language"]');
    if (languageSelect) {
        languageSelect.addEventListener('change', function() {
            const form = this.closest('form');
            if (form) {
                // Add loading state
                const originalValue = this.value;
                this.disabled = true;
                
                // Submit form
                form.submit();
            }
        });
    }
});