"""
Extra auto-reply rules: run with python seed_chat_replies_extra.py
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'e_stores.settings')
django.setup()

from core.models import ChatAutoReply  # noqa: E402

RULES = [
    # ─── LOCATION / PHYSICAL STORE ───────────────────────────────────────────
    dict(
        category="general", priority=12, is_active=True,
        question="Physical Store Location",
        keywords=(
            "where are you located, do you have a physical store, physical store, "
            "your address, store address, shop address, office address, where is your shop, "
            "where is your store, can i come to your store, walk in, walk-in, "
            "can i pick up myself, self pickup, self collection, pickup location, "
            "where are you, what is your address, do you have an office, physical shop"
        ),
        response=(
            "We are primarily an online store, which allows us to offer you the best prices!\n\n"
            "However, self-pickup may be available in certain areas. "
            "Contact our support team to confirm if pickup is an option for your location.\n\n"
            "You can also reach us via the Contact Us page for our full address details."
        ),
    ),

    # ─── PAY ON DELIVERY ─────────────────────────────────────────────────────
    dict(
        category="payment", priority=16, is_active=True,
        question="Pay On Delivery / Cash On Delivery",
        keywords=(
            "pay on delivery, cash on delivery, cod, pay when delivered, pay at door, "
            "payment on delivery, pay when i receive, pay on arrival, pay cash, "
            "can i pay cash, i want to pay cash, i dont have a card, no card payment"
        ),
        response=(
            "Yes! We offer Pay on Delivery for select locations.\n\n"
            "- Available within Lagos and some major cities\n"
            "- A small cash handling fee may apply\n"
            "- You will be informed at checkout if POD is available for your area\n\n"
            "Simply select 'Pay on Delivery' as your payment method at checkout!"
        ),
    ),

    # ─── INTERNATIONAL / OUTSIDE NIGERIA DELIVERY ────────────────────────────
    dict(
        category="orders", priority=14, is_active=True,
        question="Delivery Outside Nigeria / International Shipping",
        keywords=(
            "outside nigeria, international shipping, international delivery, deliver abroad, "
            "ship to uk, ship to usa, ship to canada, ship to ghana, ship outside, "
            "deliver to diaspora, deliver overseas, do you ship internationally, "
            "can you deliver to, outside the country, foreign delivery, ship to other country"
        ),
        response=(
            "Currently we deliver within Nigeria only.\n\n"
            "We are working on expanding to international shipping in the near future. "
            "If you are in the diaspora and want to send a gift to someone in Nigeria, "
            "we can deliver to their Nigerian address — contact us and we will help arrange it!"
        ),
    ),

    # ─── HOW TO USE COUPON ───────────────────────────────────────────────────
    dict(
        category="payment", priority=13, is_active=True,
        question="How To Apply Coupon Code",
        keywords=(
            "how to use coupon, how to apply coupon, where to enter coupon, "
            "how to use promo code, how to apply promo code, where to put coupon, "
            "coupon not working, promo code not working, discount code not working, "
            "code not accepted, invalid coupon, coupon expired, code is not working"
        ),
        response=(
            "To apply your coupon or promo code:\n"
            "1. Add items to your cart\n"
            "2. Proceed to Checkout\n"
            "3. Look for the 'Coupon Code' or 'Discount Code' field\n"
            "4. Enter your code and click Apply\n"
            "5. The discount will be deducted from your total\n\n"
            "If your code is not working, it may have expired or already been used. "
            "Contact us and we will check it for you!"
        ),
    ),

    # ─── FORGOT ORDER NUMBER ─────────────────────────────────────────────────
    dict(
        category="orders", priority=15, is_active=True,
        question="Forgot Order Number",
        keywords=(
            "forgot order number, lost order number, dont have order number, "
            "i dont remember my order number, where is my order number, "
            "cant find order number, order number lost, misplaced order number, "
            "how to find order number, where do i find my order number"
        ),
        response=(
            "No worries! You can find your order number in a few ways:\n"
            "1. Check your email inbox for the order confirmation email we sent you\n"
            "2. Log in to your account and go to 'My Orders'\n"
            "3. Check your spam/junk folder if you cannot find the email\n\n"
            "If you still cannot find it, tell us your email address and name "
            "and we will look it up for you right away!"
        ),
    ),

    # ─── CHANGE DELIVERY ADDRESS AFTER ORDERING ──────────────────────────────
    dict(
        category="orders", priority=17, is_active=True,
        question="Change Delivery Address After Order Placed",
        keywords=(
            "change delivery address, update delivery address, wrong address, "
            "i entered wrong address, address is wrong, fix my address, "
            "change address after order, update my address, address correction, "
            "i made a mistake with address, wrong shipping address, incorrect address"
        ),
        response=(
            "Please contact us immediately if you need to change your delivery address!\n\n"
            "We can update it as long as your order has not yet been dispatched. "
            "Share your order number and the correct address and we will fix it right away.\n\n"
            "Act fast — orders are processed quickly!"
        ),
    ),

    # ─── BULK / WHOLESALE ORDERS ─────────────────────────────────────────────
    dict(
        category="orders", priority=11, is_active=True,
        question="Bulk / Wholesale Orders",
        keywords=(
            "bulk order, wholesale, buy in bulk, large order, order in quantity, "
            "corporate order, business order, bulk purchase, wholesale price, "
            "bulk discount, order many, buying wholesale, reseller, i want to resell"
        ),
        response=(
            "Great news — we welcome bulk and wholesale orders!\n\n"
            "For bulk orders we offer:\n"
            "- Special discounted pricing\n"
            "- Dedicated account management\n"
            "- Flexible delivery arrangements\n\n"
            "Please contact us directly via the Contact Us page or send us a message "
            "with the product name and quantity you need and we will get back to you with a quote!"
        ),
    ),

    # ─── RECEIPT / INVOICE ───────────────────────────────────────────────────
    dict(
        category="orders", priority=10, is_active=True,
        question="Receipt or Invoice",
        keywords=(
            "receipt, invoice, proof of purchase, order invoice, i need a receipt, "
            "can i get a receipt, send me receipt, order receipt, purchase receipt, "
            "official receipt, tax invoice, i need an invoice, invoice for my order"
        ),
        response=(
            "Your order confirmation email serves as your official receipt.\n\n"
            "If you need a formal invoice:\n"
            "1. Log in to your account and go to 'My Orders'\n"
            "2. Click on the order and look for 'Download Invoice'\n\n"
            "If you cannot find it, contact us with your order number and we will email your receipt to you."
        ),
    ),

    # ─── WHATSAPP / PHONE CONTACT ────────────────────────────────────────────
    dict(
        category="general", priority=13, is_active=True,
        question="WhatsApp or Phone Number",
        keywords=(
            "whatsapp, whatsapp number, phone number, call you, telephone, "
            "can i call, contact number, mobile number, what is your number, "
            "do you have whatsapp, your phone, your whatsapp, chat on whatsapp, "
            "send me your number, how to reach you, how can i contact you"
        ),
        response=(
            "You can reach us through the following channels:\n"
            "- Live Chat: Right here! We respond quickly\n"
            "- Contact Form: Visit our Contact Us page\n"
            "- Email: Check the Contact Us page for our email address\n\n"
            "Our support team is available Monday to Friday 8am–6pm and Saturday 9am–3pm. "
            "We will get back to you as fast as possible!"
        ),
    ),

    # ─── EMAIL ADDRESS ───────────────────────────────────────────────────────
    dict(
        category="general", priority=11, is_active=True,
        question="Email Address of Store",
        keywords=(
            "your email, email address, what is your email, store email, "
            "how do i email you, send you an email, contact email, "
            "email contact, support email, what email do i send to"
        ),
        response=(
            "You can find our official email address on the Contact Us page.\n\n"
            "Alternatively, send us a message right here and we will respond quickly — "
            "this chat is monitored by our support team during business hours!"
        ),
    ),

    # ─── DELIVERED BUT NOT RECEIVED ──────────────────────────────────────────
    dict(
        category="orders", priority=28, is_active=True,
        question="Marked Delivered But Not Received",
        keywords=(
            "says delivered but i didnt receive, marked as delivered but not received, "
            "order says delivered but i dont have it, delivered but missing, "
            "i never got my package, package not delivered, delivery marked complete but not received, "
            "shows delivered but not here, says delivered but nothing, parcel not received, "
            "i did not receive my order, order not received"
        ),
        response=(
            "We are so sorry to hear this! If your order is marked as delivered but you have not received it:\n\n"
            "1. Check with neighbours or your building's reception/gate\n"
            "2. Check if a delivery note was left indicating an alternative drop-off point\n"
            "3. Contact us immediately with your order number\n\n"
            "We will investigate with our logistics partner right away and resolve this for you. "
            "Rest assured — we will make sure you get your order!"
        ),
    ),

    # ─── GIFT CARDS ──────────────────────────────────────────────────────────
    dict(
        category="general", priority=9, is_active=True,
        question="Gift Cards",
        keywords=(
            "gift card, gift voucher, buy a gift, send as gift, gift someone, "
            "do you sell gift cards, can i buy a gift card, gift certificate, "
            "i want to gift someone, buy for someone as a gift"
        ),
        response=(
            "What a lovely idea!\n\n"
            "We currently don't offer gift cards but you can:\n"
            "- Place an order on behalf of someone and ship directly to their address\n"
            "- Contact us and we can help you arrange a gift order with a personalised note\n\n"
            "Gift card support is something we are looking to introduce soon — watch this space!"
        ),
    ),

    # ─── PRODUCT PRICE NEGOTIATION ───────────────────────────────────────────
    dict(
        category="products", priority=10, is_active=True,
        question="Can You Reduce Price / Negotiate",
        keywords=(
            "can you reduce the price, price too high, too expensive, can you lower price, "
            "negotiate price, discount on this item, can i get a discount, "
            "is price negotiable, price reduction, can you bring down price, price is high, "
            "any better price, best price, final price, give me discount"
        ),
        response=(
            "We always try to offer the best prices possible!\n\n"
            "Here are ways to save:\n"
            "- Check for active promo codes on our homepage\n"
            "- Subscribe to our newsletter for exclusive discounts\n"
            "- Look out for flash sales on social media\n"
            "- Free delivery on orders above \u20a620,000\n\n"
            "For bulk orders, we do offer special pricing — contact us with details!"
        ),
    ),

    # ─── PRODUCT NOT AS DESCRIBED ────────────────────────────────────────────
    dict(
        category="returns", priority=20, is_active=True,
        question="Product Not As Described",
        keywords=(
            "not as described, not what was shown, different from picture, "
            "looks different from photo, product is different, not matching description, "
            "misleading product, not what i expected, colour is different, size is different from listing, "
            "item is not what was advertised, misrepresented"
        ),
        response=(
            "We sincerely apologise if the product does not match its description or photos!\n\n"
            "Please take photos of what you received and contact us within 7 days. "
            "We will review it and offer you a full exchange or refund — no questions asked.\n\n"
            "Your trust matters to us and we will make this right."
        ),
    ),

    # ─── NEWSLETTER / EMAIL SUBSCRIPTION ─────────────────────────────────────
    dict(
        category="general", priority=7, is_active=True,
        question="Unsubscribe Newsletter",
        keywords=(
            "unsubscribe, stop email, too many emails, remove me from list, "
            "i dont want emails, cancel subscription, opt out, stop sending me emails, "
            "unsubscribe from newsletter, stop newsletter, too many notifications"
        ),
        response=(
            "We are sorry to see you go!\n\n"
            "To unsubscribe from our newsletter, scroll to the bottom of any email we sent you "
            "and click the 'Unsubscribe' link.\n\n"
            "You can also contact us directly and we will remove you from our mailing list immediately."
        ),
    ),

    # ─── ACCOUNT DELETION ────────────────────────────────────────────────────
    dict(
        category="account", priority=12, is_active=True,
        question="Delete My Account",
        keywords=(
            "delete account, remove my account, close account, deactivate account, "
            "i want to delete my account, how to delete account, delete my profile, "
            "remove my data, erase my account, account deletion"
        ),
        response=(
            "We are sorry to hear you want to leave!\n\n"
            "To delete your account, please contact our support team via the Contact Us page "
            "with your registered email address and your request.\n\n"
            "Please note: account deletion is permanent and cannot be undone. "
            "Any pending orders must be resolved before deletion."
        ),
    ),

    # ─── PRODUCT RECOMMENDATION ──────────────────────────────────────────────
    dict(
        category="products", priority=11, is_active=True,
        question="Product Recommendation / Help Choosing",
        keywords=(
            "help me choose, recommend a product, which one should i buy, "
            "what do you recommend, best product, most popular, top selling, "
            "which is better, help me pick, i need advice, can you suggest, "
            "what should i get, best option, advice on product"
        ),
        response=(
            "Happy to help you choose!\n\n"
            "Our most popular categories are listed on the shop page. "
            "You can also filter by category, price, and ratings to find the best match for you.\n\n"
            "Tell us what you are looking for — your budget, preferred style, or purpose — "
            "and our team will personally recommend the best options for you!"
        ),
    ),

    # ─── PRIVACY / DATA ──────────────────────────────────────────────────────
    dict(
        category="general", priority=8, is_active=True,
        question="Privacy / Is My Data Safe",
        keywords=(
            "privacy policy, my data, is my data safe, personal information, "
            "data protection, what do you do with my data, data privacy, "
            "gdpr, data security, you selling my data, who has my information"
        ),
        response=(
            "Your privacy is very important to us.\n\n"
            "We do not sell, share, or misuse your personal data. "
            "Your information is used only to process orders and improve your experience with us.\n\n"
            "You can read our full Privacy Policy at the bottom of our website."
        ),
    ),
]

created = 0
for r in RULES:
    _, made = ChatAutoReply.objects.get_or_create(question=r["question"], defaults=r)
    if made:
        created += 1
        print(f"  + {r['question']}")
    else:
        print(f"  ~ already exists: {r['question']}")

print(f"\nDone: {created} new rules added out of {len(RULES)} total.")
