import stripe
import os
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from pymongo.mongo_client import MongoClient
from rest_framework_simplejwt.tokens import AccessToken
import json

# Configure Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

@csrf_exempt
@require_http_methods(["POST"])
def create_checkout_session(request):
    """Create a Stripe checkout session for subscription."""
    try:
        # Authenticate via Bearer token
        auth_header = request.headers.get('Authorization')
        if not auth_header or ' ' not in auth_header:
            return JsonResponse({'message': 'Authentication required'}, status=401)
        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'message': 'Invalid authentication type'}, status=401)

        try:
            validated = AccessToken(token)
            username = validated.payload.get('username')
            if not username:
                return JsonResponse({'message': 'Invalid token'}, status=401)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=401)

        # Parse request data
        data = json.loads(request.body)
        price_id = data.get('price_id')
        success_url = data.get('success_url')
        cancel_url = data.get('cancel_url')

        if not all([price_id, success_url, cancel_url]):
            return JsonResponse({'message': 'Missing required parameters'}, status=400)

        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]

        # Find user
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({'message': 'User not found'}, status=404)

        # Create Stripe checkout session
        checkout_session = stripe.checkout.Session.create(
            customer_email=user.get('email'),
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': str(user.get('_id')),
                'username': username
            },
            subscription_data={
                'metadata': {
                    'user_id': str(user.get('_id')),
                    'username': username
                }
            }
        )

        return JsonResponse({
            'session_url': checkout_session.url,
            'session_id': checkout_session.id
        })

    except stripe.error.StripeError as e:
        return JsonResponse({'message': f'Stripe error: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def create_payment_intent(request):
    """Create a Stripe payment intent for subscription."""
    try:
        # Authenticate via Bearer token
        auth_header = request.headers.get('Authorization')
        if not auth_header or ' ' not in auth_header:
            return JsonResponse({'message': 'Authentication required'}, status=401)
        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'message': 'Invalid authentication type'}, status=401)

        try:
            validated = AccessToken(token)
            username = validated.payload.get('username')
            if not username:
                return JsonResponse({'message': 'Invalid token'}, status=401)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=401)

        # Parse request data
        data = json.loads(request.body)
        price_id = data.get('price_id')

        if not price_id:
            return JsonResponse({'message': 'Missing price_id parameter'}, status=400)

        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]

        # Find user
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({'message': 'User not found'}, status=404)

        # Create payment intent with specific payment methods
        payment_intent = stripe.PaymentIntent.create(
            amount=1000,  # $10.00 in cents
            currency='usd',
            receipt_email=user.get('email'),
            metadata={
                'user_id': str(user.get('_id')),
                'username': username,
                'price_id': price_id,
                'user_email': user.get('email')
            },
            payment_method_types=[
                'card',
                'link',
                'us_bank_account',
                'cashapp',
                'amazon_pay',
            ]
        )

        return JsonResponse({
            'client_secret': payment_intent.client_secret,
            'payment_intent_id': payment_intent.id
        })

    except stripe.error.StripeError as e:
        return JsonResponse({'message': f'Stripe error: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def create_subscription_intent(request):
    """Create a Stripe subscription for recurring billing."""
    try:
        # Authenticate via Bearer token
        auth_header = request.headers.get('Authorization')
        if not auth_header or ' ' not in auth_header:
            return JsonResponse({'message': 'Authentication required'}, status=401)
        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'message': 'Invalid authentication type'}, status=401)

        try:
            validated = AccessToken(token)
            username = validated.payload.get('username')
            if not username:
                return JsonResponse({'message': 'Invalid token'}, status=401)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=401)

        # Parse request data
        data = json.loads(request.body)
        price_id = data.get('price_id')

        if not price_id:
            return JsonResponse({'message': 'Missing price_id parameter'}, status=400)

        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]

        # Find user
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({'message': 'User not found'}, status=404)

        # Create or get Stripe customer
        stripe_customer_id = user.get('stripe_customer_id')
        if not stripe_customer_id:
            # Create new customer
            customer = stripe.Customer.create(
                email=user.get('email'),
                name=username,
                metadata={
                    'user_id': str(user.get('_id')),
                    'username': username
                }
            )
            stripe_customer_id = customer.id
            
            # Update user with customer ID
            user_collection.update_one(
                {"username": username},
                {"$set": {"stripe_customer_id": stripe_customer_id}}
            )

        # Create subscription with payment intent
        print(f"Creating subscription for user {username} with price {price_id}")
        subscription = stripe.Subscription.create(
            customer=stripe_customer_id,
            items=[{
                'price': price_id,
            }],
            payment_behavior='default_incomplete',
            payment_settings={
                'save_default_payment_method': 'on_subscription',
                'payment_method_types': ['card']
            },
            expand=['latest_invoice.payment_intent'],
            metadata={
                'user_id': str(user.get('_id')),
                'username': username
            }
        )
        
        # Initialize client_secret
        client_secret = None
        
        # If no payment intent was created, create one manually
        if not getattr(subscription.latest_invoice, 'payment_intent', None):
            print("No payment intent in invoice, creating manual payment intent")
            
            # Create a payment intent for the subscription amount
            payment_intent = stripe.PaymentIntent.create(
                amount=subscription.latest_invoice.amount_due,
                currency=subscription.latest_invoice.currency,
                customer=stripe_customer_id,
                metadata={
                    'subscription_id': subscription.id,
                    'invoice_id': subscription.latest_invoice.id,
                    'user_id': str(user.get('_id')),
                    'username': username
                },
                automatic_payment_methods={
                    'enabled': True,
                }
            )
            
            print(f"Manual payment intent created: {payment_intent.id}")
            
            # Store the payment intent client secret
            client_secret = payment_intent.client_secret
            print(f"Using manual payment intent client secret")
        else:
            # Get client secret from existing payment intent in invoice
            payment_intent = getattr(subscription.latest_invoice, 'payment_intent', None)
            print(f"Payment intent exists in invoice: {payment_intent is not None}")
            
            if payment_intent:
                client_secret = getattr(payment_intent, 'client_secret', None)
                print(f"Client secret extracted from invoice: {client_secret is not None}")
            else:
                client_secret = None
                print("No payment intent found in invoice")
        
        print(f"Subscription created: {subscription.id}, status: {subscription.status}")
        print(f"Final client secret available: {client_secret is not None}")
        
        # Update user subscription status immediately (don't wait for webhook)
        try:
            from bson import ObjectId
            import datetime
            
            user_collection.update_one(
                {"username": username},
                {
                    "$set": {
                        "subscription": "pro",
                        "stripe_subscription_id": subscription.id,
                        "stripe_customer_id": stripe_customer_id,
                        "subscription_status": subscription.status,
                        "subscription_created_at": datetime.datetime.utcnow(),
                        "payment_status": "pending" if client_secret else "succeeded"
                    }
                }
            )
            print(f"User subscription updated to pro for {username}")
        except Exception as e:
            print(f"Error updating user subscription: {e}")
        
        response_data = {
            'subscription_id': subscription.id,
            'client_secret': client_secret,
            'status': subscription.status
        }
        print(f"Returning response: {response_data}")
        
        return JsonResponse(response_data)

    except stripe.error.StripeError as e:
        print(f"Stripe error in create_subscription_intent: {str(e)}")
        return JsonResponse({'message': f'Stripe error: {str(e)}'}, status=400)
    except Exception as e:
        print(f"General error in create_subscription_intent: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def stripe_webhook(request):
    """Handle Stripe webhooks for subscription events."""
    try:
        payload = request.body
        sig_header = request.headers.get('stripe-signature')
        endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

        if not endpoint_secret:
            return JsonResponse({'message': 'Webhook secret not configured'}, status=500)

        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, endpoint_secret
            )
        except ValueError as e:
            return JsonResponse({'message': 'Invalid payload'}, status=400)
        except stripe.error.SignatureVerificationError as e:
            return JsonResponse({'message': 'Invalid signature'}, status=400)

        # Handle the event
        if event['type'] == 'checkout.session.completed':
            session = event['data']['object']
            handle_checkout_session_completed(session)
        elif event['type'] == 'customer.subscription.created':
            subscription = event['data']['object']
            handle_subscription_created(subscription)
        elif event['type'] == 'customer.subscription.updated':
            subscription = event['data']['object']
            handle_subscription_updated(subscription)
        elif event['type'] == 'customer.subscription.deleted':
            subscription = event['data']['object']
            handle_subscription_deleted(subscription)
        elif event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            handle_payment_intent_succeeded(payment_intent)
        else:
            print(f'Unhandled event type {event["type"]}')

        return JsonResponse({'status': 'success'})

    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

