from .forms import FeedbackForm
from .models import Feedback
from django.contrib import messages
def feedback_view(request):
	if request.method == 'POST':
		form = FeedbackForm(request.POST)
		if form.is_valid():
			feedback = form.save(commit=False)
			if request.user.is_authenticated:
				feedback.user = request.user
			feedback.save()
			messages.success(request, 'Thank you for your feedback!')
			return redirect('users:feedback')
	else:
		form = FeedbackForm()
	return render(request, 'users/feedback.html', {'form': form})
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.forms import UserCreationForm
from users.models_notification import Notification
from django.db import models
from django.core.paginator import Paginator

@login_required
@require_POST
def mark_notification_read(request, pk):
	Notification.objects.filter(pk=pk, user=request.user, is_read=False).update(is_read=True)
	return redirect('users:notifications')

@login_required
def notifications_view(request):
	notifications = Notification.objects.filter(
		models.Q(user=request.user) | models.Q(user__isnull=True)
	).order_by('-created_at')[:30]
	return render(request, 'users/notifications.html', {'notifications': notifications})
from django.contrib.auth import login
from orders.models import Order
from users.models import Wishlist
from products.models import Product
from django.contrib import messages
from users.models_activity import Activity
@login_required
def activity_view(request):
	activities = Activity.objects.filter(user=request.user).order_by('-timestamp')[:20]
	return render(request, 'users/activity.html', {'activities': activities})

def is_customer(user):
	return user.is_authenticated and getattr(user, 'role', None) == 'customer'

@login_required
def customer_dashboard(request):
	if not request.user.is_authenticated:
		return redirect('users:login')
	# Always treat staff users with role 'customer' as customers
	if getattr(request.user, 'role', None) == 'customer':
		from orders.models import Order
		from users.models import Wishlist
		from users.models_notification import Notification
		from users.models import Address

		order_count = Order.objects.filter(user=request.user).count()
		recent_orders = Order.objects.filter(user=request.user).order_by('-created_at')[:3]
		wishlist_count = 0
		if hasattr(request.user, 'wishlist'):
			wishlist_count = request.user.wishlist.products.count()
		unread_notifications = Notification.objects.filter(user=request.user, is_read=False).count()
		address_count = Address.objects.filter(user=request.user).count()

		return render(request, 'users/dashboard.html', {
			'order_count': order_count,
			'recent_orders': recent_orders,
			'wishlist_count': wishlist_count,
			'unread_notifications': unread_notifications,
			'address_count': address_count,
		})
	elif getattr(request.user, 'role', None) == 'admin':
		return redirect('admin_dashboard:dashboard_home')
	return redirect('core:home')

@login_required
def profile(request):
    # Admins get their own profile page inside the admin dashboard
    if getattr(request.user, 'role', None) == 'admin':
        return redirect('admin_dashboard:admin_profile')

    from users.models import Profile
    from users.forms import ProfileEditForm
    from orders.models import Order
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileEditForm(request.POST, request.FILES)
        if form.is_valid():
            u = request.user
            # Check email uniqueness (exclude self)
            new_email = form.cleaned_data['email']
            from django.contrib.auth import get_user_model
            User = get_user_model()
            if User.objects.filter(email__iexact=new_email).exclude(pk=u.pk).exists():
                messages.error(request, 'That email address is already in use by another account.')
            else:
                u.first_name = form.cleaned_data.get('first_name', '')
                u.last_name = form.cleaned_data.get('last_name', '')
                u.email = new_email
                u.phone = form.cleaned_data.get('phone', '')
                u.save()
                profile_obj.address = form.cleaned_data.get('address', '')
                if form.cleaned_data.get('avatar'):
                    profile_obj.avatar = form.cleaned_data['avatar']
                profile_obj.save()
                messages.success(request, 'Profile updated successfully!')
                return redirect('users:profile')
    else:
        form = ProfileEditForm(initial={
            'first_name': request.user.first_name,
            'last_name': request.user.last_name,
            'email': request.user.email,
            'phone': request.user.phone,
            'address': profile_obj.address,
        })

    order_count = Order.objects.filter(user=request.user).count()
    wishlist_count = 0
    if hasattr(request.user, 'wishlist'):
        wishlist_count = request.user.wishlist.products.count()

    return render(request, 'users/profile.html', {
        'form': form,
        'profile': profile_obj,
        'order_count': order_count,
        'wishlist_count': wishlist_count,
    })

@login_required
def order_history(request):
    order_list = Order.objects.filter(user=request.user).order_by('-created_at')
    paginator = Paginator(order_list, 10)  # Show 10 orders per page
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)
    return render(request, 'users/order_history.html', {'orders': orders})

