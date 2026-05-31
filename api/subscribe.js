// api/subscribe.js — Vercel Serverless Function
// The RESEND_API_KEY environment variable is set in the Vercel dashboard
// and is NEVER exposed to the browser.

export default async function handler(req, res) {
  // Only allow POST
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  const { email } = req.body;

  if (!email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
    return res.status(400).json({ error: 'A valid email address is required.' });
  }

  const apiKey = process.env.RESEND_API_KEY;
  if (!apiKey) {
    console.error('RESEND_API_KEY is not set');
    return res.status(500).json({ error: 'Server configuration error.' });
  }

  try {
    const resendRes = await fetch('https://api.resend.com/emails', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${apiKey}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        from: 'Syncberg <onboarding@resend.dev>',
        to: ['support@syncberg.com'],
        subject: `🎉 New Beta Signup — ${email}`,
        html: `
          <div style="font-family:Inter,sans-serif;max-width:560px;margin:0 auto;padding:32px;background:#f5f2ec;border-radius:12px;">
            <h2 style="color:#161b2e;margin:0 0 8px;">New Beta Signup</h2>
            <p style="color:#5a6070;margin:0 0 24px;">Someone just joined the Syncberg beta waitlist.</p>
            <table style="width:100%;border-collapse:collapse;">
              <tr>
                <td style="padding:10px 0;color:#6b7280;font-size:14px;">Email</td>
                <td style="padding:10px 0;color:#161b2e;font-weight:600;font-size:14px;">${email}</td>
              </tr>
              <tr>
                <td style="padding:10px 0;color:#6b7280;font-size:14px;">Time</td>
                <td style="padding:10px 0;color:#161b2e;font-size:14px;">${new Date().toUTCString()}</td>
              </tr>
            </table>
            <hr style="border:none;border-top:1px solid #e2e0da;margin:24px 0;"/>
            <p style="color:#9ca3af;font-size:12px;margin:0;">Sent automatically by the Syncberg beta signup form.</p>
          </div>
        `,
      }),
    });

    if (!resendRes.ok) {
      const err = await resendRes.json().catch(() => ({}));
      console.error('Resend error:', err);
      return res.status(resendRes.status).json({ error: err.message || 'Failed to send email.' });
    }

    return res.status(200).json({ success: true });
  } catch (err) {
    console.error('Unexpected error:', err);
    return res.status(500).json({ error: 'Internal server error.' });
  }
}