def handle_checkout_session_completed(session):
    """Handle successful checkout session completion."""
    try:
        user_id = session.get('metadata', {}).get('user_id')
        if user_id:
            # Connect to MongoDB
            uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
            client = MongoClient(uri)
            db = client["NeuraNet"]
            user_collection = db["users"]

            # Update user subscription status
            from bson import ObjectId
            user_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "subscription": "pro",
                        "stripe_customer_id": session.get('customer'),
                        "stripe_subscription_id": session.get('subscription'),
                        "subscription_created_at": session.get('created')
                    }
                }
            )
    except Exception as e:
        print(f"Error handling checkout session completed: {e}")

def handle_subscription_created(subscription):
    """Handle subscription creation."""
    try:
        username = subscription.get('metadata', {}).get('username')
        user_id = subscription.get('metadata', {}).get('user_id')
        
        if username or user_id:
            # Connect to MongoDB
            uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
            client = MongoClient(uri)
            db = client["NeuraNet"]
            user_collection = db["users"]

            # Update user subscription status
            from bson import ObjectId
            import datetime
            
            query = {}
            if user_id:
                query["_id"] = ObjectId(user_id)
            elif username:
                query["username"] = username
                
            user_collection.update_one(
                query,
                {
                    "$set": {
                        "subscription": "pro",
                        "stripe_subscription_id": subscription.get('id'),
                        "stripe_customer_id": subscription.get('customer'),
                        "subscription_status": subscription.get('status'),
                        "subscription_created_at": datetime.datetime.utcnow(),
                        "payment_status": "succeeded"
                    }
                }
            )
            
            print(f"Subscription created for user {username or user_id}: {subscription.get('id')}")
            
    except Exception as e:
        print(f"Error handling subscription created: {e}")