@login_required
def wishlist_view(request):
    wishlist = None
    if hasattr(request.user, 'wishlist'):
        wishlist = request.user.wishlist.products.all()
    return render(request, 'users/wishlist.html', {'wishlist': wishlist})

@login_required
def wishlist_add_view(request):
	if request.method == 'POST':
		product_id = request.POST.get('product_id')
		product = get_object_or_404(Product, id=product_id)
		wishlist, created = Wishlist.objects.get_or_create(user=request.user)
		wishlist.products.add(product)
		# Track wishlist add activity
		user = request.user
		if user.is_authenticated:
			try:
				from users.models_activity import Activity
				Activity.objects.create(user=user, activity_type='wishlist_add', product=product)
			except Exception:
				pass
		
		success_message = f"'{product.name}' saved to wishlist."
		messages.success(request, success_message)
		
		# Return JSON for AJAX requests
		if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
			from django.http import JsonResponse
			return JsonResponse({'success': True, 'message': success_message})
		
		return redirect(request.META.get('HTTP_REFERER', 'products:shop'))
	return redirect('products:shop')

@login_required
def wishlist_remove_view(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        product = get_object_or_404(Product, id=product_id)
        wishlist, created = Wishlist.objects.get_or_create(user=request.user)
        wishlist.products.remove(product)
        
        info_message = f"'{product.name}' removed from wishlist."
        messages.info(request, info_message)
        
        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            from django.http import JsonResponse
            return JsonResponse({'success': True, 'message': info_message})
        
        return redirect(request.META.get('HTTP_REFERER', 'users:wishlist'))
    return redirect('users:wishlist')

from django.http import HttpResponse
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib import messages

def test_users(request):
	return HttpResponse('Users app is working!')

from .forms import EmailOrUsernameAuthenticationForm

class UserLoginView(LoginView):
	template_name = 'users/login.html'
	authentication_form = EmailOrUsernameAuthenticationForm

class UserLogoutView(LogoutView):
	template_name = 'users/logout.html'

def signup(request):
	from .forms import CustomUserCreationForm
	if request.method == 'POST':
		form = CustomUserCreationForm(request.POST)
		if form.is_valid():
			user = form.save()
			login(request, user)
			return redirect('core:home')
	else:
		form = CustomUserCreationForm()
	return render(request, 'users/signup.html', {'form': form})

from django.contrib.auth.views import PasswordChangeView
from django.urls import reverse_lazy

class CustomPasswordChangeView(PasswordChangeView):
	template_name = 'users/change_password.html'
	success_url = reverse_lazy('users:profile')

	def form_valid(self, form):
		messages.success(self.request, 'Your password has been updated successfully!')
		return super().form_valid(form)


@login_required
def addresses_view(request):
	from .models import Address
	from .forms import AddressForm
	addresses = Address.objects.filter(user=request.user).order_by('-is_default', 'id')
	if request.method == 'POST':
		form = AddressForm(request.POST)
		if form.is_valid():
			address = form.save(commit=False)
			address.user = request.user
			# If this is set as default, unset all others first
			if address.is_default:
				Address.objects.filter(user=request.user).update(is_default=False)
			# If this is the first address, auto-set as default
			elif not addresses.exists():
				address.is_default = True
			address.save()
			messages.success(request, 'Address added successfully!')
			return redirect('users:addresses')
	else:
		form = AddressForm()
	return render(request, 'users/addresses.html', {'addresses': addresses, 'form': form})


@login_required
def address_edit_view(request, pk):
	from .models import Address
	from .forms import AddressForm
	address = get_object_or_404(Address, pk=pk, user=request.user)
	if request.method == 'POST':
		form = AddressForm(request.POST, instance=address)
		if form.is_valid():
			updated = form.save(commit=False)
			if updated.is_default:
				Address.objects.filter(user=request.user).exclude(pk=pk).update(is_default=False)
			updated.save()
			messages.success(request, 'Address updated successfully!')
			return redirect('users:addresses')
	else:
		form = AddressForm(instance=address)
	return render(request, 'users/addresses.html', {
		'addresses': Address.objects.filter(user=request.user).order_by('-is_default', 'id'),
		'form': form,
		'editing': address,
	})


@login_required
def address_delete_view(request, pk):
	from .models import Address
	address = get_object_or_404(Address, pk=pk, user=request.user)
	if request.method == 'POST':
		was_default = address.is_default
		address.delete()
		# Promote the first remaining address to default
		if was_default:
			first = Address.objects.filter(user=request.user).first()
			if first:
				first.is_default = True
				first.save()
		messages.success(request, 'Address removed.')
	return redirect('users:addresses')
