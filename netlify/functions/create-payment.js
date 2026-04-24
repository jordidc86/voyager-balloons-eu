const crypto = require('crypto');
const { createClient } = require('@supabase/supabase-js');

// Helper to base64url encode without padding
function base64Encode(string) {
    return Buffer.from(string, 'utf-8').toString('base64');
}

function generateRedsysSignature(orderId, merchantParamsBase64, secretKeyBase64) {
    try {
        // 1. Decode secret key
        const key = Buffer.from(secretKeyBase64, 'base64');
        
        // 2. Derive order key using 3DES
        const iv = Buffer.alloc(8, 0);
        const cipher = crypto.createCipheriv('des-ede3-cbc', key, iv);
        cipher.setAutoPadding(false);
        
        let paddedOrderId = Buffer.from(orderId, 'utf8');
        const paddingLength = 8 - (paddedOrderId.length % 8);
        if (paddingLength !== 8) {
            paddedOrderId = Buffer.concat([paddedOrderId, Buffer.alloc(paddingLength, 0)]);
        }
        
        const derivedKey = Buffer.concat([cipher.update(paddedOrderId), cipher.final()]);
        
        // 3. Generate HMAC SHA256 MAC
        const hmac = crypto.createHmac('sha256', derivedKey);
        hmac.update(merchantParamsBase64);
        
        // 4. Base64 encode
        return hmac.digest('base64');
    } catch (e) {
        console.error('Error generating signature:', e);
        throw new Error('Signature generation failed');
    }
}

exports.handler = async (event, context) => {
    // Only allow POST requests
    if (event.httpMethod !== 'POST') {
        return { statusCode: 405, body: 'Method Not Allowed' };
    }

    try {
        const body = JSON.parse(event.body);
        const { customerName, customerEmail, customerPhone, flightType, date, pax, total } = body;

        if (!customerName || !customerEmail || !flightType || !date || !total) {
            return { statusCode: 400, body: JSON.stringify({ error: 'Missing required fields' }) };
        }

        // 1. Setup Supabase
        const supabaseUrl = process.env.SUPABASE_URL;
        const supabaseKey = process.env.SUPABASE_KEY;
        
        // Generate a unique order ID for Redsys (Must be up to 12 chars, alphanumeric)
        // Format: VB + timestamp (last 8 digits) + 2 random chars = 12 chars
        const timestamp = Date.now().toString().slice(-8);
        const randomStr = Math.random().toString(36).substring(2, 4).toUpperCase();
        const orderId = `VB${timestamp}${randomStr}`;

        // Create booking record if Supabase is configured
        if (supabaseUrl && supabaseKey) {
            const supabase = createClient(supabaseUrl, supabaseKey);
            const { error } = await supabase
                .from('bookings')
                .insert([{
                    order_id: orderId,
                    customer_name: customerName,
                    customer_email: customerEmail,
                    customer_phone: customerPhone,
                    flight_type: flightType,
                    flight_date: date,
                    pax: pax,
                    total_price: total,
                    status: 'pending'
                }]);
            
            if (error) console.error('Supabase Error:', error);
        } else {
            console.warn('Supabase not configured, skipping DB insert');
        }

        // 2. Setup Redsys Parameters
        const merchantCode = process.env.REDSYS_MERCHANT_CODE || '999008881'; // Default test FUC
        const terminal = process.env.REDSYS_TERMINAL || '1';
        const secretKey = process.env.REDSYS_SECRET_KEY || 'sq7HjrUOBfKmC576ILgskD5srU870gJ7'; // Default test key
        const currency = '978'; // Euros
        const transactionType = '0'; // Authorization
        
        // Convert total to cents for Redsys
        const amountCents = Math.round(total * 100).toString();
        
        const hostUrl = process.env.URL || 'http://localhost:8888';

        const merchantParameters = {
            DS_MERCHANT_AMOUNT: amountCents,
            DS_MERCHANT_ORDER: orderId,
            DS_MERCHANT_MERCHANTCODE: merchantCode,
            DS_MERCHANT_CURRENCY: currency,
            DS_MERCHANT_TRANSACTIONTYPE: transactionType,
            DS_MERCHANT_TERMINAL: terminal,
            DS_MERCHANT_MERCHANTURL: `${hostUrl}/.netlify/functions/redsys-webhook`,
            DS_MERCHANT_URLOK: `${hostUrl}/exito.html`,
            DS_MERCHANT_URLKO: `${hostUrl}/error.html`
        };

        const merchantParamsJson = JSON.stringify(merchantParameters);
        const merchantParamsBase64 = base64Encode(merchantParamsJson);

        const signature = generateRedsysSignature(orderId, merchantParamsBase64, secretKey);

        return {
            statusCode: 200,
            body: JSON.stringify({
                merchantParameters: merchantParamsBase64,
                signature: signature,
                signatureVersion: 'HMAC_SHA256_V1',
                orderId: orderId,
                redsysUrl: process.env.REDSYS_ENV === 'live' 
                    ? 'https://sis.redsys.es/sis/realizarPago' 
                    : 'https://sis-t.redsys.es/sis/realizarPago'
            })
        };

    } catch (error) {
        console.error('Error creating payment:', error);
        return {
            statusCode: 500,
            body: JSON.stringify({ error: 'Internal Server Error' })
        };
    }
};
