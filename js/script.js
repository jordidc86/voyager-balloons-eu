/**
 * Voyager Balloons EU - Main JavaScript
 * Focus on non-blocking performance and native Web APIs
 */

// Booking Wizard Logic
let currentStep = 1;
let bookingData = {
    date: '',
    flightType: 'classic',
    flightName: 'Classic Adventure',
    pricePerPax: 120,
    pax: 1,
    total: 120
};

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

    // Initialize Calendar
    const calendar = flatpickr("#booking-calendar", {
        inline: true,
        minDate: "today",
        dateFormat: "Y-m-d",
        onChange: function(selectedDates, dateStr) {
            bookingData.date = dateStr;
            updateSummary();
        }
    });

    // Flight Option Selection
    const options = document.querySelectorAll('.flight-option');
    options.forEach(opt => {
        opt.addEventListener('click', () => {
            options.forEach(o => o.classList.remove('active'));
            opt.classList.add('active');
            
            bookingData.flightType = opt.dataset.type;
            bookingData.flightName = opt.querySelector('h4').innerText;
            bookingData.pricePerPax = parseInt(opt.dataset.price);
            
            updateSummary();
        });
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

function updatePax(delta) {
    const newPax = bookingData.pax + delta;
    if (newPax >= 1 && newPax <= 20) {
        bookingData.pax = newPax;
        document.getElementById('pax-display').innerText = newPax;
        updateSummary();
    }
}

function updateSummary() {
    bookingData.total = bookingData.pricePerPax * bookingData.pax;
    
    // Update Step 3 Summary
    const summaryFlight = document.getElementById('summary-flight');
    const summaryDate = document.getElementById('summary-date');
    const summaryPax = document.getElementById('summary-pax');
    const summaryTotal = document.getElementById('summary-total');

    if(summaryFlight) summaryFlight.innerText = bookingData.flightName;
    if(summaryDate) summaryDate.innerText = bookingData.date || 'Selecciona una fecha';
    if(summaryPax) summaryPax.innerText = bookingData.pax;
    if(summaryTotal) summaryTotal.innerText = bookingData.total + '€';
}

function nextStep(step) {
    if (step === 2 && !bookingData.date) {
        alert('Por favor, selecciona una fecha para continuar.');
        return;
    }
    
    if (step === 3) {
        const name = document.getElementById('cust-name').value;
        const email = document.getElementById('cust-email').value;
        if (!name || !email) {
            alert('Por favor, completa tus datos de contacto.');
            return;
        }
    }

    // Switch screens
    document.querySelectorAll('.wizard-content').forEach(c => c.classList.remove('active'));
    const targetStep = document.getElementById(`step-${step}`);
    if(targetStep) targetStep.classList.add('active');
    
    // Update progress bar
    document.querySelectorAll('.progress-step').forEach(s => {
        if (parseInt(s.dataset.step) <= step) s.classList.add('active');
        else s.classList.remove('active');
    });
    
    currentStep = step;
    const bookingSection = document.getElementById('booking');
    if(bookingSection) window.scrollTo({ top: bookingSection.offsetTop - 100, behavior: 'smooth' });
}

function prevStep(step) {
    nextStep(step);
}

function initiateRedsysPayment() {
    const payBtn = document.getElementById('pay-button');
    if(!payBtn) return;
    
    payBtn.innerText = 'Conectando con TPV Seguro...';
    payBtn.disabled = true;

    // Simulación de proceso Redsys
    console.log('Iniciando pago Redsys para:', bookingData);
    
    setTimeout(() => {
        alert('Simulación: Redirigiendo a la pasarela de Redsys TPV...\n\nEn producción, aquí llamaríamos a la Netlify Function que genera la firma HMAC SHA-256.');
        payBtn.innerText = 'Pagar con Tarjeta / Apple Pay';
        payBtn.disabled = false;
    }, 1500);
}