def handle_subscription_updated(subscription):
    """Handle subscription updates."""
    try:
        user_id = subscription.get('metadata', {}).get('user_id')
        if user_id:
            # Connect to MongoDB
            uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
            client = MongoClient(uri)
            db = client["NeuraNet"]
            user_collection = db["users"]

            # Update user subscription status
            from bson import ObjectId
            user_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "subscription_status": subscription.get('status'),
                        "subscription_updated_at": subscription.get('updated')
                    }
                }
            )
    except Exception as e:
        print(f"Error handling subscription updated: {e}")

def handle_subscription_deleted(subscription):
    """Handle subscription cancellation."""
    try:
        user_id = subscription.get('metadata', {}).get('user_id')
        if user_id:
            # Connect to MongoDB
            uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
            client = MongoClient(uri)
            db = client["NeuraNet"]
            user_collection = db["users"]

            # Update user subscription status
            from bson import ObjectId
            user_collection.update_one(
                {"_id": ObjectId(user_id)},
                {
                    "$set": {
                        "subscription": "free",
                        "subscription_status": "canceled",
                        "subscription_canceled_at": subscription.get('canceled_at')
                    }
                }
            )
    except Exception as e:
        print(f"Error handling subscription deleted: {e}")

def handle_payment_intent_succeeded(payment_intent):
    """Handle successful payment intent completion."""
    try:
        user_id = payment_intent.get('metadata', {}).get('user_id')
        username = payment_intent.get('metadata', {}).get('username')
        
        if user_id and username:
            # Connect to MongoDB
            uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
            client = MongoClient(uri)
            db = client["NeuraNet"]
            user_collection = db["users"]

            # Update user subscription status
            from bson import ObjectId
            import datetime
            
            # Get subscription ID from metadata if this was for a subscription
            subscription_id = payment_intent.get('metadata', {}).get('subscription_id')
            
            update_data = {
                "payment_status": "succeeded",
                "stripe_payment_intent_id": payment_intent.get('id'),
                "payment_amount": payment_intent.get('amount'),
                "payment_currency": payment_intent.get('currency'),
                "payment_succeeded_at": datetime.datetime.utcnow(),
                "last_payment_date": datetime.datetime.utcnow()
            }
            
            # Only set subscription to pro if not already set
            # (since we now set it immediately when creating the subscription)
            user = user_collection.find_one({"_id": ObjectId(user_id)})
            if user and user.get('subscription') != 'pro':
                update_data["subscription"] = "pro"
            
            # If this payment was for a subscription, store the subscription ID too
            if subscription_id:
                update_data["stripe_subscription_id"] = subscription_id
                print(f"Payment for subscription {subscription_id} succeeded, activating subscription")
            
            user_collection.update_one(
                {"_id": ObjectId(user_id)},
                {"$set": update_data}
            )
            
            print(f"Payment succeeded for user {username}: {payment_intent.get('id')}")
            
    except Exception as e:
        print(f"Error handling payment intent succeeded: {e}")

