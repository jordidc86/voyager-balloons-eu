const crypto = require('crypto');
const { createClient } = require('@supabase/supabase-js');

// Helper to decode Base64url (Redsys sometimes uses base64url)
function base64urlDecode(str) {
    let base64 = str.replace(/-/g, '+').replace(/_/g, '/');
    while (base64.length % 4) {
        base64 += '=';
    }
    return Buffer.from(base64, 'base64').toString('utf8');
}

function generateExpectedSignature(orderId, merchantParamsBase64, secretKeyBase64) {
    try {
        const key = Buffer.from(secretKeyBase64, 'base64');
        const iv = Buffer.alloc(8, 0);
        const cipher = crypto.createCipheriv('des-ede3-cbc', key, iv);
        cipher.setAutoPadding(false);
        
        let paddedOrderId = Buffer.from(orderId, 'utf8');
        const paddingLength = 8 - (paddedOrderId.length % 8);
        if (paddingLength !== 8) {
            paddedOrderId = Buffer.concat([paddedOrderId, Buffer.alloc(paddingLength, 0)]);
        }
        
        const derivedKey = Buffer.concat([cipher.update(paddedOrderId), cipher.final()]);
        const hmac = crypto.createHmac('sha256', derivedKey);
        hmac.update(merchantParamsBase64);
        
        // Redsys webhook signature is Base64url encoded
        return hmac.digest('base64').replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
    } catch (e) {
        return null;
    }
}

exports.handler = async (event, context) => {
    if (event.httpMethod !== 'POST') {
        return { statusCode: 405, body: 'Method Not Allowed' };
    }

    try {
        let bodyParams;
        
        // Netlify forms are usually url-encoded or multipart
        if (event.isBase64Encoded) {
            const decodedBody = Buffer.from(event.body, 'base64').toString('utf8');
            bodyParams = new URLSearchParams(decodedBody);
        } else {
            bodyParams = new URLSearchParams(event.body);
        }

        const merchantParametersBase64 = bodyParams.get('Ds_MerchantParameters');
        const receivedSignature = bodyParams.get('Ds_Signature');

        if (!merchantParametersBase64 || !receivedSignature) {
            console.error('Missing Redsys parameters in webhook');
            return { statusCode: 400, body: 'Missing parameters' };
        }

        // Decode merchant parameters to get the order ID and response code
        const merchantParametersJson = base64urlDecode(merchantParametersBase64);
        const merchantParams = JSON.parse(merchantParametersJson);
        
        const orderId = merchantParams.Ds_Order;
        const responseCode = merchantParams.Ds_Response;
        
        // Validate signature
        const secretKey = process.env.REDSYS_SECRET_KEY || 'sq7HjrUOBfKmC576ILgskD5srU870gJ7'; // Default test key
        const expectedSignature = generateExpectedSignature(orderId, merchantParametersBase64, secretKey);

        if (expectedSignature !== receivedSignature) {
            console.error('Redsys signature mismatch! Potential fraud attempt.');
            return { statusCode: 400, body: 'Invalid signature' };
        }

        // Payment is considered successful if response code is between 0000 and 0099
        const isSuccess = parseInt(responseCode, 10) >= 0 && parseInt(responseCode, 10) <= 99;

        // Update Supabase
        const supabaseUrl = process.env.SUPABASE_URL;
        const supabaseKey = process.env.SUPABASE_KEY;
        
        if (supabaseUrl && supabaseKey) {
            const supabase = createClient(supabaseUrl, supabaseKey);
            
            const newStatus = isSuccess ? 'paid' : 'failed';
            
            const { error } = await supabase
                .from('bookings')
                .update({ 
                    status: newStatus,
                    redsys_response: responseCode
                })
                .eq('order_id', orderId);
                
            if (error) {
                console.error('Error updating Supabase booking:', error);
            } else {
                console.log(`Booking ${orderId} updated to ${newStatus}`);
            }
        }

        return { statusCode: 200, body: 'OK' };
    } catch (error) {
        console.error('Error processing Redsys webhook:', error);
        return { statusCode: 500, body: 'Internal Server Error' };
    }
};
