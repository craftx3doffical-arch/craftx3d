from store.models import Order, Review, Enquiry


def manage_sidebar_counts(request):
    """Inject sidebar badge counts for manage portal pages."""
    if not request.path.startswith('/manage/') or not request.session.get('staff_id'):
        return {}
    try:
        return {
            'pending_orders_count': Order.objects.filter(payment_status='paid', status='pending').count(),
            'pending_reviews_count': Review.objects.filter(status=Review.STATUS_PENDING).count(),
            'new_enquiries_count': Enquiry.objects.filter(status='new', enquiry_type='general').count(),
            'new_custom_enquiries_count': Enquiry.objects.filter(status='new', enquiry_type='customization').count(),
        }
    except Exception:
        return {}