@csrf_exempt
@require_http_methods(["GET"])
def check_payment_status(request):
    """Check payment status for a user."""
    try:
        # Authenticate via Bearer token
        auth_header = request.headers.get('Authorization')
        if not auth_header or ' ' not in auth_header:
            return JsonResponse({'message': 'Authentication required'}, status=401)
        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'message': 'Invalid authentication type'}, status=401)

        try:
            validated = AccessToken(token)
            username = validated.payload.get('username')
            if not username:
                return JsonResponse({'message': 'Invalid token'}, status=401)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=401)

        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]

        # Find user
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({'message': 'User not found'}, status=404)

        # Get payment status
        payment_status = user.get('payment_status', 'unknown')
        subscription = user.get('subscription', 'free')
        payment_intent_id = user.get('stripe_payment_intent_id')
        payment_succeeded_at = user.get('payment_succeeded_at')
        
        response_data = {
            'payment_status': payment_status,
            'subscription': subscription,
            'payment_succeeded': payment_status == 'succeeded',
            'stripe_payment_intent_id': payment_intent_id,
            'payment_succeeded_at': payment_succeeded_at.isoformat() if payment_succeeded_at else None
        }

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def verify_payment_intent(request):
    """Verify a payment intent status directly with Stripe."""
    try:
        # Authenticate via Bearer token
        auth_header = request.headers.get('Authorization')
        if not auth_header or ' ' not in auth_header:
            return JsonResponse({'message': 'Authentication required'}, status=401)
        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'message': 'Invalid authentication type'}, status=401)

        try:
            validated = AccessToken(token)
            username = validated.payload.get('username')
            if not username:
                return JsonResponse({'message': 'Invalid token'}, status=401)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=401)

        # Parse request data
        data = json.loads(request.body)
        payment_intent_id = data.get('payment_intent_id')

        if not payment_intent_id:
            return JsonResponse({'message': 'Missing payment_intent_id parameter'}, status=400)

        # Retrieve payment intent from Stripe
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        # Verify this payment intent belongs to the authenticated user
        if payment_intent.metadata.get('username') != username:
            return JsonResponse({'message': 'Payment intent does not belong to user'}, status=403)

        response_data = {
            'payment_intent_id': payment_intent.id,
            'status': payment_intent.status,
            'amount': payment_intent.amount,
            'currency': payment_intent.currency,
            'payment_succeeded': payment_intent.status == 'succeeded',
            'created': payment_intent.created,
            'metadata': payment_intent.metadata
        }

        # If payment succeeded, also update our database
        if payment_intent.status == 'succeeded':
            # Connect to MongoDB
            uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
            client = MongoClient(uri)
            db = client["NeuraNet"]
            user_collection = db["users"]
            
            from bson import ObjectId
            import datetime
            
            user_collection.update_one(
                {"username": username},
                {
                    "$set": {
                        "subscription": "pro",
                        "payment_status": "succeeded",
                        "stripe_payment_intent_id": payment_intent.id,
                        "payment_amount": payment_intent.amount,
                        "payment_currency": payment_intent.currency,
                        "payment_succeeded_at": datetime.datetime.utcnow(),
                        "last_payment_date": datetime.datetime.utcnow()
                    }
                }
            )

        return JsonResponse(response_data)

    except stripe.error.StripeError as e:
        return JsonResponse({'message': f'Stripe error: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def cancel_subscription(request):
    """Cancel a user's subscription."""
    try:
        # Authenticate via Bearer token
        auth_header = request.headers.get('Authorization')
        if not auth_header or ' ' not in auth_header:
            return JsonResponse({'message': 'Authentication required'}, status=401)
        auth_type, token = auth_header.split(' ', 1)
        if auth_type.lower() != 'bearer':
            return JsonResponse({'message': 'Invalid authentication type'}, status=401)

        try:
            validated = AccessToken(token)
            username = validated.payload.get('username')
            if not username:
                return JsonResponse({'message': 'Invalid token'}, status=401)
        except Exception as e:
            return JsonResponse({'message': str(e)}, status=401)

        # Connect to MongoDB
        uri = "mongodb+srv://mmills6060:Dirtballer6060@banbury.fx0xcqk.mongodb.net/?retryWrites=true&w=majority"
        client = MongoClient(uri)
        db = client["NeuraNet"]
        user_collection = db["users"]

        # Find user
        user = user_collection.find_one({"username": username})
        if not user:
            return JsonResponse({'message': 'User not found'}, status=404)

        # Check if user has an active subscription
        subscription_id = user.get('stripe_subscription_id')
        if not subscription_id:
            return JsonResponse({'message': 'No active subscription found'}, status=400)

        # Cancel the subscription in Stripe
        try:
            canceled_subscription = stripe.Subscription.cancel(subscription_id)
            
            # Update user in database
            from bson import ObjectId
            import datetime
            
            user_collection.update_one(
                {"username": username},
                {
                    "$set": {
                        "subscription": "free",
                        "subscription_status": "canceled",
                        "subscription_canceled_at": datetime.datetime.utcnow(),
                        "payment_status": "canceled"
                    }
                }
            )

            return JsonResponse({
                'message': 'Subscription canceled successfully',
                'subscription_id': subscription_id,
                'canceled_at': canceled_subscription.canceled_at,
                'status': 'canceled'
            })

        except stripe.error.InvalidRequestError as e:
            # Subscription might already be canceled or doesn't exist
            if 'No such subscription' in str(e):
                # Update database to reflect cancellation
                from bson import ObjectId
                import datetime
                
                user_collection.update_one(
                    {"username": username},
                    {
                        "$set": {
                            "subscription": "free",
                            "subscription_status": "canceled",
                            "subscription_canceled_at": datetime.datetime.utcnow(),
                            "payment_status": "canceled"
                        }
                    }
                )
                return JsonResponse({
                    'message': 'Subscription already canceled or not found',
                    'status': 'canceled'
                })
            else:
                raise e

    except stripe.error.StripeError as e:
        return JsonResponse({'message': f'Stripe error: {str(e)}'}, status=400)
    except Exception as e:
        return JsonResponse({'message': f'Error: {str(e)}'}, status=500)
