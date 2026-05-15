from django import forms
from .models import Product, ProductReview


class ProductReviewForm(forms.ModelForm):
    class Meta:
        model = ProductReview
        fields = ['rating', 'title', 'review_text']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f'{i}★') for i in range(1, 6)]),
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Summarize your review'
            }),
            'review_text': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Share your experience with this product',
                'rows': 4
            })
        }
        labels = {
            'rating': 'Your Rating',
            'title': 'Review Title',
            'review_text': 'Your Review'
        }


class ProductForm(forms.ModelForm):
    image1 = forms.FileField(
        widget=forms.ClearableFileInput(),
        required=False,
        label="Product Image 1"
    )
    image2 = forms.FileField(
        widget=forms.ClearableFileInput(),
        required=False,
        label="Product Image 2"
    )
    image3 = forms.FileField(
        widget=forms.ClearableFileInput(),
        required=False,
        label="Product Image 3"
    )

    class Meta:
        model = Product
        fields = ['name', 'description', 'price', 'stock', 'reorder_level', 'category', 'image', 'is_editable']


class BulkProductForm(forms.Form):
    """Single product row used inside the bulk-add formset."""
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Product name'}),
    )
    description = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description'}),
    )
    price = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00', 'step': '0.01'}),
    )
    stock = forms.IntegerField(
        min_value=0, initial=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'}),
    )
    reorder_level = forms.IntegerField(
        min_value=0, initial=5, required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '5'}),
    )
    image = forms.ImageField(
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
    )
