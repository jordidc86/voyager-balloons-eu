-- Create bookings table for Voyager Balloons
CREATE TABLE IF NOT EXISTS public.bookings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    order_id TEXT UNIQUE NOT NULL,
    customer_name TEXT NOT NULL,
    customer_email TEXT NOT NULL,
    customer_phone TEXT,
    flight_type TEXT NOT NULL,
    flight_date TEXT NOT NULL,
    pax INTEGER NOT NULL,
    total_price NUMERIC NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'paid', 'failed', 'cancelled')),
    redsys_response TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Enable RLS
ALTER TABLE public.bookings ENABLE ROW LEVEL SECURITY;

-- Allow anonymous inserts (for the booking form)
CREATE POLICY "Allow anonymous inserts" ON public.bookings
    FOR INSERT WITH CHECK (true);

-- Allow service role to manage all
CREATE POLICY "Service role full access" ON public.bookings
    FOR ALL USING (true);
