/**
 * Main JavaScript for Remixable Fiction Library
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function(tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Initialize Bootstrap popovers
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function(popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });

    // Book reader font size controls
    const fontSizeControls = document.querySelector('.font-size-controls');
    if (fontSizeControls) {
        const bookContent = document.querySelector('.book-content');
        const increaseFontBtn = document.getElementById('increase-font');
        const decreaseFontBtn = document.getElementById('decrease-font');
        const resetFontBtn = document.getElementById('reset-font');

        // Get current font size
        let currentFontSize = parseFloat(window.getComputedStyle(bookContent).fontSize);
        const defaultFontSize = currentFontSize;

        // Increase font size
        increaseFontBtn.addEventListener('click', function() {
            currentFontSize += 2;
            bookContent.style.fontSize = currentFontSize + 'px';
            saveReaderPreferences();
        });

        // Decrease font size
        decreaseFontBtn.addEventListener('click', function() {
            if (currentFontSize > 10) {
                currentFontSize -= 2;
                bookContent.style.fontSize = currentFontSize + 'px';
                saveReaderPreferences();
            }
        });

        // Reset font size
        resetFontBtn.addEventListener('click', function() {
            currentFontSize = defaultFontSize;
            bookContent.style.fontSize = defaultFontSize + 'px';
            saveReaderPreferences();
        });

        // Load saved preferences
        loadReaderPreferences();

        function saveReaderPreferences() {
            localStorage.setItem('readerFontSize', currentFontSize);
        }

        function loadReaderPreferences() {
            const savedFontSize = localStorage.getItem('readerFontSize');
            if (savedFontSize) {
                currentFontSize = parseFloat(savedFontSize);
                bookContent.style.fontSize = currentFontSize + 'px';
            }
        }
    }

    // Copy attribution to clipboard
    const copyAttributionBtn = document.getElementById('copy-attribution');
    if (copyAttributionBtn) {
        copyAttributionBtn.addEventListener('click', function() {
            const attributionText = document.getElementById('attribution-text').textContent;
            
            navigator.clipboard.writeText(attributionText).then(function() {
                // Show success message
                const originalText = copyAttributionBtn.innerHTML;
                copyAttributionBtn.innerHTML = '<i class="bi bi-check"></i> Copied!';
                
                setTimeout(function() {
                    copyAttributionBtn.innerHTML = originalText;
                }, 2000);
            }).catch(function(err) {
                console.error('Could not copy text: ', err);
            });
        });
    }

    // Import source selection
    const importSourceCards = document.querySelectorAll('.import-source-card');
    if (importSourceCards.length > 0) {
        importSourceCards.forEach(card => {
            card.addEventListener('click', function() {
                // Remove selected class from all cards
                importSourceCards.forEach(c => c.classList.remove('selected'));
                
                // Add selected class to clicked card
                this.classList.add('selected');
                
                // Set the value in the hidden input
                const sourceInput = document.getElementById('selected-source');
                sourceInput.value = this.dataset.source;
                
                // Show the corresponding form
                const forms = document.querySelectorAll('.source-form');
                forms.forEach(form => form.classList.add('d-none'));
                
                const selectedForm = document.getElementById(`${this.dataset.source}-form`);
                if (selectedForm) {
                    selectedForm.classList.remove('d-none');
                }
            });
        });
    }

    // Book search autocomplete
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        searchInput.addEventListener('input', debounce(function() {
            const query = this.value.trim();
            if (query.length < 3) return;

            fetch(`/api/search?q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    // Handle autocomplete suggestions
                    console.log(data);
                })
                .catch(error => console.error('Error fetching search results:', error));
        }, 300));
    }

    // Utility function for debouncing
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func.apply(this, args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }

    // Handle license filter changes
    const licenseFilter = document.getElementById('license');
    if (licenseFilter) {
        licenseFilter.addEventListener('change', function() {
            updateLicenseInfo(this.value);
        });

        function updateLicenseInfo(licenseType) {
            const licenseInfo = document.getElementById('license-info');
            if (!licenseInfo) return;

            let infoText = '';
            
            switch(licenseType) {
                case 'PD-US':
                    infoText = 'US Public Domain works have no copyright restrictions in the United States.';
                    break;
                case 'CC0':
                    infoText = 'CC0 (Creative Commons Zero) works have been dedicated to the public domain worldwide.';
                    break;
                case 'CC-BY':
                    infoText = 'CC BY (Creative Commons Attribution) works require attribution to the original creator.';
                    break;
                case 'CC-BY-SA':
                    infoText = 'CC BY-SA (Creative Commons Attribution-ShareAlike) works require attribution and sharing derivatives under the same license.';
                    break;
                default:
                    infoText = 'Select a license to see more information.';
            }
            
            licenseInfo.textContent = infoText;
        }

        // Initialize with current value
        updateLicenseInfo(licenseFilter.value);
    }
});
