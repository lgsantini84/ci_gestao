# app/utils/pagination.py
from flask import request, url_for
from math import ceil

class Pagination:
    def __init__(self, page, per_page, total_count):
        self.page = page
        self.per_page = per_page
        self.total_count = total_count

    @property
    def pages(self):
        return int(ceil(self.total_count / float(self.per_page)))

    @property
    def has_prev(self):
        return self.page > 1

    @property
    def has_next(self):
        return self.page < self.pages

    @property
    def prev_num(self):
        return self.page - 1

    @property
    def next_num(self):
        return self.page + 1

    @property
    def offset(self):
        return (self.page - 1) * self.per_page

    def iter_pages(self, left_edge=2, left_current=2,
                   right_current=5, right_edge=2):
        last = 0
        for num in range(1, self.pages + 1):
            if num <= left_edge or \
               (num > self.page - left_current - 1 and 
                num < self.page + right_current) or \
               num > self.pages - right_edge:
                if last + 1 != num:
                    yield None
                yield num
                last = num

def paginate_query(query, per_page=50):
    """Helper function to paginate SQLAlchemy queries."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', per_page, type=int)
    
    # Validate page and per_page
    page = max(1, page)
    per_page = max(1, min(per_page, 500))  # Max 500 per page
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    items = query.limit(per_page).offset((page - 1) * per_page).all()
    
    # Create pagination object
    pagination = Pagination(page, per_page, total)
    
    return items, pagination