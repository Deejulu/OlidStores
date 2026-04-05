"""
One-time seed script: populate ChatAutoReply with 28 comprehensive bot rules.
Run with: python seed_chat_replies.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from core.models import ChatAutoReply  # noqa: E402

RULES = [
    # ─── GREETINGS ───────────────────────────────────────────────────────────
    dict(
        category="general", priority=5, is_active=True,
        question="Greeting - Hello Hi Hey",
        keywords="hello, hi, hey, hii, heyy, hello there, hi there, hey there, howdy, greetings, good day, wassup, sup, yo, hola, ello, helo, helloo, hihi",
        response="Hello! Welcome to our store! How can I help you today?",
    ),
    dict(
        category="general", priority=6, is_active=True,
        question="Greeting - Good Morning",
        keywords="good morning, gm, morning, mornin, gud morning, good morn, morning sir, morning ma",
        response="Good morning! Hope you have a wonderful day. How can I assist you?",
    ),
    dict(
        category="general", priority=6, is_active=True,
        question="Greeting - Good Afternoon",
        keywords="good afternoon, afternoon, good after, gud afternoon, aftn, afternoon sir, afternoon ma",
        response="Good afternoon! Thanks for reaching out. How can I help you today?",
    ),
    dict(
        category="general", priority=6, is_active=True,
        question="Greeting - Good Evening",
        keywords="good evening, evening, good eve, gud evening, evening sir, evening ma, good evning",
        response="Good evening! Thanks for reaching out. How can I assist you today?",
    ),
    dict(
        category="general", priority=5, is_active=True,
        question="How Are You",
        keywords=(
            "how are you, how are u, how r you, how r u, hows it going, how is it going, "
            "how have you been, you good, are you good, how do you do, hope you are well, "
            "how you doing, how u doing, wassup with you, how far"
        ),
        response="I am doing great, thank you for asking! I am here and ready to help you. What can I do for you today?",
    ),
    dict(
        category="general", priority=5, is_active=True,
        question="Farewell - Bye Goodbye",
        keywords=(
            "bye, goodbye, bye bye, see you, see ya, take care, cya, later, "
            "good night, goodnight, ttyl, talk later, have a good day, bye for now, good nite, nite nite"
        ),
        response="Goodbye! Thank you for chatting with us. Have a wonderful day! Feel free to come back anytime.",
    ),
    dict(
        category="general", priority=5, is_active=True,
        question="Thank You",
        keywords=(
            "thank you, thanks, thank u, thankyou, thx, ty, much appreciated, "
            "appreciate it, thanks a lot, thanks so much, thank you so much, many thanks, "
            "cheers, thank u so much, i appreciate, big thanks"
        ),
        response="You are very welcome! It is our pleasure to assist you. Is there anything else I can help you with?",
    ),
    dict(
        category="general", priority=3, is_active=True,
        question="Acknowledgment - OK Sure Noted",
        keywords=(
            "ok, okay, alright, got it, understood, noted, i see, i understand, "
            "makes sense, sure, sounds good, cool, great, perfect, nice, no worries, "
            "that is fine, ok thanks, okay thanks"
        ),
        response="Great! Let me know if you need anything else. We are always here to help.",
    ),

    # ─── ORDERS & DELIVERY ───────────────────────────────────────────────────
    dict(
        category="orders", priority=20, is_active=True,
        question="Where Is My Order / Order Tracking",
        keywords=(
            "where is my order, track my order, order tracking, where is my package, "
            "order status, check my order, track order, my order, order update, "
            "has my order shipped, did my order ship, when will my order arrive, "
            "order not arrived, order not delivered, where my order, "
            "i have not received my order, order taking too long"
        ),
        response=(
            "To track your order, go to your account and click 'My Orders' to see the latest status.\n"
            "If you have your order number handy, share it here and our team will look it up for you right away!"
        ),
    ),
    dict(
        category="orders", priority=18, is_active=True,
        question="How Long Does Delivery Take",
        keywords=(
            "delivery time, how long delivery, when will it arrive, how long does shipping take, "
            "delivery days, how many days delivery, how long will it take, when will i receive, "
            "when will i get my order, estimated delivery, expected delivery, delivery duration, "
            "how long shipping, delivery how long, fast delivery, quick delivery"
        ),
        response=(
            "Standard delivery typically takes 3 to 5 business days within Lagos "
            "and 5 to 7 business days for other states.\n"
            "You will receive a tracking number via email once your order ships. "
            "Express delivery is also available at checkout!"
        ),
    ),
    dict(
        category="orders", priority=17, is_active=True,
        question="Cancel My Order",
        keywords=(
            "cancel order, cancel my order, i want to cancel, how to cancel, "
            "order cancellation, stop my order, undo order, reverse order, "
            "cancel purchase, how do i cancel, i need to cancel, please cancel my order"
        ),
        response=(
            "You can cancel your order within 1 hour of placing it. "
            "Go to 'My Orders' in your account and click 'Cancel Order'.\n"
            "After 1 hour the order may already be in processing — "
            "contact us immediately and we will do our best to help you!"
        ),
    ),
    dict(
        category="orders", priority=16, is_active=True,
        question="Modify or Change Order",
        keywords=(
            "change order, modify order, edit order, update order, ordered wrong item, "
            "wrong size, wrong colour, wrong color, wrong address, change delivery address, "
            "update address, change my order, i made a mistake on my order"
        ),
        response=(
            "To modify your order, please contact us as soon as possible since orders are processed quickly.\n"
            "If your order has not shipped yet, we can make changes for you. "
            "Share your order number and we will sort it out!"
        ),
    ),
    dict(
        category="orders", priority=22, is_active=True,
        question="Received Wrong Item",
        keywords=(
            "wrong item, received wrong, wrong product, not what i ordered, "
            "different from what i ordered, got wrong item, sent wrong item, "
            "incorrect item, wrong thing, they sent me wrong, this is not what i ordered"
        ),
        response=(
            "We sincerely apologise for sending the wrong item!\n"
            "Please take a photo of what you received and contact our support team. "
            "We will arrange a free exchange and correct delivery right away at no extra cost to you."
        ),
    ),
    dict(
        category="orders", priority=22, is_active=True,
        question="Damaged or Defective Item",
        keywords=(
            "damaged order, broken item, item damaged, damaged product, package damaged, "
            "arrived broken, came broken, defective, not working, faulty, "
            "item not working, product broken, received damaged, item is damaged"
        ),
        response=(
            "We are so sorry your item arrived damaged!\n"
            "Please take clear photos of the damage and send them to our support. "
            "We will replace it or issue a full refund immediately. Your satisfaction is our priority!"
        ),
    ),
    dict(
        category="orders", priority=13, is_active=True,
        question="How To Place An Order",
        keywords=(
            "how to order, how to buy, how do i order, how to place order, ordering process, "
            "steps to order, how do i buy, how to purchase, place an order, how do i purchase, "
            "buying process, i want to buy"
        ),
        response=(
            "Placing an order is simple!\n"
            "1. Browse our products and click Add to Cart\n"
            "2. Review your cart and click Checkout\n"
            "3. Enter your delivery address\n"
            "4. Choose your payment method and complete payment\n"
            "5. You will receive an order confirmation email instantly!\n\n"
            "Need help? We are here every step of the way."
        ),
    ),

    # ─── PAYMENT ─────────────────────────────────────────────────────────────
    dict(
        category="payment", priority=15, is_active=True,
        question="Payment Methods Accepted",
        keywords=(
            "payment methods, how to pay, ways to pay, accepted payment, do you accept card, "
            "can i pay with, payment options, how can i pay, bank transfer, card payment, "
            "pay online, paystack, pay on delivery, cash on delivery, what payment, which payment"
        ),
        response=(
            "We accept the following payment methods:\n"
            "- Debit/Credit Cards (Visa, Mastercard, Verve)\n"
            "- Bank Transfer\n"
            "- Paystack secure online checkout\n"
            "- Pay on Delivery (available in select areas)\n\n"
            "All online payments are 100% secure and encrypted."
        ),
    ),
    dict(
        category="payment", priority=20, is_active=True,
        question="Payment Failed",
        keywords=(
            "payment failed, payment not successful, transaction failed, payment declined, "
            "card declined, my payment failed, payment error, unable to pay, payment issue, "
            "payment unsuccessful, payment not going through, payment problem, "
            "transaction not successful, cant pay"
        ),
        response=(
            "Sorry about that! If your payment failed, please try:\n"
            "1. Double-check your card details\n"
            "2. Ensure your card is enabled for online transactions\n"
            "3. Try a different payment method\n"
            "4. Contact your bank if the error persists\n\n"
            "If you were charged but got no order confirmation, contact us immediately with your transaction reference!"
        ),
    ),
    dict(
        category="payment", priority=25, is_active=True,
        question="Charged But No Order Confirmation",
        keywords=(
            "charged but no order, money deducted no order, payment taken but no order, "
            "debited but no order, money gone but no order, paid but order not placed, "
            "charged twice, double charge, duplicate charge, money left account no order, "
            "i was charged but no order"
        ),
        response=(
            "Please do not panic! If you were charged but did not receive an order confirmation, "
            "it usually reverses automatically within 24 to 48 hours.\n\n"
            "However, please contact us immediately with your transaction reference and "
            "we will investigate and resolve it as a top priority."
        ),
    ),
    dict(
        category="payment", priority=12, is_active=True,
        question="Is Payment Secure",
        keywords=(
            "is payment safe, is it safe to pay, safe to enter card, secure payment, "
            "is the website safe, is my card safe, payment security, is this site safe, "
            "can i trust this site, is it legit"
        ),
        response=(
            "Absolutely! All payments are processed through Paystack, "
            "a fully PCI-DSS compliant payment gateway.\n"
            "Your card details are never stored on our servers. "
            "Shopping with us is 100% safe and secure."
        ),
    ),

    # ─── RETURNS & REFUNDS ───────────────────────────────────────────────────
    dict(
        category="returns", priority=18, is_active=True,
        question="Return Policy",
        keywords=(
            "return policy, return item, how to return, can i return, return product, "
            "returns, send back, i want to return, return process, return request, "
            "returning an item, how do i return, what is your return policy"
        ),
        response=(
            "We have a 7-day return policy.\n\n"
            "To return an item:\n"
            "1. Contact us within 7 days of delivery\n"
            "2. Item must be unused and in original packaging\n"
            "3. We will arrange a pickup from your address\n\n"
            "Note: Some items (e.g. personal care products) are non-returnable for hygiene reasons."
        ),
    ),
    dict(
        category="returns", priority=18, is_active=True,
        question="Refund - When and How",
        keywords=(
            "refund, get my money back, money back, when will i get refund, refund policy, "
            "how long refund, refund time, refund status, when will i be refunded, "
            "when is my refund coming, want a refund, i want my money back"
        ),
        response=(
            "Refunds are processed within 3 to 7 business days after we receive and inspect your returned item.\n"
            "The money will be returned to your original payment method. "
            "You will receive an email confirmation once your refund is processed."
        ),
    ),
    dict(
        category="returns", priority=15, is_active=True,
        question="Exchange Item",
        keywords=(
            "exchange, swap, change product, exchange item, change size, exchange size, "
            "swap product, different size, want different color, change color, "
            "want to swap, exchange for another"
        ),
        response=(
            "Yes, we offer exchanges! You can exchange an item within 7 days of delivery "
            "for a different size, colour, or product (subject to availability).\n"
            "Contact us with your order number and we will guide you through the exchange process."
        ),
    ),

    # ─── PRODUCTS & STOCK ────────────────────────────────────────────────────
    dict(
        category="products", priority=14, is_active=True,
        question="Product Availability / In Stock",
        keywords=(
            "in stock, available, is it available, do you have, out of stock, "
            "when will it be back, back in stock, restock, restocking, product available, "
            "when available, will it come back, sold out, is this available, is it in stock"
        ),
        response=(
            "You can check real-time stock availability on the product page.\n"
            "If an item shows Out of Stock:\n"
            "- Contact us to be notified when it is back in stock\n"
            "- Check back in a few days as we restock regularly\n"
            "- Browse similar items in the same category"
        ),
    ),
    dict(
        category="products", priority=13, is_active=True,
        question="What Sizes Are Available",
        keywords=(
            "sizes available, what sizes, size guide, which sizes, size chart, "
            "do you have my size, size options, available sizes, size range, what size, sizing"
        ),
        response=(
            "Available sizes are listed on each product page. We typically stock sizes XS to 3XL.\n"
            "If you are unsure about sizing, check our Size Guide on the product page "
            "or contact us — we are happy to help you pick the right fit!"
        ),
    ),
    dict(
        category="products", priority=14, is_active=True,
        question="Product Quality / Authenticity",
        keywords=(
            "is it original, is it authentic, product quality, is it fake, "
            "are products genuine, original products, quality of products, "
            "real or fake, is it real, are they original"
        ),
        response=(
            "All our products are 100% genuine and authentic.\n"
            "We source directly from verified manufacturers and trusted suppliers. "
            "Customer satisfaction and product quality are our top priorities."
        ),
    ),

    # ─── ACCOUNT ─────────────────────────────────────────────────────────────
    dict(
        category="account", priority=15, is_active=True,
        question="Forgot Password / Reset Password",
        keywords=(
            "forgot password, reset password, cant login, cannot login, lost password, "
            "password reset, change password, update password, i forgot my password, "
            "how to reset password, password help, login problem, cant log in"
        ),
        response=(
            "To reset your password:\n"
            "1. Click 'Forgot Password' on the login page\n"
            "2. Enter your email address\n"
            "3. Check your email for a reset link (also check your spam folder)\n"
            "4. Click the link and create a new password\n\n"
            "If you still have issues, contact us and we will help you get back in!"
        ),
    ),
    dict(
        category="account", priority=13, is_active=True,
        question="How To Create An Account",
        keywords=(
            "create account, register, sign up, make account, how to register, "
            "open account, new account, how do i sign up, how to create, registration, "
            "how to make account"
        ),
        response=(
            "Creating an account is easy and free!\n"
            "1. Click 'Sign Up' at the top of the page\n"
            "2. Fill in your name, email, and password\n"
            "3. Verify your email address\n"
            "4. You are ready to shop!\n\n"
            "Having an account lets you track orders, save wishlist items, and checkout faster."
        ),
    ),

    # ─── GENERAL / SUPPORT ───────────────────────────────────────────────────
    dict(
        category="general", priority=30, is_active=True,
        question="Contact Support / Speak To Human",
        keywords=(
            "contact support, speak to agent, speak to human, speak to someone, contact us, "
            "talk to someone, real person, human agent, customer service, customer care, "
            "support team, speak with agent, connect me to agent, i want to speak, "
            "talk to a person, i need help from a person"
        ),
        response=(
            "You would like to speak with our team — we would love to help!\n\n"
            "Our support team is available:\n"
            "- Monday to Friday: 8am to 6pm\n"
            "- Saturday: 9am to 3pm\n\n"
            "You can also send a message via the Contact Us page and we will respond within a few hours. "
            "What is your concern? We are listening!"
        ),
    ),
    dict(
        category="general", priority=10, is_active=True,
        question="Store Opening Hours",
        keywords=(
            "opening hours, business hours, working hours, when are you open, "
            "what time do you open, what time do you close, are you open, store hours, "
            "shop hours, hours of operation, when do you work, when can i reach you"
        ),
        response=(
            "Our support team is available:\n"
            "- Monday to Friday: 8am to 6pm\n"
            "- Saturday: 9am to 3pm\n"
            "- Sunday: Closed\n\n"
            "You can still browse and place orders 24/7 on our website!"
        ),
    ),
    dict(
        category="general", priority=25, is_active=True,
        question="Complaint or Bad Experience",
        keywords=(
            "complaint, complain, not happy, unhappy, disappointed, bad service, "
            "bad experience, terrible, awful, very bad, this is bad, frustrated, angry, "
            "upset, not satisfied, not good, this is rubbish, this is terrible, poor service"
        ),
        response=(
            "We are genuinely sorry to hear about your experience and we sincerely apologise.\n"
            "Your satisfaction is our top priority. Please tell us exactly what happened and "
            "a senior member of our team will personally attend to your issue and make it right. "
            "We truly value you as our customer."
        ),
    ),
    dict(
        category="general", priority=12, is_active=True,
        question="Discount Coupon Promo Code",
        keywords=(
            "coupon, discount code, promo code, voucher, discount, promo, have a code, "
            "use code, apply code, any discount, any promo, any coupon, sale, offers, "
            "how to get discount, is there a discount, any deals"
        ),
        response=(
            "We regularly run promotions and discounts!\n"
            "- Subscribe to our newsletter for exclusive offers\n"
            "- Follow us on social media for flash sales\n"
            "- Check the homepage banners for active promotions\n\n"
            "If you have a promo code, enter it at checkout in the 'Coupon Code' field."
        ),
    ),
    dict(
        category="general", priority=14, is_active=True,
        question="Delivery Fee / Free Shipping",
        keywords=(
            "free delivery, free shipping, minimum order, how much for free delivery, "
            "delivery fee, shipping fee, how much is delivery, delivery cost, shipping cost, "
            "how much to deliver, cost of delivery, what is delivery fee, is delivery free"
        ),
        response=(
            "Delivery fees vary by location:\n"
            "- Lagos: starts from \u20a61,500\n"
            "- Other States: \u20a62,500 to \u20a64,000\n\n"
            "Enjoy FREE delivery on orders above \u20a620,000 within Lagos! "
            "Your exact delivery fee is shown clearly at checkout."
        ),
    ),
]

created = 0
for r in RULES:
    _, made = ChatAutoReply.objects.get_or_create(question=r["question"], defaults=r)
    if made:
        created += 1
        print(f"  + {r['question']}")

print(f"\nDone: {created} new rules created out of {len(RULES)} total.")
