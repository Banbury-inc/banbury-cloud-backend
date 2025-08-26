# Twilio SendGrid Email Integration Setup

This document explains how to set up Twilio SendGrid for sending welcome emails to new users.

## Prerequisites

1. A Twilio SendGrid account (free tier available)
2. A verified sender email address in SendGrid

## Setup Steps

### 1. Create a SendGrid Account

1. Go to [SendGrid](https://sendgrid.com/) and create an account
2. Complete the account verification process

### 2. Create an API Key

1. In your SendGrid dashboard, go to Settings > API Keys
2. Click "Create API Key"
3. Choose "Restricted Access" and give it a name like "Banbury Email Service"
4. Grant the following permissions:
   - Mail Send: Full Access
   - Template Engine: Read Access (if you plan to use templates)
5. Copy the generated API key (you won't be able to see it again)

### 3. Verify Your Sender Email

1. In SendGrid dashboard, go to Settings > Sender Authentication
2. Choose "Single Sender Verification" (easier for development)
3. Add your email address and complete verification
4. Alternatively, you can set up domain authentication for production

### 4. Set Environment Variables

Add the following environment variables to your deployment environment:

```bash
# Required
SENDGRID_API_KEY=your_api_key_here

# Optional (with defaults)
SENDGRID_FROM_EMAIL=noreply@yourdomain.com
SENDGRID_FROM_NAME=Banbury
SENDGRID_BCC_EMAIL=admin@yourdomain.com  # Email to BCC on all outgoing emails
```

### 5. Install Dependencies

The SendGrid Python package has already been added to `requirements.txt`. Install it with:

```bash
pip install -r requirements.txt
```

## Configuration

The email service is configured in `apps/authentication/email_service.py` and automatically reads the environment variables:

- `SENDGRID_API_KEY`: Your SendGrid API key (required)
- `SENDGRID_FROM_EMAIL`: The email address to send from (defaults to michael.mills@banbury.io)
- `SENDGRID_FROM_NAME`: The name to display as sender (defaults to Michael Mills)
- `SENDGRID_BCC_EMAIL`: Email address to BCC on all outgoing emails (defaults to michael.mills@banbury.io)

## How It Works

1. When a user registers through the `/authentication/register/` endpoint
2. The system creates the user account in MongoDB
3. If an email address is provided, a welcome email is automatically sent
4. The email includes the user's account details and a professional welcome message
5. A BCC copy is automatically sent to the configured admin email for monitoring

## BCC Functionality

All outgoing emails automatically include a BCC to the configured admin email address. This allows you to:
- Monitor all emails being sent from the system
- Keep a record of user communications
- Debug email issues
- Ensure email delivery is working properly

The BCC email is only added if:
- `SENDGRID_BCC_EMAIL` is configured
- The BCC email is different from the recipient's email (prevents duplicate emails)

## Email Templates

The system currently uses SendGrid dynamic templates:

### Welcome Email Template
- **Template ID**: `d-f532cd6b475a437dab553dfea64ac8a6`
- Sent when a new user creates an account
- Uses dynamic template data with the following variables:
  - `first_name`: User's first name
  - `last_name`: User's last name  
  - `full_name`: User's full name (first + last)
  - `username`: User's username
  - `email`: User's email address

### Password Reset Email (ready for future use)
- Template ready for password reset functionality
- Includes secure reset link with expiration
- Currently uses hardcoded HTML (can be converted to template)

## Error Handling

- Email sending failures won't prevent user registration
- Errors are logged for debugging
- If SendGrid API key is not configured, the service gracefully disables email functionality

## Testing

To test the email integration:

1. Set up your SendGrid account and API key
2. Configure the environment variables
3. Register a new user through the frontend
4. Check that the welcome email is received

## Production Considerations

1. **Domain Authentication**: Set up domain authentication instead of single sender verification
2. **Rate Limiting**: Consider SendGrid's rate limits for your plan
3. **Monitoring**: Set up monitoring for email delivery rates
4. **Templates**: Consider using SendGrid templates for more complex email designs
5. **Compliance**: Ensure compliance with email regulations (CAN-SPAM, GDPR, etc.)

## Troubleshooting

### Common Issues

1. **API Key not working**: Ensure the API key has the correct permissions
2. **Emails not sending**: Check that the sender email is verified
3. **Emails going to spam**: Implement domain authentication and SPF/DKIM records

### Debug Logs

Email sending events are logged with the following format:
- Success: "Welcome email sent successfully to [email]"
- Failure: "Failed to send welcome email to [email]"
- Errors: "Error sending welcome email to [email]: [error details]"

## Cost Considerations

- SendGrid free tier: 100 emails/day
- Paid plans start at $14.95/month for higher volumes
- Monitor your usage through the SendGrid dashboard
