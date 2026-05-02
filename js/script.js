/**
 * Voyager Balloons EU - Main JavaScript
 */

let currentStep = 1;
let bookingData = {
    date: '',
    flightType: 'classic',
    flightName: 'Classic Adventure',
    pricePerPax: 120,
    pax: 1,
    total: 120,
    isTestDiscount: false
};

document.addEventListener('DOMContentLoaded', () => {
    // 1. Sticky Navbar
    const navbar = document.getElementById('navbar');
    const toggleNavbarState = () => {
        if (window.scrollY > 50) navbar.classList.add('scrolled');
        else navbar.classList.remove('scrolled');
    };
    window.addEventListener('scroll', () => window.requestAnimationFrame(toggleNavbarState));
    toggleNavbarState();

    // 2. Initialize Calendar (Spanish, Monday start)
    if (document.getElementById('booking-calendar')) {
        flatpickr("#booking-calendar", {
            locale: "es",
            minDate: "today",
            inline: true,
            dateFormat: "Y-m-d",
            "locale": { "firstDayOfWeek": 1 },
            onChange: function(selectedDates, dateStr) {
                document.getElementById('selected-date').value = dateStr;
                bookingData.date = dateStr;
                updateSummary();
            }
        });
    }

    // 3. Flight Option Selection
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

    // 4. Smooth Scrolling
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

    // 5. FAQ Accordion
    const faqItems = document.querySelectorAll('.faq-item');
    faqItems.forEach(item => {
        const question = item.querySelector('.faq-question');
        question.addEventListener('click', () => {
            const isActive = item.classList.contains('active');
            faqItems.forEach(oi => {
                oi.classList.remove('active');
                oi.querySelector('.faq-answer').style.maxHeight = null;
            });
            if (!isActive) {
                item.classList.add('active');
                const answer = item.querySelector('.faq-answer');
                answer.style.maxHeight = answer.scrollHeight + "px";
            }
        });
    });

    // 6. Scroll Animations (Intersection Observer)
    const observerOptions = {
        root: null,
        rootMargin: '0px 0px -50px 0px',
        threshold: 0.1
    };

    const fadeInObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-visible');
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    document.querySelectorAll('.fade-in, .slide-up').forEach(element => {
        fadeInObserver.observe(element);
    });

    // Initial UI Setup
    renderPassengerFields();
    updateSummary();
});

function updatePax(delta) {
    const newPax = bookingData.pax + delta;
    if (newPax >= 1 && newPax <= 20) {
        bookingData.pax = newPax;
        document.getElementById('pax-display').innerText = newPax;
        updateSummary();
        renderPassengerFields();
    }
}

function renderPassengerFields() {
    const container = document.getElementById('passenger-details-container');
    if (!container) return;
    
    // Save current values to avoid losing them on re-render
    const currentData = [];
    for (let i = 0; i < 20; i++) {
        const nInput = document.getElementById(`pax-name-${i}`);
        const wInput = document.getElementById(`pax-weight-${i}`);
        if (nInput) currentData[i] = { name: nInput.value, weight: wInput.value };
    }

    container.innerHTML = `<h4 style="margin: 1.5rem 0 1rem;">Detalles de los Pasajeros</h4>`;
    
    for (let i = 0; i < bookingData.pax; i++) {
        const row = document.createElement('div');
        row.className = 'form-row';
        row.innerHTML = `
            <div class="form-group">
                <label>Nombre Pasajero ${i + 1}</label>
                <input type="text" id="pax-name-${i}" placeholder="Nombre completo" required value="${currentData[i]?.name || ''}">
            </div>
            <div class="form-group">
                <label>Peso Pasajero ${i + 1} (kg)</label>
                <input type="number" id="pax-weight-${i}" placeholder="Ej: 75" required min="10" max="150" value="${currentData[i]?.weight || ''}">
            </div>
        `;
        container.appendChild(row);
    }
}

