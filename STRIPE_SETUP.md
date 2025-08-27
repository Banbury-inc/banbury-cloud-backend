# Stripe Integration Setup Guide

This guide will help you set up Stripe for subscription billing in your application.

## 1. Stripe Account Setup

1. Create a Stripe account at https://stripe.com
2. Get your API keys from the Stripe Dashboard
3. Set up a product and price for the Pro subscription

## 2. Environment Variables

Add these environment variables to your `.env` file:

```bash
STRIPE_SECRET_KEY=sk_test_...  # Your Stripe secret key
STRIPE_PUBLISHABLE_KEY=pk_test_...  # Your Stripe publishable key
STRIPE_WEBHOOK_SECRET=whsec_...  # Webhook endpoint secret
```

## 3. Stripe Product Setup

1. Go to your Stripe Dashboard
2. Navigate to Products
3. Create a new product called "Pro Plan"
4. Add a recurring price:
   - Amount: $10.00
   - Billing: Monthly
   - Currency: USD
5. Copy the Price ID (starts with `price_`)

## 4. Price ID Configuration

The price ID is already configured in `Banbury-Website/frontend/src/pages/Pricing.tsx`:

```javascript
const response = await ApiService.post('/billing/create-checkout-session/', {
  price_id: 'price_1S0mgfJ2ajHEyFo7q8TEcrO1', // Your Stripe price ID
  success_url: `${window.location.origin}/dashboard?success=true`,
  cancel_url: `${window.location.origin}/pricing?canceled=true`
});
```

**Note**: This price ID corresponds to your $10/month Pro subscription in Stripe.

## 5. Webhook Setup

1. In your Stripe Dashboard, go to Webhooks
2. Add endpoint: `https://yourdomain.com/billing/stripe-webhook/`
3. Select these events:
   - `checkout.session.completed`
   - `customer.subscription.created`
   - `customer.subscription.updated`
   - `customer.subscription.deleted`
4. Copy the webhook signing secret and add it to your environment variables

## 6. Testing

1. Use Stripe test cards for testing:
   - Success: `4242 4242 4242 4242`
   - Decline: `4000 0000 0000 0002`
2. Test the complete flow:
   - User clicks "Get Pro"
   - Redirected to Stripe Checkout
   - Completes payment
   - Redirected back to dashboard
   - User subscription updated to "pro"

## 7. Production Deployment

1. Switch to live Stripe keys
2. Update webhook endpoint to production URL
3. Test with real payment methods
4. Monitor webhook events in Stripe Dashboard

## 8. Subscription Management

The system automatically handles:
- Subscription creation
- Subscription updates
- Subscription cancellation
- User status updates in MongoDB

## 9. Error Handling

The integration includes error handling for:
- Authentication failures
- Stripe API errors
- Webhook signature verification
- Database connection issues

## 10. Security Notes

- Never expose your secret key in frontend code
- Always verify webhook signatures
- Use HTTPS in production
- Monitor webhook events for security
