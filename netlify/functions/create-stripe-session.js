const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const { createClient } = require('@supabase/supabase-js');

exports.handler = async (event) => {
    if (event.httpMethod !== 'POST') {
        return { statusCode: 405, body: 'Method Not Allowed' };
    }

    try {
        const { date, flightType, pax, passengers, customer, total } = JSON.parse(event.body);
        
        const supabaseUrl = process.env.SUPABASE_URL;
        const supabaseKey = process.env.SUPABASE_KEY;
        const hostUrl = process.env.URL || 'http://localhost:8888';

        // 1. Create booking in Supabase
        let bookingId = null;
        if (supabaseUrl && supabaseKey) {
            const supabase = createClient(supabaseUrl, supabaseKey);
            const { data, error } = await supabase
                .from('bookings')
                .insert([{
                    customer_name: customer.name,
                    customer_email: customer.email,
                    customer_phone: customer.phone,
                    flight_date: date,
                    flight_type: flightType,
                    pax_count: pax,
                    passengers: passengers,
                    total_amount: total,
                    status: 'pending',
                    payment_method: 'stripe'
                }])
                .select();

            if (error) throw error;
            bookingId = data[0].id;
        }

        // 2. Create Stripe Checkout Session
        const session = await stripe.checkout.sessions.create({
            payment_method_types: ['card'],
            line_items: [
                {
                    price_data: {
                        currency: 'eur',
                        product_data: {
                            name: `Vuelo en Globo: ${flightType.toUpperCase()}`,
                            description: `Fecha: ${date} - ${pax} pasajeros`,
                        },
                        unit_amount: Math.round(total * 100),
                    },
                    quantity: 1,
                },
            ],
            mode: 'payment',
            success_url: `${hostUrl}/exito.html?session_id={CHECKOUT_SESSION_ID}`,
            cancel_url: `${hostUrl}/#booking`,
            customer_email: customer.email,
            client_reference_id: bookingId ? bookingId.toString() : null,
            metadata: {
                booking_id: bookingId,
                flight_date: date,
                pax_count: pax
            }
        });

        return {
            statusCode: 200,
            body: JSON.stringify({ id: session.id, url: session.url }),
        };
    } catch (error) {
        console.error('Stripe Error:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: error.message }),
        };
    }
};
