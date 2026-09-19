from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render

from quotes.forms import QUOTE_STATUS_LABELS
from .models import Customer


@login_required
def customer_list(request):
    search = request.GET.get("q", "").strip()[:200]
    customers = Customer.objects.annotate(offer_count=Count("quotes"))
    for term in search.split():
        customers = customers.filter(
            Q(first_name__icontains=term) | Q(last_name__icontains=term)
            | Q(full_name_latin__icontains=term) | Q(email__icontains=term)
            | Q(phone_1__icontains=term) | Q(phone_2__icontains=term)
            | Q(phone_3__icontains=term)
        )
    page = Paginator(customers.order_by("first_name", "last_name", "pk"), 25).get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "customers/list.html", {
        "page_obj": page, "search": search, "filter_query": query.urlencode(),
        "active_menu": "customers",
    })


@login_required
def customer_detail(request, customer_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    page = Paginator(customer.quotes.order_by("-created_at", "-pk"), 25).get_page(request.GET.get("page"))
    for quote in page:
        quote.status_label = QUOTE_STATUS_LABELS.get(quote.status, quote.status)
    return render(request, "customers/detail.html", {
        "customer": customer, "page_obj": page, "active_menu": "customers",
    })
