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
