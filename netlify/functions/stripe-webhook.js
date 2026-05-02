const stripe = require('stripe')(process.env.STRIPE_SECRET_KEY);
const { createClient } = require('@supabase/supabase-js');

exports.handler = async (event) => {
    const sig = event.headers['stripe-signature'];
    const endpointSecret = process.env.STRIPE_WEBHOOK_SECRET;

    let stripeEvent;

    try {
        stripeEvent = stripe.webhooks.constructEvent(event.body, sig, endpointSecret);
    } catch (err) {
        console.error(`Webhook Error: ${err.message}`);
        return { statusCode: 400, body: `Webhook Error: ${err.message}` };
    }

    if (stripeEvent.type === 'checkout.session.completed') {
        const session = stripeEvent.data.object;
        const bookingId = session.client_reference_id || session.metadata.booking_id;

        if (bookingId) {
            const supabaseUrl = process.env.SUPABASE_URL;
            const supabaseKey = process.env.SUPABASE_KEY;
            const supabase = createClient(supabaseUrl, supabaseKey);

            const { error } = await supabase
                .from('bookings')
                .update({ status: 'paid', stripe_session_id: session.id })
                .eq('id', bookingId);

            if (error) {
                console.error('Supabase Update Error:', error);
                return { statusCode: 500, body: 'Database error' };
            }
        }
    }

    return {
        statusCode: 200,
        body: JSON.stringify({ received: true }),
    };
};
