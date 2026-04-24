/**
 * Voyager Balloons EU - Main JavaScript
 * Focus on non-blocking performance and native Web APIs
 */

document.addEventListener('DOMContentLoaded', () => {
    
    // ==========================================================================
    // 1. Sticky Navbar Logic
    // ==========================================================================
    const navbar = document.getElementById('navbar');
    
    const toggleNavbarState = () => {
        if (window.scrollY > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    };

    // Initial check and scroll event listener
    toggleNavbarState();
    window.addEventListener('scroll', () => {
        // Use requestAnimationFrame for performance
        window.requestAnimationFrame(toggleNavbarState);
    });

    // ==========================================================================
    // 2. Scroll Animations (Intersection Observer)
    // ==========================================================================
    // Configure observer options
    const observerOptions = {
        root: null, // viewport
        rootMargin: '0px 0px -50px 0px', // Trigger slightly before the element hits the bottom
        threshold: 0.1 // Trigger when 10% of the element is visible
    };

    // Create the observer
    const fadeInObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Add the animation class
                entry.target.classList.add('is-visible');
                // Unobserve after animating to improve performance
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Select elements to animate and observe them
    const elementsToAnimate = document.querySelectorAll('.fade-in');
    elementsToAnimate.forEach(element => {
        fadeInObserver.observe(element);
    });

    // ==========================================================================
    // 3. Smooth Scrolling for Navigation Links
    // ==========================================================================
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            const targetId = this.getAttribute('href');
            
            // Skip if it's just "#"
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

});
