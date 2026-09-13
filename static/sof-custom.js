// Dynamic Favicon switcher for SOF documentation
(function() {
    function updateFavicon() {
        var theme = document.documentElement.dataset.theme;
        var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        var isDark = theme === 'dark' || (theme === 'auto' && prefersDark) || (!theme && prefersDark);

        var links = document.querySelectorAll('link[rel="icon"], link[rel="shortcut icon"]');
        links.forEach(function(link) {
            var href = link.getAttribute('href') || '';
            if (href.indexOf('sof-favicon') !== -1) {
                var dir = href.substring(0, href.lastIndexOf('/') + 1);
                if (theme === 'dark') {
                    link.href = dir + 'sof-favicon-dark.png';
                } else if (theme === 'light') {
                    link.href = dir + 'sof-favicon-light.png';
                } else {
                    link.href = dir + (isDark ? 'sof-favicon-dark.png' : 'sof-favicon.svg');
                }
            }
        });
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', updateFavicon);
    } else {
        updateFavicon();
    }

    var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'data-theme') {
                updateFavicon();
            }
        });
    });

    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-theme']
    });

    if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateFavicon);
    }
})();
