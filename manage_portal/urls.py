from django.urls import path
from . import views

app_name = 'manage'

urlpatterns = [
    path('login/', views.manage_login, name='login'),
    path('logout/', views.manage_logout, name='logout'),
    path('', views.dashboard, name='dashboard'),
    path('dashboard/', views.dashboard, name='dashboard'),

    # Products
    path('products/', views.products_list, name='products'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('products/<int:pk>/toggle/', views.product_toggle_status, name='product_toggle'),
    path('products/image/<int:pk>/delete/', views.delete_product_image, name='delete_product_image'),

    # Categories
    path('categories/', views.categories_list, name='categories'),
    path('categories/add/', views.category_add, name='category_add'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    path('categories/image/<int:pk>/delete/', views.delete_category_image, name='delete_category_image'),

    # Inventory
    path('inventory/', views.inventory, name='inventory'),
    path('inventory/<int:pk>/update/', views.inventory_update, name='inventory_update'),
    path('inventory/<int:pk>/toggle-tracking/', views.inventory_toggle_tracking, name='inventory_toggle_tracking'),
    path('export/inventory/', views.export_inventory, name='export_inventory'),

    # Orders
    path('orders/', views.orders_list, name='orders'),
    path('orders/<str:order_id>/', views.order_detail_manage, name='order_detail'),
    path('orders/<str:order_id>/resend-email/', views.resend_order_email, name='resend_order_email'),
    path('orders/<str:order_id>/invoice/', views.order_invoice, name='order_invoice'),
    path('orders/<str:order_id>/printing-invoice/', views.printing_invoice, name='printing_invoice'),
    path('orders/<str:order_id>/status/', views.order_update_status, name='order_status'),
    path('export/orders/', views.export_orders, name='export_orders'),
    path('delivered/', views.delivered_orders, name='delivered_orders'),
    path('cancelled/', views.cancelled_orders, name='cancelled_orders'),
    path('export/delivered/', views.export_delivered, name='export_delivered'),
    path('export/cancelled/', views.export_cancelled, name='export_cancelled'),

    # Coupons
    path('coupons/', views.coupons_list, name='coupons'),
    path('coupons/add/', views.coupon_add, name='coupon_add'),
    path('coupons/<int:pk>/delete/', views.coupon_delete, name='coupon_delete'),

    # Customers
    path('customers/', views.customers_list, name='customers'),
    path('customers/<int:pk>/block/', views.customer_block, name='customer_block'),
    path('export/customers/', views.export_customers, name='export_customers'),

    # Reviews
    path('reviews/', views.reviews_list, name='reviews'),
    path('reviews/add/', views.review_add, name='review_add'),
    path('reviews/<int:pk>/approve/', views.review_approve, name='review_approve'),
    path('reviews/<int:pk>/reject/', views.review_reject, name='review_reject'),
    path('reviews/<int:pk>/delete/', views.review_delete, name='review_delete'),
    path('reviews/<int:pk>/toggle-feature/', views.review_toggle_feature, name='review_toggle_feature'),

    # FAQs
    path('faqs/', views.faqs_list, name='faqs'),
    path('faqs/add/', views.faq_add, name='faq_add'),
    path('faqs/<int:pk>/edit/', views.faq_edit, name='faq_edit'),
    path('faqs/<int:pk>/delete/', views.faq_delete, name='faq_delete'),
    path('terms/', views.terms_list, name='terms'),
    path('terms/add/', views.terms_add, name='terms_add'),
    path('terms/<int:pk>/edit/', views.terms_edit, name='terms_edit'),
    path('terms/<int:pk>/delete/', views.terms_delete, name='terms_delete'),
    path('privacy/', views.privacy_list, name='privacy'),
    path('privacy/add/', views.privacy_add, name='privacy_add'),
    path('privacy/<int:pk>/edit/', views.privacy_edit, name='privacy_edit'),
    path('privacy/<int:pk>/delete/', views.privacy_delete, name='privacy_delete'),
    path('refund/', views.refund_list, name='refund'),
    path('refund/add/', views.refund_add, name='refund_add'),
    path('refund/<int:pk>/edit/', views.refund_edit, name='refund_edit'),
    path('refund/<int:pk>/delete/', views.refund_delete, name='refund_delete'),
    path('shipping/', views.shipping_list, name='shipping'),
    path('shipping/add/', views.shipping_add, name='shipping_add'),
    path('shipping/<int:pk>/edit/', views.shipping_edit, name='shipping_edit'),
    path('shipping/<int:pk>/delete/', views.shipping_delete, name='shipping_delete'),
    path('custom-order-policy/', views.custom_order_policy_list, name='custom_order_policy'),
    path('custom-order-policy/add/', views.custom_order_policy_add, name='custom_order_policy_add'),
    path('custom-order-policy/<int:pk>/edit/', views.custom_order_policy_edit, name='custom_order_policy_edit'),
    path('custom-order-policy/<int:pk>/delete/', views.custom_order_policy_delete, name='custom_order_policy_delete'),
    path('product-disclaimer/', views.product_disclaimer_list, name='product_disclaimer'),
    path('product-disclaimer/add/', views.product_disclaimer_add, name='product_disclaimer_add'),
    path('product-disclaimer/<int:pk>/edit/', views.product_disclaimer_edit, name='product_disclaimer_edit'),
    path('product-disclaimer/<int:pk>/delete/', views.product_disclaimer_delete, name='product_disclaimer_delete'),
    path('contact-info/', views.contact_info_edit, name='contact_info'),

    # Enquiries
    path('enquiries/', views.enquiries_list, name='enquiries'),
    path('enquiries/<int:pk>/status/', views.enquiry_update_status, name='enquiry_status'),
    path('enquiries/<int:pk>/delete/', views.enquiry_delete, name='enquiry_delete'),
    path('export/enquiries/', views.export_enquiries, name='export_enquiries'),
    path('customization-enquiries/', views.custom_enquiries_list, name='custom_enquiries'),
    path('export/customization-enquiries/', views.export_custom_enquiries, name='export_custom_enquiries'),

    # Banners
    path('banners/', views.banners_list, name='banners'),
    path('banners/add/', views.banner_add, name='banner_add'),
    path('banners/<int:pk>/edit/', views.banner_edit, name='banner_edit'),
    path('banners/<int:pk>/delete/', views.banner_delete, name='banner_delete'),
    path('banners/<int:pk>/toggle/', views.banner_toggle, name='banner_toggle'),
    path('banners/image/<int:pk>/delete/', views.banner_image_delete, name='banner_image_delete'),

    # About
    path('about-page/', views.about_page, name='about_page'),

    # Staff logins
    path('logins/', views.manage_logins, name='manage_logins'),
    path('logins/<int:pk>/delete/', views.staff_delete, name='staff_delete'),

    # Settings
    path('settings/', views.store_settings_view, name='settings'),
]
