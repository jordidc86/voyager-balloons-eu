/**
 * Voyager Balloons EU - Main JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    const navbar = document.getElementById('navbar');
    const navToggle = document.querySelector('.nav-toggle');
    const navLinks = document.querySelector('.nav-links');

    const toggleNavbarState = () => {
        if (!navbar) return;
        if (window.scrollY > 50 || navbar.classList.contains('nav-open')) navbar.classList.add('scrolled');
        else navbar.classList.remove('scrolled');
    };

    window.addEventListener('scroll', () => window.requestAnimationFrame(toggleNavbarState));
    toggleNavbarState();

    const closeNavigation = () => {
        if (!navbar || !navToggle) return;
        navbar.classList.remove('nav-open');
        navToggle.setAttribute('aria-expanded', 'false');
        navToggle.setAttribute('aria-label', 'Abrir menú');
        toggleNavbarState();
    };

    if (navbar && navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            const isOpen = navbar.classList.toggle('nav-open');
            navToggle.setAttribute('aria-expanded', String(isOpen));
            navToggle.setAttribute('aria-label', isOpen ? 'Cerrar menú' : 'Abrir menú');
            toggleNavbarState();
        });

        navLinks.querySelectorAll('a').forEach(link => {
            link.addEventListener('click', closeNavigation);
        });

        document.addEventListener('keydown', event => {
            if (event.key === 'Escape') closeNavigation();
        });
    }

    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;

            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        });
    });

    document.querySelectorAll('.faq-item').forEach(item => {
        const question = item.querySelector('.faq-question');
        if (!question) return;

        question.addEventListener('click', () => {
            const isActive = item.classList.contains('active');
            document.querySelectorAll('.faq-item').forEach(otherItem => {
                otherItem.classList.remove('active');
                const answer = otherItem.querySelector('.faq-answer');
                if (answer) answer.style.maxHeight = null;
            });

            if (!isActive) {
                item.classList.add('active');
                const answer = item.querySelector('.faq-answer');
                if (answer) answer.style.maxHeight = `${answer.scrollHeight}px`;
            }
        });
    });

    const fadeInObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            }
        });
    }, {
        root: null,
        rootMargin: '0px 0px -50px 0px',
        threshold: 0.1
    });

    document.querySelectorAll('.fade-in, .slide-up').forEach(element => {
        fadeInObserver.observe(element);
    });

    const cookieBanner = document.querySelector('.cookie-banner');
    const reviewsConsentNote = document.querySelector('.reviews-consent-note');
    const cookieScripts = document.querySelectorAll('script[data-cookie-src]');
    const consentKey = 'voyagerCookieConsent';

    const setCookieBannerVisible = isVisible => {
        document.body.classList.toggle('cookie-visible', isVisible);
        if (cookieBanner) cookieBanner.hidden = !isVisible;
    };

    const loadThirdPartyScripts = () => {
        cookieScripts.forEach(scriptPlaceholder => {
            if (scriptPlaceholder.dataset.loaded === 'true') return;

            const script = document.createElement('script');
            script.src = scriptPlaceholder.dataset.cookieSrc;
            if (scriptPlaceholder.dataset.cookieDefer === 'true') script.defer = true;
            document.body.appendChild(script);
            scriptPlaceholder.dataset.loaded = 'true';
        });

        if (reviewsConsentNote) reviewsConsentNote.hidden = true;
    };

    const applyCookieChoice = choice => {
        window.localStorage.setItem(consentKey, choice);
        setCookieBannerVisible(false);
        if (choice === 'accept') loadThirdPartyScripts();
    };

    if (cookieBanner && cookieScripts.length > 0) {
        const storedChoice = window.localStorage.getItem(consentKey);

        if (storedChoice === 'accept') {
            setCookieBannerVisible(false);
            loadThirdPartyScripts();
        } else if (storedChoice === 'reject') {
            setCookieBannerVisible(false);
        } else {
            setCookieBannerVisible(true);
        }

        cookieBanner.querySelectorAll('[data-cookie-choice]').forEach(button => {
            button.addEventListener('click', () => applyCookieChoice(button.dataset.cookieChoice));
        });
    }
});