function updateSummary() {
    if (bookingData.isTestDiscount) bookingData.total = 1;
    else bookingData.total = bookingData.pricePerPax * bookingData.pax;
    
    const dateStr = bookingData.date || 'Selecciona fecha';
    
    // Step 3 Summary
    const sFlight = document.getElementById('summary-flight');
    const sDate = document.getElementById('summary-date');
    const sPax = document.getElementById('summary-pax');
    const sTotal = document.getElementById('summary-total');

    if (sFlight) sFlight.innerText = bookingData.flightName;
    if (sDate) sDate.innerText = dateStr;
    if (sPax) sPax.innerText = bookingData.pax;
    if (sTotal) {
        sTotal.innerText = `${bookingData.total}€`;
        if (bookingData.isTestDiscount) sTotal.innerHTML += ' <small style="color:#27ae60">(Test)</small>';
    }

    // Live Bar Summary
    const lTotal = document.getElementById('live-total');
    const pillDate = document.getElementById('pill-date');
    const pillFlight = document.getElementById('pill-flight');
    const pillPax = document.getElementById('pill-pax');

    if (lTotal) lTotal.innerText = `${bookingData.total}€`;
    if (pillDate) pillDate.innerHTML = `<i class="icon">📅</i> ${dateStr}`;
    if (pillFlight) pillFlight.innerHTML = `<i class="icon">🎈</i> ${bookingData.flightName}`;
    if (pillPax) pillPax.innerHTML = `<i class="icon">👤</i> ${bookingData.pax} pax`;
}

function applyPromoCode() {
    const code = document.getElementById('promo-code').value.trim().toUpperCase();
    const msg = document.getElementById('promo-message');
    if (code === 'VOYAGER1') {
        bookingData.isTestDiscount = true;
        msg.innerText = '¡Código aplicado! (1€ para pruebas)';
        msg.style.color = '#27ae60';
    } else {
        bookingData.isTestDiscount = false;
        msg.innerText = code === '' ? '' : 'Código no válido';
        msg.style.color = '#e74c3c';
    }
    updateSummary();
}

function nextStep(step) {
    if (step === 2 && !bookingData.date) {
        alert("Por favor, selecciona una fecha.");
        return;
    }
    if (step === 3) {
        const name = document.getElementById('cust-name').value;
        const email = document.getElementById('cust-email').value;
        const phone = document.getElementById('cust-phone').value;
        if (!name || !email || !phone) {
            alert("Por favor, completa tus datos de contacto.");
            return;
        }
        for (let i = 0; i < bookingData.pax; i++) {
            if (!document.getElementById(`pax-name-${i}`).value || !document.getElementById(`pax-weight-${i}`).value) {
                alert("Completa los datos de todos los pasajeros.");
                return;
            }
        }
    }

    currentStep = step;
    document.querySelectorAll('.wizard-content').forEach(c => c.classList.remove('active'));
    document.getElementById(`step-${step}`).classList.add('active');
    document.querySelectorAll('.progress-step').forEach(ps => {
        if (parseInt(ps.dataset.step) <= step) ps.classList.add('active');
        else ps.classList.remove('active');
    });

    const wizard = document.querySelector('.booking-wizard');
    if (wizard) {
        const rect = wizard.getBoundingClientRect();
        if (rect.top < 0 || rect.top > 200) window.scrollTo({ top: window.scrollY + rect.top - 80, behavior: 'smooth' });
    }
}

function prevStep(step) {
    nextStep(step);
}

async function initiatePayment() {
    // Defaulting to Stripe for validation as requested
    await initiateStripePayment();
}

async function initiateStripePayment() {
    const btn = document.getElementById('pay-button');
    btn.disabled = true;
    btn.innerText = 'Redirigiendo a Stripe...';

    const passengers = [];
    for (let i = 0; i < bookingData.pax; i++) {
        passengers.push({
            name: document.getElementById(`pax-name-${i}`).value,
            weight: document.getElementById(`pax-weight-${i}`).value
        });
    }

    const payload = {
        date: bookingData.date,
        flightType: bookingData.flightType,
        pax: bookingData.pax,
        passengers: passengers,
        customer: {
            name: document.getElementById('cust-name').value,
            email: document.getElementById('cust-email').value,
            phone: document.getElementById('cust-phone').value
        },
        total: bookingData.total
    };

    try {
        const response = await fetch('/.netlify/functions/create-stripe-session', {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        const session = await response.json();
        if (session.url) window.location.href = session.url;
        else throw new Error(session.error || 'Error en Stripe');
    } catch (err) {
        console.error(err);
        alert('Error: ' + err.message);
        btn.disabled = false;
        btn.innerText = 'Pagar con Tarjeta / Apple Pay';
    }
}
